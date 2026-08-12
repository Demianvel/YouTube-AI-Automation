from __future__ import annotations

import hashlib
import html
import random
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "YouTube-AI-Automation/1.0 (https://github.com/Demianvel/YouTube-AI-Automation)"
W, H = 1080, 1920
ALLOWED_LICENSE_PREFIXES = ("cc0", "public domain", "cc by")


def _seed(meta: dict, scene_index: int) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{scene_index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _clean(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    text = html.unescape(str(value or ""))
    return re.sub(r"<[^>]+>", "", text).strip()


def _search(query: str, media_type: str = "video") -> list[dict[str, Any]]:
    suffix = " filemime:video" if media_type == "video" else ""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query}{suffix}",
        "gsrnamespace": 6,
        "gsrlimit": 40,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "format": "json",
        "formatversion": 2,
        "origin": "*",
    }
    response = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=(15, 60))
    response.raise_for_status()
    pages = (response.json().get("query") or {}).get("pages") or []
    results: list[dict[str, Any]] = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        mime = str(info.get("mime") or "")
        if media_type == "video" and not mime.startswith("video/"):
            continue
        if media_type == "image" and not mime.startswith("image/"):
            continue
        metadata = info.get("extmetadata") or {}
        license_name = _clean(metadata.get("LicenseShortName")).lower()
        if not license_name.startswith(ALLOWED_LICENSE_PREFIXES):
            continue
        url = info.get("url")
        if not url:
            continue
        results.append({
            "title": page.get("title") or "",
            "url": str(url),
            "mime": mime,
            "license": _clean(metadata.get("LicenseShortName")),
            "artist": _clean(metadata.get("Artist")) or "Wikimedia Commons contributor",
            "credit": _clean(metadata.get("Credit")),
            "description_url": str(info.get("descriptionurl") or ""),
        })
    return results


def _queries(channel: dict, scene: dict) -> list[str]:
    primary = " ".join(str(scene.get("stock_query") or "").split())
    botanical = "botanical" in channel.get("visual_mode", "")
    if botanical:
        fallback = [
            "seed germination timelapse",
            "plant growth timelapse",
            "germinating seed plant",
            "flower growth timelapse",
        ]
    else:
        fallback = [
            "small business entrepreneur",
            "budget calculator money",
            "shop owner working",
            "packing orders business",
        ]
    return [q for q in [primary, *fallback] if q]


def _download(url: str, path: Path) -> None:
    with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=(20, 180)) as response:
        response.raise_for_status()
        with path.open("wb") as fh:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if not path.exists() or path.stat().st_size < 5000:
        raise RuntimeError("Wikimedia devolvio un archivo vacio o invalido.")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except (ValueError, TypeError):
        return 0.0


def _video_clip(source: Path, out: Path, duration: int, seed: int) -> None:
    source_duration = _probe_duration(source)
    rng = random.Random(seed)
    start = 0.0 if source_duration <= duration + 1 else rng.uniform(0, max(0.0, source_duration - duration - 0.2))
    loop = ["-stream_loop", "-1"] if source_duration and source_duration < duration else []
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,"
        "eq=contrast=1.025:saturation=1.035:brightness=0.003,"
        "unsharp=5:5:0.18:5:5:0,fps=30"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", *loop, "-ss", f"{start:.3f}", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def _image_clip(source: Path, out: Path, duration: int, seed: int) -> None:
    # Real-photo fallback with a subtle Ken Burns movement when no real video exists.
    zoom_rate = 0.00055 + (seed % 4) * 0.00008
    frames = duration * 30
    vf = (
        f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
        f"crop={W * 2}:{H * 2},"
        f"zoompan=z='min(zoom+{zoom_rate},1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps=30,setsar=1,eq=contrast=1.02:saturation=1.03"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def generate_wikimedia_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    scene_duration = int(channel["scene_seconds"])
    clips: list[Path] = []
    credits: list[dict[str, str]] = []
    used_urls: set[str] = set()

    for index, scene in enumerate(meta.get("scenes") or []):
        chosen: dict[str, Any] | None = None
        chosen_query = ""
        kind = "video"
        for query in _queries(channel, scene):
            results = [x for x in _search(query, "video") if x["url"] not in used_urls]
            if results:
                chosen = random.Random(_seed(meta, index)).choice(results[:12])
                chosen_query = query
                break
        if chosen is None:
            kind = "image"
            for query in _queries(channel, scene):
                results = [x for x in _search(query, "image") if x["url"] not in used_urls]
                if results:
                    chosen = random.Random(_seed(meta, index) ^ 0x1A2B).choice(results[:16])
                    chosen_query = query
                    break
        if chosen is None:
            raise RuntimeError(f"Wikimedia Commons no encontro material real para la escena {index + 1}.")

        used_urls.add(chosen["url"])
        ext = ".mp4" if kind == "video" else ".jpg"
        source = workdir / f"commons_source_{index + 1}{ext}"
        clip = workdir / f"commons_scene_{index + 1}.mp4"
        _download(chosen["url"], source)
        if kind == "video":
            _video_clip(source, clip, scene_duration, _seed(meta, index))
        else:
            _image_clip(source, clip, scene_duration, _seed(meta, index))
        clips.append(clip)
        credits.append({
            "provider": "Wikimedia Commons",
            "creator": chosen["artist"],
            "license": chosen["license"],
            "source_url": chosen["description_url"],
            "query": chosen_query,
            "media_type": kind,
        })

    if not clips:
        raise RuntimeError("No se generaron escenas con material real de Wikimedia Commons.")

    visual = workdir / "real_commons_visual.mp4"
    if len(clips) == 1:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clips[0]), "-an", "-c:v", "copy", str(visual)], check=True)
    else:
        manifest = workdir / "commons_concat.txt"
        manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
        ], check=True)

    meta["source_credits"] = credits
    total_duration = int(channel["scenes_per_short"]) * scene_duration
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
