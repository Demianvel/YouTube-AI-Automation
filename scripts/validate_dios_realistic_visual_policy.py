from __future__ import annotations

from app.dios_realistic_visual_policy import (
    CHARACTER_VARIANTS,
    COMPOSITION_MODES,
    LIGHTING_MODES,
    LOCATION_FAMILIES,
    NEGATIVE_VISUAL_CLAUSE,
    SCENE_FAMILIES,
    THUMBNAIL_SCENE_FAMILIES,
    VISUAL_POLICY_ID,
    decorate_scene_prompt,
    scene_bundle,
    shuffled_thumbnail_bundles,
)


def main() -> int:
    assert VISUAL_POLICY_ID == "realistic_biblical_premium_v5"
    assert len(CHARACTER_VARIANTS) >= 8
    assert len(LOCATION_FAMILIES) >= 14
    assert len(SCENE_FAMILIES) >= 10
    assert len(LIGHTING_MODES) >= 8
    assert len(COMPOSITION_MODES) >= 8
    assert len(THUMBNAIL_SCENE_FAMILIES) >= 10

    negative = NEGATIVE_VISUAL_CLAUSE.lower()
    for blocked in (
        "triangles",
        "sacred geometry",
        "geometric halos",
        "clipart",
        "cartoon",
        "doodles",
        "low-poly",
        "plastic cgi",
        "text",
        "logo",
        "watermark",
    ):
        assert blocked in negative, blocked

    locations_text = " ".join(LOCATION_FAMILIES).lower()
    assert "norwegian" in locations_text or "norway" in locations_text
    assert "noah's ark" in locations_text
    assert "fjord" in locations_text
    assert "northern lights" in locations_text
    assert "lake" in locations_text
    assert "mountain" in locations_text

    seen_characters: set[str] = set()
    seen_locations: set[str] = set()
    seen_scenes: set[str] = set()
    seen_lights: set[str] = set()
    seen_compositions: set[str] = set()
    for seed in range(2026090400, 2026090500):
        bundle = scene_bundle(seed, require_jesus=True)
        seen_characters.add(bundle["character_variant"])
        seen_locations.add(bundle["location_family"])
        seen_scenes.add(bundle["scene_family"])
        seen_lights.add(bundle["lighting_mode"])
        seen_compositions.add(bundle["composition_mode"])

    assert len(seen_characters) >= 6, seen_characters
    assert len(seen_locations) >= 10, seen_locations
    assert len(seen_scenes) >= 8, seen_scenes
    assert len(seen_lights) >= 6, seen_lights
    assert len(seen_compositions) >= 6, seen_compositions

    prompt, bundle = decorate_scene_prompt(
        "Jesus brings hope after a difficult night",
        2026090401,
        require_jesus=True,
    )
    low = prompt.lower()
    assert "completely new original" in low
    assert "live-action photorealistic" in low
    assert "beautiful real-world-looking landscape" in low
    assert "triangles" in low  # explicit negative instruction
    assert "symbolic biblical frame" not in low
    assert bundle["character_variant"].startswith("character-")

    thumbs = shuffled_thumbnail_bundles(20260904)
    thumb_looks = {
        (
            row["motif_id"],
            row["character_variant"],
            row["location_family"],
            row["lighting_mode"],
            row["composition_mode"],
        )
        for row in thumbs
    }
    assert len(thumb_looks) >= 16, len(thumb_looks)

    print(
        "REALISTIC_VISUAL_POLICY_OK",
        f"characters={len(seen_characters)}",
        f"locations={len(seen_locations)}",
        f"scenes={len(seen_scenes)}",
        f"lights={len(seen_lights)}",
        f"compositions={len(seen_compositions)}",
        f"thumbnail_looks={len(thumb_looks)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
