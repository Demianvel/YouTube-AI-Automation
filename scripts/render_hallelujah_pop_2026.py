from __future__ import annotations

import base64
import glob
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from gradio_client import Client

ROOT = Path.cwd()
OUT = ROOT / "output" / "hallelujah_pop_2026"
MUSIC_DIR = OUT / "music"
VIDEO_DIR = OUT / "video"
FINAL_DIR = OUT / "final"

TITLE = "Aleluya (Hallelujah) x DemianVelo | Música Cristiana Pop 2026"
BPM = 112
TARGET_SECONDS = 240

STYLE_PROMPT = (
    "Original 2026 Christian pop worship song for DemianVelo, modern polished pop, 112 BPM, "
    "warm magnetic original adult male lead vocal in Rioplatense Argentine Spanish, intimate verses, "
    "emotional ascending pre-chorus, huge anthemic chorus, piano and atmospheric synths, clean electric guitar textures, "
    "warm bass, punchy modern drums, subtle cinematic strings, tasteful electronic production, "
    "wide layered final chorus, radio-ready contemporary mix, expressive dynamics, memorable original hook, "
    "hopeful spiritual atmosphere about God and Jesus, contemporary 2026 production, "
    "no imitation of any real singer, no copyrighted melody, no commercial samples, no cover song."
)

LYRICS = """[INTRO]
Hay momentos en que el cielo parece callar,
y aun así Tu luz me vuelve a encontrar.

[VERSO 1]
Cuando el camino se hace largo frente a mí,
cuando las fuerzas ya no alcanzan para seguir,
Tu presencia llega suave al corazón,
y me recuerda que jamás camino solo, Dios.

[PRE-CORO]
Aunque no vea lo que viene después,
si Tu mano me sostiene, vuelvo a creer.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[VERSO 2]
No necesito comprender cada razón,
para confiar en Tu promesa y Tu dirección.
Si la tormenta vuelve a hablar más fuerte que mi fe,
Tu voz me dice que de nuevo venceré.

[PRE-CORO]
Aunque el mundo cambie alrededor,
Tu palabra sigue viva en mi interior.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[PUENTE]
Dios de vida, Dios eterno,
en la calma y el desierto,
si me pierdo, Vos me llamás,
si me caigo, me levantás.
No hay distancia, no hay silencio,
que me aparte de Tu amor,
y aunque tiemble todo el suelo,
sigo firme en Tu favor.

[BUILD]
Aleluya…
Hallelujah…
Que lo cante el corazón,
que lo escuche el mundo entero:
mi esperanza está en Dios.

[CORO FINAL]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
para siempre sos mi Dios.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[POST-CORO]
Oh-oh, Aleluya,
oh-oh, Hallelujah,
Tu amor no se termina,
Tu luz siempre estará.

[OUTRO]
Aleluya… Hallelujah…
Tu luz siempre estará.
"""

SECTIONS = [
    """[INTRO]
Hay momentos en que el cielo parece callar,
y aun así Tu luz me vuelve a encontrar.

[VERSO 1]
Cuando el camino se hace largo frente a mí,
cuando las fuerzas ya no alcanzan para seguir,
Tu presencia llega suave al corazón,
y me recuerda que jamás camino solo, Dios.

[PRE-CORO]
Aunque no vea lo que viene después,
si Tu mano me sostiene, vuelvo a creer.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.""",
    """[CORO]
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[VERSO 2]
No necesito comprender cada razón,
para confiar en Tu promesa y Tu dirección.
Si la tormenta vuelve a hablar más fuerte que mi fe,
Tu voz me dice que de nuevo venceré.

[PRE-CORO]
Aunque el mundo cambie alrededor,
Tu palabra sigue viva en mi interior.""",
    """[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[PUENTE]
Dios de vida, Dios eterno,
en la calma y el desierto,
si me pierdo, Vos me llamás,
si me caigo, me levantás.
No hay distancia, no hay silencio,
que me aparte de Tu amor.""",
    """[PUENTE]
y aunque tiemble todo el suelo,
sigo firme en Tu favor.

[BUILD]
Aleluya…
Hallelujah…
Que lo cante el corazón,
que lo escuche el mundo entero:
mi esperanza está en Dios.

[CORO FINAL]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
para siempre sos mi Dios.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[POST-CORO]
Oh-oh, Aleluya,
oh-oh, Hallelujah,
Tu amor no se termina,
Tu luz siempre estará.

[OUTRO]
Aleluya… Hallelujah…
Tu luz siempre estará.""",
]

