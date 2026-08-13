from __future__ import annotations

from pathlib import Path

from . import video as base_video
from .hf_video import available as hf_video_available
from .hf_video import generate_hf_short


def _sanitize_botanical_prompts(metadata: dict) -> list[str]:
    originals: list[str] = []
    for scene in metadata.get("scenes") or []:
        original = str(scene.get("visual_prompt") or "")
        originals.append(original)
        helper = " ".join(str(scene.get("stock_query") or metadata.get("content_family") or metadata.get("topic") or "seed germination").split())
        scene["visual_prompt"] = (
            f"{helper}. Premium botanical macro time-lapse visualization, one seed, same species throughout, "
            "seed coat opens, primary root grows downward, fine roots branch, shoot rises through moist soil, "
            "stem straightens, cotyledons or first leaves unfold, believable plant anatomy, realistic moisture, "
            "continuous coherent growth, locked macro camera, natural colors, no magical morphing, no species change, "
            "no duplicate plants, no hands, no tools, no text, no logo, no watermark, vertical 9:16."
        )
    return originals


def _restore_visual_prompts(metadata: dict, originals: list[str]) -> None:
    for scene, original in zip(metadata.get("scenes") or [], originals):
        scene["visual_prompt"] = original


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    """Prefer unique AI video for BrotaVida, EnViKids and Dinero Claro.

    Hugging Face is best-effort because free ZeroGPU/provider availability can vary.
    If AI generation is unavailable, each channel returns to its existing stable renderer.
    BrotaVida AI output is explicitly marked synthetic in metadata; its fallback remains
    species-specific real footage rather than a generic plant clip.
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
                "huggingface_botanical_ai_visualization"
                if botanical
                else "huggingface_unique_ai_video"
            )
            if botanical:
                metadata["botanical_source_type"] = "synthetic_ai_visualization"
            return final
        except Exception as exc:
            print(f"Hugging Face text-to-video no disponible ({exc}); usando renderer estable del canal.")
        finally:
            if botanical and originals:
                _restore_visual_prompts(metadata, originals)

    return base_video.generate_short(channel, metadata, workdir)
