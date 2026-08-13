from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from gradio_client import Client, handle_file


ROOT = Path.cwd()
OUT = ROOT / "output" / "dios_actua_demianvelo"
MUSIC_DIR = OUT / "music"
FINAL_DIR = OUT / "final"
REFERENCE_DIR = ROOT / "reference_aleluya"
ASSET_DIR = ROOT / "assets" / "dios-actua"

TITLE = "DIOS ACTÚA — DemianVelo | Video Oficial 4K • Música Cristiana"
BPM = 84
TARGET_SECONDS = 240

STYLE_PROMPT = (
    "Completely original melodic Christian pop worship song for DemianVelo, 84 BPM, G major with emotional E minor colors, "
    "organic premium cinematic production, intimate grand piano, warm acoustic guitar, delicate clean electric guitar swells, "
    "rounded live bass, tasteful real acoustic drums, wide cinematic strings, subtle Nordic folk textures and a restrained human choir "
    "only in the final chorus. Sweet warm original adult male tenor-baritone lead vocal in neutral Rioplatense Argentine Spanish, "
    "matching the supplied DemianVelo Aleluya vocal identity when a reference is available: velvety low register, clear gentle diction, "
    "natural believable breaths, controlled vibrato, tender chest voice, luminous upper notes and an emotionally comforting delivery. "
    "Radio-ready vocal-forward mix, detailed acoustic transients, natural dynamics, wide but intimate master. Build from a quiet polar-night "
    "intro into a memorable heart-filling chorus, an expansive bridge and a powerful final chorus. Theme: God is working during silence, "
    "Jesus, hope, healing, courage and beginning again. Completely original melody, harmony, rhythm, lyric phrasing and hook. "
    "Do not imitate any third-party singer, song, worship recording or copyrighted melody. No EDM, no dance beat, no trap, no reggaeton, "
    "no electronic lead, no heavy autotune, no commercial samples."
)

LYRICS = (ASSET_DIR / "letra-original.txt").read_text(encoding="utf-8").split("\n", 2)[2].strip()

SCENE_QUERIES = [
    ["Norway aurora borealis timelapse", "Tromso northern lights", "aurora borealis sky"],
    ["Lofoten Norway aerial winter", "Norway snow mountains aerial", "snow mountain drone"],
    ["Svalbard glacier Arctic", "Arctic glacier ocean", "glacier sea"],
    ["Norway fjord winter aerial", "Norwegian fjord drone", "mountain fjord"],
    ["Arctic sea ice Svalbard", "polar ocean ice", "winter ocean ice"],
    ["North Cape Norway winter", "Norway arctic coast", "snow coast aerial"],
    ["Tromso Norway polar night", "Norway winter village night", "snow village night"],
    ["Reine Lofoten sunrise", "Lofoten sunrise aerial", "snow mountain sunrise"],
    ["Norway waterfall winter", "Scandinavia frozen waterfall", "waterfall snow"],
    ["Norwegian fjord aurora", "aurora over mountains", "northern lights landscape"],
]


def run(cmd: list[str]) -> None:
    print("RUN", " ".join(cmd))
    subprocess.run(cmd, check=True)


def duration(path: Path) -> float:
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(cp.stdout.strip())


def find_media(value: Any, suffixes: set[str]) -> list[Path]:
    found: list[Path] = []
    if isinstance(value, str):
        candidate = Path(value)
        if candidate.exists() and candidate.suffix.lower() in suffixes:
            found.append(candidate)
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(find_media(item, suffixes))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(find_media(item, suffixes))
    return found


def decode_audio(value: Any, out: Path) -> Path:
    files = find_media(value, {".wav", ".mp3", ".flac", ".m4a", ".ogg"})
    if files:
        shutil.copy2(files[0], out)
        return out
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("data:audio/") and ";base64," in text:
            out.write_bytes(base64.b64decode(text.split(";base64,", 1)[1]))
            return out
        try:
            raw = base64.b64decode(text, validate=True)
            if len(raw) > 100_000:
                out.write_bytes(raw)
                return out
        except Exception:
            pass
    if isinstance(value, dict):
        for item in value.values():
            try:
                return decode_audio(item, out)
            except Exception:
                pass
    if isinstance(value, (list, tuple)):
        for item in value:
            try:
                return decode_audio(item, out)
            except Exception:
                pass
    raise RuntimeError("El motor ACE-Step no devolvió un archivo de audio utilizable")


def vocal_reference() -> Path | None:
    candidates: list[Path] = []
    if REFERENCE_DIR.exists():
        for pattern in ("*.wav", "*.mp3", "*.flac", "*.m4a"):
            candidates.extend(REFERENCE_DIR.rglob(pattern))
    return max(candidates, key=lambda p: p.stat().st_size) if candidates else None


