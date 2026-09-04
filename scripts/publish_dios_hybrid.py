from __future__ import annotations

import os
from pathlib import Path

from app import pipeline, spiritual_audio, spiritual_image, spiritual_tts, youtube as youtube_module
from app import spiritual_reference_generation as reference_generation
from app import dios_premium_editorial_v8 as editorial_v8
from app.qwen_voice import generate_qwen_premium_voice
from app.spiritual_auto_thumbnail import build_auto_thumbnail
import scripts.publish_dios_fast as fast
import scripts.publish_dios_locked as locked

SYMBOLIC_VISUAL_VERSION = "dios-symbolic-ai-v1"
SYMBOLIC_FALLBACK_VERSION = "dios-symbolic-fresh-fallback-v1"

_ORIGINAL_PIPELINE_UPLOAD = pipeline.upload_video
_ORIGINAL_PIPELINE_UNIQUENESS = pipeline.validate_spiritual_uniqueness
_ORIGINAL_APPEND_HISTORY = pipeline.append_history
_LAST_THUMBNAIL_FIELDS: dict = {}


def _allow_qwen_backup() -> bool:
    return os.getenv("SPIRITUAL_ALLOW_QWEN_BACKUP", "false").strip().lower() == "true"


def _premium_hybrid_voice(path: Path, text: str) -> str:
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
            reference, synthetic_prompt, out, seed, (1080, 1920)
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

    locked._ORIGINAL_VISUAL_GUARD(channel, metadata)


def _premium_uniqueness(metadata: dict, previous: list[dict]) -> dict:
    metadata = editorial_v8.restore_unique_packaging(metadata, previous)
    return _ORIGINAL_PIPELINE_UNIQUENESS(metadata, previous)


def _premium_upload(channel: dict, metadata: dict, video_path: Path) -> str:
    global _LAST_THUMBNAIL_FIELDS
    thumbnail = build_auto_thumbnail(
        video_path.parent,
        metadata,
        content_type="short",
        video_path=video_path,
    )
    video_id = _ORIGINAL_PIPELINE_UPLOAD(channel, metadata, video_path)

    try:
        youtube_module.set_custom_thumbnail(channel, video_id, thumbnail)
        metadata["thumbnail_status"] = "uploaded_to_youtube"
        metadata["thumbnail_upload_status"] = "set"
        print(f"Miniatura premium 9:16 unica aplicada a {video_id}: {thumbnail.name}")
    except Exception as exc:
        metadata["thumbnail_status"] = f"upload_failed_nonfatal:{type(exc).__name__}"
        metadata["thumbnail_upload_status"] = metadata["thumbnail_status"]
        print(f"Short {video_id} publicado; miniatura personalizada no aplicada: {exc}")

    keys = (
        "thumbnail_status", "thumbnail_upload_status", "thumbnail_sha256", "thumbnail_dhash",
        "thumbnail_nearest_distance", "thumbnail_source", "thumbnail_provider",
        "thumbnail_prompt_hash", "thumbnail_style_id", "thumbnail_layout_id",
        "thumbnail_aspect", "thumbnail_ai_policy", "thumbnail_openai_fallback_reason",
    )
    _LAST_THUMBNAIL_FIELDS = {key: metadata.get(key) for key in keys if metadata.get(key) is not None}
    return video_id


def _append_history_with_thumbnail(path, record: dict) -> None:
    enriched = dict(record)
    enriched.update(_LAST_THUMBNAIL_FIELDS)
    _ORIGINAL_APPEND_HISTORY(path, enriched)


def configure_hybrid_publisher() -> None:
    locked.configure_locked_publisher()
    pipeline.generate_metadata = editorial_v8.generate_metadata
    pipeline.validate_spiritual_uniqueness = _premium_uniqueness
    pipeline.upload_video = _premium_upload
    pipeline.append_history = _append_history_with_thumbnail
    spiritual_image._download = _premium_visual_download
    youtube_module._enforce_spiritual_visual_guard = _premium_visual_upload_guard
    spiritual_audio.make_spiritual_spanish_voice = _premium_hybrid_voice
    spiritual_tts.make_spiritual_spanish_voice = _premium_hybrid_voice


def main() -> dict:
    configure_hybrid_publisher()
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
