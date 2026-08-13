from __future__ import annotations

import hashlib
import os
import random
import subprocess
from pathlib import Path
from typing import Any

import requests

PEXELS_SEARCH = "https://api.pexels.com/v1/videos/search"
W, H = 1080, 1920


def _seed(meta: dict, scene_index: int) -> int:
    run = os.getenv("GITHUB_RUN_NUMBER", "").strip()
    raw = f"{meta.get('content_family','')}|{meta.get('topic','')}|{meta.get('title','')}|{scene_index}|{run}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _api_key() -> str:
    key = os.getenv("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Falta PEXELS_API_KEY. Configurala como GitHub Secret para usar metraje real gratuito."
        )
    return key


def _search(query: str, portrait_first: bool = True) -> list[dict[str, Any]]:
    headers = {"Authorization": _api_key()}
    attempts = [True, False] if portrait_first else [False]
    last_error = None

    for portrait in attempts:
        params: dict[str, Any] = {"query": query, "per_page": 60}
        if portrait:
            params["orientation"] = "portrait"
        try:
            response = requests.get(
                PEXELS_SEARCH,
                headers=headers,
                params=params,
                timeout=(15, 45),
            )
            response.raise_for_status()
            videos = response.json().get("videos") or []
            if videos:
                return videos
        except requests.RequestException as exc:
            last_error = exc

    if last_error:
        raise RuntimeError(f"Pexels API fallo buscando '{query}': {last_error}")
    return []


def _choose_video(videos: list[dict[str, Any]], duration: int, seed: int, used_ids: set[int]) -> dict[str, Any]:
    candidates = [v for v in videos if int(v.get("id", 0)) not in used_ids and v.get("video_files")]
    if not candidates:
        candidates = [v for v in videos if v.get("video_files")]
    if not candidates:
        raise RuntimeError("Pexels no devolvio archivos de video utilizables.")

    def score(v: dict[str, Any]) -> tuple[int, int, int]:
        width = int(v.get("width") or 0)
        height = int(v.get("height") or 0)
        dur = int(v.get("duration") or 0)
        portrait = 1 if height > width else 0
        enough = 1 if dur >= duration else 0
        pixels = width * height
        return (portrait, enough, pixels)

    candidates.sort(key=score, reverse=True)
    # Use a wider high-quality pool and the GitHub run-dependent seed. This
    # avoids repeatedly selecting the same first handful of stock clips.
    top = candidates[: min(28, len(candidates))]
    chosen = top[seed % len(top)]
    used_ids.add(int(chosen.get("id", 0)))
    return chosen


def _choose_file(video: dict[str, Any]) -> str:
    files = [
        f for f in (video.get("video_files") or [])
        if f.get("link") and str(f.get("file_type", "")).lower() == "video/mp4"
    ]
    if not files:
        raise RuntimeError(f"Video Pexels {video.get('id')} no tiene MP4 disponible.")

    def score(f: dict[str, Any]) -> tuple[int, int, int]:
        width = int(f.get("width") or 0)
        height = int(f.get("height") or 0)
        portrait = 1 if height > width else 0
        min_side = min(width, height)
        hd = 2 if min_side >= 720 else 1 if min_side >= 480 else 0
        pixels = width * height
        return (portrait, hd, pixels)

    files.sort(key=score, reverse=True)
    return str(files[0]["link"])


def _download(url: str, path: Path) -> None:
    with requests.get(url, stream=True, timeout=(20, 180)) as response:
        response.raise_for_status()
        with path.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError("La descarga de Pexels produjo un archivo vacio o invalido.")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    try:
        return max(0.0, float(result.stdout.strip()))
    except ValueError:
        return 0.0


def _edit_clip(source: Path, out: Path, duration: int, seed: int, botanical: bool) -> None:
    source_duration = _probe_duration(source)
    rng = random.Random(seed ^ 0x5058454C53)

    if botanical or source_duration <= duration + 1:
        start = 0.0
    else:
        start = rng.uniform(0.0, max(0.0, source_duration - duration - 0.2))

    input_args: list[str] = []
    if source_duration and source_duration < duration:
        input_args.extend(["-stream_loop", "-1"])
    input_args.extend(["-ss", f"{start:.3f}", "-i", str(source)])

    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,"
        "eq=contrast=1.035:saturation=1.045:brightness=0.004,"
        "unsharp=5:5:0.22:5:5:0.0,fps=30"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", *input_args,
            "-t", str(duration), "-vf", vf, "-an",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )


def _queries(channel: dict, scene: dict, meta: dict) -> list[str]:
    primary = " ".join(str(scene.get("stock_query") or "").split())
    botanical = "botanical" in channel.get("visual_mode", "")
    family = str(meta.get("content_family") or "").lower().strip()

    if botanical:
        # Species-specific BrotaVida runs MUST NOT fall back to a generic plant
        # search, because that was the main source of visually repeated uploads.
        species_specific = family.startswith("germinacion real de ")
        if species_specific:
            return [q for q in [primary] if q]
        fallback = [
            "roots growing macro timelapse",
            "seed sprout soil timelapse",
            "seedling first leaves timelapse",
        ]
    else:
        fallback = [
            "small business entrepreneur working",
            "budget planning calculator desk",
            "small business packing orders",
        ]
    return [q for q in [primary, *fallback] if q]


def generate_pexels_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    duration_per_scene = int(channel["scene_seconds"])
    botanical = "botanical" in channel.get("visual_mode", "")
    used_ids: set[int] = set()
    edited: list[Path] = []
    credits: list[dict[str, Any]] = []

    for i, scene in enumerate(meta.get("scenes") or []):
        videos: list[dict[str, Any]] = []
        chosen_query = ""
        for query in _queries(channel, scene, meta):
            videos = _search(query, portrait_first=not botanical)
            if videos:
                chosen_query = query
                break
        if not videos:
            family = meta.get("content_family") or meta.get("topic") or "esta planta"
            raise RuntimeError(
                f"No se encontro timelapse real verificable para '{family}'. "
                "Se rechaza usar una planta generica o repetir otro clip."
            )

        seed = _seed(meta, i)
        video = _choose_video(videos, duration_per_scene, seed, used_ids)
        video_url = _choose_file(video)
        source = workdir / f"pexels_source_{i + 1}.mp4"
        clip = workdir / f"pexels_scene_{i + 1}.mp4"
        _download(video_url, source)
        _edit_clip(source, clip, duration_per_scene, seed, botanical)
        edited.append(clip)

        user = video.get("user") or {}
        credits.append(
            {
                "provider": "Pexels",
                "video_id": video.get("id"),
                "creator": user.get("name") or "Pexels contributor",
                "creator_url": user.get("url") or "",
                "source_url": video.get("url") or "",
                "query": chosen_query,
            }
        )

    if not edited:
        raise RuntimeError("No se generaron escenas con metraje real.")

    visual = workdir / "real_stock_visual.mp4"
    if len(edited) == 1:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(edited[0]), "-an", "-c:v", "copy", str(visual)],
            check=True,
        )
    else:
        manifest = workdir / "pexels_concat.txt"
        manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in edited), encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
            ],
            check=True,
        )

    meta["source_credits"] = credits
    total_duration = int(channel["scenes_per_short"]) * duration_per_scene
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
