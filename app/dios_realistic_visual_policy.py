from __future__ import annotations

import hashlib
import random

VISUAL_POLICY_ID = "realistic_biblical_premium_v5"

# No abstract/sacred-geometry visual language. Symbols may appear only as
# secondary natural objects inside a believable photographic scene.
NEGATIVE_VISUAL_CLAUSE = (
    "Absolutely no triangles, sacred geometry, geometric halos, abstract mystical shapes, "
    "floating icons, clipart, doodles, childish drawings, flat illustration, cartoon, anime, "
    "low-poly art, plastic CGI, videogame render, posterized vector art, surreal symbol collage, "
    "text, captions, logo or watermark. Never make a symbol or geometric shape the main subject."
)

CHARACTER_VARIANTS = (
    "fresh fully synthetic adult Jesus depiction, warm compassionate expression, natural olive-toned skin, shoulder-length dark-brown hair, groomed beard, realistic linen robe, three-quarter view",
    "fresh fully synthetic adult Jesus depiction walking naturally, calm confident expression, wind moving dark-brown hair and linen mantle, believable human anatomy",
    "fresh fully synthetic adult Jesus depiction in quiet prayer, realistic hands and skin texture, subtle emotion, side profile, natural woven robe",
    "fresh fully synthetic adult Jesus depiction looking toward the horizon, peaceful eyes, realistic beard and hair strands, candid documentary-style framing",
    "fresh fully synthetic adult Jesus depiction helping a traveler on a mountain path, compassionate body language, realistic clothing and human proportions",
    "fresh fully synthetic adult Jesus depiction beside a lake at dawn, serene expression, natural skin pores, soft backlight, cinematic medium shot",
    "fresh fully synthetic reverent humanlike representation of divine presence, non-celebrity face, natural realistic features, simple ancient linen clothing, soft luminous atmosphere",
    "fresh fully synthetic adult Jesus depiction near an ancient stone village, authentic first-century-inspired clothing, realistic candid photography",
)

LOCATION_FAMILIES = (
    "majestic Norwegian fjord with steep green mountains, crystal water and distant waterfalls",
    "snow-covered Norwegian mountains above a still blue fjord beneath northern lights",
    "beautiful alpine lake with pine forest, snow peaks and clear morning mist",
    "wide biblical valley with olive trees, wild grass and warm golden sunrise",
    "Noah's Ark as a monumental believable wooden vessel resting near mountains after a storm, wet timber, clearing clouds and warm light",
    "Noah's Ark sailing on a vast realistic sea beneath dramatic rain clouds breaking into sunlight",
    "peaceful Sea of Galilee shoreline with realistic reeds, stones, distant hills and dawn light",
    "ancient Judean stone path winding through olive groves and sunlit hills",
    "dramatic desert canyon after rain with fresh streams, warm rock and luminous sky",
    "lush green valley with a powerful waterfall, mist and sunlight through clouds",
    "quiet Nordic forest with tall pines, moss, mountain stream and shafts of natural light",
    "Atlantic coast with tall cliffs, waves calming after a storm and warm horizon light",
    "high mountain trail above clouds at sunrise with expansive realistic landscape",
    "old stone village near rolling hills, olive trees and soft evening light",
    "flowering meadow beside a clear river with distant mountains and realistic golden-hour atmosphere",
    "snowy valley with wooden footbridge, frozen lake and soft winter sunrise",
)

SCENE_FAMILIES = (
    "Jesus walking through the landscape with natural full-body movement",
    "Jesus standing near water while looking toward the horizon",
    "Jesus in quiet prayer integrated naturally into the landscape",
    "Jesus helping or comforting one anonymous traveler without crowding the frame",
    "Jesus seated on a rock beside a beautiful lake or river in reflective silence",
    "Jesus walking toward warm sunrise light from a three-quarter rear angle",
    "cinematic Noah's Ark environment with believable people only as tiny distant silhouettes",
    "beautiful creation landscape with a subtle humanlike divine presence formed by natural light, not geometry",
    "realistic biblical road scene with Jesus approaching through natural atmospheric depth",
    "Jesus beside an ancient olive tree with wind, natural fabric movement and expansive scenery",
    "Jesus on a cliff above a calm sea after a storm, realistic wind and clouds",
    "Jesus near a mountain waterfall with realistic spray, mist and morning light",
)

LIGHTING_MODES = (
    "soft golden sunrise with physically plausible volumetric haze",
    "cool blue-hour light with subtle warm horizon glow",
    "dramatic post-storm sunlight through realistic clouds",
    "clean Nordic overcast light with cinematic contrast",
    "warm late-afternoon side light with natural skin tones",
    "northern-lights night with realistic low-light exposure and restrained aurora",
    "soft mountain morning light with mist and realistic atmospheric perspective",
    "sunset backlight with believable rim light and deep environmental detail",
)

COMPOSITION_MODES = (
    "cinematic medium shot with subject on the left third and landscape opening to the right",
    "wide environmental portrait with the person occupying less than one third of the frame",
    "three-quarter body candid composition with strong foreground-to-background depth",
    "low-angle natural perspective emphasizing mountains and sky without distortion",
    "eye-level documentary framing with shallow but believable depth of field",
    "rear three-quarter walking composition leading the eye into the landscape",
    "close environmental portrait with visible landscape context and natural facial detail",
    "high scenic vantage with subject small enough to showcase the location",
)