WAN_PROMPTS = [
    "Original fictional adult male Christian pop singer performing emotionally on a minimal cinematic stage at blue hour, warm expressive face, natural body movement, volumetric blue and golden lighting, realistic premium commercial music video cinematography, smooth dolly-in, no celebrity resemblance, no logos, no text, 16:9",
    "Epic sunrise over mountain landscape, golden rays breaking through dramatic clouds, smooth cinematic drone movement, hopeful spiritual atmosphere, photorealistic premium Christian pop music video, sophisticated color grading, no logos, no text, 16:9",
    "Original fictional adult male singer walking slowly through a rain-wet city street at blue hour, cinematic reflections and soft bokeh, emotional performance, modern tasteful wardrobe without logos, realistic commercial music video camera movement, no celebrity resemblance, no text, 16:9",
    "Ocean cliffs at golden hour, powerful waves, wind moving through grass, warm sun beams through clouds, cinematic aerial movement, spiritual hopeful atmosphere, photorealistic premium pop music video, no text, no logos, 16:9",
]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("RUN", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=False)


def media_duration(path: Path) -> float:
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(cp.stdout.strip())


def decode_audio_result(result: Any, out: Path) -> Path:
    if isinstance(result, str):
        p = Path(result)
        if p.exists() and p.is_file():
            shutil.copy2(p, out)
            return out
        s = result.strip()
        if ";base64," in s and s.startswith("data:audio/"):
            out.write_bytes(base64.b64decode(s.split(";base64,", 1)[1]))
            return out
        try:
            raw = base64.b64decode(s, validate=True)
            if len(raw) > 100_000:
                out.write_bytes(raw)
                return out
        except Exception:
            pass
    if isinstance(result, dict):
        for value in result.values():
            try:
                return decode_audio_result(value, out)
            except Exception:
                continue
    if isinstance(result, (list, tuple)):
        for value in result:
            try:
                return decode_audio_result(value, out)
            except Exception:
                continue
    raise RuntimeError("ACE-Step no devolvió audio utilizable")


def generate_music() -> Path:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    final = MUSIC_DIR / "Aleluya_Hallelujah_x_DemianVelo_2026.wav"
    token = os.getenv("HF_TOKEN") or None
    client = Client("victor/ace-step-jam", token=token, verbose=False)

    # Prefer one continuous render so the singer and arrangement stay coherent.
    try:
        print("ACE_STEP: intentando canción continua de 240 segundos")
        result = client.predict(STYLE_PROMPT, LYRICS, 240.0, 12, 7.0, -1, "", 0.8, api_name="/generate")
        decode_audio_result(result, final)
        duration = media_duration(final)
        if not 180 <= duration <= 300:
            raise RuntimeError(f"duración ACE-Step fuera de 3-5 min: {duration}")
        print("ACE_STEP_CONTINUOUS_OK", duration, final.stat().st_size)
        return final
    except Exception as exc:
        print("ACE_STEP_CONTINUOUS_FAIL", type(exc).__name__, exc)

    # Free-space fallback: same prompt and stable seed for four coherent one-minute sections.
    section_files: list[Path] = []
    stable_seed = 20260813
    for index, lyrics in enumerate(SECTIONS, start=1):
        print("ACE_STEP_SECTION", index)
        result = client.predict(
            STYLE_PROMPT + f". Coherent section {index} of one continuous song; keep the same singer identity, instrumentation, key family and production.",
            lyrics,
            60.0,
            12,
            7.0,
            stable_seed,
            "",
            0.8,
            api_name="/generate",
        )
        section = MUSIC_DIR / f"section_{index}.wav"
        decode_audio_result(result, section)
        section_files.append(section)

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for section in section_files:
        cmd += ["-i", str(section)]
    cmd += [
        "-filter_complex",
        "[0:a][1:a]acrossfade=d=0.35:c1=tri:c2=tri[a01];"
        "[a01][2:a]acrossfade=d=0.35:c1=tri:c2=tri[a012];"
        "[a012][3:a]acrossfade=d=0.35:c1=tri:c2=tri[outa]",
        "-map", "[outa]",
        "-c:a", "pcm_s16le",
        str(final),
    ]
    run(cmd)
    duration = media_duration(final)
    if not 180 <= duration <= 300:
        raise RuntimeError(f"canción final fuera de 3-5 minutos: {duration}")
    print("ACE_STEP_SEGMENTED_OK", duration, final.stat().st_size)
    return final


def _collect_video_files(value: Any, files: list[Path]) -> None:
    if isinstance(value, str):
        p = Path(value)
        if p.exists() and p.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}:
            files.append(p)
    elif isinstance(value, dict):
        for v in value.values():
            _collect_video_files(v, files)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _collect_video_files(v, files)


