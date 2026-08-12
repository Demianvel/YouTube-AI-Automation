from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests

BASE = "https://gen.pollinations.ai/image/"
W, H = 1080, 1920


def _seed(meta: dict, index: int) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _download_generated_image(prompt: str, out: Path, seed: int) -> None:
    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    full_prompt = (
        prompt
        + ", premium polished 3D animated family film look, cute fictional characters, "
          "soft cinematic lighting, expressive faces, clean materials, colorful environment, "
          "vertical composition, no text, no logo, no watermark, no real people"
    )
    url = BASE + quote(full_prompt, safe="")
    params = {
        "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        "width": W,
        "height": H,
        "seed": seed,
        "nologo": "true",
        "enhance": "true",
    }
    headers = {"User-Agent": "YouTube-AI-Automation/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    response = requests.get(url, params=params, headers=headers, timeout=(20, 180))
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "image" not in content_type and len(response.content) < 20_000:
        raise RuntimeError(f"Pollinations no devolvio una imagen valida: {content_type}")
    out.write_bytes(response.content)
    if out.stat().st_size < 20_000:
        raise RuntimeError("La imagen generada por Pollinations es demasiado pequena o invalida.")


def _animate_image(source: Path, out: Path, duration: int, index: int) -> None:
    frames = duration * 30
    if index % 3 == 0:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif index % 3 == 1:
        x_expr = "min(iw-iw/zoom,(iw-iw/zoom)*on/max(1,duration*30))"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "min(ih-ih/zoom,(ih-ih/zoom)*on/max(1,duration*30))"

    vf = (
        f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
        f"crop={W * 2}:{H * 2},"
        f"zoompan=z='min(zoom+0.0008,1.08)':x='{x_expr}':y='{y_expr}':"
        f"d={frames}:s={W}x{H}:fps=30,setsar=1,"
        "eq=contrast=1.02:saturation=1.05:brightness=0.005"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def generate_pollinations_kids_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    scene_duration = int(channel["scene_seconds"])
    scenes = meta.get("scenes") or []
    clips: list[Path] = []

    for index, scene in enumerate(scenes):
        image = workdir / f"kids_generated_{index + 1}.jpg"
        clip = workdir / f"kids_scene_{index + 1}.mp4"
        prompt = str(scene.get("visual_prompt") or scene.get("stock_query") or "cute 3D kids adventure")
        _download_generated_image(prompt, image, _seed(meta, index))
        _animate_image(image, clip, scene_duration, index)
        clips.append(clip)

    if not clips:
        raise RuntimeError("No se generaron escenas 3D para EnViKids.")

    manifest = workdir / "kids_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "kids_generated_visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(visual),
    ], check=True)

    total_duration = int(channel["scenes_per_short"]) * scene_duration
    meta["generated_visual_provider"] = "Pollinations image API"
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
