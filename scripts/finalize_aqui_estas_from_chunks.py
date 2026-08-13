from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

from app.config import load_channel
from app.music_video import _get_real_segment
from app.youtube import upload_long_video
from scripts.render_aqui_estas_demianvelo import FINAL_DIR, LYRICS, TITLE, make_thumbnail, media_duration

CHUNK_NAMES = [
    "aqui_estas_045.wav",
    "aqui_estas_090.wav",
    "aqui_estas_135.wav",
    "aqui_estas_180.wav",
    "aqui_estas_225.wav",
    "Aqui_Estas_x_DemianVelo.wav",
]

VISUAL_QUERIES = [
    "sunrise mountain",
    "ocean waves sunset",
    "city night lights",
    "open road landscape",
    "church architecture sunlight",
    "dramatic clouds sky",
    "forest sunlight",
    "mountain lake sunrise",
    "piano performance hands",
    "sunset silhouette landscape",
]

GENERIC_FALLBACKS = [
    "nature landscape",
    "mountain",
    "ocean",
    "city",
    "sky clouds",
    "forest",
]


def run(cmd: list[str]) -> None:
    print("RUN", " ".join(cmd))
    subprocess.run(cmd, check=True)


def join_chunks(chunks_dir: Path, out: Path) -> Path:
    chunks = [chunks_dir / name for name in CHUNK_NAMES]
    for chunk in chunks:
        if not chunk.exists() or chunk.stat().st_size < 100_000:
            raise RuntimeError(f"Falta un tramo ACE-Step valido: {chunk}")
        duration = media_duration(chunk)
        if not 35 <= duration <= 70:
            raise RuntimeError(f"Tramo fuera de rango: {chunk.name} = {duration:.2f}s")

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for chunk in chunks:
        cmd += ["-i", str(chunk)]

    # Very short crossfades hide extension boundaries while retaining the original ACE-Step mix.
    filters = ["[0:a][1:a]acrossfade=d=0.35:c1=tri:c2=tri[a1]"]
    previous = "a1"
    for idx in range(2, len(chunks)):
        current = f"a{idx}"
        filters.append(f"[{previous}][{idx}:a]acrossfade=d=0.35:c1=tri:c2=tri[{current}]")
        previous = current
    filters.append(f"[{previous}]loudnorm=I=-14:TP=-1.0:LRA=11[master]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[master]",
        "-ar", "48000",
        "-ac", "2",
        "-c:a", "pcm_s16le",
        str(out),
    ]
    run(cmd)

    duration = media_duration(out)
    if not 180 <= duration <= 300:
        raise RuntimeError(f"Master unido fuera de 3-5 minutos: {duration:.2f}s")
    print("MASTER_JOINED", out, f"{duration:.2f}s", out.stat().st_size)
    return out


def get_unique_visuals(target_seconds: float, workdir: Path) -> tuple[list[Path], list[dict[str, str]], int]:
    count = len(VISUAL_QUERIES)
    transition = 0.6
    segment_seconds = max(20, math.ceil((target_seconds + (count - 1) * transition) / count))
    used: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []

    for index, primary in enumerate(VISUAL_QUERIES, start=1):
        candidates = [primary, *GENERIC_FALLBACKS]
        last_error: Exception | None = None
        for attempt, query in enumerate(candidates):
            try:
                clip, credit = _get_real_segment(
                    query,
                    workdir,
                    500 + index,
                    segment_seconds,
                    False,
                    used,
                    88000 + index * 101 + attempt,
                    target_4k=False,
                )
                clips.append(clip)
                credits.append(credit)
                print("VISUAL_OK", index, query, clip)
                break
            except Exception as exc:
                last_error = exc
                print("VISUAL_RETRY", index, query, type(exc).__name__, exc)
        else:
            raise RuntimeError(f"No se pudo conseguir una escena real unica para bloque {index}: {last_error}")

    if len(clips) != count:
        raise RuntimeError(f"Se esperaban {count} escenas y se obtuvieron {len(clips)}")
    return clips, credits, segment_seconds


