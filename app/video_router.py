from __future__ import annotations

from pathlib import Path

from . import video as base_video
from .hf_video import available as hf_video_available
from .hf_video import generate_hf_short


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
        try:
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

    return base_video.generate_short(channel, metadata, workdir)
