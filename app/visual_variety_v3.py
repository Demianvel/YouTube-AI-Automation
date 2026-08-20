from __future__ import annotations

import hashlib
import os
import random
from typing import Any

from .visual_variety_v2 import ATMOSPHERES, CAMERAS, LIGHTING, FAMILY_SCENES as V2_FAMILY_SCENES


EXTRA_FAMILY_SCENES: dict[str, tuple[str, ...]] = {
    "animals_and_creation": (
        "small sparrows drinking from a shallow woodland stream at sunrise with natural feathers and reflections",
        "gentle sheep walking through a green valley toward clear water beneath soft morning light",
        "white dove flying above a river canyon after rain with realistic wings and mountain mist",
        "wild horses moving calmly through a broad meadow beneath dramatic summer clouds",
        "deer standing at the edge of a quiet forest lake during golden hour",
        "seabirds crossing a bright coastal sky above natural ocean waves and dark cliffs",
        "lamb resting beside an adult sheep in a peaceful field with distant hills",
        "small birds perched among olive branches while warm sunrise light enters through leaves",
        "butterflies moving above wildflowers beside a clear mountain stream",
        "two birds flying across a rainbow forming in distant rain above a green valley",
    ),
    "sacred_architecture": (
        "quiet stone chapel interior illuminated only by warm dawn light through tall windows, no people",
        "ancient stone church exterior on a hill beneath moving clouds and soft evening light",
        "simple wooden church beside a snowy mountain valley under a blue-hour sky",
        "sunlight crossing an empty monastery corridor with natural stone texture and deep perspective",
        "small countryside chapel beside wheat fields under a luminous sunset",
        "old stone doorway opening from a dark chapel toward a bright green valley",
        "simple church bell tower seen through olive branches in warm Mediterranean light",
        "empty wooden pews facing soft natural light in a modest peaceful church interior",
        "historic stone sanctuary beside a river with mist lifting from surrounding trees",
        "quiet candlelit stone alcove with an open Bible and no decorative text",
    ),
}

FAMILY_SCENES: dict[str, tuple[str, ...]] = {**V2_FAMILY_SCENES, **EXTRA_FAMILY_SCENES}

SCENE_COOLDOWN_VIDEOS = 42
FAMILY_USAGE_WINDOW = 16
FAMILY_HARD_RECENT = 2


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _rng(metadata: dict) -> random.Random:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"
    raw = f"visual-pack-v3|{metadata.get('topic','')}|{metadata.get('title','')}|{marker}"
    return random.Random(int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16))


def _packs(previous: list[dict], limit: int) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    for row in previous[-limit:]:
        pack = row.get("visual_pack") or row.get("visual_rotation_manifest") or []
        clean = [item for item in pack if isinstance(item, dict)]
        if clean:
            rows.append(clean)
    return rows


def _recent_scene_texts(previous: list[dict], limit: int = SCENE_COOLDOWN_VIDEOS) -> set[str]:
    result: set[str] = set()
    for pack in _packs(previous, limit):
        for item in pack:
            scene = " ".join(str(item.get("scene") or "").lower().split())
            if scene:
                result.add(scene)
    return result


def _recent_prompt_hashes(previous: list[dict], limit: int = 160) -> set[str]:
    result: set[str] = set()
    for row in previous[-limit:]:
        for value in row.get("visual_prompt_hashes") or []:
            if str(value).strip():
                result.add(str(value).strip())
        for item in row.get("visual_pack") or []:
            if isinstance(item, dict) and item.get("prompt_hash"):
                result.add(str(item["prompt_hash"]))
    return result


def _family_usage(previous: list[dict], limit: int = FAMILY_USAGE_WINDOW) -> dict[str, int]:
    usage = {family: 0 for family in FAMILY_SCENES}
    for pack in _packs(previous, limit):
        for item in pack:
            family = str(item.get("family") or "")
            if family in usage:
                usage[family] += 1
    return usage


def _recent_families(previous: list[dict], videos: int = FAMILY_HARD_RECENT) -> set[str]:
    result: set[str] = set()
    for pack in _packs(previous, videos):
        for item in pack:
            family = str(item.get("family") or "")
            if family:
                result.add(family)
    return result


