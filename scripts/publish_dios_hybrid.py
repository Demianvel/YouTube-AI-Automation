from __future__ import annotations

import os
import time
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from app import pipeline, spiritual_audio, spiritual_image, spiritual_tts, youtube as youtube_module
from app import spiritual_reference_generation as reference_generation
from app import dios_premium_editorial_v7 as editorial_v7
from app import dios_premium_editorial_v8 as editorial_v8
from app import dios_brain
from app.dios_brain import strategist as brain_strategist
from app.dios_realistic_visual_policy import VISUAL_POLICY_ID, decorate_scene_prompt
from app.qwen_voice import generate_qwen_premium_voice
from app.spiritual_auto_thumbnail import build_auto_thumbnail
import scripts.publish_dios_fast as fast
import scripts.publish_dios_locked as locked

REALISTIC_VISUAL_VERSION = "dios-realistic-scenic-v5"
REALISTIC_FALLBACK_VERSION = "dios-realistic-scenic-fallback-v5"

_ORIGINAL_PIPELINE_UPLOAD = pipeline.upload_video
_ORIGINAL_PIPELINE_UNIQUENESS = pipeline.validate_spiritual_uniqueness
_ORIGINAL_APPEND_HISTORY = pipeline.append_history
_ORIGINAL_V7_CHOOSE_THEME = editorial_v7._choose_theme
_LAST_THUMBNAIL_FIELDS: dict = {}
_LAST_BRAIN_FIELDS: dict = {}
_LAST_THEME: dict = {}


def _allow_qwen_backup() -> bool:
    return os.getenv("SPIRITUAL_ALLOW_QWEN_BACKUP", "false").strip().lower() == "true"


def _premium_hybrid_voice(path: Path, text: str) -> str:
    locked._assert_permanent_voice_environment()
    try:
        used = spiritual_tts._gemini_spiritual_voice(path, text)
        if not spiritual_tts.is_configured_gemini_provider(used):
            raise RuntimeError(f"VOICE_IDENTITY_LOCK: proveedor Gemini inesperado: {used}")
        spiritual_tts._brand_master(path)
        return used
    except Exception as exc:
        if not _allow_qwen_backup() or not spiritual_tts._is_gemini_quota_error(exc):
            raise
        print(
            f"Gemini/{spiritual_tts.configured_gemini_voice()} sin cuota. Activando respaldo local Hugging Face Qwen3-TTS; "
            "es una voz premium alternativa de Voz de Luz, no se etiqueta como la voz Gemini.",
            flush=True,
        )
        used = generate_qwen_premium_voice(path, text)
        spiritual_tts._brand_master(path)
        return used


def _is_jesus_scene(prompt: str) -> bool:
    low = str(prompt or "").lower()
    markers = (
        "jesus", "jesús", "christ", "cristo", "messiah", "mesías",
        "sea of galilee", "disciple", "discípulo",
    )
    return any(marker in low for marker in markers)


def _provider_label(provider: str, bundle: dict[str, str], *, fallback: bool) -> str:
    version = REALISTIC_FALLBACK_VERSION if fallback else REALISTIC_VISUAL_VERSION
    return (
        f"{provider}:{version}:{VISUAL_POLICY_ID}:"
        f"{bundle['scene_family']}:{bundle['character_variant']}:"
        f"{bundle['location_family']}:{bundle['lighting_mode']}:{bundle['composition_mode']}"
    )


def _premium_visual_download(prompt: str, out: Path, seed: int) -> str:
    require_jesus = _is_jesus_scene(prompt)
    realistic_prompt, bundle = decorate_scene_prompt(prompt, seed, require_jesus=require_jesus)
    reference = locked._locked_choose_reference(seed)

    # Use the existing reference-guided ZeroGPU path as a creative guide, but
    # explicitly ask for a fresh synthetic depiction and a new environment.
    # This prevents the previous abstract-symbol interpretation while retaining
    # a reverent, realistic Jesus look.
    try:
        provider = reference_generation._generate_text_zerogpu(
            reference,
            realistic_prompt,
            out,
            seed,
            (1080, 1920),
        )
        return _provider_label(provider, bundle, fallback=False)
    except Exception as exc:
        print(
            "Generacion realista guiada no disponible "
            f"({exc}); intentando fuente visual fresca con el mismo prompt realista.",
            flush=True,
        )

    # Last-resort path keeps the same strict photographic/scenic prompt. The
    # provider is still tagged as realistic-v5 and geometric/abstract imagery
    # is explicitly forbidden by the prompt policy.
    provider = fast._fresh_free_media(realistic_prompt, out, seed, attempts=24)
    return _provider_label(provider, bundle, fallback=True)


