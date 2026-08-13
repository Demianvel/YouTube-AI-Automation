from __future__ import annotations

import os
from pathlib import Path

from . import video as base_video
from .hf_video import available as hf_video_available
from .hf_video import generate_hf_short


def _sanitize_botanical_prompts(metadata: dict) -> list[str]:
    """Give HF a clean species/context hint; hf_video adds the phase-specific master prompt."""
    originals: list[str] = []
    family = str(metadata.get("content_family") or metadata.get("topic") or "seed germination").strip()
    for scene in metadata.get("scenes") or []:
        original = str(scene.get("visual_prompt") or "")
        originals.append(original)
        species_hint = " ".join(
            str(scene.get("stock_query") or family or "seed germination time lapse").split()
        )
        scene["visual_prompt"] = (
            f"{species_hint}. Seed germination time lapse of this exact species in a transparent soil cross-section, "
            "one centered seed, macro scientific studio setup, same seed and species throughout."
        )
    return originals


def _restore_visual_prompts(metadata: dict, originals: list[str]) -> None:
    for scene, original in zip(metadata.get("scenes") or [], originals):
        scene["visual_prompt"] = original


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    """Use Hugging Face text-to-video as the primary visual engine for every automated channel.

    Default behavior is strict: if HF cannot generate the visual, publication stops instead of
    silently using a non-HF renderer. Set HF_REQUIRE_TEXT_TO_VIDEO=false only when a reliability
    fallback is explicitly desired.
    """
    visual_mode = str(channel.get("visual_mode") or "").lower()
    botanical = "botanical" in visual_mode
    eligible = botanical or "kids" in visual_mode or "mixed_finance" in visual_mode
    require_hf = os.getenv("HF_REQUIRE_TEXT_TO_VIDEO", "true").lower() == "true"

    if not eligible:
        return base_video.generate_short(channel, metadata, workdir)

    if not hf_video_available():
        if require_hf:
            raise RuntimeError("HF_REQUIRE_TEXT_TO_VIDEO=true pero HF_VIDEO_ENABLED esta deshabilitado.")
        return base_video.generate_short(channel, metadata, workdir)

    final = workdir / "short.mp4"
    workdir.mkdir(parents=True, exist_ok=True)
    originals: list[str] = []
    try:
        if botanical:
            originals = _sanitize_botanical_prompts(metadata)
        generate_hf_short(channel, metadata, workdir, final, base_video.apply_audio)
        metadata["visual_source"] = (
            "huggingface_seed_germination_text_to_video"
            if botanical
            else "huggingface_text_to_video_primary"
        )
        metadata["hf_primary"] = True
        metadata["hf_required"] = require_hf
        if botanical:
            metadata["botanical_source_type"] = "synthetic_ai_seed_germination_timelapse"
            metadata["visual_format"] = "seed germination time lapse"
        return final
    except Exception as exc:
        metadata["hf_primary_failed"] = str(exc)
        if require_hf:
            raise RuntimeError(
                f"Hugging Face text-to-video era obligatorio y no pudo generar el video: {exc}"
            ) from exc
        print(f"Hugging Face text-to-video no disponible ({exc}); usando renderer estable del canal como fallback.")
        return base_video.generate_short(channel, metadata, workdir)
    finally:
        if botanical and originals:
            _restore_visual_prompts(metadata, originals)