def parameter_value(name: str, default: Any, reference: Path | None) -> Any:
    key = name.lower().replace("-", "_")
    if "reference_audio" in key or "refer_audio" in key:
        return handle_file(str(reference)) if reference else None
    if "src_audio" in key or "source_audio" in key:
        return None
    if key in {"prompt", "caption", "music_prompt", "description", "song_description"} or (
        "prompt" in key and "negative" not in key
    ):
        return STYLE_PROMPT
    if "negative" in key:
        return "EDM, electronic dance, trap, reggaeton, harsh autotune, celebrity imitation, copyrighted melody, low quality"
    if "lyric" in key:
        return LYRICS
    if "model" in key:
        return "acestep-v15-turbo"
    if "task_type" in key:
        return "text2music"
    if "generation_mode" in key:
        return "custom"
    if "instrumental" in key:
        return False
    if "vocal_language" in key or key in {"language", "lang"}:
        return "es"
    if key == "bpm" or key.endswith("_bpm"):
        return BPM
    if "duration" in key and "repaint" not in key:
        return float(TARGET_SECONDS)
    if "inference_step" in key or key == "steps":
        return 12
    if "guidance" in key:
        return 7.0
    if "thinking" in key or "cot_caption" in key or "cot_language" in key:
        return True
    if "random_seed" in key:
        return False
    if key in {"seed", "manual_seed", "seed_number"}:
        return 20260813
    if "cover_strength" in key or "ref_audio_strength" in key:
        return 0.52
    if "batch" in key and "chunk" not in key:
        return 1
    if "audio_format" in key or key == "format":
        return "wav"
    if "temperature" in key:
        return 0.82
    if "cfg_scale" in key:
        return 2.0
    if "top_p" in key:
        return 0.9
    if "top_k" in key:
        return 0
    return default


def try_reference_generation(reference: Path, raw: Path) -> str | None:
    token = os.getenv("HF_TOKEN") or None
    spaces = ["ACE-Step/Ace-Step-v1.5", "techfreakworm/ACE-Music-Studio"]
    for space in spaces:
        try:
            client = Client(space, token=token, verbose=False)
            named = client.view_api(return_format="dict").get("named_endpoints", {})
            choices: list[tuple[str, dict[str, Any]]] = []
            for endpoint, spec in named.items():
                if not isinstance(spec, dict):
                    continue
                names = [str(p.get("parameter_name") or "").lower() for p in spec.get("parameters", [])]
                blob = endpoint.lower() + " " + " ".join(names)
                if "lyric" in blob and any("reference_audio" in name or "refer_audio" in name for name in names):
                    choices.append((endpoint, spec))
            for endpoint, spec in sorted(choices, key=lambda pair: len(pair[1].get("parameters", [])), reverse=True):
                args = [parameter_value(str(p.get("parameter_name") or ""), p.get("default"), reference) for p in spec.get("parameters", [])]
                print("ACE_REFERENCE_ATTEMPT", space, endpoint)
                result = client.predict(*args, api_name=endpoint)
                decode_audio(result, raw)
                if 180 <= duration(raw) <= 300:
                    return f"{space} reference-audio"
                raw.unlink(missing_ok=True)
        except Exception as exc:
            print("ACE_REFERENCE_FAIL", space, type(exc).__name__, exc)
            raw.unlink(missing_ok=True)
    return None


