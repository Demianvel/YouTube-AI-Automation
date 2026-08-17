from __future__ import annotations

import hashlib
import os
import random
from typing import Any


VISUAL_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "family": "jesus_and_prayer",
        "scenes": (
            ("recurring synthetic Jesus praying alone beside an olive tree at first light", "intimate side-profile medium shot", "soft golden sunrise"),
            ("recurring synthetic Jesus walking beside a clear mountain stream with his robe moving naturally in the breeze", "wide environmental full-body shot", "cool morning light with warm rim light"),
            ("recurring synthetic Jesus reading an open Scripture on a quiet stone path", "over-the-shoulder cinematic composition", "warm late-afternoon sunlight"),
            ("recurring synthetic Jesus extending one open hand toward the viewer beside a calm lake", "three-quarter medium shot with visible natural hand", "blue hour with subtle warm horizon light"),
            ("recurring synthetic Jesus standing among wildflowers looking across a valley", "off-center wide portrait with strong landscape depth", "sun rays through moving clouds"),
            ("recurring synthetic Jesus kneeling in prayer on a rocky hill above a distant sea", "low respectful full-body angle", "natural moonlight and subtle stars"),
        ),
    },
    {
        "family": "norway",
        "scenes": (
            ("Tromso winter fjord beneath vivid green and violet aurora borealis reflected on still water", "wide low-angle landscape composition", "realistic aurora and moonlight"),
            ("Lofoten Islands with steep snowy peaks rising from a calm Norwegian sea and small warm village lights", "long-lens layered landscape", "deep blue hour"),
            ("Geirangerfjord with immense cliffs, waterfalls and low natural mist", "high scenic viewpoint with leading lines", "clear diffused morning light"),
            ("Senja coastline with rugged dark peaks, cold sea and passing clouds", "slow tracking-style coastal composition", "northern golden hour"),
            ("Norwegian waterfall descending through dark rock and vivid moss after rain", "close environmental landscape with foreground spray", "soft overcast daylight"),
            ("quiet red cabin beside a snowy Norwegian fjord under northern lights", "wide cinematic establishing shot", "aurora-lit winter night"),
        ),
    },
    {
        "family": "biblical_stories",
        "scenes": (
            ("Noah's Ark as a massive historically inspired wooden vessel on flood waters while animals approach in pairs", "epic wide establishing shot from water level", "storm clearing into warm sunlight"),
            ("the Good Samaritan compassionately helping an injured traveler on an ancient road, non-graphic and reverent", "human-scale medium-wide storytelling frame", "warm late-afternoon desert light"),
            ("Jesus calming a storm on the Sea of Galilee with disciples in a wooden boat, dramatic but peaceful", "wide cinematic boat-level composition", "storm clouds opening to sunlight"),
            ("David alone beneath a star-filled sky holding a simple shepherd staff before dawn", "full-body environmental portrait", "natural starlight with first blue dawn"),
            ("Moses overlooking a vast desert valley with a distant traveling people, historically inspired and reverent", "high wide landscape composition", "clear sunrise through desert haze"),
            ("a peaceful Bethlehem hillside at night beneath one brilliant star with distant warm village lights", "wide contemplative landscape", "deep night sky and warm practical lights"),
        ),
    },
    {
        "family": "symbols_of_faith",
        "scenes": (
            ("open Bible on natural wood beside a simple ceramic lamp, pages moving gently in a breeze", "close cinematic tabletop tracking composition", "warm window sunrise"),
            ("simple wooden cross on a grassy hill above a sea of clouds", "low wide silhouette composition", "golden dawn breaking through clouds"),
            ("two natural hands resting beside an open Bible in quiet prayer, no jewelry and no text overlay", "top-down intimate composition", "soft window daylight"),
            ("white dove crossing a bright opening in storm clouds above a peaceful valley", "telephoto sky-and-landscape composition", "sun rays after rain"),
            ("empty stone tomb entrance at early dawn with folded linen visible inside, reverent and historically inspired", "low interior-to-exterior composition", "soft sunrise entering the tomb"),
            ("shepherd staff beside calm sheep near a clear stream in a green valley", "ground-level pastoral composition", "gentle morning mist"),
        ),
    },
    {
        "family": "creation_and_nature",
        "scenes": (
            ("clear river winding through a green valley with distant mountains and realistic moving clouds", "high scenic viewpoint", "fresh morning sunlight"),
            ("powerful waterfall in a lush canyon with sunlight catching natural spray", "wide landscape with strong foreground depth", "sun rays through mist"),
            ("ancient forest path covered in soft moss leading toward warm light", "eye-level leading-line composition", "golden dawn through trees"),
            ("desert dunes beneath a dense star-filled sky and subtle moonlight", "wide minimalist landscape", "natural moonlight"),
            ("calm alpine lake reflecting snowy mountains with small ripples on the surface", "low shoreline composition", "pastel sunrise"),
            ("ocean waves reaching a quiet rocky coast after rain while clouds open to sunlight", "wide coastal cinematic frame", "warm post-storm light"),
        ),
    },
    {
        "family": "biblical_places",
        "scenes": (
            ("ancient Jerusalem-inspired stone street at dawn, empty and peaceful, historically plausible architecture", "street-level cinematic depth", "soft sunrise"),
            ("olive grove on a hillside overlooking a distant ancient city", "wide contemplative landscape", "warm sunset"),
            ("Sea of Galilee shoreline with reeds, small wooden fishing boat and natural moving water", "low shoreline establishing composition", "clear morning light"),
            ("quiet Judean desert path between warm sandstone hills", "long-lens compressed landscape", "late-afternoon light"),
            ("simple ancient stone room with an open scroll, clay lamp and woven cloth", "intimate interior composition", "warm lamp and window light"),
            ("green hillside overlooking a lake, evoking a peaceful biblical teaching place without crowds", "wide elevated composition", "bright diffused daylight"),
        ),
    },
    {
        "family": "hope_and_light",
        "scenes": (
            ("storm clouds opening above mountains as a broad shaft of sunlight reaches a distant valley", "epic wide landscape", "dramatic natural sun rays"),
            ("single quiet path through wheat fields leading toward a bright horizon", "low centered leading-line composition", "warm sunrise"),
            ("rain ending over a green valley with a natural rainbow appearing in distant mist", "wide realistic landscape", "clear post-rain light"),
            ("small warm lantern illuminating a stone path through darkness", "close foreground composition with deep background", "natural night ambience"),
            ("sunrise above a sea of clouds viewed from a mountain summit", "ultra-wide elevated composition", "first golden light"),
            ("gentle rays of light entering a quiet room through a window beside an open Bible", "side-lit interior composition", "soft morning light"),
        ),
    },
)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _recent_hashes(previous: list[dict], limit: int = 60) -> set[str]:
    hashes: set[str] = set()
    for row in previous[-limit:]:
        for value in row.get("visual_prompt_hashes") or []:
            hashes.add(str(value))
        for item in row.get("visual_pack") or []:
            if isinstance(item, dict) and item.get("prompt_hash"):
                hashes.add(str(item["prompt_hash"]))
    return hashes


