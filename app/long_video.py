from __future__ import annotations

import hashlib
import os
import random
import subprocess
from pathlib import Path
from typing import Any

import requests

from .audio import make_pleasant_original_music
from .wikimedia_video import _download as commons_download
from .wikimedia_video import _search as commons_search

PEXELS_SEARCH = "https://api.pexels.com/v1/videos/search"
W, H, FPS = 1920, 1080, 30
CHAPTER_SECONDS = 30
TOTAL_SECONDS = 300


def _seed(meta: dict, index: int) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError:
        return 0.0


def _edit_landscape(source: Path, out: Path, duration: int, seed: int, botanical: bool) -> None:
    source_duration = _probe_duration(source)
    if source_duration <= 0:
        raise RuntimeError("El archivo descargado no contiene video valido.")
    rng = random.Random(seed)
    if botanical or source_duration <= duration + 1:
        start = 0.0
    else:
        start = rng.uniform(0.0, max(0.0, source_duration - duration - 0.2))
    loop = ["-stream_loop", "-1"] if source_duration < duration else []
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,"
        "eq=contrast=1.025:saturation=1.035:brightness=0.002,"
        f"unsharp=5:5:0.16:5:5:0,fps={FPS}"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", *loop, "-ss", f"{start:.3f}", "-i", str(source),
            "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )


def _pexels_search(query: str) -> list[dict[str, Any]]:
    key = os.getenv("PEXELS_API_KEY", "").strip()
    if not key:
        return []
    response = requests.get(
        PEXELS_SEARCH,
        headers={"Authorization": key},
        params={"query": query, "per_page": 40, "orientation": "landscape"},
        timeout=(15, 60),
    )
    response.raise_for_status()
    return response.json().get("videos") or []


def _choose_pexels(videos: list[dict[str, Any]], used: set[int], seed: int) -> dict[str, Any] | None:
    candidates = [v for v in videos if int(v.get("id") or 0) not in used and v.get("video_files")]
    if not candidates:
        candidates = [v for v in videos if v.get("video_files")]
    if not candidates:
        return None

    def score(v: dict[str, Any]) -> tuple[int, int, int]:
        width, height = int(v.get("width") or 0), int(v.get("height") or 0)
        landscape = 1 if width >= height else 0
        long_enough = 1 if int(v.get("duration") or 0) >= CHAPTER_SECONDS else 0
        return (landscape, long_enough, width * height)

    candidates.sort(key=score, reverse=True)
    chosen = random.Random(seed).choice(candidates[: min(10, len(candidates))])
    used.add(int(chosen.get("id") or 0))
    return chosen


def _pexels_file(video: dict[str, Any]) -> str:
    files = [
        f for f in (video.get("video_files") or [])
        if f.get("link") and str(f.get("file_type") or "").lower() == "video/mp4"
    ]
    if not files:
        raise RuntimeError("Pexels no devolvio MP4 para el video elegido.")
    files.sort(key=lambda f: (int(f.get("width") or 0) >= int(f.get("height") or 0), int(f.get("width") or 0) * int(f.get("height") or 0)), reverse=True)
    return str(files[0]["link"])


def _download_generic(url: str, path: Path) -> None:
    with requests.get(url, stream=True, timeout=(20, 180)) as response:
        response.raise_for_status()
        with path.open("wb") as fh:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError("La descarga produjo un archivo invalido.")


def _fallback_queries(channel: dict) -> list[str]:
    if "botanical" in channel.get("visual_mode", ""):
        return [
            "seed germination timelapse",
            "roots growing timelapse",
            "plant sprout timelapse",
            "seedling growth timelapse",
            "plant leaves growing timelapse",
        ]
    return [
        "small business owner working",
        "business budget calculator",
        "entrepreneur inventory products",
        "packing online orders business",
        "small shop owner finances",
    ]


def _get_real_clip(channel: dict, meta: dict, chapter: dict, index: int, workdir: Path, used_pexels: set[int], used_commons: set[str]) -> tuple[Path, dict[str, str]]:
    botanical = "botanical" in channel.get("visual_mode", "")
    queries = [str(chapter.get("stock_query") or "").strip(), *_fallback_queries(channel)]
    queries = [q for q in queries if q]
    seed = _seed(meta, index)

    if os.getenv("PEXELS_API_KEY", "").strip():
        for query in queries:
            try:
                videos = _pexels_search(query)
                chosen = _choose_pexels(videos, used_pexels, seed)
                if not chosen:
                    continue
                source = workdir / f"long_pexels_source_{index + 1}.mp4"
                _download_generic(_pexels_file(chosen), source)
                clip = workdir / f"long_scene_{index + 1}.mp4"
                _edit_landscape(source, clip, CHAPTER_SECONDS, seed, botanical)
                user = chosen.get("user") or {}
                return clip, {
                    "provider": "Pexels",
                    "creator": str(user.get("name") or "Pexels contributor"),
                    "source_url": str(chosen.get("url") or ""),
                    "query": query,
                }
            except Exception as exc:
                print(f"Pexels capitulo {index + 1} no disponible para '{query}': {exc}")

    for query in queries:
        results = [item for item in commons_search(query, "video") if item["url"] not in used_commons]
        if not results:
            continue
        chosen = random.Random(seed ^ 0xC0AA).choice(results[: min(12, len(results))])
        used_commons.add(chosen["url"])
        source = workdir / f"long_commons_source_{index + 1}.mp4"
        commons_download(chosen["url"], source)
        clip = workdir / f"long_scene_{index + 1}.mp4"
        _edit_landscape(source, clip, CHAPTER_SECONDS, seed, botanical)
        return clip, {
            "provider": "Wikimedia Commons",
            "creator": str(chosen.get("artist") or "Wikimedia Commons contributor"),
            "license": str(chosen.get("license") or ""),
            "source_url": str(chosen.get("description_url") or ""),
            "query": query,
        }

    raise RuntimeError(f"No se encontro VIDEO REAL para el capitulo {index + 1}.")


