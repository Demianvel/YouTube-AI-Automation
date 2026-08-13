from __future__ import annotations

import hashlib
import os
import random
import subprocess
from pathlib import Path
from typing import Any

import requests

from .wikimedia_video import _download as commons_download
from .wikimedia_video import _search as commons_search

PEXELS_SEARCH = "https://api.pexels.com/v1/videos/search"
FPS = 30


def _seed(meta: dict, index: int) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _probe(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except Exception:
        return 0.0


def _pexels_candidates(query: str, portrait: bool) -> list[dict[str, Any]]:
    key = os.getenv("PEXELS_API_KEY", "").strip()
    if not key:
        return []
    response = requests.get(
        PEXELS_SEARCH,
        headers={"Authorization": key},
        params={"query": query, "per_page": 40, "orientation": "portrait" if portrait else "landscape"},
        timeout=(15, 60),
    )
    response.raise_for_status()
    return response.json().get("videos") or []


def _pexels_file(video: dict[str, Any], portrait: bool) -> str:
    files = [f for f in (video.get("video_files") or []) if f.get("link") and str(f.get("file_type") or "").lower() == "video/mp4"]
    if not files:
        raise RuntimeError("Pexels no devolvio MP4.")
    def score(f: dict[str, Any]) -> tuple[int, int]:
        w, h = int(f.get("width") or 0), int(f.get("height") or 0)
        orientation = 1 if ((h >= w) if portrait else (w >= h)) else 0
        return orientation, min(w, 1920) * min(h, 1920)
    files.sort(key=score, reverse=True)
    return str(files[0]["link"])


def _download_http(url: str, path: Path) -> None:
    path.unlink(missing_ok=True)
    with requests.get(url, stream=True, timeout=(20, 180)) as response:
        response.raise_for_status()
        with path.open("wb") as fh:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError("Descarga de video invalida.")


def _edit(source: Path, out: Path, seconds: int, portrait: bool, seed: int) -> None:
    src_duration = _probe(source)
    if src_duration <= 0:
        raise RuntimeError("Fuente sin video valido.")
    rng = random.Random(seed)
    start = 0.0 if src_duration <= seconds + 1 else rng.uniform(0.0, max(0.0, src_duration - seconds - 0.2))
    loop = ["-stream_loop", "-1"] if src_duration < seconds else []
    w, h = (1080, 1920) if portrait else (1920, 1080)
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,"
        "eq=contrast=1.05:saturation=1.08:brightness=0.002,"
        "unsharp=5:5:0.16:5:5:0,fps=30"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", *loop, "-ss", f"{start:.3f}", "-i", str(source),
        "-t", str(seconds), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)
    if _probe(out) < max(1.0, seconds - 1.0):
        raise RuntimeError("El clip editado quedo incompleto.")


def _get_segment(query: str, workdir: Path, index: int, seconds: int, portrait: bool, used: set[str], seed: int) -> tuple[Path, dict[str, str]]:
    # Prefer Pexels when the optional API key is configured.
    try:
        candidates = _pexels_candidates(query, portrait)
    except Exception as exc:
        print(f"Pexels fallo para {query}: {exc}")
        candidates = []
    random.Random(seed).shuffle(candidates)
    for video in candidates[:12]:
        vid = str(video.get("id") or "")
        if not vid or f"pexels:{vid}" in used:
            continue
        source = workdir / f"music_src_{index}.mp4"
        clip = workdir / f"music_scene_{index}.mp4"
        try:
            _download_http(_pexels_file(video, portrait), source)
            _edit(source, clip, seconds, portrait, seed)
            used.add(f"pexels:{vid}")
            user = video.get("user") or {}
            source.unlink(missing_ok=True)
            return clip, {
                "provider": "Pexels",
                "creator": str(user.get("name") or "Pexels contributor"),
                "source_url": str(video.get("url") or ""),
                "query": query,
            }
        except Exception as exc:
            print(f"Descartando Pexels music segment {index}: {exc}")
            source.unlink(missing_ok=True)
            clip.unlink(missing_ok=True)

    # Open-media fallback. Only real video files, never photos.
    try:
        common = [x for x in commons_search(query, "video") if f"commons:{x['url']}" not in used]
    except Exception as exc:
        print(f"Commons fallo para {query}: {exc}")
        common = []
    random.Random(seed ^ 0xCAFE).shuffle(common)
    for item in common[:16]:
        source = workdir / f"music_src_{index}.media"
        clip = workdir / f"music_scene_{index}.mp4"
        try:
            commons_download(item["url"], source)
            _edit(source, clip, seconds, portrait, seed)
            used.add(f"commons:{item['url']}")
            source.unlink(missing_ok=True)
            return clip, {
                "provider": "Wikimedia Commons",
                "creator": str(item.get("artist") or "Wikimedia Commons contributor"),
                "license": str(item.get("license") or ""),
                "source_url": str(item.get("description_url") or ""),
                "query": query,
            }
        except Exception as exc:
            print(f"Descartando Commons music segment {index}: {exc}")
            source.unlink(missing_ok=True)
            clip.unlink(missing_ok=True)

    raise RuntimeError(f"No se encontro VIDEO REAL utilizable para '{query}'.")


def render_music_video(meta: dict, music_path: Path, workdir: Path) -> Path:
    duration = int(meta["duration_seconds"])
    portrait = bool(meta.get("is_short"))
    queries = list(meta.get("visual_queries") or [])
    if not queries:
        raise RuntimeError("Faltan consultas visuales para el videoclip.")

    segment_count = max(5, min(30, duration // 30))
    segment_seconds = max(8, int((duration + segment_count - 1) / segment_count))
    used: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []

    for index in range(segment_count):
        query = queries[index % len(queries)]
        try:
            clip, credit = _get_segment(query, workdir, index + 1, segment_seconds, portrait, used, _seed(meta, index))
        except RuntimeError:
            # Wider but still cinematic real-camera fallback queries.
            fallback = "cinematic nature landscape" if meta.get("faith_theme") else "cinematic city night lights"
            clip, credit = _get_segment(fallback, workdir, index + 1, segment_seconds, portrait, used, _seed(meta, index) ^ 0x1111)
        clips.append(clip)
        credits.append(credit)

    manifest = workdir / "music_visual_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "music_visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-t", str(duration), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
    ], check=True)

    out = workdir / ("demianvelo_short_1min.mp4" if portrait else f"demianvelo_{meta['duration_minutes']}min.mp4")
    wave_w, wave_h = (900, 110) if portrait else (1500, 100)
    overlay_y = "H-h-140" if portrait else "H-h-70"
    filter_complex = (
        f"[1:a]showwaves=s={wave_w}x{wave_h}:mode=line:rate=30:colors=white@0.34,format=yuva420p[w];"
        f"[0:v][w]overlay=(W-w)/2:{overlay_y}:shortest=1[v]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(music_path),
        "-filter_complex", filter_complex, "-map", "[v]", "-map", "1:a:0", "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-c:a", "aac", "-b:a", "256k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)

    meta["source_credits"] = credits
    meta["music_source"] = "original_synthesized_in_repository_no_third_party_samples"
    if not out.exists() or _probe(out) < duration - 2:
        raise RuntimeError("El videoclip final quedo incompleto.")
    return out
