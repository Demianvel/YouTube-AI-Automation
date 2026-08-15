from __future__ import annotations

import hashlib
from pathlib import Path

from . import wikimedia_video as commons


_QUERIES = (
    "mountain sunrise landscape",
    "forest stream nature",
    "ocean waves sunrise",
    "lake mountains landscape",
    "clouds moving sky timelapse",
    "olive grove landscape",
    "desert dunes sunrise",
    "snow mountain landscape",
    "meadow sheep nature",
    "wild birds flying nature",
    "river valley landscape",
    "forest sunlight mist",
)


def _seed(meta: dict, index: int) -> int:
    raw = f"spiritual-commons|{meta.get('topic','')}|{meta.get('title','')}|{index}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def make_spiritual_commons_clip(
    meta: dict,
    workdir: Path,
    index: int,
    duration: int,
    used_urls: set[str] | None = None,
) -> tuple[Path, str, dict[str, str]]:
    """Create one diverse real nature/animal B-roll clip from licensed Commons media."""
    used_urls = used_urls if used_urls is not None else set()
    base = _seed(meta, index)
    queries = [_QUERIES[(base + index * 3 + step) % len(_QUERIES)] for step in range(len(_QUERIES))]

    chosen = None
    chosen_query = ""
    kind = "video"
    for query in queries:
        results = [item for item in commons._search(query, "video") if item["url"] not in used_urls]
        if results:
            chosen = results[base % min(len(results), 12)]
            chosen_query = query
            break

    if chosen is None:
        kind = "image"
        for query in queries:
            results = [item for item in commons._search(query, "image") if item["url"] not in used_urls]
            if results:
                chosen = results[(base ^ 0x51A7) % min(len(results), 16)]
                chosen_query = query
                break

    if chosen is None:
        raise RuntimeError("Wikimedia Commons no encontro naturaleza con licencia admitida para esta escena.")

    used_urls.add(chosen["url"])
    source = workdir / f"spiritual_commons_source_{index + 1}.{'webm' if kind == 'video' else 'jpg'}"
    clip = workdir / f"spiritual_commons_scene_{index + 1}.mp4"
    commons._download(chosen["url"], source)
    if kind == "video":
        commons._video_clip(source, clip, duration, base)
    else:
        commons._image_clip(source, clip, duration, base)

    credit = {
        "provider": "Wikimedia Commons",
        "creator": chosen["artist"],
        "license": chosen["license"],
        "source_url": chosen["description_url"],
        "query": chosen_query,
        "media_type": kind,
    }
    return clip, f"Wikimedia Commons licensed {kind}/{chosen.get('title','media')}", credit
