from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import quote

import requests
from huggingface_hub import InferenceClient
from PIL import Image, ImageEnhance, ImageOps

from .hf_video import _safe_seed
from .spiritual_commons import make_spiritual_commons_clip

BASE = "https://gen.pollinations.ai/image/"
ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
W, H = 1080, 1920


def _seed(meta: dict, index: int) -> int:
    raw = f"spiritual|{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


def _style() -> str:
    return (
        "premium live-action photoreal cinematic spiritual scene, fully synthetic human representation of Jesus that looks like a real filmed adult man, "
        "shoulder-length wavy dark-brown hair with individual strands, full groomed beard, hazel-brown eyes, natural skin pores and fine facial detail, "
        "cream or ivory woven linen robe, beige mantle, realistic anatomy and hands, physically plausible golden sunlight, real-looking mountains valleys rivers lakes forests desert or aurora landscape, "
        "cinematic depth of field and photographic optics, peaceful hopeful atmosphere, vertical 9:16 portrait composition, no resemblance to a specific actor or celebrity, "
        "ABSOLUTELY NO cartoon, no illustration, no painting, no anime, no stylized 3D, no videogame look, no plastic CGI, no doll face, no text, no subtitles, no logo, no watermark"
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
    return f"Hugging Face Inference Providers / {model}"


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
    return "Pollinations authenticated image API"


def _local_reference(out: Path, seed: int) -> str:
    refs = sorted(REFERENCE_DIR.glob("jesus_reference_*.jpg"))
    if not refs:
        raise RuntimeError("No hay referencias fotorrealistas locales de emergencia.")
    chosen = refs[_safe_seed(seed) % len(refs)]
    with Image.open(chosen) as original:
        image = original.convert("RGB")
        if (_safe_seed(seed) // 7) % 2:
            image = ImageOps.mirror(image)
        brightness = 0.97 + ((_safe_seed(seed) % 9) / 100.0)
        contrast = 0.98 + (((_safe_seed(seed) // 11) % 8) / 100.0)
        color = 0.98 + (((_safe_seed(seed) // 17) % 9) / 100.0)
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)
        image = ImageEnhance.Color(image).enhance(color)
        image.save(out, format="JPEG", quality=95, optimize=True)
    if not out.exists() or out.stat().st_size < 20_000:
        raise RuntimeError("La referencia fotorrealista local no pudo prepararse.")
    return f"local_proven_photoreal_reference/{chosen.name}"


def _download(prompt: str, out: Path, seed: int) -> str:
    full_prompt = f"{prompt}, {_style()}"
    errors: list[str] = []

    try:
        return _download_hf(full_prompt, out, seed)
    except Exception as exc:
        errors.append(f"HF image: {exc}")
        print(f"Hugging Face text-to-image no disponible ({exc}); intentando respaldos.")

    if os.getenv("POLLINATIONS_API_KEY", "").strip():
        try:
            return _download_pollinations(full_prompt, out, seed)
        except Exception as exc:
            errors.append(f"Pollinations: {exc}")
    else:
        errors.append("Pollinations: falta POLLINATIONS_API_KEY")

    try:
        provider = _local_reference(out, seed)
        print("Usando referencia fotorrealista local de emergencia; no consume creditos de imagen.")
        return provider
    except Exception as exc:
        errors.append(f"local reference: {exc}")

    raise RuntimeError("No hubo generador de imagen fotorrealista disponible. " + "; ".join(errors))


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
    credits: list[dict[str, str]] = list(meta.get("source_credits") or [])
    used_commons_urls: set[str] = set()

    for index, scene in enumerate(meta.get("scenes") or []):
        prompt = str(scene.get("visual_prompt") or scene.get("stock_query") or "photoreal synthetic Jesus walking through a real peaceful valley at golden sunrise")
        prompts.append(prompt)
        image = workdir / f"spiritual_generated_{index + 1}.jpg"
        clip = workdir / f"spiritual_scene_{index + 1}.mp4"
        image_provider = _download(prompt, image, _seed(meta, index))

        # When paid/free AI image capacity is exhausted, do not mass-produce a
        # whole Short from the same three emergency portraits. Keep roughly one
        # Jesus anchor shot out of three and use fresh licensed nature/animal
        # B-roll for the other scenes. If Commons cannot provide enough variety,
        # the central visual-diversity upload gate will reject the final video.
        if image_provider.startswith("local_proven_photoreal_reference/") and index % 3 != 0:
            try:
                commons_clip, commons_provider, credit = make_spiritual_commons_clip(
                    meta, workdir, index, scene_duration, used_commons_urls
                )
                clips.append(commons_clip)
                provider_labels.append(commons_provider)
                credits.append(credit)
                continue
            except Exception as exc:
                print(f"Commons espiritual no disponible en escena {index + 1} ({exc}); conservando referencia local para que el gate final decida.")

        _animate(image, clip, scene_duration, index)
        provider_labels.append(f"{image_provider} + cinematic camera motion")
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
    meta["source_credits"] = credits
    meta["synthetic_visual"] = True
    meta["character_reference_profile"] = "dioshablahoyia_photoreal_human_v2"
    meta["render_quality"] = "1080x1920_30fps_photoreal_mixed_fallback"
    meta["still_fallback_explicitly_enabled"] = True
    meta["mixed_licensed_nature_fallback"] = True
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
