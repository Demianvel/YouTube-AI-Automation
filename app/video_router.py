from __future__ import annotations

from pathlib import Path

from . import video as base_video
from .hf_video import available as hf_video_available
from .hf_video import generate_hf_short


def _sanitize_botanical_prompts(metadata: dict) -> list[str]:
    """Build a dedicated seed-germination time-lapse prompt for BrotaVida HF video."""
    originals: list[str] = []
    family = str(metadata.get("content_family") or metadata.get("topic") or "seed germination").strip()
    for scene in metadata.get("scenes") or []:
        original = str(scene.get("visual_prompt") or "")
        originals.append(original)
        species_hint = " ".join(
            str(scene.get("stock_query") or family or "seed germination time lapse").split()
        )
        scene["visual_prompt"] = (
            f"{species_hint}. SEED GERMINATION TIME LAPSE, premium macro botanical documentary visualization. "
            "Start with one clearly visible seed resting in or just below moist dark soil. Keep the exact same seed and species "
            "throughout the entire shot. Show a smooth continuous biological progression compressed as a real time-lapse: the seed absorbs moisture, "
            "seed coat swells and splits, the white primary root emerges and grows downward, secondary fine roots branch naturally, the shoot curves upward, "
            "pushes through the soil surface, the stem straightens, cotyledons open and the first small green leaves unfold. "
            "Use a locked macro camera or transparent soil cross-section view so roots and shoot remain visible. Realistic plant anatomy, natural gravity, "
            "realistic soil particles and moisture, subtle natural light changes, satisfying organic motion, photographic macro detail, no jump cuts. "
            "Do not morph into another species, do not duplicate the plant, no magical growth, no fantasy colors, no hands, no tools, no pot labels, "
            "no text, no subtitles, no logos, no watermark. Vertical 9:16 premium YouTube Shorts composition."
        )
    return originals


def _restore_visual_prompts(metadata: dict, originals: list[str]) -> None:
    for scene, original in zip(metadata.get("scenes") or [], originals):
        scene["visual_prompt"] = original


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    """Use Hugging Face text-to-video as the primary visual engine for every automated channel.

    BrotaVida receives a dedicated seed-germination time-lapse master prompt. EnViKids and
    Dinero Claro also go through HF first. Existing channel renderers are reliability fallbacks
    only when the free HF/ZeroGPU/provider route is unavailable.
    """
    visual_mode = str(channel.get("visual_mode") or "").lower()
    botanical = "botanical" in visual_mode
    eligible = botanical or "kids" in visual_mode or "mixed_finance" in visual_mode

    if eligible and hf_video_available():
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
            if botanical:
                metadata["botanical_source_type"] = "synthetic_ai_seed_germination_timelapse"
                metadata["visual_format"] = "seed germination time lapse"
            return final
        except Exception as exc:
            metadata["hf_primary_failed"] = str(exc)
            print(f"Hugging Face text-to-video no disponible ({exc}); usando renderer estable del canal como fallback.")
        finally:
            if botanical and originals:
                _restore_visual_prompts(metadata, originals)

    return base_video.generate_short(channel, metadata, workdir)
