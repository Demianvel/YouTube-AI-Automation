from __future__ import annotations

import os
from pathlib import Path

from app import pipeline, spiritual_audio, spiritual_image, spiritual_tts, youtube as youtube_module
from app import spiritual_reference_generation as reference_generation
from app import dios_premium_editorial_v8 as editorial_v8
from app.qwen_voice import generate_qwen_premium_voice
import scripts.publish_dios_fast as fast
import scripts.publish_dios_locked as locked

SYMBOLIC_VISUAL_VERSION = "dios-symbolic-ai-v1"
SYMBOLIC_FALLBACK_VERSION = "dios-symbolic-fresh-fallback-v1"


def _allow_qwen_backup() -> bool:
    return os.getenv("SPIRITUAL_ALLOW_QWEN_BACKUP", "false").strip().lower() == "true"


def _premium_hybrid_voice(path: Path, text: str) -> str:
    """Prefer Algenib; use local Qwen3-TTS only when Gemini is quota-blocked."""
    locked._assert_permanent_voice_environment()

    try:
        used = spiritual_tts._gemini_spiritual_voice(path, text)
        low = str(used or "").lower()
        if "gemini" not in low or ":algenib:" not in low or "kokoro" in low:
            raise RuntimeError(f"VOICE_IDENTITY_LOCK: proveedor Gemini inesperado: {used}")
        spiritual_tts._brand_master(path)
        return used
    except Exception as exc:
        if not _allow_qwen_backup() or not spiritual_tts._is_gemini_quota_error(exc):
            raise

        print(
            "Gemini/Algenib sin cuota. Activando respaldo local Hugging Face Qwen3-TTS; "
            "es una voz premium alternativa, no se etiqueta como Algenib identica.",
            flush=True,
        )
        used = generate_qwen_premium_voice(path, text)
        spiritual_tts._brand_master(path)
        return used


def _is_jesus_scene(prompt: str) -> bool:
    low = str(prompt or "").lower()
    markers = (
        "jesus", "jesús", "christ", "cristo", "recurring synthetic jesus",
        "sea of galilee", "disciple", "discípulo",
    )
    return any(marker in low for marker in markers)


def _premium_visual_download(prompt: str, out: Path, seed: int) -> str:
    """Generate a fresh visual according to subject type.

    Jesus-visible scenes preserve the recurring synthetic reference identity.
    Symbolic/Bible/nature scenes are generated as new frames with FLUX ZeroGPU
    when available. If remote generation is quota-blocked, use a fresh licensed
    source instead of recycling a Jesus portrait.
    """
    if _is_jesus_scene(prompt):
        return locked._locked_reference_download(prompt, out, seed)

    reference = locked._locked_choose_reference(seed)
    synthetic_prompt = (
        f"{prompt}. Create an entirely new original AI-generated symbolic biblical frame. "
        "Photoreal cinematic optics, physically plausible natural light, realistic materials, "
        "emotionally clear composition, vertical 9:16, no text, no captions, no logo, no watermark, "
        "no celebrity resemblance, no identifiable real person."
    )
    try:
        provider = reference_generation._generate_text_zerogpu(
            reference,
            synthetic_prompt,
            out,
            seed,
            (1080, 1920),
        )
        return f"{provider}:{SYMBOLIC_VISUAL_VERSION}:original_synthetic_frame"
    except Exception as exc:
        print(f"FLUX simbolico no disponible ({exc}); buscando una fuente visual fresca no repetida.")
        provider = fast._fresh_free_media(synthetic_prompt, out, seed, attempts=20)
        return f"{provider}:{SYMBOLIC_FALLBACK_VERSION}"


def _premium_visual_upload_guard(channel: dict, metadata: dict) -> None:
    if youtube_module._is_spiritual_channel(channel):
        labels = metadata.get("generated_visual_provider") or metadata.get("visual_providers") or []
        if isinstance(labels, str):
            labels = [labels]
        labels = [str(item) for item in labels]
        if not labels:
            raise RuntimeError("PREMIUM_VISUAL_GUARD: no hay trazabilidad visual antes de YouTube.")

        jesus_count = 0
        symbolic_count = 0
        for label in labels:
            low = label.lower()
            if locked.VISUAL_LOCK_VERSION.lower() in low:
                if not any(f"reference:{name}" in label for name in locked.REFERENCE_NAMES):
                    raise RuntimeError(f"PREMIUM_VISUAL_GUARD: Jesus sin referencia autorizada: {label}")
                jesus_count += 1
                continue
            if SYMBOLIC_VISUAL_VERSION in label or SYMBOLIC_FALLBACK_VERSION in label:
                symbolic_count += 1
                continue
            raise RuntimeError(f"PREMIUM_VISUAL_GUARD: proveedor visual no autorizado: {label}")

        metadata["visual_identity_locked"] = jesus_count > 0
        metadata["visual_identity_profile"] = "realistic_synthetic_jesus_reference_abc_v1"
        metadata["visual_symbolic_ai_scene_count"] = symbolic_count
        metadata["visual_jesus_reference_scene_count"] = jesus_count
        metadata["visual_mixed_premium_mode"] = True
        metadata["visual_synthetic_disclosure"] = True

    # Run the generic anti-duplicate visual validator after the premium policy.
    locked._ORIGINAL_VISUAL_GUARD(channel, metadata)


def configure_hybrid_publisher() -> None:
    locked.configure_locked_publisher()

    # Premium editorial v8: broader hooks, stronger topic/visual rotation and a
    # unique thumbnail concept. Final SEO/anti-spam checks still run in pipeline.
    pipeline.generate_metadata = editorial_v8.generate_metadata

    # Subject-aware visual routing. Only visible Jesus scenes use the recurring
    # identity reference; symbolic scenes are newly generated instead.
    spiritual_image._download = _premium_visual_download
    youtube_module._enforce_spiritual_visual_guard = _premium_visual_upload_guard

    # Narrator: Algenib first, local Qwen backup on quota-only failures.
    spiritual_audio.make_spiritual_spanish_voice = _premium_hybrid_voice
    spiritual_tts.make_spiritual_spanish_voice = _premium_hybrid_voice


def main() -> dict:
    configure_hybrid_publisher()
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
