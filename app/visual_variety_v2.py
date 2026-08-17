from __future__ import annotations

import hashlib
import os
import random
from typing import Any


FAMILY_SCENES: dict[str, tuple[str, ...]] = {
    "jesus_and_prayer": (
        "recurring synthetic Jesus walking beside a cold mountain river while an ivory robe moves naturally in the breeze",
        "recurring synthetic Jesus praying alone beside an old olive tree with a peaceful natural expression",
        "recurring synthetic Jesus reading an open Scripture on a rocky hillside above a distant lake",
        "recurring synthetic Jesus extending one open hand toward the viewer beside living water",
        "recurring synthetic Jesus standing among alpine wildflowers looking toward a distant valley",
        "recurring synthetic Jesus walking along a quiet Sea of Galilee shoreline at dawn",
        "recurring synthetic Jesus seated on a natural stone beside a river in calm contemplation with an open Bible nearby",
        "recurring synthetic Jesus standing on a Norwegian overlook above a deep fjord without posing for the camera",
        "recurring synthetic Jesus beneath a star-filled sky looking upward in silent prayer",
        "recurring synthetic Jesus crossing an ancient stone path after rain while warm light breaks through clouds",
    ),
    "norway": (
        "Tromso winter fjord beneath vivid green and violet aurora borealis reflected on still water",
        "Lofoten Islands with steep snowy peaks rising from a calm Norwegian sea and tiny warm village lights",
        "Geirangerfjord with immense cliffs, waterfalls and low natural mist",
        "Senja coastline with rugged dark peaks, cold sea and moving northern clouds",
        "Norwegian waterfall descending through dark rock and vivid moss after rain",
        "quiet red cabin beside a snowy Norwegian fjord beneath northern lights",
        "Preikestolen-style cliff overlooking a vast Norwegian fjord at sunrise, no people",
        "snow-covered Norwegian valley with a narrow river reflecting pale winter sunlight",
        "rocky Arctic beach in northern Norway beneath dramatic aurora and stars",
        "high mountain road overlooking layered Norwegian fjords under changing weather",
    ),
    "biblical_stories": (
        "Noah's Ark as a massive historically inspired wooden vessel with animals approaching in pairs after the storm",
        "Noah's Ark resting in a green mountain valley after the flood beneath a natural rainbow with animals nearby",
        "Jesus calming a storm on the Sea of Galilee with disciples in a wooden boat, dramatic but peaceful",
        "the Good Samaritan compassionately helping an injured traveler on an ancient road, non-graphic and reverent",
        "David alone beneath a star-filled sky holding a simple shepherd staff before dawn",
        "Moses overlooking a vast desert valley with a distant traveling people, historically inspired and reverent",
        "peaceful Bethlehem hillside at night beneath one brilliant star and distant warm village lights",
        "Daniel praying beside an open window in a simple ancient room, reverent and peaceful",
        "a shepherd guiding sheep toward clear water through a green valley inspired by Psalm 23",
        "a small wooden fishing boat on the Sea of Galilee at sunrise evoking the Gospel stories",
    ),
    "symbols_of_faith": (
        "open Bible on natural wood beside a simple ceramic lamp with pages moving gently in a breeze",
        "simple wooden cross on a grassy hill above a sea of clouds",
        "two natural hands resting beside an open Bible in quiet prayer with no jewelry",
        "white dove crossing a bright opening in storm clouds above a peaceful valley",
        "empty stone tomb entrance at early dawn with folded linen visible inside",
        "shepherd staff beside calm sheep near a clear stream in a green valley",
        "open Bible beside a rain-covered window while the first morning light enters",
        "simple cross reflected in calm water at golden hour without text or decorations",
        "old olive-wood prayer bench beside an open Scripture in warm natural window light",
        "single white dove flying above a river through a mountain valley after rain",
    ),
    "creation_and_nature": (
        "clear river winding through a green valley with distant mountains and realistic moving clouds",
        "powerful waterfall in a lush canyon with sunlight catching natural spray",
        "ancient forest path covered in soft moss leading toward warm light",
        "desert dunes beneath a dense star-filled sky and subtle moonlight",
        "calm alpine lake reflecting snowy mountains with small ripples on the surface",
        "ocean waves reaching a quiet rocky coast after rain while clouds open to sunlight",
        "mist drifting through a pine valley as sunrise reaches the mountain peaks",
        "wildflower meadow beside a clear stream beneath enormous summer clouds",
        "rocky canyon river illuminated by a narrow shaft of afternoon sunlight",
        "quiet winter lake surrounded by snow-covered forest beneath a clear blue hour sky",
    ),
    "biblical_places": (
        "ancient Jerusalem-inspired stone street at dawn, empty and peaceful with historically plausible architecture",
        "olive grove on a hillside overlooking a distant ancient city",
        "Sea of Galilee shoreline with reeds, a small wooden fishing boat and natural moving water",
        "quiet Judean desert path between warm sandstone hills",
        "simple ancient stone room with an open scroll, clay lamp and woven cloth",
        "green hillside overlooking a lake evoking a peaceful biblical teaching place without crowds",
        "ancient stone gate opening toward a sunlit valley in a historically inspired Judean landscape",
        "narrow path through an olive grove after rain with distant limestone hills",
        "rocky shoreline beside the Sea of Galilee beneath soft morning mist",
        "Bethlehem-inspired stone village seen from a distant hillside before sunrise",
    ),
    "hope_and_light": (
        "storm clouds opening above mountains as a broad shaft of sunlight reaches a distant valley",
        "single quiet path through wheat fields leading toward a bright horizon",
        "rain ending over a green valley with a natural rainbow appearing in distant mist",
        "small warm lantern illuminating a stone path through darkness",
        "sunrise above a sea of clouds viewed from a mountain summit",
        "gentle rays of light entering a quiet room through a window beside an open Bible",
        "golden light breaking through dark clouds above a calm lake after a storm",
        "bright horizon appearing beyond a long mountain trail at first light",
        "rainbow forming above distant mountains while a river reflects the clearing sky",
        "sunlight entering a deep forest and illuminating drifting mist over a narrow path",
    ),
}