def _premium_visual_upload_guard(channel: dict, metadata: dict) -> None:
    if youtube_module._is_spiritual_channel(channel):
        labels = metadata.get("generated_visual_provider") or metadata.get("visual_providers") or []
        if isinstance(labels, str):
            labels = [labels]
        labels = [str(item) for item in labels]
        if not labels:
            raise RuntimeError("REALISTIC_VISUAL_GUARD: no hay trazabilidad visual antes de YouTube.")

        realistic_count = 0
        legacy_reference_count = 0
        for label in labels:
            low = label.lower()
            if REALISTIC_VISUAL_VERSION in label or REALISTIC_FALLBACK_VERSION in label:
                if VISUAL_POLICY_ID not in label:
                    raise RuntimeError(f"REALISTIC_VISUAL_GUARD: escena sin politica v5: {label}")
                realistic_count += 1
                continue
            if locked.VISUAL_LOCK_VERSION.lower() in low:
                # Accept historical in-flight frames produced before the v5
                # switch, but new frames are generated through realistic-v5.
                legacy_reference_count += 1
                continue
            raise RuntimeError(
                "REALISTIC_VISUAL_GUARD: se rechazo una escena fuera del motor realista premium: "
                f"{label}"
            )

        metadata["visual_identity_locked"] = False
        metadata["visual_identity_profile"] = "fresh_synthetic_realistic_jesus_rotating_v5"
        metadata["visual_policy"] = VISUAL_POLICY_ID
        metadata["visual_realistic_scene_count"] = realistic_count
        metadata["visual_legacy_reference_scene_count"] = legacy_reference_count
        metadata["visual_symbolic_ai_scene_count"] = 0
        metadata["visual_abstract_geometry_allowed"] = False
        metadata["visual_cartoon_allowed"] = False
        metadata["visual_beautiful_landscape_required"] = True
        metadata["visual_character_rotation_required"] = True
        metadata["visual_mixed_premium_mode"] = True
        metadata["visual_synthetic_disclosure"] = True

    locked._ORIGINAL_VISUAL_GUARD(channel, metadata)


def _brain_choose_theme(previous: list[dict]):
    """Strategist agent first; the original v7 selector stays as fallback."""
    global _LAST_THEME
    result = None
    if dios_brain.enabled():
        try:
            result = dios_brain.brain_choose_theme(editorial_v7, previous)
        except Exception as exc:
            print(f"Dios Brain strategist no disponible ({exc}); se usa el selector editorial v7.", flush=True)
            result = None
    if result is None:
        brain_strategist.LAST_DECISION = {"brain_selection_mode": "original_v7_selector"}
        result = _ORIGINAL_V7_CHOOSE_THEME(previous)
    _LAST_THEME = dict(result[0])
    return result


def _brain_generate_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    metadata = editorial_v8.generate_metadata(channel, previous, retries=retries)
    try:
        metadata.update({k: v for k, v in dict(brain_strategist.LAST_DECISION).items() if v is not None})
        if _LAST_THEME:
            metadata["_brain_theme"] = dict(_LAST_THEME)
    except Exception as exc:
        print(f"Dios Brain: no se pudo adjuntar la decision del estratega ({exc}).", flush=True)
    return metadata


def _premium_uniqueness(metadata: dict, previous: list[dict]) -> dict:
    metadata = editorial_v8.restore_unique_packaging(metadata, previous)
    # Writer/SEO + CTA + quality editor run after every existing SEO transform so
    # nothing downstream overwrites them; any brain failure keeps the original.
    metadata = dios_brain.apply_brain_packaging(metadata, previous, themes=editorial_v7.THEMES)
    metadata["visual_policy"] = VISUAL_POLICY_ID
    metadata["visual_abstract_geometry_allowed"] = False
    metadata["visual_character_rotation_required"] = True
    metadata["visual_beautiful_landscape_required"] = True
    return _ORIGINAL_PIPELINE_UNIQUENESS(metadata, previous)