def _kokoro_chapters(chapters: list[dict], workdir: Path) -> list[Path]:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice = os.getenv("KOKORO_VOICE", "em_alex")
    speed = float(os.getenv("KOKORO_SPEED", "0.95"))
    pipeline = KPipeline(lang_code="e")
    outputs: list[Path] = []
    for index, chapter in enumerate(chapters):
        chunks = []
        for _g, _p, audio in pipeline(str(chapter["narration"]), voice=voice, speed=speed, split_pattern=r"(?<=[.!?])\s+"):
            if audio is not None and len(audio):
                chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise RuntimeError(f"Kokoro no genero audio para capitulo {index + 1}.")
        out = workdir / f"long_voice_{index + 1}.wav"
        sf.write(out, np.concatenate(chunks), 24000, subtype="PCM_16")
        outputs.append(out)
    return outputs


def _chatterbox_chapters(chapters: list[dict], workdir: Path) -> list[Path]:
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
    outputs: list[Path] = []
    for index, chapter in enumerate(chapters):
        wav = model.generate(str(chapter["narration"]), language_id="es")
        out = workdir / f"long_voice_{index + 1}.wav"
        ta.save(str(out), wav.cpu(), model.sr)
        outputs.append(out)
    return outputs


def _generate_chapter_voices(meta: dict, workdir: Path) -> tuple[list[Path], str]:
    chapters = meta.get("chapters") or []
    provider = os.getenv("TTS_PROVIDER", "chatterbox").lower().strip()
    if provider == "chatterbox":
        try:
            return _chatterbox_chapters(chapters, workdir), "chatterbox-v3"
        except Exception as exc:
            if os.getenv("TTS_FALLBACK_KOKORO", "true").lower() != "true":
                raise
            print(f"Chatterbox V3 fallo en long-form ({exc}); regenerando toda la voz con Kokoro.")
            for path in workdir.glob("long_voice_*.wav"):
                path.unlink(missing_ok=True)
            return _kokoro_chapters(chapters, workdir), "kokoro-fallback"
    return _kokoro_chapters(chapters, workdir), "kokoro"


def _normalize_voice_segments(voices: list[Path], workdir: Path) -> Path:
    normalized: list[Path] = []
    for index, voice in enumerate(voices):
        out = workdir / f"long_voice_segment_{index + 1}.wav"
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(voice),
                "-af", f"highpass=f=70,lowpass=f=9000,acompressor=threshold=-18dB:ratio=1.9:attack=12:release=160,loudnorm=I=-16:TP=-1.5:LRA=8,apad=pad_dur={CHAPTER_SECONDS},atrim=0:{CHAPTER_SECONDS}",
                "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out),
            ],
            check=True,
        )
        normalized.append(out)
    manifest = workdir / "long_voice_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in normalized), encoding="utf-8")
    full = workdir / "long_voice_full.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest), "-c:a", "pcm_s16le", str(full)],
        check=True,
    )
    return full


def generate_long_video(channel: dict, meta: dict, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    chapters = meta.get("chapters") or []
    if len(chapters) != 10:
        raise RuntimeError("El video largo requiere exactamente 10 capitulos.")

    used_pexels: set[int] = set()
    used_commons: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []
    for index, chapter in enumerate(chapters):
        clip, credit = _get_real_clip(channel, meta, chapter, index, workdir, used_pexels, used_commons)
        clips.append(clip)
        credits.append(credit)

    visual_manifest = workdir / "long_visual_concat.txt"
    visual_manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "long_visual_5min.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(visual_manifest),
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
        ],
        check=True,
    )

    voices, used_tts = _generate_chapter_voices(meta, workdir)
    voice_full = _normalize_voice_segments(voices, workdir)
    music = workdir / "long_music.wav"
    make_pleasant_original_music(music, TOTAL_SECONDS, _seed(meta, 999))

    final = workdir / "video_5min.mp4"
    music_volume = "0.028" if "botanical" in channel.get("visual_mode", "") else "0.022"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(voice_full), "-i", str(music),
            "-filter_complex", f"[1:a]volume=1.0[v];[2:a]volume={music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(TOTAL_SECONDS),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final),
        ],
        check=True,
    )

    meta["source_credits"] = credits
    meta["tts_provider_used"] = used_tts
    return final