CAMERAS = (
    "ultra-wide cinematic establishing shot with strong foreground depth",
    "low-angle environmental composition with natural leading lines",
    "long-lens layered composition with realistic atmospheric compression",
    "off-center three-quarter composition with generous landscape context",
    "high scenic viewpoint with a natural winding visual path",
    "ground-level perspective with foreground texture and deep background",
    "side-profile cinematic composition with shallow but natural depth of field",
    "over-the-shoulder contemplative composition with realistic optical depth",
    "medium-wide documentary-style composition with natural body proportions",
    "slow-tracking-style frame with subject placed on the rule of thirds",
)

LIGHTING = (
    "physically plausible first golden light",
    "soft diffused overcast daylight",
    "warm sunset rim light with realistic shadows",
    "deep blue hour with subtle practical light",
    "natural moonlight and restrained starlight",
    "sun rays passing through moving post-storm clouds",
    "cool northern daylight with a warm horizon glow",
    "green and violet aurora light with natural color balance",
    "fresh morning light after rain with visible atmospheric moisture",
    "late-afternoon light filtered through thin clouds",
)

ATMOSPHERES = (
    "light natural mist in the distance",
    "subtle breeze moving fabric, grass or water",
    "fresh air after rain with tiny droplets on foreground surfaces",
    "slow realistic clouds creating changing patches of light",
    "crisp clear air with strong distant detail",
    "very light snow or airborne moisture appropriate to the location",
    "gentle water reflections and physically plausible ripples",
    "quiet cinematic atmosphere with no crowds and no staged posing",
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _recent_hashes(previous: list[dict], limit: int = 100) -> set[str]:
    result: set[str] = set()
    for row in previous[-limit:]:
        for value in row.get("visual_prompt_hashes") or []:
            result.add(str(value))
        for item in row.get("visual_pack") or []:
            if isinstance(item, dict) and item.get("prompt_hash"):
                result.add(str(item["prompt_hash"]))
    return result


def _family_usage(previous: list[dict], limit: int = 24) -> dict[str, int]:
    usage = {family: 0 for family in FAMILY_SCENES}
    for row in previous[-limit:]:
        pack = row.get("visual_pack") or row.get("visual_rotation_manifest") or []
        for item in pack:
            if isinstance(item, dict):
                family = str(item.get("family") or "")
                if family in usage:
                    usage[family] += 1
    return usage


def _rng(metadata: dict) -> random.Random:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"
    raw = f"visual-pack-v2|{metadata.get('topic','')}|{metadata.get('title','')}|{marker}"
    return random.Random(int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16))


