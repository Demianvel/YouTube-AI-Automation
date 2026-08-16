from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from .hf_video import _safe_seed

BASE = "https://gen.pollinations.ai/image/"
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
W, H = 1080, 1920


def _seed(meta: dict, index: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"spiritual-variety-v3|{meta.get('topic','')}|{meta.get('title','')}|{index}|{marker}"
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


def _style() -> str:
    return (
        "premium live-action photoreal cinematic spiritual scene about Jesus, God and the Bible, using either an original fully synthetic recurring representation of Jesus or a reverent symbolic cutaway of God's presence through Scripture, natural light, creation, a simple cross, a dove, an empty tomb or a shepherd image, "
        "when Jesus appears: shoulder-length wavy dark-brown hair with individual strands, full groomed beard, hazel-brown eyes, natural skin pores and fine facial detail, cream or ivory woven linen robe, beige or muted-red mantle, realistic anatomy and hands, "
        "vary camera distance, body position, action, environment and lighting from adjacent scenes; do not make every image the same centered talking portrait, "
        "physically plausible sunrise, moonlight or soft golden illumination, real mountains valleys rivers lakes forests olive groves desert coast snow aurora gardens or ancient stone paths, "
        "cinematic depth of field and photographic optics, peaceful hopeful loving atmosphere, vertical 9:16 portrait composition, no resemblance to a specific actor or celebrity, "
        "NO unrelated people, politics, sports, news, products, social networks, Wikipedia, Wikimedia, reused stock media, cartoon, illustration, painting, anime, stylized 3D, videogame look, plastic CGI, doll face, text, subtitles, logo or watermark"
    )


def _download_hf(full_prompt: str, out: Path, seed: int) -> str:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN no esta disponible para text-to-image.")
    provider = os.getenv("HF_IMAGE_PROVIDER", "auto").strip() or "auto"
    model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
    client = InferenceClient(provider=provider, api_key=token, timeout=180)
    image = client.text_to_image(full_prompt, model=model, seed=_safe_seed(seed))
    if image is None:
        raise RuntimeError("Hugging Face text-to-image no devolvio una imagen.")
    image.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
    if not out.exists() or out.stat().st_size < 20_000:
        raise RuntimeError("Hugging Face text-to-image devolvio una imagen invalida.")
    return f"Hugging Face generated image / {model}"


def _download_pollinations(full_prompt: str, out: Path, seed: int) -> str:
    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("POLLINATIONS_API_KEY no esta configurada.")
    url = BASE + quote(full_prompt, safe="")
    params = {
        "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        "width": W,
        "height": H,
        "seed": _safe_seed(seed),
        "nologo": "true",
        "enhance": "true",
    }
    headers = {
        "User-Agent": "YouTube-AI-Automation/1.0",
        "Authorization": f"Bearer {key}",
    }
    response = requests.get(url, params=params, headers=headers, timeout=(20, 180))
    response.raise_for_status()
    if len(response.content) < 20_000:
        raise RuntimeError("Pollinations no devolvio una imagen espiritual fotorrealista valida.")
    out.write_bytes(response.content)
    return "Pollinations generated original image"


def _centering(variant: int) -> tuple[float, float]:
    values = (
        (0.50, 0.50), (0.42, 0.48), (0.58, 0.48),
        (0.50, 0.40), (0.38, 0.42), (0.62, 0.42),
        (0.45, 0.58), (0.55, 0.58), (0.50, 0.32),
    )
    return values[variant % len(values)]


def _light_overlay(image: Image.Image, variant: int) -> Image.Image:
    base = image.convert("RGBA")
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    left = variant % 2 == 0
    cx = int(W * (0.18 if left else 0.82))
    cy = int(H * (0.16 + 0.05 * (variant % 3)))
    radius = int(W * (0.34 + 0.03 * (variant % 4)))
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(255, 228, 164, 54),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(radius // 2))
    return Image.alpha_composite(base, glow).convert("RGB")


def _vignette(image: Image.Image, strength: int) -> Image.Image:
    mask = Image.new("L", image.size, max(25, min(115, strength)))
    draw = ImageDraw.Draw(mask)
    margin_x = int(W * 0.06)
    margin_y = int(H * 0.04)
    draw.ellipse(
        (margin_x, margin_y, W - margin_x, H - margin_y),
        fill=0,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(int(W * 0.16)))
    shadow = Image.new("RGB", image.size, (8, 9, 14))
    return Image.composite(shadow, image, mask)


def _local_variant(original: Image.Image, seed: int) -> tuple[Image.Image, int]:
    safe = _safe_seed(seed)
    variant = safe % 24
    source = original.convert("RGB")
    if (safe // 7) % 2:
        source = ImageOps.mirror(source)

    centering = _centering(variant)
    if variant < 12:
        # Twelve full-frame crops with varied focal position and zoom.
        zoom = 1.00 + (variant % 4) * 0.045
        fitted = ImageOps.fit(
            source,
            (int(W * zoom), int(H * zoom)),
            method=Image.Resampling.LANCZOS,
            centering=centering,
        )
        left = max(0, (fitted.width - W) // 2)
        top = max(0, (fitted.height - H) // 2)
        image = fitted.crop((left, top, left + W, top + H))
    else:
        # Twelve layered compositions: softly blurred photographic background plus
        # a sharper reframed foreground. This preserves photorealism while changing
        # silhouette, scale and negative space for every scene.
        background = ImageOps.fit(
            source,
            (W, H),
            method=Image.Resampling.LANCZOS,
            centering=centering,
        ).filter(ImageFilter.GaussianBlur(24 + (variant % 4) * 4))
        background = ImageEnhance.Brightness(background).enhance(0.68 + (variant % 3) * 0.06)
        max_w = int(W * (0.82 + (variant % 3) * 0.05))
        max_h = int(H * (0.78 + (variant % 2) * 0.08))
        foreground = ImageOps.contain(source, (max_w, max_h), method=Image.Resampling.LANCZOS)
        foreground = ImageEnhance.Sharpness(foreground).enhance(1.08)
        canvas = background.convert("RGBA")
        x_shift = (-1, 0, 1)[variant % 3] * int(W * 0.06)
        y_shift = (-1, 0, 1)[(variant // 3) % 3] * int(H * 0.035)
        x = (W - foreground.width) // 2 + x_shift
        y = (H - foreground.height) // 2 + y_shift
        alpha = Image.new("L", foreground.size, 255)
        edge = Image.new("L", foreground.size, 0)
        edge_draw = ImageDraw.Draw(edge)
        edge_draw.rounded_rectangle(
            (8, 8, foreground.width - 8, foreground.height - 8),
            radius=max(24, foreground.width // 18),
            fill=255,
        )
        edge = edge.filter(ImageFilter.GaussianBlur(10))
        alpha = ImageChops_lighter(alpha, edge)
        canvas.alpha_composite(foreground.convert("RGBA"), dest=(x, y))
        image = canvas.convert("RGB")

    brightness = 0.96 + ((safe % 11) / 100.0)
    contrast = 0.98 + (((safe // 11) % 10) / 100.0)
    color = 0.97 + (((safe // 17) % 12) / 100.0)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(color)
    image = _light_overlay(image, variant)
    image = _vignette(image, 50 + (variant % 4) * 10)
    return image, variant


def ImageChops_lighter(first: Image.Image, second: Image.Image) -> Image.Image:
    # Local helper avoids importing the full ImageChops module in older Pillow
    # builds while preserving a soft alpha edge.
    return Image.fromarray(
        __import__("numpy").maximum(
            __import__("numpy").asarray(first, dtype="uint8"),
            __import__("numpy").asarray(second, dtype="uint8"),
        )
    )


def _local_reference(out: Path, seed: int) -> str:
    refs = sorted(REFERENCE_DIR.glob("jesus_reference_*.jpg"))
    if not refs:
        raise RuntimeError("No hay referencias fotorrealistas locales de emergencia.")
    safe = _safe_seed(seed)
    chosen = refs[(safe // 29) % len(refs)]
    with Image.open(chosen) as original:
        image, variant = _local_variant(original, safe)
        image.save(out, format="JPEG", quality=95, optimize=True)
    if not out.exists() or out.stat().st_size < 20_000:
        raise RuntimeError("La referencia fotorrealista local no pudo prepararse.")
    return f"local_project_jesus_reference/{chosen.name}/variant_{variant:02d}_of_24"


def _download(prompt: str, out: Path, seed: int) -> str:
    full_prompt = f"{prompt}, {_style()}"
    errors: list[str] = []

    try:
        return _download_hf(full_prompt, out, seed)
    except Exception as exc:
        errors.append(f"HF image: {exc}")
        print(f"Hugging Face text-to-image no disponible ({exc}); intentando generador original de respaldo.")

    if os.getenv("POLLINATIONS_API_KEY", "").strip():
        try:
            return _download_pollinations(full_prompt, out, seed)
        except Exception as exc:
            errors.append(f"Pollinations: {exc}")
    else:
        errors.append("Pollinations: falta POLLINATIONS_API_KEY")

    try:
        provider = _local_reference(out, seed)
        print("Usando una variante fotorrealista local del proyecto; no se descarga multimedia externa.")
        return provider
    except Exception as exc:
        errors.append(f"local reference: {exc}")

    raise RuntimeError("No hubo generador visual original disponible. " + "; ".join(errors))


def _animate(source: Path, out: Path, duration: int, index: int) -> None:
    frames = duration * 30
    motion = index % 6
    zoom_rate = 0.00055 + motion * 0.00005
    if motion == 0:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == 1:
        x_expr, y_expr = "min(iw-iw/zoom,(iw-iw/zoom)*on/max(1,duration*30))", "ih/2-(ih/zoom/2)"
    elif motion == 2:
        x_expr, y_expr = "max(0,(iw-iw/zoom)*(1-on/max(1,duration*30)))", "ih/2-(ih/zoom/2)"
    elif motion == 3:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "min(ih-ih/zoom,(ih-ih/zoom)*on/max(1,duration*30))"
    elif motion == 4:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "max(0,(ih-ih/zoom)*(1-on/max(1,duration*30)))"
    else:
        x_expr = "min(iw-iw/zoom,(iw-iw/zoom)*on/max(1,duration*30))"
        y_expr = "min(ih-ih/zoom,(ih-ih/zoom)*on/max(1,duration*30))"
    vf = (
        f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
        f"crop={W * 2}:{H * 2},"
        f"zoompan=z='min(zoom+{zoom_rate:.5f},1.09)':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps=30,"
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
        prompt = str(scene.get("visual_prompt") or "original synthetic Jesus walking through a peaceful biblical landscape at golden sunrise")
        prompts.append(prompt)
        image = workdir / f"spiritual_generated_{index + 1}.jpg"
        clip = workdir / f"spiritual_scene_{index + 1}.mp4"
        image_provider = _download(prompt, image, _seed(meta, index))
        _animate(image, clip, scene_duration, index)
        provider_labels.append(f"{image_provider} + original cinematic motion_{index % 6}")
        clips.append(clip)

    if not clips:
        raise RuntimeError("No se generaron escenas espirituales originales de respaldo.")

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
    meta["source_credits"] = []
    meta["synthetic_visual"] = True
    meta["external_media_allowed"] = False
    meta["original_generated_media_only"] = True
    meta["character_reference_profile"] = "dioshablahoyia_photoreal_human_v3_high_variety"
    meta["render_quality"] = "1080x1920_30fps_photoreal_original_high_variety_fallback"
    meta["still_fallback_explicitly_enabled"] = True
    meta["local_visual_variants_per_reference"] = 24
    meta["local_reference_count"] = len(list(REFERENCE_DIR.glob("jesus_reference_*.jpg")))
    meta["mixed_licensed_nature_fallback"] = False
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