def xfade_visuals(clips: list[Path], segment_seconds: int, target_seconds: float, out: Path) -> Path:
    transition = 0.6
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for clip in clips:
        cmd += ["-i", str(clip)]

    filters: list[str] = []
    previous = "0:v"
    for i in range(1, len(clips)):
        output = f"v{i}"
        offset = i * (segment_seconds - transition)
        filters.append(
            f"[{previous}][{i}:v]xfade=transition=fade:duration={transition}:offset={offset:.3f}[{output}]"
        )
        previous = output
    filters.append(
        f"[{previous}]trim=duration={target_seconds:.3f},setpts=PTS-STARTPTS,"
        "eq=contrast=1.035:saturation=1.055:brightness=0.002,"
        "unsharp=5:5:0.12:5:5:0,fps=30[finalv]"
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[finalv]",
        "-an",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out),
    ]
    run(cmd)
    duration = media_duration(out)
    if duration < target_seconds - 1.0:
        raise RuntimeError(f"Visual demasiado corto: {duration:.2f}s / {target_seconds:.2f}s")
    return out


def mux_master(visual: Path, audio: Path, out: Path) -> Path:
    duration = media_duration(audio)
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(visual),
        "-i", str(audio),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-t", f"{duration:.3f}",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "256k",
        "-movflags", "+faststart",
        str(out),
    ])
    final_duration = media_duration(out)
    if not 180 <= final_duration <= 300 or out.stat().st_size < 5_000_000:
        raise RuntimeError(f"Video final invalido: {final_duration:.2f}s / {out.stat().st_size} bytes")
    print("VIDEO_MASTER_READY", out, f"{final_duration:.2f}s", out.stat().st_size)
    return out


def upload(video: Path, thumbnail: Path, credits: list[dict[str, str]]) -> str:
    channel = load_channel("demianvelo")
    description = (
        "Aquí Estás x DemianVelo es una canción cristiana original sobre esos momentos en los que todo parece incierto, "
        "pero la presencia de Dios sigue cerca. Una canción sobre fe, paz, restauración, esperanza y Jesús.\n\n"
        "Si esta canción te acompaña, guardala, compartila con alguien que la necesite y suscribite para escuchar las próximas canciones de DemianVelo.\n\n"
        "LETRA:\n" + LYRICS.strip() + "\n\n"
        "#DemianVelo #AquiEstas #MusicaCristiana #Jesus #Adoracion"
    )
    metadata = {
        "title": TITLE,
        "description": description,
        "hashtags": ["#DemianVelo", "#AquiEstas", "#MusicaCristiana", "#Jesus", "#Adoracion"],
        "tags": [
            "DemianVelo", "Aquí Estás", "Aqui Estas", "música cristiana", "musica cristiana", "Jesús", "Jesus",
            "Dios", "fe", "esperanza", "adoración", "adoracion", "worship", "christian music", "canción cristiana",
            "Argentina", "música de fe", "música para orar",
        ],
        "duration_minutes": 5,
        "long_form": True,
        "thumbnail_text": "AQUÍ ESTÁS",
        "source_credits": credits,
    }
    video_id = upload_long_video(
        channel,
        metadata,
        video,
        thumbnail_path=thumbnail,
        expected_minutes=5,
    )
    result = {
        "status": "uploaded",
        "video_id": video_id,
        "title": TITLE,
        "duration_seconds": media_duration(video),
        "video": str(video),
        "thumbnail": str(thumbnail),
    }
    (FINAL_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("YOUTUBE_UPLOAD_SUCCESS", json.dumps(result, ensure_ascii=False))
    return video_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-dir", default="chunks")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    master_audio = join_chunks(Path(args.chunks_dir), FINAL_DIR / "Aqui_Estas_x_DemianVelo_master.wav")
    target = media_duration(master_audio)
    clips, credits, segment_seconds = get_unique_visuals(target, FINAL_DIR)
    visual = xfade_visuals(clips, segment_seconds, target, FINAL_DIR / "Aqui_Estas_visual_1080p.mp4")
    video = mux_master(visual, master_audio, FINAL_DIR / "Aqui_Estas_x_DemianVelo.mp4")
    thumbnail = make_thumbnail(video)

    metadata = {
        "title": TITLE,
        "duration_seconds": media_duration(video),
        "audio_chunks": CHUNK_NAMES,
        "visual_scene_count": len(clips),
        "visual_segment_seconds": segment_seconds,
        "thumbnail": str(thumbnail),
        "publish_requested": args.publish,
    }
    (FINAL_DIR / "finalization_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (FINAL_DIR / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.publish:
        video_id = upload(video, thumbnail, credits)
        print("PUBLISHED_VIDEO_ID", video_id)


if __name__ == "__main__":
    main()