def _new_combo(family: str, blocked: set[str], rng: random.Random) -> dict[str, str]:
    scenes = FAMILY_SCENES[family]
    for _ in range(240):
        scene = rng.choice(scenes)
        camera = rng.choice(CAMERAS)
        lighting = rng.choice(LIGHTING)
        atmosphere = rng.choice(ATMOSPHERES)
        fingerprint = _hash(f"v2|{family}|{scene}|{camera}|{lighting}|{atmosphere}")
        if fingerprint in blocked:
            continue
        blocked.add(fingerprint)
        return {
            "family": family,
            "scene": scene,
            "camera": camera,
            "lighting": lighting,
            "atmosphere": atmosphere,
            "prompt_hash": fingerprint,
        }
    raise RuntimeError(f"No se encontro una composicion visual nueva para {family}.")


def attach_visual_pack_v2(metadata: dict, previous: list[dict], content_type: str = "short") -> dict:
    if content_type != "short":
        return metadata

    rows = [dict(item) for item in (metadata.get("scenes") or [])]
    scene_count = max(1, len(rows) or 6)
    if not rows:
        rows = [{} for _ in range(scene_count)]

    blocked = _recent_hashes(previous, limit=100)
    usage = _family_usage(previous)
    rng = _rng(metadata)

    # Norway and one Jesus scene are deliberate brand anchors, but their exact
    # compositions are always regenerated from a large combinatorial space.
    selected_families: list[str] = []
    for required in ("norway", "jesus_and_prayer"):
        if required not in selected_families and len(selected_families) < scene_count:
            selected_families.append(required)

    remaining = [family for family in FAMILY_SCENES if family not in selected_families]
    rng.shuffle(remaining)
    remaining.sort(key=lambda family: usage.get(family, 0))
    selected_families.extend(remaining[: max(0, scene_count - len(selected_families))])

    while len(selected_families) < scene_count:
        choices = list(FAMILY_SCENES)
        rng.shuffle(choices)
        selected_families.append(choices[len(selected_families) % len(choices)])

    chosen = [_new_combo(family, blocked, rng) for family in selected_families[:scene_count]]

    topic = str(metadata.get("topic") or metadata.get("content_family") or "mensaje biblico de esperanza")
    reference = str(metadata.get("bible_reference") or "").strip()
    run_marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"

    manifest: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        item = chosen[index]
        variation = _hash(f"{item['prompt_hash']}|{run_marker}|scene-{index}")[:12]
        row["visual_family"] = item["family"]
        row["visual_prompt_hash"] = item["prompt_hash"]
        row["visual_prompt"] = (
            f"{item['scene']}. Camera: {item['camera']}. Lighting: {item['lighting']}. "
            f"Atmosphere: {item['atmosphere']}. Spiritual context: {topic}. "
            + (f"Biblical reference: {reference}. " if reference else "")
            + "Create a completely NEW original photorealistic live-action cinematic frame. Never reproduce an image, pose, crop, background, camera position or composition from an earlier video. "
            "Use realistic anatomy, natural hands, physically plausible fabric, water, clouds and light. Vertical 9:16. No text, no captions, no logo, no watermark, no celebrity resemblance. "
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
    metadata["visual_no_repeat_window"] = 100
    metadata["fresh_reference_bank_required"] = True
    metadata["visual_engine_version"] = "2026.08.17-hf-fresh-bank-v2"
    return metadata
