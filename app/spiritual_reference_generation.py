from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from huggingface_hub import InferenceClient
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
HISTORY_FILE = ROOT / "state" / "history.jsonl"

CAMERAS = (
    "cinematic close-up with shallow depth of field",
    "medium three-quarter shot with visible hand gesture",
    "full-body walking shot from a low cinematic angle",
    "wide environmental portrait with the subject off-center",
    "over-the-shoulder contemplative composition",
    "side-profile tracking composition with strong natural depth",
)

ACTIONS = (
    "walking calmly while the robe moves naturally in the wind",
    "raising one open hand in a restrained welcoming gesture",
    "reading an open Scripture beside a quiet path",
    "looking across a valley with a peaceful reflective expression",
    "kneeling in prayer beside an olive tree",
    "standing beside living water while turning naturally toward the light",
)

ENVIRONMENTS = (
    "Lofoten Islands in Norway at blue hour with snowy peaks and calm sea",
    "Geirangerfjord in Norway with immense cliffs and realistic waterfalls",
    "Tromso beneath a vivid aurora borealis reflected on a winter fjord",
    "Senja coastline in Norway with rugged peaks and cold northern sunlight",
    "a biblical olive grove at warm sunrise",
    "a peaceful Sea of Galilee shoreline with natural moving water",
    "a green mountain valley with a clear river and distant waterfalls",
    "an ancient stone path beneath dramatic clouds opening to golden light",
    "a quiet alpine lake reflecting snow-covered mountains",
)

LIGHTING = (
    "physically plausible golden sunrise",
    "soft overcast cinematic daylight",
    "warm sunset rim light",
    "natural moonlight and subtle starlight",
    "green and violet aurora light with realistic skin tones",
    "sun rays passing through moving clouds",
)

NEGATIVE_PROMPT = (
    "text, subtitles, logo, watermark, duplicate subject, duplicate people, deformed hands, "
    "extra fingers, malformed anatomy, plastic CGI skin, doll face, cartoon, anime, painting, "
    "illustration, videogame, celebrity resemblance, recognizable actor, horror, gore, politics, brands"
)


def _reference_files() -> list[Path]:
    return sorted(REFERENCE_DIR.glob("jesus_reference_*.jpg"))


def _provider_strings(row: dict) -> list[str]:
    values: list[str] = []
    for key in ("generated_visual_provider", "visual_providers"):
        value = row.get(key) or []
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
    return values


def _recent_reference_names(limit_records: int = 40) -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    rows: list[dict] = []
    for raw in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") == "dioshablahoyia":
            rows.append(row)
    names: list[str] = []
    for row in rows[-limit_records:]:
        for label in _provider_strings(row):
            marker = "reference:"
            if marker in label:
                tail = label.split(marker, 1)[1]
                names.append(tail.split("/", 1)[0].strip())
    return names


def choose_reference(seed: int) -> Path:
    refs = _reference_files()
    if not refs:
        raise RuntimeError("No hay referencias del personaje en assets/dioshablahoyia/reference.")

    avoid_count = max(0, int(os.getenv("SPIRITUAL_REFERENCE_AVOID_RECENT", "8")))
    recent = set(_recent_reference_names(limit_records=max(20, avoid_count * 4))[-avoid_count:])
    preferred = [ref for ref in refs if ref.name not in recent]
    pool = preferred or refs

    # Prefer the user's supplied bank whenever it still contains a reference that
    # has not been used recently. Defaults remain emergency identity references.
    user_pool = [ref for ref in pool if "_user_" in ref.name]
    if user_pool:
        pool = user_pool

    safe = int(seed) & 0x7FFFFFFF
    return pool[(safe // 31) % len(pool)]


def _variation(seed: int) -> tuple[str, str, str, str]:
    safe = int(seed) & 0x7FFFFFFF
    return (
        CAMERAS[safe % len(CAMERAS)],
        ACTIONS[(safe // 7) % len(ACTIONS)],
        ENVIRONMENTS[(safe // 13) % len(ENVIRONMENTS)],
        LIGHTING[(safe // 19) % len(LIGHTING)],
    )


def build_reference_prompt(base_prompt: str, seed: int, target_size: tuple[int, int] = (1080, 1920)) -> str:
    camera, action, environment, lighting = _variation(seed)
    width, height = target_size
    orientation = "vertical 9:16" if height > width else "horizontal 16:9"
    fingerprint = hashlib.sha256(f"{base_prompt}|{seed}|{width}x{height}".encode()).hexdigest()[:10]
    return (
        f"{base_prompt}. Use the supplied image only as a visual identity and wardrobe reference for the recurring synthetic Jesus character. "
        "Create a clearly NEW photograph-like scene; do not copy the original background, pose, crop, camera angle or lighting. "
        f"New composition: {camera}. New action: {action}. New environment: {environment}. Lighting: {lighting}. "
        "Preserve a reverent adult synthetic Jesus identity with shoulder-length wavy dark-brown hair, groomed beard, warm eyes, natural skin texture, "
        "cream or ivory linen robe and optional muted beige or deep-red mantle. Keep realistic anatomy, natural hands and physically plausible fabric. "
        f"Premium live-action cinema, photorealistic optics, natural atmospheric depth, {orientation}, no text and no watermark. "
        f"Variation fingerprint {fingerprint}."
    )


def _normalize_to_target(image: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    width, height = target_size
    target_ratio = width / max(1, height)
    current_ratio = image.width / max(1, image.height)
    if abs(current_ratio - target_ratio) > 0.03:
        if current_ratio > target_ratio:
            new_w = int(image.height * target_ratio)
            left = max(0, (image.width - new_w) // 2)
            image = image.crop((left, 0, left + new_w, image.height))
        else:
            new_h = int(image.width / target_ratio)
            top = max(0, (image.height - new_h) // 2)
            image = image.crop((0, top, image.width, top + new_h))
    if image.size != target_size:
        image = image.resize(target_size, Image.Resampling.LANCZOS)
    return image


def generate_reference_guided_image(
    full_prompt: str,
    out: Path,
    seed: int,
    target_size: tuple[int, int] = (1080, 1920),
) -> tuple[str, str]:
    if os.getenv("HF_REFERENCE_IMAGE_ENABLED", "true").lower().strip() != "true":
        raise RuntimeError("HF reference image generation esta deshabilitado.")

    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN no esta disponible para image-to-image.")

    reference = choose_reference(seed)
    provider = os.getenv("HF_REFERENCE_IMAGE_PROVIDER", "auto").strip() or "auto"
    model = os.getenv("HF_REFERENCE_IMAGE_MODEL", "black-forest-labs/FLUX.1-Kontext-dev").strip()
    prompt = build_reference_prompt(full_prompt, seed, target_size=target_size)

    client = InferenceClient(provider=provider, api_key=token, timeout=240)
    image = client.image_to_image(
        reference.read_bytes(),
        prompt=prompt,
        model=model,
        negative_prompt=NEGATIVE_PROMPT,
    )
    if image is None:
        raise RuntimeError("Hugging Face image-to-image no devolvio una imagen.")

    image = _normalize_to_target(image.convert("RGB"), target_size)
    image.save(out, format="JPEG", quality=95, optimize=True)
    if not out.exists() or out.stat().st_size < 20_000:
        raise RuntimeError("Hugging Face image-to-image devolvio una imagen invalida.")

    return (
        f"Hugging Face reference-guided image / {model} / reference:{reference.name}",
        reference.name,
    )
