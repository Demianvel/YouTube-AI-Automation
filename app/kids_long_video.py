from __future__ import annotations

import hashlib
import math
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

import numpy as np
import requests
import soundfile as sf
from kokoro import KPipeline

from .audio import make_pleasant_original_music

BASE = "https://gen.pollinations.ai/image/"
W, H, FPS = 1920, 1080, 30


def _seed(meta: dict, index: int) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _download_image(prompt: str, out: Path, seed: int) -> None:
    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    full_prompt = (
        prompt
        + ", original premium 3D family animation, fictional characters only, rounded appealing shapes, "
          "soft cinematic lighting, expressive friendly faces, polished clean materials, vibrant colors, "
          "landscape 16:9 composition, no text, no logo, no watermark, no real people, no copyrighted characters"
    )
    headers = {"User-Agent": "YouTube-AI-Automation/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    params = {
        "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        "width": 1280,
        "height": 720,
        "seed": seed,
        "nologo": "true",
        "enhance": "true",
    }
    url = BASE + quote(full_prompt, safe="")
    last_error = None
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=(20, 180))
            if response.status_code == 429:
                time.sleep(4 + attempt * 4)
                continue
            response.raise_for_status()
            if len(response.content) < 20_000:
                raise RuntimeError("imagen demasiado pequena")
            out.write_bytes(response.content)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"No se pudo generar imagen 3D premium: {last_error}")


def _image_clip(image: Path, out: Path, duration: int, index: int) -> None:
    frames = duration * FPS
    if index % 4 == 0:
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif index % 4 == 1:
        x, y = "(iw-iw/zoom)*on/max(1,duration*30)", "ih/2-(ih/zoom/2)"
    elif index % 4 == 2:
        x, y = "iw-iw/zoom-(iw-iw/zoom)*on/max(1,duration*30)", "ih/2-(ih/zoom/2)"
    else:
        x, y = "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*on/max(1,duration*30)"
    vf = (
        "scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,"
        f"zoompan=z='min(zoom+0.00045,1.07)':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
        "setsar=1,eq=contrast=1.025:saturation=1.06:brightness=0.004"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(image),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def _probe_audio(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _kids_voice_segments(meta: dict, workdir: Path) -> list[Path]:
    pipeline = KPipeline(lang_code="e")
    voice = os.getenv("KOKORO_KIDS_VOICE", "ef_dora")
    speed = float(os.getenv("KOKORO_KIDS_SPEED", "1.03"))
    scene_seconds = int(meta["scene_seconds"])
    outputs: list[Path] = []

    for index, scene in enumerate(meta["scenes"]):
        parts = []
        for _g, _p, audio in pipeline(scene["narration"], voice=voice, speed=speed, split_pattern=r"(?<=[.!?])\s+"):
            if audio is not None and len(audio):
                parts.append(np.asarray(audio, dtype=np.float32))
        if not parts:
            raise RuntimeError(f"Kokoro no genero voz infantil para escena {index + 1}.")
        raw = workdir / f"kids_voice_raw_{index + 1}.wav"
        sf.write(raw, np.concatenate(parts), 24000, subtype="PCM_16")
        duration = _probe_audio(raw)
        out = workdir / f"kids_voice_{index + 1}.wav"
        filters = ["highpass=f=75", "lowpass=f=9500", "acompressor=threshold=-18dB:ratio=1.7:attack=12:release=150", "loudnorm=I=-16:TP=-1.5:LRA=8"]
        if duration > scene_seconds - 0.35:
            factor = min(1.35, max(1.0, duration / (scene_seconds - 0.45)))
            filters.insert(0, f"atempo={factor:.4f}")
        filters.append(f"apad=pad_dur={scene_seconds}")
        filters.append(f"atrim=0:{scene_seconds}")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
            "-af", ",".join(filters), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out),
        ], check=True)
        raw.unlink(missing_ok=True)
        outputs.append(out)
    return outputs


def render_kids_long(meta: dict, workdir: Path) -> Path:
    scene_seconds = int(meta["scene_seconds"])
    clips: list[Path] = []
    for index, scene in enumerate(meta["scenes"]):
        image = workdir / f"kids_long_image_{index + 1}.jpg"
        clip = workdir / f"kids_long_scene_{index + 1}.mp4"
        _download_image(scene["visual_prompt"], image, _seed(meta, index))
        _image_clip(image, clip, scene_seconds, index)
        image.unlink(missing_ok=True)
        clips.append(clip)

    visual_manifest = workdir / "kids_long_visuals.txt"
    visual_manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "kids_long_visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(visual_manifest),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(visual),
    ], check=True)

    voices = _kids_voice_segments(meta, workdir)
    voice_manifest = workdir / "kids_long_voices.txt"
    voice_manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in voices), encoding="utf-8")
    voice_full = workdir / "kids_long_voice.wav"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(voice_manifest),
        "-c:a", "pcm_s16le", str(voice_full),
    ], check=True)

    duration = int(meta["duration_seconds"])
    music = workdir / "kids_long_music.wav"
    make_pleasant_original_music(music, duration, _seed(meta, 999))
    out = workdir / f"envikids_{meta['duration_minutes']}min.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(voice_full), "-i", str(music),
        "-filter_complex", "[1:a]volume=1.0[v];[2:a]volume=0.028[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ], check=True)
    meta["tts_provider_used"] = "kokoro-ef_dora"
    meta["generated_visual_provider"] = "Pollinations image API"
    return out
