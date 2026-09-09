from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SHORT_HISTORY = ROOT / "state" / "history.jsonl"
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"


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


def fingerprint_image(path: Path) -> dict[str, str]:
    return {"sha256": _sha256(path), "dhash": _dhash(path)}


def _provider_base_identity(provider: str) -> str:
    text = str(provider or "")
    local = re.search(r"reference:([^/|]+\.jpg)", text)
    if local and "local_project_jesus_reference" in text:
        return f"local:{local.group(1)}"
    pexels = re.search(r"\bid=([0-9]+)", text)
    if pexels and text.startswith("Pexels"):
        return f"pexels:{pexels.group(1)}"
    source = re.search(r"\bsource=([^ |]+)", text)
    if source:
        return f"source:{source.group(1)}"
    return ""


def _history_fingerprints(previous: list[dict]) -> tuple[set[str], list[str]]:
    exact: set[str] = set()
    perceptual: list[str] = []
    for row in previous[-320:]:
        for value in row.get("visual_asset_sha256") or []:
            if str(value).strip():
                exact.add(str(value).strip())
        for value in row.get("visual_asset_dhash") or []:
            if str(value).strip():
                perceptual.append(str(value).strip())
    return exact, perceptual


def _read_persisted_rows() -> list[dict]:
    rows: list[dict] = []
    for path in (SHORT_HISTORY, LONG_HISTORY):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            if item.get("channel") == "dioshablahoyia":
                rows.append(item)
    return rows[-500:]


def _distance_threshold() -> int:
    configured = max(0, int(os.getenv("SPIRITUAL_VISUAL_PHASH_MAX_DISTANCE", "18")))
    return max(18, configured)


def _provider_distance_threshold(provider: str, default: int) -> int:
    """Use a practical threshold for local cinematic transforms.

    A local reference may be reused across different Shorts, but only a previously
    unseen transformation that passes the perceptual-distance guard is accepted.
    This avoids exhausting the small reference bank when remote image generation
    is unavailable, without permitting pixel/exact or near-identical duplicates.
    """
    low = str(provider or "").lower()
    if "direct cinematic reference transform" not in low:
        return default
    try:
        configured = int(os.getenv("SPIRITUAL_LOCAL_VISUAL_PHASH_MAX_DISTANCE", "10"))
    except Exception:
        configured = 10
    return max(4, min(default, configured))


def fresh_against_persisted_history(path: Path, current_dhash: list[str] | None = None) -> tuple[bool, dict[str, str], int]:
    signature = fingerprint_image(path)
    previous_exact, previous_perceptual = _history_fingerprints(_read_persisted_rows())
    current_dhash = current_dhash or []
    threshold = _distance_threshold()
    if signature["sha256"] in previous_exact:
        return False, signature, 0
    distance = min([_hamming_hex(signature["dhash"], old) for old in previous_perceptual + current_dhash] or [10_000])
    return distance > threshold, signature, distance


def validate_short_visuals(workdir: Path, previous: list[dict], metadata: dict) -> dict:
    """Reject exact, perceptual and same-Short base repetition before upload."""
    strict = _env_true("SPIRITUAL_REQUIRE_FRESH_VISUAL", True)
    images = sorted(workdir.glob("spiritual_generated_*.jpg"))
    if not images:
        if strict and str(metadata.get("visual_source") or "").endswith("image_motion_fallback"):
            raise RuntimeError("FRESH_VISUAL_GUARD: no se encontraron las imagenes generadas para verificarlas.")
        metadata["visual_freshness_verified"] = True
        metadata["visual_fingerprint_mode"] = "video_or_nonstill_path"
        return metadata

    providers = metadata.get("generated_visual_provider") or []
    if isinstance(providers, str):
        providers = [providers]
    providers = [str(item) for item in providers]

    current_base_sources: set[str] = set()
    base_source_ids: list[str] = []
    for provider in providers:
        identity = _provider_base_identity(provider)
        if not identity:
            continue
        if identity in current_base_sources:
            raise RuntimeError(f"FRESH_VISUAL_GUARD: una misma fuente base se intento reutilizar en dos escenas: {identity}")
        # Base references are allowed to recur on different Shorts. Freshness is
        # enforced by exact SHA-256, perceptual distance and local variant IDs.
        current_base_sources.add(identity)
        base_source_ids.append(identity)

    previous_exact, previous_perceptual = _history_fingerprints(previous)
    current_exact: set[str] = set()
    current_perceptual: list[str] = []
    sha_values: list[str] = []
    dhash_values: list[str] = []
    perceptual_distances: list[int] = []
    applied_thresholds: list[int] = []
    threshold = _distance_threshold()

    for index, path in enumerate(images):
        exact = _sha256(path)
        perceptual = _dhash(path)
        if exact in previous_exact or exact in current_exact:
            raise RuntimeError(f"FRESH_VISUAL_GUARD: imagen exacta repetida detectada: {path.name}")

        near_recent = min((_hamming_hex(perceptual, old) for old in previous_perceptual), default=10_000)
        near_current = min((_hamming_hex(perceptual, old) for old in current_perceptual), default=10_000)
        nearest = min(near_recent, near_current)
        provider = providers[index] if index < len(providers) else ""
        effective_threshold = _provider_distance_threshold(provider, threshold)
        direct_locked_transform = "direct cinematic reference transform" in provider.lower()
        too_close = nearest < effective_threshold if direct_locked_transform else nearest <= effective_threshold
        if strict and too_close:
            comparator = "<" if direct_locked_transform else "<="
            raise RuntimeError(
                f"FRESH_VISUAL_GUARD: {path.name} es demasiado parecida a una imagen anterior "
                f"(distancia perceptual {nearest} {comparator} {effective_threshold})."
            )

        current_exact.add(exact)
        current_perceptual.append(perceptual)
        sha_values.append(exact)
        dhash_values.append(perceptual)
        perceptual_distances.append(nearest)
        applied_thresholds.append(effective_threshold)

    local_providers = [item for item in providers if "local_project_jesus_reference" in item]
    if strict:
        if len(local_providers) > 1:
            raise RuntimeError("FRESH_VISUAL_GUARD: un Short no puede usar mas de una escena derivada del banco local de Jesus.")
        for provider in local_providers:
            if "variant_" not in provider:
                raise RuntimeError("FRESH_VISUAL_GUARD: se rechazo la referencia local base sin transformacion como imagen final.")

    metadata["visual_asset_sha256"] = sha_values
    metadata["visual_asset_dhash"] = dhash_values
    metadata["visual_freshness_verified"] = True
    metadata["visual_fingerprint_mode"] = "sha256_plus_256bit_dhash_plus_provider_aware_threshold_v7"
    metadata["visual_perceptual_distance_threshold"] = threshold
    metadata["visual_perceptual_applied_thresholds"] = applied_thresholds
    metadata["visual_perceptual_nearest_distances"] = perceptual_distances
    metadata["visual_base_source_ids"] = base_source_ids
    metadata["visual_unique_base_source_count"] = len(current_base_sources)
    metadata["visual_local_variant_verified"] = bool(local_providers)
    metadata["visual_local_scene_count"] = len(local_providers)
    metadata["visual_local_base_reuse_forbidden"] = False
    metadata["visual_local_reuse_requires_fresh_variant"] = True
    return metadata
