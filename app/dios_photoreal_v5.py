from __future__ import annotations

import base64
import re
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "dios-photoreal-human-v5"
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
APPROVED_REFERENCE = REFERENCE_DIR / "jesus_divine_reference_v5.jpg"
APPROVED_REFERENCE_B64 = REFERENCE_DIR / "jesus_divine_reference_v5.jpg.b64"
APPROVED_REFERENCE_PARTS = REFERENCE_DIR / "v5_parts"

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


def _decode_reference_payload(text: str) -> bytes:
    """Decode the versioned JPEG while tolerating transport separators/BOMs."""
    raw = str(text or "").strip()
    head = raw[:160].lower()
    if "base64," in head:
        raw = raw.split(",", 1)[1]
    clean = re.sub(r"[^A-Za-z0-9+/=]", "", raw)
    if len(clean) < 1000:
        raise RuntimeError("La referencia v5 no contiene un payload Base64 utilizable.")
    clean += "=" * ((4 - len(clean) % 4) % 4)
    try:
        data = base64.b64decode(clean, validate=False)
    except Exception as exc:
        raise RuntimeError("No se pudo decodificar la referencia visual v5.") from exc
    if len(data) < 10_000 or not data.startswith(b"\xff\xd8"):
        raise RuntimeError("El payload de la referencia v5 no es un JPEG valido.")
    return data


def _reference_payload_text() -> str:
    """Prefer small versioned chunks so Git transports cannot truncate the JPEG."""
    parts = sorted(APPROVED_REFERENCE_PARTS.glob("part*.b64")) if APPROVED_REFERENCE_PARTS.exists() else []
    if parts:
        payload = "".join(part.read_text(encoding="utf-8-sig").strip() for part in parts)
        if len(payload) >= 10_000:
            return payload
    if APPROVED_REFERENCE_B64.exists():
        return APPROVED_REFERENCE_B64.read_text(encoding="utf-8-sig")
    raise RuntimeError(
        "Falta la referencia aprobada v5: no hay partes versionadas ni payload monolitico."
    )


def materialize_approved_reference() -> Path:
    """Restore and fully validate the approved photoreal visual reference."""
    if APPROVED_REFERENCE.exists() and APPROVED_REFERENCE.stat().st_size >= 10_000:
        try:
            with Image.open(APPROVED_REFERENCE) as opened:
                opened.load()
                if opened.width >= 300 and opened.height >= 500:
                    return APPROVED_REFERENCE
        except Exception:
            APPROVED_REFERENCE.unlink(missing_ok=True)

    data = _decode_reference_payload(_reference_payload_text())
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    APPROVED_REFERENCE.write_bytes(data)

    try:
        with Image.open(APPROVED_REFERENCE) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened).convert("RGB")
            image.load()
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