THUMBNAIL_SCENE_FAMILIES = (
    "fresh synthetic Jesus in a strong realistic close environmental portrait beside a Norwegian fjord",
    "fresh synthetic Jesus walking toward a bright mountain sunrise with dramatic landscape depth",
    "fresh synthetic Jesus beside a crystal lake with snowy peaks and natural mist",
    "fresh synthetic Jesus under restrained northern lights above a Norwegian fjord",
    "fresh synthetic Jesus near Noah's Ark after a storm, monumental realistic timber ship in background",
    "Noah's Ark on a realistic sea as storm clouds open to golden light, no abstract symbols",
    "fresh synthetic Jesus on a cliff above a calm sea after a storm",
    "fresh synthetic Jesus praying beside an alpine waterfall and green valley",
    "fresh synthetic Jesus on an ancient olive-tree path at golden hour",
    "fresh synthetic Jesus in a snowy Nordic valley at sunrise",
    "fresh synthetic Jesus beside a mountain river with forest and warm heavenly natural light",
    "fresh synthetic Jesus overlooking a vast biblical valley with realistic sunrise clouds",
)


def _pick(items: tuple[str, ...], seed: int, salt: str) -> tuple[int, str]:
    digest = hashlib.sha256(f"{VISUAL_POLICY_ID}|{salt}|{seed}".encode("utf-8")).digest()
    index = int.from_bytes(digest[:8], "big") % len(items)
    return index, items[index]


def scene_bundle(seed: int, *, require_jesus: bool = False) -> dict[str, str]:
    scene_i, scene = _pick(SCENE_FAMILIES, seed, "scene")
    character_i, character = _pick(CHARACTER_VARIANTS, seed, "character")
    location_i, location = _pick(LOCATION_FAMILIES, seed, "location")
    light_i, light = _pick(LIGHTING_MODES, seed, "light")
    comp_i, comp = _pick(COMPOSITION_MODES, seed, "composition")
    if not require_jesus and scene_i in {6, 7}:
        # These two families can work without a foreground Jesus figure.
        character = "no foreground character; use only believable distant anonymous figures if necessary"
    return {
        "scene_family": f"scene-{scene_i:02d}",
        "scene": scene,
        "character_variant": f"character-{character_i:02d}",
        "character": character,
        "location_family": f"location-{location_i:02d}",
        "location": location,
        "lighting_mode": f"light-{light_i:02d}",
        "lighting": light,
        "composition_mode": f"composition-{comp_i:02d}",
        "composition": comp,
    }


def decorate_scene_prompt(base_prompt: str, seed: int, *, require_jesus: bool = False) -> tuple[str, dict[str, str]]:
    bundle = scene_bundle(seed, require_jesus=require_jesus)
    prompt = (
        f"{base_prompt}. {bundle['scene']}. Character treatment: {bundle['character']}. "
        f"Location: {bundle['location']}. Lighting: {bundle['lighting']}. Composition: {bundle['composition']}. "
        "Create a completely new original premium live-action photorealistic biblical frame, with believable human anatomy, "
        "natural skin pores, individual hair strands, realistic woven fabric, physically plausible optics and atmospheric depth. "
        "The environment must be a beautiful real-world-looking landscape, not a studio backdrop. "
        "Keep the scene peaceful, hopeful, reverent and visually impressive for a premium Christian short. "
        "No resemblance to any actor, celebrity or identifiable real person. "
        f"{NEGATIVE_VISUAL_CLAUSE}"
    )
    return prompt, bundle


def thumbnail_bundle(seed: int) -> dict[str, str]:
    motif_i, motif = _pick(THUMBNAIL_SCENE_FAMILIES, seed, "thumbnail-motif")
    character_i, character = _pick(CHARACTER_VARIANTS, seed, "thumbnail-character")
    location_i, location = _pick(LOCATION_FAMILIES, seed, "thumbnail-location")
    light_i, light = _pick(LIGHTING_MODES, seed, "thumbnail-light")
    comp_i, comp = _pick(COMPOSITION_MODES, seed, "thumbnail-composition")
    return {
        "motif_id": f"motif-{motif_i:02d}",
        "motif": motif,
        "character_variant": f"character-{character_i:02d}",
        "character": character,
        "location_family": f"location-{location_i:02d}",
        "location": location,
        "lighting_mode": f"light-{light_i:02d}",
        "lighting": light,
        "composition_mode": f"composition-{comp_i:02d}",
        "composition": comp,
    }


def shuffled_thumbnail_bundles(seed: int) -> list[dict[str, str]]:
    # Build many deterministic combinations, then shuffle them so adjacent runs
    # do not always walk the same visual order.
    bundles: list[dict[str, str]] = []
    for offset in range(max(len(THUMBNAIL_SCENE_FAMILIES), 24)):
        bundles.append(thumbnail_bundle(seed + offset * 104729))
    rng = random.Random(seed ^ 0xD105B1B1)
    rng.shuffle(bundles)
    return bundles
