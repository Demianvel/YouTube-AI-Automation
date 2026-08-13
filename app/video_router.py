from __future__ import annotations

from pathlib import Path

from . import video as base_video
from .hf_video import available as hf_video_available
from .hf_video import generate_hf_short


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    """Prefer unique AI video for EnViKids/Dinero Claro, preserve real-only BrotaVida.

    Hugging Face is intentionally best-effort: free-tier/provider availability can vary.
    Existing renderers remain the reliability fallback.
    """
    visual_mode = str(channel.get("visual_mode") or "").lower()
    botanical = "botanical" in visual_mode
    eligible = "kids" in visual_mode or "mixed_finance" in visual_mode

    if not botanical and eligible and hf_video_available():
        final = workdir / "short.mp4"
        workdir.mkdir(parents=True, exist_ok=True)
        try:
            generate_hf_short(channel, metadata, workdir, final, base_video.apply_audio)
            metadata["visual_source"] = "huggingface_unique_ai_video"
            return final
        except Exception as exc:
            print(f"Hugging Face text-to-video no disponible ({exc}); usando renderer estable del canal.")

    return base_video.generate_short(channel, metadata, workdir)
