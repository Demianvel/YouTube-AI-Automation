from __future__ import annotations

import hashlib
import os
from pathlib import Path

from PIL import Image


def _env_true(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower().strip() == "true"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dhash(path: Path) -> str:
    with Image.open(path) as source:
        image = source.convert("L").resize((17, 16), Image.Resampling.LANCZOS)
        pixels = list(image.getdata())
    bits = []
    for row in range(16):
        offset = row * 17
        for col in range(16):
            bits.append(1 if pixels[offset + col] > pixels[offset + col + 1] else 0)
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return f"{value:064x}"


def _hamming_hex(left: str, right: str) -> int:
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except Exception:
        return 10_000


def _history_fingerprints(previous: list[dict]) -> tuple[set[str], list[str]]:
    exact: set[str] = set()
    perceptual: list[str] = []
    for row in previous[-100:]:
        for value in row.get("visual_asset_sha256") or []:
            if str(value).strip():
                exact.add(str(value).strip())
        for value in row.get("visual_asset_dhash") or []:
            if str(value).strip():
                perceptual.append(str(value).strip())
    return exact, perceptual


def validate_short_visuals(workdir: Path, previous: list[dict], metadata: dict) -> dict:
    """Block exact or near-duplicate stills before a Dios Short can be uploaded."""
    strict = _env_true("SPIRITUAL_REQUIRE_FRESH_VISUAL", True)
    images = sorted(workdir.glob("spiritual_generated_*.jpg"))
    if not images:
        if strict and str(metadata.get("visual_source") or "").endswith("image_motion_fallback"):
            raise RuntimeError("FRESH_VISUAL_GUARD: no se encontraron las imagenes generadas para verificarlas.")
        metadata["visual_freshness_verified"] = True
        metadata["visual_fingerprint_mode"] = "video_or_nonstill_path"
        return metadata

    previous_exact, previous_perceptual = _history_fingerprints(previous)
    current_exact: set[str] = set()
    current_perceptual: list[str] = []
    sha_values: list[str] = []
    dhash_values: list[str] = []
    threshold = max(0, int(os.getenv("SPIRITUAL_VISUAL_PHASH_MAX_DISTANCE", "7")))

    for path in images:
        exact = _sha256(path)
        perceptual = _dhash(path)

        if exact in previous_exact or exact in current_exact:
            raise RuntimeError(f"FRESH_VISUAL_GUARD: imagen exacta repetida detectada: {path.name}")

        near_recent = min((_hamming_hex(perceptual, old) for old in previous_perceptual), default=10_000)
        near_current = min((_hamming_hex(perceptual, old) for old in current_perceptual), default=10_000)
        if strict and min(near_recent, near_current) <= threshold:
            raise RuntimeError(
                f"FRESH_VISUAL_GUARD: {path.name} es demasiado parecida a una imagen reciente "
                f"(distancia perceptual {min(near_recent, near_current)} <= {threshold})."
            )

        current_exact.add(exact)
        current_perceptual.append(perceptual)
        sha_values.append(exact)
        dhash_values.append(perceptual)

    providers = metadata.get("generated_visual_provider") or []
    if isinstance(providers, str):
        providers = [providers]
    if strict and any("local_project_jesus_reference" in str(item) for item in providers):
        raise RuntimeError("FRESH_VISUAL_GUARD: se rechazo una referencia local antigua como imagen final.")

    metadata["visual_asset_sha256"] = sha_values
    metadata["visual_asset_dhash"] = dhash_values
    metadata["visual_freshness_verified"] = True
    metadata["visual_fingerprint_mode"] = "sha256_plus_256bit_dhash"
    metadata["visual_perceptual_distance_threshold"] = threshold
    return metadata
