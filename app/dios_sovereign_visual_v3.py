from __future__ import annotations

from pathlib import Path

from . import dios_sovereign_ai as sovereign
from .dios_sovereign_scene import ENGINE_VERSION as DIVERSITY_ENGINE, render_unique_scene

VISUAL_PROVIDER = "dhh-sovereign-local-visual-v3"


def generate_visual(prompt: str, out: Path, seed: int) -> str:
    """Use local diffusion when available, otherwise the diverse CPU renderer.

    This wrapper preserves the higher-quality local diffusion/LoRA path on a GPU
    machine, but prevents the hosted CPU catch-up from recycling six crops of the
    same three Jesus references. The CPU path uses one recurring human Jesus
    composite plus original symbolic/nature scenes and self-checks dHash freshness.
    """
    config = sovereign.load_config()
    sovereign.enforce_offline_runtime()

    global_cache_ready = bool(getattr(sovereign, "_PIPELINE_CACHE_READY", False))
    if not global_cache_ready:
        sovereign._PIPELINE_CACHE = sovereign._load_diffusion_pipeline(config)
        sovereign._PIPELINE_CACHE_READY = True

    if getattr(sovereign, "_PIPELINE_CACHE", None) is not None:
        provider = sovereign.generate_visual(prompt, out, seed)
        return f"{VISUAL_PROVIDER}/local-diffusion/{provider}"

    image_cfg = config["image"]
    refs = sovereign._reference_files(config)
    provider = render_unique_scene(
        out,
        prompt,
        seed,
        references=refs,
        width=int(image_cfg["width"]),
        height=int(image_cfg["height"]),
        max_attempts=9,
    )
    return f"{VISUAL_PROVIDER}/{DIVERSITY_ENGINE}/{provider}"