def _set_thumbnail_verified(channel: dict, video_id: str, thumbnail: Path) -> tuple[int, dict]:
    last_exc: Exception | None = None
    for attempt in range(1, 6):
        try:
            youtube = youtube_module._youtube_for_channel(channel)
            response = youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg", resumable=False),
            ).execute()
            items = response.get("items") or []
            if not items:
                raise RuntimeError(f"YouTube thumbnails.set respondio sin items: {response}")
            return attempt, response
        except Exception as exc:
            last_exc = exc
            if attempt >= 5:
                break
            time.sleep(min(20, 2 * attempt + 1))
    raise RuntimeError(f"No se pudo confirmar miniatura tras 5 intentos: {last_exc}")


def _premium_upload(channel: dict, metadata: dict, video_path: Path) -> str:
    global _LAST_THUMBNAIL_FIELDS, _LAST_BRAIN_FIELDS
    try:
        _LAST_BRAIN_FIELDS = dios_brain.record_fields(metadata)
    except Exception:
        _LAST_BRAIN_FIELDS = {}
    thumbnail = build_auto_thumbnail(
        video_path.parent,
        metadata,
        content_type="short",
        video_path=video_path,
    )
    video_id = _ORIGINAL_PIPELINE_UPLOAD(channel, metadata, video_path)

    try:
        attempts, response = _set_thumbnail_verified(channel, video_id, thumbnail)
        metadata["thumbnail_status"] = "uploaded_to_youtube_verified_response"
        metadata["thumbnail_upload_status"] = "set_verified"
        metadata["thumbnail_upload_attempts"] = attempts
        metadata["thumbnail_youtube_response_items"] = len(response.get("items") or [])
        metadata["thumbnail_repair_required"] = False
        print(f"Miniatura premium realista 9:16 verificada en YouTube para {video_id}: {thumbnail.name}")
    except Exception as exc:
        metadata["thumbnail_status"] = f"upload_failed_after_retries:{type(exc).__name__}"
        metadata["thumbnail_upload_status"] = metadata["thumbnail_status"]
        metadata["thumbnail_repair_required"] = True
        metadata["thumbnail_upload_error"] = str(exc)[:700]
        print(f"Short {video_id} publicado; miniatura requiere reparacion automatica: {exc}")

    keys = (
        "thumbnail_status", "thumbnail_upload_status", "thumbnail_upload_attempts",
        "thumbnail_youtube_response_items", "thumbnail_repair_required", "thumbnail_upload_error",
        "thumbnail_sha256", "thumbnail_dhash", "thumbnail_nearest_distance",
        "thumbnail_source", "thumbnail_provider", "thumbnail_prompt_hash",
        "thumbnail_style_id", "thumbnail_layout_id", "thumbnail_aspect",
        "thumbnail_ai_policy", "thumbnail_openai_fallback_reason",
        "thumbnail_scene_family", "thumbnail_character_variant", "thumbnail_location_family",
        "thumbnail_lighting_mode", "thumbnail_composition_mode",
    )
    _LAST_THUMBNAIL_FIELDS = {key: metadata.get(key) for key in keys if metadata.get(key) is not None}
    return video_id


def _append_history_with_thumbnail(path, record: dict) -> None:
    enriched = dict(record)
    enriched.update(_LAST_THUMBNAIL_FIELDS)
    # Analyst agent: persist the variants used so future runs can prefer winners.
    for key, value in _LAST_BRAIN_FIELDS.items():
        enriched.setdefault(key, value)
    _ORIGINAL_APPEND_HISTORY(path, enriched)


def configure_hybrid_publisher() -> None:
    locked.configure_locked_publisher()
    editorial_v7._choose_theme = _brain_choose_theme
    pipeline.generate_metadata = _brain_generate_metadata
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
