from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests

from .hf_video import _safe_seed

BASE = "https://gen.pollinations.ai/image/"
W, H = 1080, 1920


def _seed(meta: dict, index: int) -> int:
    raw = f"spiritual|{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


def _style() -> str:
    return (
        "premium live-action photoreal cinematic spiritual scene, fully synthetic human representation of Jesus that looks like a real filmed adult man, "
        "shoulder-length wavy dark-brown hair with individual strands, full groomed beard, hazel-brown eyes, natural skin pores and fine facial detail, "
        "cream or ivory woven linen robe, beige mantle, realistic anatomy and hands, physically plausible golden sunlight, real-looking mountains valleys rivers lakes forests desert or aurora landscape, "
        "cinematic depth of field and photographic optics, peaceful hopeful atmosphere, vertical 9:16, no resemblance to a specific actor or celebrity, "
        "ABSOLUTELY NO cartoon, no illustration, no painting, no anime, no stylized 3D, no videogame look, no plastic CGI, no doll face, no text, no subtitles, no logo, no watermark"
    )


def _download(prompt: str, out: Path, seed: int) -> None:
    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    full_prompt = f"{prompt}, {_style()}"
    url = BASE + quote(full_prompt, safe="")
    params = {
        "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        "width": W,
        "height": H,
        "seed": _safe_seed(seed),
        "nologo": "true",
        "enhance": "true",
    }
    headers = {"User-Agent": "YouTube-AI-Automation/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    response = requests.get(url, params=params, headers=headers, timeout=(20, 180))
    response.raise_for_status()
    if len(response.content) < 20_000:
        raise RuntimeError("El generador de imagenes no devolvio una imagen espiritual fotorrealista valida.")
    out.write_bytes(response.content)


def _animate(source: Path, out: Path, duration: int, index: int) -> None:
    frames = duration * 30
    zoom_rate = 0.0007 + (index % 3) * 0.0001
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
        f"zoompan=z='min(zoom+{zoom_rate:.4f},1.08)':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps=30,"
        "setsar=1,eq=contrast=1.025:saturation=1.045:brightness=0.004"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def generate_spiritual_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    if os.getenv("SPIRITUAL_ALLOW_STILL_FALLBACK", "false").lower().strip() != "true":
        raise RuntimeError(
            "El fallback de imagen fija esta deshabilitado para Dios Habla Hoy IA: se exige video humano fotorrealista con movimiento."
        )

    scene_duration = int(channel["scene_seconds"])
    clips: list[Path] = []
    prompts: list[str] = []
    provider_labels: list[str] = []

    for index, scene in enumerate(meta.get("scenes") or []):
        prompt = str(scene.get("visual_prompt") or scene.get("stock_query") or "photoreal synthetic Jesus walking through a real peaceful valley at golden sunrise")
        prompts.append(prompt)
        image = workdir / f"spiritual_generated_{index + 1}.jpg"
        clip = workdir / f"spiritual_scene_{index + 1}.mp4"
        _download(prompt, image, _seed(meta, index))
        _animate(image, clip, scene_duration, index)
        provider_labels.append("Pollinations photoreal image API + cinematic camera motion")
        clips.append(clip)

    if not clips:
        raise RuntimeError("No se generaron escenas espirituales fotorrealistas de respaldo.")

    manifest = workdir / "spiritual_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "spiritual_generated_visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(visual),
    ], check=True)

    total_duration = int(channel["scenes_per_short"]) * scene_duration
    meta["generated_visual_provider"] = provider_labels
    meta["generated_video_prompts"] = prompts
    meta["synthetic_visual"] = True
    meta["character_reference_profile"] = "dioshablahoyia_photoreal_human_v2"
    meta["render_quality"] = "1080x1920_30fps_photoreal_still_fallback"
    meta["still_fallback_explicitly_enabled"] = True
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
