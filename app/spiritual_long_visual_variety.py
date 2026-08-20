from __future__ import annotations

import hashlib
import os
import random


LONG_VISUAL_DIRECTIONS = (
    "wide Norwegian fjord at dawn with layered mountains, changing clouds and natural mist, no people",
    "open Bible on weathered natural wood beside an olive branch in warm window light, no human portrait",
    "recurring synthetic Jesus walking along a Sea of Galilee shoreline at sunrise, full-body environmental shot",
    "small sparrows moving among olive branches above a clear stream in morning light, no people",
    "ancient Jerusalem-inspired stone street after rain at dawn, empty and historically plausible",
    "storm clouds opening above a mountain lake while sunlight reaches the water, no people",
    "shepherd guiding sheep through a green valley toward clear water, distant cinematic composition",
    "recurring synthetic Jesus praying beside an old olive tree at blue hour, side-profile medium-wide shot",
    "empty stone tomb entrance at first dawn with natural warm light and folded linen, reverent and non-graphic",
    "powerful waterfall in a mossy canyon with realistic spray and moving sunlight, no people",
    "quiet stone chapel interior with sunlight crossing empty wooden pews, no people",
    "recurring synthetic Jesus reading Scripture on a rocky hillside above a lake, over-the-shoulder composition",
    "desert dunes beneath a dense star field and subtle moonlight, no people",
    "white dove crossing a bright opening in post-storm clouds above a river valley, no people",
    "Lofoten-style Arctic coast beneath green and violet aurora reflected on dark water, no people",
    "simple wooden cross on a grassy ridge above a sea of clouds at sunrise, no people",
    "recurring synthetic Jesus walking through alpine wildflowers while fabric moves naturally in the breeze",
    "wild river winding through a broad mountain valley under huge summer clouds, no people",
    "ancient olive grove path with limestone hills and late-afternoon sunlight, no people",
    "rainbow forming over distant mountains after rain while a river reflects clearing sky, no people",
    "lamb resting beside an adult sheep in a peaceful meadow with distant hills, no people",
    "recurring synthetic Jesus looking over a valley as sunlight breaks through clouds, restrained three-quarter shot",
    "ocean waves reaching dark rocks after rain while golden light appears at the horizon, no people",
    "simple clay lamp beside an open Scripture in an ancient stone room, close cinematic detail, no people",
)

SHOT_DIRECTIONS = (
    "ultra-wide establishing shot with strong foreground depth and slow dolly feeling",
    "medium-wide documentary composition with natural perspective",
    "low-angle environmental frame with realistic leading lines",
    "high scenic viewpoint with layered atmospheric depth",
    "off-center rule-of-thirds composition with generous negative space",
    "long-lens layered composition with restrained depth compression",
    "ground-level perspective with tactile foreground texture",
    "side-profile composition with shallow but natural depth of field",
    "over-the-shoulder contemplative composition",
    "slow push-in style framing with the focal point away from exact center",
)


def _rng(meta: dict) -> random.Random:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"
    raw = f"dios-long-visual-v3|{meta.get('title','')}|{meta.get('topic','')}|{marker}"
    return random.Random(int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16))


def apply_long_visual_diversity(meta: dict) -> dict:
    sections = [dict(item) for item in (meta.get("sections") or [])]
    if not sections:
        return meta

    rng = _rng(meta)
    directions = list(LONG_VISUAL_DIRECTIONS)
    shots = list(SHOT_DIRECTIONS)
    rng.shuffle(directions)
    rng.shuffle(shots)

    used: list[str] = []
    for index, section in enumerate(sections):
        direction = directions[index % len(directions)]
        shot = shots[(index * 3) % len(shots)]
        original = " ".join(str(section.get("visual_prompt") or "").split())
        section["visual_prompt"] = (
            f"Primary visual direction: {direction}. Camera language: {shot}. "
            "This section must look visibly different from the previous and next sections: change subject arrangement, environment, focal distance, camera height, light direction and dominant shapes. "
            "Use premium photoreal live-action cinematic optics, physically plausible light and natural environmental motion. "
            "Do not reuse a prior frame, portrait crop, background, camera angle or composition. "
            "Horizontal 16:9, no text, no captions, no logo, no watermark. "
            + (f"Narrative context only: {original}" if original else "")
        )[:1900]
        section["visual_direction_v3"] = direction
        section["visual_shot_v3"] = shot
        used.append(direction)

    meta["sections"] = sections
    meta["long_visual_diversity_version"] = "2026.08.20-semantic-motion-v3"
    meta["long_visual_unique_direction_count"] = len(set(used))
    meta["long_visual_portrait_every_section"] = False
    return meta
