from __future__ import annotations

from pathlib import Path

from . import dios_sovereign_ai as sovereign
from . import dios_photoreal_v5 as photoreal
from .dios_sovereign_scene import ENGINE_VERSION as DIVERSITY_ENGINE, render_unique_scene

VISUAL_PROVIDER = "dhh-premium-photoreal-visual-v5"


def generate_visual(prompt: str, out: Path, seed: int) -> str:
    """Generate premium human/cinematic Christian imagery with no 3D aesthetic.

    Priority:
      1. Local diffusion + identity LoRA, grounded by the approved v5 reference.
      2. CPU reference composition for scene 1 plus diverse symbolic/nature scenes.

    The approved reference is materialized from the repository's versioned base64
    payload before readiness, so hosted runners can use the same visual identity.
    """
    photoreal.materialize_approved_reference()
    config = sovereign.load_config()
    sovereign.enforce_offline_runtime()
    premium_prompt = photoreal.strengthen_prompt(prompt)

    global_cache_ready = bool(getattr(sovereign, "_PIPELINE_CACHE_READY", False))
    if not global_cache_ready:
        sovereign._PIPELINE_CACHE = sovereign._load_diffusion_pipeline(config)
        sovereign._PIPELINE_CACHE_READY = True

    if getattr(sovereign, "_PIPELINE_CACHE", None) is not None:
        provider = sovereign.generate_visual(premium_prompt, out, seed)
        return f"{VISUAL_PROVIDER}/local-diffusion/{photoreal.MODEL_VERSION}/{provider}"

    image_cfg = config["image"]
    refs = photoreal.preferred_references(sovereign._reference_files(config))
    provider = render_unique_scene(
        out,
        premium_prompt,
        seed,
        references=refs,
        width=int(image_cfg["width"]),
        height=int(image_cfg["height"]),
        max_attempts=9,
    )
    return f"{VISUAL_PROVIDER}/{photoreal.MODEL_VERSION}/{DIVERSITY_ENGINE}/{provider}"