def _call_known_openking(prompt: str, seed: int) -> Path:
    token = os.getenv("HF_TOKEN") or None
    c = Client("OpenKing/wan2-video-generation", token=token, verbose=False)
    result = c.predict(prompt, None, 1280, 704, 73, 20, 5.0, seed, api_name="/generate_video")
    files: list[Path] = []
    _collect_video_files(result, files)
    if not files:
        raise RuntimeError("OpenKing Wan2.2 no devolvió video")
    return files[0]


def _call_dynamic_wan(space: str, prompt: str, seed: int) -> Path:
    token = os.getenv("HF_TOKEN") or None
    c = Client(space, token=token, verbose=False)
    api = c.view_api(return_format="dict")
    named = api.get("named_endpoints", api)
    candidates: list[tuple[str, dict[str, Any]]] = []
    for endpoint, spec in named.items():
        if not isinstance(spec, dict):
            continue
        params = spec.get("parameters", [])
        returns = " ".join(str(r.get("component") or r.get("type") or "") for r in spec.get("returns", [])).lower()
        pnames = [str(p.get("parameter_name") or "").lower() for p in params]
        if any("prompt" in n for n in pnames) and ("video" in returns or "video" in endpoint.lower()):
            candidates.append((endpoint, spec))
    if not candidates:
        raise RuntimeError(f"{space}: sin endpoint T2V visible")
    endpoint, spec = max(candidates, key=lambda x: len(x[1].get("parameters", [])))
    args: list[Any] = []
    for p in spec.get("parameters", []):
        n = str(p.get("parameter_name") or "").lower().replace("-", "_")
        default = p.get("default", None)
        if "image" in n:
            value = None
        elif "prompt" in n and "negative" not in n:
            value = prompt
        elif "negative" in n:
            value = "blurry, low quality, text, watermark, logo, duplicate people, deformed hands, celebrity resemblance"
        elif "height" in n:
            value = 704
        elif "width" in n:
            value = 1280
        elif "duration" in n or "seconds" in n:
            value = 3.0
        elif "frame" in n:
            value = 73
        elif "sampling" in n or "inference_step" in n or n == "steps":
            value = 12
        elif "guide" in n:
            value = 5.0
        elif "shift" in n:
            value = default if default is not None else 5.0
        elif "seed" in n:
            value = seed
        elif "random" in n and "seed" in n:
            value = False
        elif "solver" in n:
            value = default or "unipc"
        else:
            value = default
        args.append(value)
    print("WAN_DYNAMIC", space, endpoint, [str(p.get("parameter_name") or "") for p in spec.get("parameters", [])])
    result = c.predict(*args, api_name=endpoint)
    files: list[Path] = []
    _collect_video_files(result, files)
    if not files:
        raise RuntimeError(f"{space}: no devolvió video")
    return files[0]


