from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "dioshablahoyia_visual_engine.json"
PLAN_PATH = ROOT / "state" / "dioshablahoyia_visual_plan.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def visual_config() -> dict[str, Any]:
    return _load_json(CONFIG_PATH)


def image_model_candidates() -> list[str]:
    configured = os.getenv("HF_IMAGE_MODELS", "").strip()
    if configured:
        return [item.strip() for item in configured.split(",") if item.strip()]
    single = os.getenv("HF_IMAGE_MODEL", "").strip()
    config_models = [str(item).strip() for item in visual_config().get("image_models", []) if str(item).strip()]
    ordered = ([single] if single else []) + config_models
    out: list[str] = []
    for model in ordered:
        if model and model not in out:
            out.append(model)
    return out or ["black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-xl-base-1.0"]


def _daily_marker(metadata: dict[str, Any]) -> str:
    run = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return "|".join((
        day,
        run,
        str(metadata.get("topic", "")),
        str(metadata.get("title", "")),
        str(metadata.get("bible_reference", "")),
    ))


def _seed(metadata: dict[str, Any], index: int, aspect: str) -> int:
    raw = f"visual-library-v1|{_daily_marker(metadata)}|{index}|{aspect}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _forced_family(metadata: dict[str, Any]) -> str | None:
    text = " ".join((
        str(metadata.get("topic", "")),
        str(metadata.get("title", "")),
        str(metadata.get("bible_reference", "")),
    )).lower()
    if any(token in text for token in ("noé", "noe", "arca", "diluvio", "génesis 6", "genesis 6")):
        return "biblical_stories"
    if any(token in text for token in ("moisés", "moises", "mar rojo", "david", "samaritano", "belén", "belen", "tumba")):
        return "biblical_stories"
    if any(token in text for token in ("noche", "dormir", "descanso", "paz")):
        return "norway"
    return None


def _family_order(config: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    families = config.get("families") or {}
    plan = _load_json(PLAN_PATH)
    planned = [str(item) for item in (plan.get("family_order") or []) if str(item) in families]
    forced = _forced_family(metadata)
    names = planned or list(families)
    if forced and forced in names:
        names = [forced] + [name for name in names if name != forced]
    elif forced and forced in families:
        names = [forced] + names
    return names


def _weighted_families(config: dict[str, Any], metadata: dict[str, Any]) -> list[str]:
    families = config.get("families") or {}
    weighted: list[str] = []
    for name in _family_order(config, metadata):
        row = families.get(name) or {}
        weight = max(1, int(row.get("weight", 1)))
        weighted.extend([name] * weight)
    return weighted or ["creation_and_nature"]


def choose_visual_theme(metadata: dict[str, Any], index: int, *, aspect: str) -> dict[str, str]:
    config = visual_config()
    families = config.get("families") or {}
    weighted = _weighted_families(config, metadata)
    seed = _seed(metadata, index, aspect)

    # A large prime stride prevents adjacent scenes from selecting the same family.
    family = weighted[(seed + index * 17) % len(weighted)]
    row = families.get(family) or {}
    scenes = [str(item).strip() for item in (row.get("scenes") or []) if str(item).strip()]
    if not scenes:
        scenes = ["beautiful natural landscape at sunrise with peaceful cinematic light"]
    scene = scenes[(seed // 19 + index * 7) % len(scenes)]

    camera_modes = (
        "wide establishing shot with strong depth and natural scale",
        "slow cinematic tracking composition with foreground depth",
        "intimate medium shot balanced with a detailed real environment",
        "low-angle respectful composition with moving clouds",
        "high scenic viewpoint with natural leading lines",
        "side-profile composition with soft directional light",
        "long-lens landscape composition with layered atmosphere",
        "gentle orbit-style composition around the main subject",
    )
    lighting = (
        "soft golden sunrise",
        "blue-hour natural light",
        "warm sunset after rain",
        "moonlight and realistic stars",
        "sun rays through moving clouds",
        "diffused Arctic daylight",
        "gentle candle and window light",
        "clear morning light with natural mist",
    )
    return {
        "family": family,
        "scene": scene,
        "camera": camera_modes[(seed // 23 + index * 3) % len(camera_modes)],
        "lighting": lighting[(seed // 29 + index * 5) % len(lighting)],
        "aspect": aspect,
        "theme_id": hashlib.sha1(f"{family}|{scene}|{aspect}".encode("utf-8")).hexdigest()[:12],
    }


def enrich_visual_prompt(
    base_prompt: str,
    metadata: dict[str, Any],
    index: int,
    *,
    aspect: str,
) -> tuple[str, dict[str, str]]:
    config = visual_config()
    selected = choose_visual_theme(metadata, index, aspect=aspect)
    negative = str(config.get("negative_prompt") or "text, logo, watermark, cartoon, deformed hands")
    recurring = (
        "When Jesus appears, use the same original fully synthetic recurring adult Middle Eastern/Mediterranean representation: "
        "shoulder-length wavy dark-brown hair, groomed beard, hazel-brown eyes, natural skin detail, ivory linen robe, "
        "realistic anatomy and hands, no resemblance to any actor or identifiable person. "
    )
    prompt = (
        f"{base_prompt}. New visual direction: {selected['scene']}. {selected['camera']}. "
        f"Lighting: {selected['lighting']}. {recurring}Premium photoreal live-action cinema, physically plausible nature, "
        f"peaceful reverent atmosphere, composition {aspect}. Avoid: {negative}."
    )
    return " ".join(prompt.split()), selected


def enrich_metadata_visuals(metadata: dict[str, Any], *, content_type: str) -> dict[str, Any]:
    rows_key = "scenes" if content_type == "short" else "sections"
    aspect = "vertical 9:16" if content_type == "short" else "horizontal 16:9"
    rows = list(metadata.get(rows_key) or [])
    manifest: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        base_prompt = str(row.get("visual_prompt") or "reverent biblical scene with nature and peaceful light")
        prompt, selected = enrich_visual_prompt(base_prompt, metadata, index, aspect=aspect)
        row["visual_prompt"] = prompt
        row["visual_theme"] = selected
        manifest.append(selected)
    metadata[rows_key] = rows
    metadata["visual_rotation_manifest"] = manifest
    metadata["visual_engine_version"] = str(visual_config().get("version") or "visual-library-v1")
    metadata["visual_image_models"] = image_model_candidates()
    metadata["visual_daily_rotation"] = True
    metadata["visual_norway_enabled"] = True
    metadata["visual_noahs_ark_enabled"] = True
    return metadata
