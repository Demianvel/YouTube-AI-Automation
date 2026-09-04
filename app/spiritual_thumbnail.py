from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "history.jsonl"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dhash(path: Path) -> str:
    with Image.open(path) as opened:
        image = opened.convert("L").resize((17, 16), Image.Resampling.LANCZOS)
        px = list(image.getdata())
    value = 0
    for row in range(16):
        off = row * 17
        for col in range(16):
            value = (value << 1) | int(px[off + col] > px[off + col + 1])
    return f"{value:064x}"


def _hamming(a: str, b: str) -> int:
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count()
    except Exception:
        return 10_000


def _previous_thumbnails(limit: int = 90) -> tuple[set[str], list[str], set[str]]:
    exact: set[str] = set()
    perceptual: list[str] = []
    sources: set[str] = set()
    if not HISTORY.exists():
        return exact, perceptual, sources
    rows = HISTORY.read_text(encoding="utf-8").splitlines()[-limit:]
    for raw in rows:
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") != "dioshablahoyia":
            continue
        sha = str(row.get("thumbnail_sha256") or "").strip()
        dh = str(row.get("thumbnail_dhash") or "").strip()
        source = str(row.get("thumbnail_source_scene") or "").strip()
        if sha:
            exact.add(sha)
        if dh:
            perceptual.append(dh)
        if source:
            sources.add(source)
    return exact, perceptual, sources


def _seed(metadata: dict) -> int:
    raw = "|".join([
        str(metadata.get("topic") or ""),
        str(metadata.get("thumbnail_prompt_hash") or ""),
        str(metadata.get("visual_prompt_hashes") or ""),
        os.getenv("GITHUB_RUN_ID", ""),
        os.getenv("GITHUB_RUN_ATTEMPT", ""),
        os.getenv("DIOS_SOVEREIGN_VARIATION_NONCE", ""),
    ])
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _compose(source: Path, out: Path, seed: int, variant: int) -> str:
    with Image.open(source) as opened:
        src = ImageOps.exif_transpose(opened).convert("RGB")
        layout = variant % 6
        cx_options = (0.36, 0.43, 0.50, 0.57, 0.64, 0.47)
        cy_options = (0.38, 0.46, 0.52, 0.42, 0.58, 0.49)
        cx = max(0.28, min(0.72, cx_options[layout] + (((seed >> 5) % 9) - 4) * 0.006))
        cy = max(0.28, min(0.72, cy_options[layout] + (((seed >> 11) % 9) - 4) * 0.006))

        frame = ImageOps.fit(src, (1280, 720), method=Image.Resampling.LANCZOS, centering=(cx, cy))

        # Six restrained cinematic treatments create real layout variation while
        # preserving the underlying synthetic biblical image and human anatomy.
        contrast = (1.08, 1.13, 1.05, 1.16, 1.10, 1.07)[layout]
        color = (1.04, 1.08, 1.02, 1.06, 1.10, 1.03)[layout]
        brightness = (1.00, 0.98, 1.03, 0.97, 1.01, 1.02)[layout]
        frame = ImageEnhance.Brightness(frame).enhance(brightness)
        frame = ImageEnhance.Contrast(frame).enhance(contrast)
        frame = ImageEnhance.Color(frame).enhance(color)
        frame = ImageEnhance.Sharpness(frame).enhance(1.10)

        soft = frame.filter(ImageFilter.GaussianBlur(radius=18 + 2 * layout))
        if layout in {1, 4}:
            frame = Image.blend(soft, frame, 0.93)
        elif layout in {2, 5}:
            frame = Image.blend(frame, soft, 0.06)

        out.parent.mkdir(parents=True, exist_ok=True)
        frame.save(out, "JPEG", quality=95, optimize=True, progressive=True)
        return f"layout_{layout}_cx_{cx:.3f}_cy_{cy:.3f}"


def build_unique_short_thumbnail(workdir: Path, metadata: dict) -> Path | None:
    images = sorted(workdir.glob("spiritual_generated_*.jpg"))
    if not images:
        metadata["thumbnail_status"] = "no_generated_scene_available"
        return None

    seed = _seed(metadata)
    exact_history, dh_history, source_history = _previous_thumbnails()
    threshold = max(12, int(os.getenv("SPIRITUAL_THUMBNAIL_DHASH_MIN_DISTANCE", "20")))
    out = workdir / "youtube_thumbnail.jpg"

    # Prefer a scene filename not recently used as a thumbnail source when possible.
    preferred = [p for p in images if p.name not in source_history]
    pool = preferred or images
    attempts = max(18, len(pool) * 8)

    for attempt in range(attempts):
        source = pool[(seed + attempt * 7) % len(pool)]
        layout_id = _compose(source, out, seed, attempt)
        sha = _sha256(out)
        dh = _dhash(out)
        distance = min((_hamming(dh, old) for old in dh_history), default=10_000)
        if sha in exact_history or distance <= threshold:
            continue
        metadata["thumbnail_status"] = "generated_unique"
        metadata["thumbnail_sha256"] = sha
        metadata["thumbnail_dhash"] = dh
        metadata["thumbnail_nearest_distance"] = distance
        metadata["thumbnail_source_scene"] = source.name
        metadata["thumbnail_layout_id"] = layout_id
        metadata["thumbnail_provider"] = "fresh_ai_scene_cinematic_rotation_v2"
        metadata["thumbnail_unique_policy"] = "sha256_plus_dhash_plus_source_rotation"
        return out

    metadata["thumbnail_status"] = "freshness_guard_rejected"
    metadata["thumbnail_unique_policy"] = "rejected_because_no_sufficiently_distinct_candidate"
    out.unlink(missing_ok=True)
    return None
