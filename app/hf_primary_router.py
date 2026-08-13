from __future__ import annotations

import os
from pathlib import Path

from . import video as base_video
from .hf_video import available as hf_video_available
from .hf_video import generate_hf_short


def _brotavida_prompts(metadata: dict) -> list[str]:
    originals: list[str] = []
    family = str(metadata.get("content_family") or metadata.get("topic") or "seed germination").strip()
    for scene in metadata.get("scenes") or []:
        original = str(scene.get("visual_prompt") or "")
        originals.append(original)
        species = " ".join(str(scene.get("stock_query") or family or "seed germination time lapse").split())
        scene["visual_prompt"] = (
            f"{species}. SEED GERMINATION TIME LAPSE. Premium photorealistic macro botanical documentary text-to-video. "
            "One seed and one exact plant species throughout the entire shot. Show a smooth continuous biological progression compressed across days: "
            "the seed absorbs moisture and swells, the seed coat cracks open, a white primary root emerges and grows downward, fine secondary roots branch, "
            "a pale shoot bends upward through moist dark soil, breaks the soil surface, the stem straightens, cotyledons open and the first green leaves unfold. "
            "Locked macro camera, transparent soil cross-section or clean side-view germination setup, clear root and shoot visibility, realistic plant anatomy, "
            "natural gravity, realistic soil particles and moisture, subtle daylight change, shallow depth of field, smooth satisfying organic time-lapse motion. "
            "No mature plant jump, no species change, no duplicate plant, no fantasy colors, no hands, no tools, no labels, no text, no subtitles, no logo, "
            "no watermark. Vertical 9:16 premium YouTube Shorts composition."
        )
    return originals


def _restore(metadata: dict, originals: list[str]) -> None:
    for scene, original in zip(metadata.get("scenes") or [], originals):
        scene["visual_prompt"] = original


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    visual_mode = str(channel.get("visual_mode") or "").lower()
    botanical = "botanical" in visual_mode
    eligible = botanical or "kids" in visual_mode or "mixed_finance" in visual_mode
    strict = os.getenv("HF_VIDEO_STRICT", "true").lower().strip() == "true"

    if not eligible:
        return base_video.generate_short(channel, metadata, workdir)

    if not hf_video_available():
        if strict:
            raise RuntimeError("Hugging Face text-to-video esta deshabilitado y HF_VIDEO_STRICT=true.")
        return base_video.generate_short(channel, metadata, workdir)

    final = workdir / "short.mp4"
    workdir.mkdir(parents=True, exist_ok=True)
    originals: list[str] = []
    try:
        if botanical:
            originals = _brotavida_prompts(metadata)
        generate_hf_short(channel, metadata, workdir, final, base_video.apply_audio)
        metadata["visual_source"] = "huggingface_seed_germination_text_to_video" if botanical else "huggingface_text_to_video_primary"
        metadata["hf_primary"] = True
        metadata["hf_strict"] = strict
        if botanical:
            metadata["botanical_source_type"] = "synthetic_ai_seed_germination_timelapse"
            metadata["visual_format"] = "seed germination time lapse"
        return final
    except Exception as exc:
        metadata["hf_primary_failed"] = str(exc)
        if strict:
            raise RuntimeError(f"Hugging Face no pudo generar el Short y HF_VIDEO_STRICT=true: {exc}") from exc
        print(f"Hugging Face text-to-video no disponible ({exc}); usando renderer estable del canal como fallback.")
        return base_video.generate_short(channel, metadata, workdir)
    finally:
        if botanical and originals:
            _restore(metadata, originals)
