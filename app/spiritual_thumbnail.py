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


def _previous_thumbnails(limit: int = 60) -> tuple[set[str], list[str]]:
    exact: set[str] = set()
    perceptual: list[str] = []
    if not HISTORY.exists():
        return exact, perceptual
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
        if sha:
            exact.add(sha)
        if dh:
            perceptual.append(dh)
    return exact, perceptual


def _seed(metadata: dict) -> int:
    raw = "|".join([
        str(metadata.get("topic") or ""),
        str(metadata.get("thumbnail_prompt_hash") or ""),
        os.getenv("GITHUB_RUN_ID", ""),
        os.getenv("GITHUB_RUN_ATTEMPT", ""),
    ])
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _compose(source: Path, out: Path, seed: int, variant: int) -> None:
    with Image.open(source) as opened:
        src = ImageOps.exif_transpose(opened).convert("RGB")
        # The background uses the same freshly generated frame but a different
        # focal crop. This keeps a coherent cinematic palette without reusing an
        # old thumbnail asset.
        center_x = 0.42 + (((seed // 7) + variant) % 17) * 0.01
        center_y = 0.40 + (((seed // 17) + variant) % 13) * 0.01
        center_x = max(0.32, min(0.68, center_x))
        center_y = max(0.32, min(0.68, center_y))
        frame = ImageOps.fit(
            src,
            (1280, 720),
            method=Image.Resampling.LANCZOS,
            centering=(center_x, center_y),
        )
        frame = ImageEnhance.Contrast(frame).enhance(1.08 + 0.02 * (variant % 3))
        frame = ImageEnhance.Color(frame).enhance(1.04 + 0.015 * (variant % 4))
        frame = ImageEnhance.Sharpness(frame).enhance(1.10)

        # A restrained vignette improves focal hierarchy without text overlays.
        blurred = frame.filter(ImageFilter.GaussianBlur(radius=18))
        if variant % 2:
            overlay = Image.blend(blurred, frame, 0.90)
        else:
            overlay = Image.blend(frame, blurred, 0.08)
        out.parent.mkdir(parents=True, exist_ok=True)
        overlay.save(out, "JPEG", quality=94, optimize=True, progressive=True)


def build_unique_short_thumbnail(workdir: Path, metadata: dict) -> Path | None:
    images = sorted(workdir.glob("spiritual_generated_*.jpg"))
    if not images:
        metadata["thumbnail_status"] = "no_generated_scene_available"
        return None

    seed = _seed(metadata)
    exact_history, dh_history = _previous_thumbnails()
    threshold = max(8, int(os.getenv("SPIRITUAL_THUMBNAIL_DHASH_MIN_DISTANCE", "20")))
    out = workdir / "youtube_thumbnail.jpg"

    for attempt in range(max(6, len(images) * 3)):
        source = images[(seed + attempt * 5) % len(images)]
        _compose(source, out, seed, attempt)
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
        metadata["thumbnail_provider"] = "fresh_ai_scene_cinematic_crop_v1"
        return out

    metadata["thumbnail_status"] = "freshness_guard_rejected"
    out.unlink(missing_ok=True)
    return None