def _choose_families(previous: list[dict], count: int, rng: random.Random) -> list[str]:
    usage = _family_usage(previous)
    recent = _recent_families(previous)
    families = list(FAMILY_SCENES)
    noise = {family: rng.random() for family in families}

    # A family used in either of the previous two videos receives a large penalty.
    # This removes the old behavior that forced Norway + Jesus into every Short.
    families.sort(key=lambda family: (1 if family in recent else 0, usage.get(family, 0), noise[family]))

    chosen: list[str] = []
    for family in families:
        if len(chosen) >= count:
            break
        chosen.append(family)

    # If a future format asks for more scenes than families, only then cycle.
    cursor = 0
    while len(chosen) < count:
        family = families[cursor % len(families)]
        chosen.append(family)
        cursor += 1
    return chosen


def _new_combo(
    family: str,
    recent_scenes: set[str],
    blocked_hashes: set[str],
    rng: random.Random,
) -> dict[str, str]:
    candidates = list(FAMILY_SCENES[family])
    rng.shuffle(candidates)

    fresh_semantic = [scene for scene in candidates if " ".join(scene.lower().split()) not in recent_scenes]
    pool = fresh_semantic or candidates

    for scene in pool:
        for _ in range(80):
            camera = rng.choice(CAMERAS)
            lighting = rng.choice(LIGHTING)
            atmosphere = rng.choice(ATMOSPHERES)
            fingerprint = _hash(f"v3|{family}|{scene}|{camera}|{lighting}|{atmosphere}")
            if fingerprint in blocked_hashes:
                continue
            blocked_hashes.add(fingerprint)
            recent_scenes.add(" ".join(scene.lower().split()))
            return {
                "family": family,
                "scene": scene,
                "camera": camera,
                "lighting": lighting,
                "atmosphere": atmosphere,
                "prompt_hash": fingerprint,
            }
    raise RuntimeError(f"No se encontro una composicion visual suficientemente nueva para {family}.")


def attach_visual_pack_v3(metadata: dict, previous: list[dict], content_type: str = "short") -> dict:
    if content_type != "short":
        return metadata

    rows = [dict(item) for item in (metadata.get("scenes") or [])]
    scene_count = max(1, len(rows) or 6)
    if not rows:
        rows = [{} for _ in range(scene_count)]

    rng = _rng(metadata)
    recent_scenes = _recent_scene_texts(previous)
    blocked_hashes = _recent_prompt_hashes(previous)
    selected_families = _choose_families(previous, scene_count, rng)
    chosen = [
        _new_combo(family, recent_scenes, blocked_hashes, rng)
        for family in selected_families[:scene_count]
    ]

    topic = str(metadata.get("topic") or metadata.get("content_family") or "mensaje biblico de esperanza")
    reference = str(metadata.get("bible_reference") or "").strip()
    run_marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"

    manifest: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        item = chosen[index]
        variation = _hash(f"{item['prompt_hash']}|{run_marker}|scene-{index}|v3")[:12]
        row["visual_family"] = item["family"]
        row["visual_prompt_hash"] = item["prompt_hash"]
        row["visual_prompt"] = (
            f"{item['scene']}. Camera: {item['camera']}. Lighting: {item['lighting']}. "
            f"Atmosphere: {item['atmosphere']}. Spiritual context: {topic}. "
            + (f"Biblical reference: {reference}. " if reference else "")
            + "Create a completely NEW original photorealistic live-action cinematic frame. The scene must be visibly different from every other scene in this video: different subject arrangement, background, camera distance, focal point and light direction. "
            "Never reproduce an earlier image, pose, crop, background, camera position or composition. Use realistic anatomy, natural hands, physically plausible fabric, water, clouds and light. Vertical 9:16. No text, no captions, no logo, no watermark, no celebrity resemblance. "
            f"Unique production fingerprint {variation}."
        )
        manifest.append({
            "family": item["family"],
            "scene": item["scene"],
            "camera": item["camera"],
            "lighting": item["lighting"],
            "atmosphere": item["atmosphere"],
            "aspect": "vertical 9:16",
            "theme_id": item["prompt_hash"][:12],
        })

    metadata["scenes"] = rows
    metadata["visual_pack"] = chosen
    metadata["visual_prompt_hashes"] = [item["prompt_hash"] for item in chosen]
    metadata["visual_rotation_manifest"] = manifest
    metadata["visual_variety_enabled"] = True
    metadata["visual_no_repeat_window"] = SCENE_COOLDOWN_VIDEOS
    metadata["visual_family_cooldown_videos"] = FAMILY_HARD_RECENT
    metadata["visual_unique_families_per_short"] = min(scene_count, len(set(selected_families)))
    metadata["visual_brand_anchor_forced"] = False
    metadata["visual_engine_version"] = "2026.08.20-semantic-source-motion-v3"
    return metadata
