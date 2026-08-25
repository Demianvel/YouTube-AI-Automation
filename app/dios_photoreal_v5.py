from __future__ import annotations

import base64
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "dios-photoreal-human-v5"
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
APPROVED_REFERENCE = REFERENCE_DIR / "jesus_divine_reference_v5.jpg"
APPROVED_REFERENCE_B64 = REFERENCE_DIR / "jesus_divine_reference_v5.jpg.b64"

PHOTOREAL_PROMPT_PREFIX = (
    "live-action photographic biblical cinema, human adult Jesus, physically plausible human anatomy, "
    "natural skin pores and facial texture, realistic eyes, realistic hands, individual hair strands, "
    "natural linen fabric, physically plausible light and shadows, full-frame cinema camera, realistic lens depth, "
    "subtle volumetric sunlight, reverent symbolic divine presence through light and atmosphere, "
    "emotionally warm, compassionate and serene, premium cinematic color science, no celebrity resemblance"
)

PHOTOREAL_NEGATIVE = (
    "3d, 3d render, CGI, game render, game asset, octane render, unreal engine look, animated, animation, anime, "
    "cartoon, illustration, painting, plastic skin, wax skin, doll, toy, stylized face, low-poly, fake beard, "
    "oversmoothed skin, deformed face, malformed hands, extra fingers, extra limbs, duplicate person, text, "
    "watermark, logo, low resolution, oversaturated"
)


def materialize_approved_reference() -> Path:
    """Restore the approved visual reference from its versioned base64 asset.

    GitHub stores the reference payload as text so the repository can version the
    user-approved image even in environments where binary file writes are limited.
    The runtime materializes the JPEG before any visual readiness checks run.
    """
    if APPROVED_REFERENCE.exists() and APPROVED_REFERENCE.stat().st_size >= 10_000:
        return APPROVED_REFERENCE
    if not APPROVED_REFERENCE_B64.exists():
        raise RuntimeError(f"Falta la referencia aprobada v5: {APPROVED_REFERENCE_B64}")

    raw = "".join(APPROVED_REFERENCE_B64.read_text(encoding="utf-8").split())
    data = base64.b64decode(raw, validate=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    APPROVED_REFERENCE.write_bytes(data)

    try:
        with Image.open(APPROVED_REFERENCE) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            if image.width < 300 or image.height < 500:
                raise RuntimeError(
                    f"Referencia v5 demasiado pequena: {image.width}x{image.height}"
                )
    except Exception:
        APPROVED_REFERENCE.unlink(missing_ok=True)
        raise

    return APPROVED_REFERENCE


def preferred_references(existing: list[Path]) -> list[Path]:
    approved = materialize_approved_reference()
    ordered = [approved]
    seen = {approved.resolve()}
    for ref in existing:
        try:
            key = ref.resolve()
        except Exception:
            key = ref
        if key in seen:
            continue
        seen.add(key)
        ordered.append(ref)
    return ordered


def strengthen_prompt(prompt: str) -> str:
    clean = " ".join(str(prompt or "").split())
    return f"{PHOTOREAL_PROMPT_PREFIX}, {clean}" if clean else PHOTOREAL_PROMPT_PREFIX
