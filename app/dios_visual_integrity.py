from __future__ import annotations

import hashlib
import json
import os
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


def _history_fingerprints(previous: list[dict]) -> tuple[set[str], list[str]]:
    exact: set[str] = set()
    perceptual: list[str] = []
    for row in previous[-160:]:
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
    return rows[-200:]


def fresh_against_persisted_history(path: Path, current_dhash: list[str] | None = None) -> tuple[bool, dict[str, str], int]:
    signature = fingerprint_image(path)
    previous_exact, previous_perceptual = _history_fingerprints(_read_persisted_rows())
    current_dhash = current_dhash or []
    threshold = max(0, int(os.getenv("SPIRITUAL_VISUAL_PHASH_MAX_DISTANCE", "7")))

    if signature["sha256"] in previous_exact:
        return False, signature, 0

    distance = min(
        [_hamming_hex(signature["dhash"], old) for old in previous_perceptual + current_dhash] or [10_000]
    )
    return distance > threshold, signature, distance


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