def try_continuous_generation(raw: Path) -> str:
    token = os.getenv("HF_TOKEN") or None
    spaces = [
        "victor/ace-step-jam",
        "R-Kentaren/ace-step-jam",
        "Lanston/ACE-Step-v1-5-Music",
        "LububMusicAi/ACE-Step-Custom",
        "Gamahea/ACE-Step-Custom",
        "techfreakworm/ACE-Music-Studio",
    ]
    errors: list[str] = []
    for space in spaces:
        try:
            client = Client(space, token=token, verbose=False)
            if "ace-step-jam" in space.lower():
                try:
                    print("ACE_STABLE_ATTEMPT", space)
                    result = client.predict(
                        STYLE_PROMPT, LYRICS, float(TARGET_SECONDS), 12, 7.0, 20260813, "", 0.82, api_name="/generate"
                    )
                    decode_audio(result, raw)
                    if 180 <= duration(raw) <= 300:
                        return f"{space} continuous"
                    raw.unlink(missing_ok=True)
                except Exception as exc:
                    errors.append(f"{space}/generate: {type(exc).__name__}: {exc}")
                    raw.unlink(missing_ok=True)

            api = client.view_api(return_format="dict")
            named = api.get("named_endpoints", api)
            choices: list[tuple[str, dict[str, Any]]] = []
            for endpoint, spec in named.items():
                if not isinstance(spec, dict):
                    continue
                names = [str(p.get("parameter_name") or "") for p in spec.get("parameters", [])]
                blob = (endpoint + " " + " ".join(names)).lower()
                if "lyric" in blob and any(word in blob for word in ("generate", "song", "music", "custom")):
                    choices.append((endpoint, spec))
            for endpoint, spec in sorted(choices, key=lambda pair: len(pair[1].get("parameters", [])), reverse=True)[:4]:
                try:
                    args = [parameter_value(str(p.get("parameter_name") or ""), p.get("default"), None) for p in spec.get("parameters", [])]
                    print("ACE_DYNAMIC_ATTEMPT", space, endpoint)
                    result = client.predict(*args, api_name=endpoint)
                    decode_audio(result, raw)
                    if 180 <= duration(raw) <= 300:
                        return f"{space}{endpoint} continuous"
                    raw.unlink(missing_ok=True)
                except Exception as exc:
                    errors.append(f"{space}{endpoint}: {type(exc).__name__}: {exc}")
                    raw.unlink(missing_ok=True)
        except Exception as exc:
            errors.append(f"{space}: {type(exc).__name__}: {exc}")
            raw.unlink(missing_ok=True)
    raise RuntimeError("Ningún motor ACE-Step disponible generó 3–5 minutos:\n" + "\n".join(errors[-20:]))


def generate_music() -> tuple[Path, str, str | None]:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    raw = MUSIC_DIR / "Dios_Actua_raw.wav"
    reference = vocal_reference()
    engine = try_reference_generation(reference, raw) if reference else None
    if not engine:
        engine = try_continuous_generation(raw)

    mastered = MUSIC_DIR / "Dios_Actua_DemianVelo_MASTER.wav"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
        "-af", "aresample=48000,highpass=f=32,lowpass=f=19000,acompressor=threshold=-18dB:ratio=2:attack=20:release=180:makeup=2,alimiter=limit=0.94,loudnorm=I=-13:LRA=9:TP=-1",
        "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(mastered),
    ])
    actual = duration(mastered)
    if not 180 <= actual <= 300 or mastered.stat().st_size < 20_000_000:
        raise RuntimeError(f"Máster musical inválido: {actual:.2f}s, {mastered.stat().st_size} bytes")
    ref_hash = hashlib.sha256(reference.read_bytes()).hexdigest() if reference else None
    return mastered, engine, ref_hash


def make_title_clip(image: Path, out: Path, seconds: float, outro: bool = False) -> None:
    frames = int(math.ceil(seconds * 30))
    zoom = "max(1.09-0.00045*on,1.0)" if outro else "min(1.0+0.00045*on,1.09)"
    vf = (
        "scale=2200:1238:force_original_aspect_ratio=increase,crop=2200:1238,"
        f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps=30,"
        f"fade=t=in:st=0:d=1.0,fade=t=out:st={max(0.0, seconds - 1.0):.2f}:d=1.0,"
        "eq=contrast=1.04:saturation=1.06,unsharp=5:5:0.12:5:5:0,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(image), "-t", f"{seconds:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", str(out),
    ])


def download_real_scenes(seconds_each: int) -> tuple[list[Path], list[dict[str, str]]]:
    from app.music_video import _get_real_segment

    used: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []
    for index, candidates in enumerate(SCENE_QUERIES, start=1):
        last_error: Exception | None = None
        fallbacks = candidates + ["Norway nature", "Arctic landscape", "snow mountain", "aurora borealis", "cinematic nature landscape"]
        for attempt, query in enumerate(fallbacks):
            try:
                clip, credit = _get_real_segment(
                    query, FINAL_DIR, 300 + index, seconds_each, False, used, 84000 + index * 101 + attempt, target_4k=False
                )
                clips.append(clip)
                credits.append(credit)
                print("NORWAY_SCENE_OK", index, query, clip)
                break
            except Exception as exc:
                last_error = exc
                print("NORWAY_SCENE_RETRY", index, query, type(exc).__name__, exc)
        else:
            raise RuntimeError(f"No se pudo conseguir una escena real única para el bloque {index}: {last_error}")
    return clips, credits


