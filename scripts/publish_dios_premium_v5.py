from __future__ import annotations

import os
from pathlib import Path

from app import hf_primary_router, pipeline, spiritual_audio, spiritual_tts, youtube as youtube_module
from app import dios_photoreal_v5 as photoreal
from app import dios_sovereign_ai as sovereign
from app import dios_sovereign_visual_v3 as premium_visual
from app import dios_sovereign_voice as local_voice
import scripts.publish_dios_sovereign as base


PRIMARY_VOICE = "Algenib"
PRIMARY_BRAND = spiritual_tts.VOICE_BRAND_NAME
PRIMARY_PROFILE = spiritual_tts.SPIRITUAL_VOICE_PROFILE
PRIMARY_LOCK_VERSION = spiritual_tts.VOICE_LOCK_VERSION
LOCAL_PROVIDER = local_voice.VOICE_PROVIDER
_GEMINI_MAKE_VOICE = spiritual_tts.make_spiritual_spanish_voice


def _allow_local_fallback() -> bool:
    config = sovereign.load_config()
    return bool(config.get("voice", {}).get("allow_local_fallback_on_quota_or_provider_error", True))


def _is_primary_voice(used: str) -> bool:
    low = str(used or "").lower()
    return "gemini" in low and f":{PRIMARY_VOICE.lower()}:" in low


def _is_local_voice(used: str) -> bool:
    return LOCAL_PROVIDER.lower() in str(used or "").lower()


def _make_premium_voice(path: Path, text: str) -> str:
    """Prefer the established Voz de Luz / Algenib identity, then local fallback.

    Algenib is a synthetic Google voice, not a real person or a speaker clone. The
    local Piper profile is used only when the primary service is unavailable or
    quota-limited, so publishing can continue without silently using random voices.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        os.environ["TTS_PROVIDER"] = "gemini_tts"
        os.environ["GEMINI_TTS_VOICE"] = PRIMARY_VOICE
        os.environ["SPIRITUAL_MALE_GEMINI_VOICE"] = PRIMARY_VOICE
        os.environ["SPIRITUAL_VOICE_LOCKED"] = "true"
        os.environ["SPIRITUAL_REQUIRE_PRIMARY_VOICE"] = "true"
        os.environ["TTS_FALLBACK_KOKORO"] = "false"
        try:
            return _GEMINI_MAKE_VOICE(path, text)
        except Exception as exc:
            if not _allow_local_fallback():
                raise
            print(
                "Voz de Luz/Algenib no estuvo disponible; se usa temporalmente "
                f"Voz de Luz Local sin cambiar a voces aleatorias. Motivo: {exc}"
            )

    os.environ["TTS_PROVIDER"] = "piper_local"
    return local_voice.make_voice(path, text)


def _enforce_premium_voice(used: str) -> None:
    low = str(used or "").lower()
    if _is_primary_voice(used):
        if "kokoro" in low or "espeak" in low or "clone" in low:
            raise RuntimeError(f"VOICE_PREMIUM_LOCK: proveedor inesperado: {used}")
        return
    if _is_local_voice(used):
        if "kokoro" in low or "espeak" in low:
            raise RuntimeError(f"VOICE_PREMIUM_LOCK: fallback local inesperado: {used}")
        return
    raise RuntimeError(f"VOICE_PREMIUM_LOCK: voz no autorizada: {used}")


def _apply_premium_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    spiritual_audio.apply_spiritual_audio(video, out, channel, meta, duration, seed)
    used = str(meta.get("tts_provider_used") or "")
    _enforce_premium_voice(used)

    if _is_primary_voice(used):
        meta["voice_profile"] = PRIMARY_PROFILE
        meta["voice_brand"] = PRIMARY_BRAND
        meta["voice_identity_locked"] = True
        meta["voice_lock_version"] = PRIMARY_LOCK_VERSION
        meta["voice_expected_provider"] = "Gemini TTS / Algenib / Voz de Luz"
        meta["voice_remote_ai_used"] = True
        meta["voice_local_fallback_used"] = False
    else:
        meta["voice_profile"] = local_voice.VOICE_PROFILE
        meta["voice_brand"] = local_voice.VOICE_BRAND
        meta["voice_identity_locked"] = True
        meta["voice_lock_version"] = local_voice.VOICE_PROVIDER
        meta["voice_expected_provider"] = "Voz de Luz Local / Piper fallback"
        meta["voice_remote_ai_used"] = False
        meta["voice_local_fallback_used"] = True

    meta["premium_voice_policy"] = "algenib_primary_local_fallback_v5"
    meta["visual_model_profile"] = photoreal.MODEL_VERSION
    meta["sovereign_ai_version"] = sovereign.ENGINE_VERSION
    meta["sovereign_visual_version"] = premium_visual.VISUAL_PROVIDER


def configure() -> None:
    # Materialize the user-approved photoreal reference before the base readiness
    # check, because it is versioned as a base64 payload in the repository.
    photoreal.materialize_approved_reference()

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview").strip()

    # Reuse all sovereign visual, anti-duplicate, metadata and upload guards.
    base.configure()

    # The base sovereign setup deliberately clears remote AI credentials. Restore
    # only TTS; image/video generation remains local/offline and quota-independent.
    os.environ["GEMINI_API_KEY"] = gemini_key
    os.environ["GEMINI_TTS_MODEL"] = gemini_model
    os.environ["GEMINI_TTS_VOICE"] = PRIMARY_VOICE
    os.environ["SPIRITUAL_MALE_GEMINI_VOICE"] = PRIMARY_VOICE
    os.environ["GEMINI_VIDEO_ENABLED"] = "false"
    os.environ["HF_VIDEO_ENABLED"] = "false"
    os.environ["HF_REFERENCE_IMAGE_ENABLED"] = "false"
    os.environ["HF_REFERENCE_EDITOR_ENABLED"] = "false"
    os.environ["HF_TEXT_ZERO_ENABLED"] = "false"
    os.environ["HF_INFERENCE_PROVIDER_ENABLED"] = "false"
    os.environ["SPIRITUAL_VOICE_LOCKED"] = "true"
    os.environ["SPIRITUAL_REQUIRE_PRIMARY_VOICE"] = "true"
    os.environ["TTS_FALLBACK_KOKORO"] = "false"
    os.environ["SPIRITUAL_VOICE_BRAND"] = PRIMARY_BRAND
    os.environ["SPIRITUAL_VOICE_PROFILE"] = PRIMARY_PROFILE
    os.environ["SPIRITUAL_VISUAL_REFERENCE_PROFILE"] = photoreal.MODEL_VERSION

    spiritual_audio.make_spiritual_spanish_voice = _make_premium_voice
    spiritual_tts.make_spiritual_spanish_voice = _make_premium_voice
    spiritual_audio._enforce_voice_identity = _enforce_premium_voice
    spiritual_audio.EXPECTED_VOICE = PRIMARY_BRAND
    spiritual_audio.EXPECTED_PROFILE = PRIMARY_PROFILE
    spiritual_audio.VOICE_LOCK_VERSION = PRIMARY_LOCK_VERSION

    hf_primary_router.apply_spiritual_audio = _apply_premium_audio
    youtube_module._enforce_spiritual_voice_guard = base._enforce_sovereign_voice_upload_guard


def main() -> dict:
    configure()
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