def generate_wan_scenes() -> list[Path]:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    spaces = [
        "OpenKing/wan2-video-generation",
        "shafqat786/Wan-AI-Wan2.2-TI2V-5B",
        "Teheby63736363/Wan-AI-Wan2.2-TI2V-5B",
        "skrov/Wan-AI-Wan2.2-TI2V-5B",
    ]
    produced: list[Path] = []
    errors: list[str] = []

    for index, prompt in enumerate(WAN_PROMPTS, start=1):
        scene_ok = False
        seed = 2600 + index
        for space in spaces:
            try:
                if space == "OpenKing/wan2-video-generation":
                    src = _call_known_openking(prompt, seed)
                else:
                    src = _call_dynamic_wan(space, prompt, seed)
                dst = VIDEO_DIR / f"wan_scene_{index:02d}{src.suffix.lower()}"
                shutil.copy2(src, dst)
                if dst.stat().st_size < 50_000:
                    raise RuntimeError("archivo de video demasiado pequeño")
                print("WAN_SCENE_OK", index, space, dst.stat().st_size)
                produced.append(dst)
                scene_ok = True
                break
            except Exception as exc:
                msg = f"scene {index} {space}: {type(exc).__name__}: {exc}"
                errors.append(msg)
                print("WAN_SCENE_FAIL", msg)
        if not scene_ok:
            print("WAN_SCENE_SKIPPED", index)

    (VIDEO_DIR / "wan_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    if not produced:
        raise RuntimeError("Ningún Space gratuito de Wan2.2 entregó una escena válida; se cancela la publicación")
    return produced


def _download_real_stock() -> tuple[list[Path], list[dict[str, str]]]:
    # Reuse the repository's real-camera Pexels/Wikimedia logic for cinematic filler between Wan hero shots.
    from app.music_video import _get_real_segment

    queries = [
        "cinematic sunrise mountains golden hour",
        "ocean waves golden hour cinematic",
        "night city lights cinematic street",
        "empty highway night cinematic",
        "church architecture sunlight cinematic",
        "dramatic clouds sun rays cinematic",
        "forest sunlight rays cinematic",
        "mountain lake sunrise cinematic",
    ]
    used: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []
    meta = {"topic": "Aleluya Hallelujah Christian pop worship", "title": TITLE}
    for index, query in enumerate(queries, start=1):
        clip, credit = _get_real_segment(query, FINAL_DIR, 100 + index, 30, False, used, 9000 + index, target_4k=False)
        clips.append(clip)
        credits.append(credit)
    return clips, credits


def build_video(audio: Path, wan_scenes: list[Path]) -> tuple[Path, list[dict[str, str]]]:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    target = media_duration(audio)
    if not 180 <= target <= 300:
        raise RuntimeError(f"audio fuera de 3-5 min: {target}")

    stock, credits = _download_real_stock()
    wan_norm: list[Path] = []
    for index, src in enumerate(wan_scenes, start=1):
        dst = FINAL_DIR / f"wan_norm_{index}.mp4"
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(src), "-t", "6",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.15:5:5:0,fps=30",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(dst),
        ])
        wan_norm.append(dst)

    sequence: list[Path] = []
    wi = 0
    for i, stock_clip in enumerate(stock):
        sequence.append(stock_clip)
        if wi < len(wan_norm) and i % 2 == 0:
            sequence.append(wan_norm[wi])
            wi += 1
    while wi < len(wan_norm):
        sequence.append(wan_norm[wi])
        wi += 1

    manifest = FINAL_DIR / "concat.txt"
    manifest.write_text("\n".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'" for p in sequence), encoding="utf-8")
    visual = FINAL_DIR / "visual_1080p.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-t", f"{target:.3f}", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
    ])

    final = FINAL_DIR / "Aleluya_Hallelujah_x_DemianVelo_Pop_2026.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0", "-t", f"{target:.3f}",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(final),
    ])
    fd = media_duration(final)
    if not 180 <= fd <= 300 or final.stat().st_size < 5_000_000:
        raise RuntimeError(f"video final inválido: duration={fd}, bytes={final.stat().st_size}")
    print("FINAL_VIDEO_OK", final, fd, final.stat().st_size)
    return final, credits


def upload(video: Path, credits: list[dict[str, str]]) -> str:
    from app.config import load_channel
    from app.youtube import upload_long_video

    channel = load_channel("demianvelo")
    description = (
        "Aleluya (Hallelujah) x DemianVelo. Canción cristiana original sobre Dios, Jesucristo, fe, esperanza y encontrar luz incluso en los momentos difíciles.\n\n"
        "Producción pop moderna 2026 con voz masculina original en castellano rioplatense y videoclip cinematográfico.\n\n"
        "LETRA UTILIZADA:\n" + LYRICS.strip() + "\n\n"
        "#DemianVelo #Aleluya #Hallelujah #MusicaCristiana #Jesus"
    )
    meta = {
        "title": TITLE,
        "description": description,
        "hashtags": ["#DemianVelo", "#Aleluya", "#Hallelujah", "#MusicaCristiana", "#Jesus"],
        "tags": [
            "DemianVelo", "Aleluya", "Hallelujah", "música cristiana", "musica cristiana 2026", "Jesús", "Jesus", "Dios",
            "fe", "esperanza", "christian pop", "worship pop", "música de adoración", "Argentina", "pop cristiano", "cancion cristiana",
        ],
        "source_credits": credits,
        "duration_minutes": 4,
        "long_form": True,
    }
    video_id = upload_long_video(channel, meta, video, thumbnail_path=None, expected_minutes=4)
    result = {"status": "uploaded", "video_id": video_id, "title": TITLE, "video": str(video)}
    (FINAL_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("YOUTUBE_UPLOAD_SUCCESS", json.dumps(result, ensure_ascii=False))
    return video_id


def main() -> None:
    publish = "--publish" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    audio = generate_music()
    wan = generate_wan_scenes()
    video, credits = build_video(audio, wan)
    (FINAL_DIR / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata = {
        "title": TITLE,
        "bpm": BPM,
        "duration_seconds": media_duration(audio),
        "music_engine": "ACE-Step",
        "video_engine": "Wan2.2 + real-camera cinematic montage",
        "voice": "original warm magnetic adult male, Argentine/Rioplatense Spanish",
        "lyrics": LYRICS,
        "publish_requested": publish,
    }
    (FINAL_DIR / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if publish:
        upload(video, credits)


if __name__ == "__main__":
    main()