def build_video(audio: Path) -> tuple[Path, list[dict[str, str]]]:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    target = duration(audio)
    intro_seconds = 6.0
    outro_seconds = 6.0
    stock_seconds = max(20, math.ceil((target - intro_seconds - outro_seconds) / len(SCENE_QUERIES)))
    opening = FINAL_DIR / "opening.mp4"
    ending = FINAL_DIR / "ending.mp4"
    make_title_clip(ASSET_DIR / "thumbnail-a-jesus-noruega.jpg", opening, intro_seconds)
    make_title_clip(ASSET_DIR / "thumbnail-b-emocion-noruega.jpg", ending, outro_seconds, outro=True)
    stock, credits = download_real_scenes(stock_seconds)
    sequence = [opening, *stock, ending]
    manifest = FINAL_DIR / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in sequence), encoding="utf-8")

    visual_1080 = FINAL_DIR / "Dios_Actua_visual_1080p.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-t", f"{target:.3f}", "-an", "-vf", "eq=contrast=1.025:saturation=1.045,unsharp=5:5:0.10:5:5:0,fps=30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual_1080),
    ])

    final = FINAL_DIR / "Dios_Actua_DemianVelo_4K.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual_1080), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0", "-t", f"{target:.3f}",
        "-vf", "scale=3840:2160:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
        "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", str(final),
    ])
    actual = duration(final)
    if not 180 <= actual <= 300 or final.stat().st_size < 20_000_000:
        raise RuntimeError(f"Video final inválido: {actual:.2f}s, {final.stat().st_size} bytes")
    return final, credits


def credits_text(credits: list[dict[str, str]]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for credit in credits:
        source = credit.get("source_url") or ""
        if not source or source in seen:
            continue
        seen.add(source)
        creator = credit.get("creator") or "colaborador"
        provider = credit.get("provider") or "Fuente visual"
        license_name = credit.get("license") or ""
        line = f"- {provider} — {creator}"
        if license_name:
            line += f" — {license_name}"
        lines.append(f"{line}: {source}")
    return "\n".join(lines[:15])


def upload(video: Path, credits: list[dict[str, str]]) -> dict[str, Any]:
    from app.config import load_channel
    from app.youtube import upload_long_video

    description = (
        "“Dios Actúa” es una canción cristiana original de DemianVelo sobre confiar cuando el camino todavía no se ve. "
        "Un pop melódico y cinematográfico que viaja por los fiordos de Noruega, la noche polar y la aurora boreal para recordar "
        "que Dios puede traer esperanza, libertad y un nuevo comienzo.\n\n"
        "Si esta canción llena tu corazón, compartila con alguien que necesite volver a creer, dejá tu comentario y suscribite "
        "a DemianVelo para escuchar las próximas canciones.\n\n"
        "¿En qué momento sentiste que Dios estaba actuando en tu vida? Te leo en los comentarios.\n\n"
        "LETRA ORIGINAL:\n" + LYRICS + "\n\n"
        "CRÉDITOS VISUALES:\n" + credits_text(credits)
    ).strip()
    metadata = {
        "title": TITLE,
        "description": description,
        "hashtags": ["#DiosActua", "#DemianVelo", "#MusicaCristiana", "#Jesus", "#PopCristiano"],
        "tags": [
            "DemianVelo", "Dios Actúa", "Dios Actua", "música cristiana", "musica cristiana", "pop cristiano",
            "Jesús", "Jesus", "Dios", "adoración", "esperanza", "música de fe", "canción cristiana 2026",
            "Norway", "aurora boreal", "Christian music", "worship en español",
        ],
        "duration_minutes": 4,
    }
    video_id = upload_long_video(
        load_channel("demianvelo"), metadata, video,
        thumbnail_path=ASSET_DIR / "thumbnail-b-emocion-noruega.jpg", expected_minutes=4,
    )
    return {
        "status": "uploaded",
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "title": TITLE,
        "thumbnail_status": metadata.get("thumbnail_upload_status"),
    }


def main() -> None:
    publish = "--publish" in sys.argv
    audio, music_engine, reference_hash = generate_music()
    video, credits = build_video(audio)
    video_probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=width,height,codec_name:format=duration,size", "-of", "json", str(video)],
        check=True, text=True, capture_output=True,
    )
    result: dict[str, Any] = {
        "title": TITLE,
        "bpm": BPM,
        "duration_seconds": duration(video),
        "music_engine": music_engine,
        "reference_vocal_sha256": reference_hash,
        "voice_reference_used": bool(reference_hash),
        "visual_scene_count": len(SCENE_QUERIES) + 2,
        "visual_concept": "Norway, Svalbard, Arctic landscapes and aurora borealis",
        "thumbnail_primary": str(ASSET_DIR / "thumbnail-b-emocion-noruega.jpg"),
        "thumbnail_ab_alternative": str(ASSET_DIR / "thumbnail-a-jesus-noruega.jpg"),
        "qa": json.loads(video_probe.stdout),
        "publish_requested": publish,
    }
    if publish:
        result.update(upload(video, credits))
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    (FINAL_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (FINAL_DIR / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    print("DIOS_ACTUA_RELEASE", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
