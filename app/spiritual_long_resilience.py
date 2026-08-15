from __future__ import annotations

import os
import subprocess
from pathlib import Path

from huggingface_hub import InferenceClient

from .hf_video import _safe_seed
from .spiritual_image import _local_reference
from . import wikimedia_video as commons

_COMMONS_QUERIES = (
    "mountain sunrise landscape",
    "forest stream nature",
    "ocean waves sunrise",
    "lake mountains landscape",
    "olive grove landscape",
    "desert dunes sunrise",
    "snow mountain landscape",
    "meadow sheep nature",
    "wild birds nature",
    "river valley landscape",
    "forest sunlight mist",
    "clouds sky landscape",
)


def _download_commons_landscape(out: Path, seed: int) -> str:
    for step in range(len(_COMMONS_QUERIES)):
        query = _COMMONS_QUERIES[(_safe_seed(seed) + step * 5) % len(_COMMONS_QUERIES)]
        results = commons._search(query, "image")
        if not results:
            continue
        chosen = results[_safe_seed(seed ^ (step + 1) * 7919) % min(len(results), 16)]
        commons._download(chosen["url"], out)
        return f"Wikimedia Commons licensed image/{chosen.get('title','nature')}"
    raise RuntimeError("Wikimedia Commons no encontro un paisaje con licencia admitida.")


def download_landscape_image(prompt: str, out: Path, seed: int, style: str) -> str:
    """Prefer new AI imagery, then licensed diverse Commons nature, then local reference."""
    full_prompt = f"{prompt}, {style}"
    errors: list[str] = []
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        try:
            provider = os.getenv("HF_IMAGE_PROVIDER", "auto").strip() or "auto"
            model = os.getenv("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell").strip()
            client = InferenceClient(provider=provider, api_key=token, timeout=180)
            image = client.text_to_image(full_prompt, model=model, seed=_safe_seed(seed))
            if image is None:
                raise RuntimeError("HF no devolvio imagen")
            image.convert("RGB").save(out, format="JPEG", quality=95, optimize=True)
            if not out.exists() or out.stat().st_size < 20_000:
                raise RuntimeError("HF devolvio una imagen invalida")
            return f"Hugging Face Inference Providers / {model}"
        except Exception as exc:
            errors.append(f"HF image: {exc}")

    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    if key:
        try:
            from urllib.parse import quote
            import requests

            url = "https://gen.pollinations.ai/image/" + quote(full_prompt, safe="")
            params = {
                "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
                "width": 1920,
                "height": 1080,
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
                raise RuntimeError("Pollinations devolvio una imagen invalida")
            out.write_bytes(response.content)
            return "Pollinations authenticated image API"
        except Exception as exc:
            errors.append(f"Pollinations: {exc}")
    else:
        errors.append("Pollinations: falta POLLINATIONS_API_KEY")

    # Prefer genuinely different licensed nature imagery before recycling the
    # tiny local Jesus reference set. Long-form can use these visual breathing
    # moments while the continuous narration carries the biblical reflection.
    try:
        provider = _download_commons_landscape(out, seed)
        print("Usando paisaje con licencia abierta de Wikimedia Commons como respaldo visual largo.")
        return provider
    except Exception as exc:
        errors.append(f"Commons: {exc}")

    try:
        provider = _local_reference(out, seed)
        print("Usando referencia fotorrealista local de emergencia como ultimo respaldo.")
        return provider
    except Exception as exc:
        errors.append(f"local reference: {exc}")

    raise RuntimeError("No hubo generador fotorrealista disponible. " + "; ".join(errors))


def create_thumbnail_candidates(video: Path, workdir: Path) -> tuple[Path, list[str]]:
    """Create three visually different thumbnail candidates for manual/native Studio A/B testing."""
    probes = [(8, "a"), (45, "b"), (78, "c")]
    outputs: list[Path] = []
    for pct, label in probes:
        out = workdir / f"thumbnail_{label}.jpg"
        duration = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)],
            capture_output=True,
            text=True,
            check=True,
        )
        seconds = max(1.0, float(duration.stdout.strip() or 1.0) * (pct / 100.0))
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{seconds:.3f}", "-i", str(video),
            "-frames:v", "1",
            "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,eq=contrast=1.04:saturation=1.05,unsharp=5:5:0.25:5:5:0",
            "-q:v", "2", str(out),
        ], check=True)
        outputs.append(out)
    return outputs[0], [str(p) for p in outputs]


def apply_long_cta_overlay(video: Path, duration_seconds: int) -> None:
    if os.getenv("SPIRITUAL_CTA_OVERLAY", "true").lower().strip() != "true":
        return
    start = max(0.0, float(duration_seconds) - 12.0)
    temp = video.with_name(video.stem + ".cta.mp4")
    font = os.getenv("SPIRITUAL_CTA_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    vf = (
        f"drawbox=x=iw*0.18:y=ih*0.80:w=iw*0.64:h=100:color=black@0.55:t=fill:enable='between(t,{start:.2f},{float(duration_seconds):.2f})',"
        f"drawtext=fontfile='{font}':text='SUSCRIBITE  |  COMPARTI  |  AMEN':fontcolor=white:fontsize=38:"
        f"x=(w-text_w)/2:y=h*0.825:enable='between(t,{start:.2f},{float(duration_seconds):.2f})'"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", "-movflags", "+faststart", str(temp),
    ], check=True)
    if temp.exists() and temp.stat().st_size > 100_000:
        temp.replace(video)