def _recent_families(previous: list[dict], limit: int = 12) -> list[str]:
    result: list[str] = []
    for row in previous[-limit:]:
        pack = row.get("visual_pack") or []
        if pack:
            result.extend(str(item.get("family")) for item in pack if isinstance(item, dict) and item.get("family"))
            continue
        for item in row.get("visual_rotation_manifest") or []:
            if isinstance(item, dict) and item.get("family"):
                result.append(str(item["family"]))
    return result


def _rng(metadata: dict) -> random.Random:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"
    raw = f"visual-pack-v1|{metadata.get('topic','')}|{metadata.get('title','')}|{marker}"
    return random.Random(int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16))


def attach_visual_pack(metadata: dict, previous: list[dict], content_type: str = "short") -> dict:
    if content_type != "short":
        return metadata

    rows = list(metadata.get("scenes") or [])
    scene_count = max(1, len(rows) or 6)
    blocked = _recent_hashes(previous)
    recent_families = _recent_families(previous)
    rng = _rng(metadata)

    families = list(VISUAL_FAMILIES)
    rng.shuffle(families)
    # Prefer families not heavily used in the most recent Shorts.
    families.sort(key=lambda block: recent_families.count(str(block["family"])))

    candidates: list[dict[str, str]] = []
    for block in families:
        scene_options = list(block["scenes"])
        rng.shuffle(scene_options)
        for scene, camera, lighting in scene_options:
            fingerprint_source = f"{block['family']}|{scene}|{camera}|{lighting}"
            prompt_hash = _hash(fingerprint_source)
            if prompt_hash in blocked:
                continue
            candidates.append({
                "family": str(block["family"]),
                "scene": scene,
                "camera": camera,
                "lighting": lighting,
                "prompt_hash": prompt_hash,
            })
            break

    # If a long history has exhausted one option per family, reopen unseen scene options.
    if len(candidates) < scene_count:
        for block in families:
            scene_options = list(block["scenes"])
            rng.shuffle(scene_options)
            for scene, camera, lighting in scene_options:
                fingerprint_source = f"{block['family']}|{scene}|{camera}|{lighting}"
                prompt_hash = _hash(fingerprint_source)
                if prompt_hash in blocked or any(item["prompt_hash"] == prompt_hash for item in candidates):
                    continue
                candidates.append({
                    "family": str(block["family"]),
                    "scene": scene,
                    "camera": camera,
                    "lighting": lighting,
                    "prompt_hash": prompt_hash,
                })
                if len(candidates) >= scene_count:
                    break
            if len(candidates) >= scene_count:
                break

    if not candidates:
        raise RuntimeError("No se pudo construir un paquete visual nuevo.")

    chosen = candidates[:scene_count]
    if not rows:
        rows = [{} for _ in range(scene_count)]

    topic = str(metadata.get("topic") or metadata.get("content_family") or "mensaje biblico de esperanza")
    bible_reference = str(metadata.get("bible_reference") or "").strip()
    context = f" Context: {topic}." + (f" Biblical reference: {bible_reference}." if bible_reference else "")

    manifest: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        item = chosen[index % len(chosen)]
        variation = _hash(f"{item['prompt_hash']}|{os.getenv('GITHUB_RUN_ID','')}|{index}")[:10]
        row["visual_family"] = item["family"]
        row["visual_prompt_hash"] = item["prompt_hash"]
        row["visual_prompt"] = (
            f"{item['scene']}. Camera: {item['camera']}. Lighting: {item['lighting']}."
            f"{context} Create a completely NEW original photorealistic cinematic frame; do not reuse a previous image, pose, crop, background or composition. "
            "Natural anatomy, physically plausible light, premium live-action photography, vertical 9:16, no text, no logo, no watermark. "
            f"Unique composition fingerprint {variation}."
        )
        manifest.append({
            "family": item["family"],
            "scene": item["scene"],
            "camera": item["camera"],
            "lighting": item["lighting"],
            "aspect": "vertical 9:16",
            "theme_id": item["prompt_hash"][:12],
        })

    metadata["scenes"] = rows
    metadata["visual_pack"] = chosen
    metadata["visual_prompt_hashes"] = [item["prompt_hash"] for item in chosen]
    metadata["visual_rotation_manifest"] = manifest
    metadata["visual_variety_enabled"] = True
    metadata["visual_no_repeat_window"] = 60
    metadata["visual_engine_version"] = "2026.08.16-free-fresh-v1"
    return metadata
