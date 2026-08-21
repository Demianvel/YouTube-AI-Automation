from __future__ import annotations

import os
from pathlib import Path

from app import hf_primary_router, pipeline, spiritual_audio, spiritual_image, spiritual_tts
from app import dios_sovereign_ai as sovereign
from app import dios_sovereign_voice as sovereign_voice
import scripts.publish_dios_fast as fast


LOCAL_VOICE_PROFILE = sovereign_voice.VOICE_PROFILE
LOCAL_VOICE_BRAND = sovereign_voice.VOICE_BRAND
LOCAL_VOICE_LOCK_VERSION = sovereign_voice.VOICE_PROVIDER


def _configure_offline_env() -> None:
    sovereign.enforce_offline_runtime()
    os.environ["GEMINI_API_KEY"] = ""
    os.environ["GEMINI_VIDEO_ENABLED"] = "false"
    os.environ["HF_VIDEO_ENABLED"] = "false"
    os.environ["HF_REFERENCE_IMAGE_ENABLED"] = "false"
    os.environ["HF_REFERENCE_EDITOR_ENABLED"] = "false"
    os.environ["HF_TEXT_ZERO_ENABLED"] = "false"
    os.environ["HF_INFERENCE_PROVIDER_ENABLED"] = "false"
    os.environ["POLLINATIONS_API_KEY"] = ""
    os.environ["PEXELS_API_KEY"] = ""
    os.environ["TTS_PROVIDER"] = "piper_local"
    os.environ["TTS_FALLBACK_KOKORO"] = "false"
    os.environ["SPIRITUAL_REQUIRE_PRIMARY_VOICE"] = "true"
    os.environ["SPIRITUAL_VOICE_LOCKED"] = "true"
    os.environ["SPIRITUAL_VOICE_BRAND"] = LOCAL_VOICE_BRAND
    os.environ["SPIRITUAL_VOICE_PROFILE"] = LOCAL_VOICE_PROFILE
    os.environ["SPIRITUAL_ALLOW_LOCAL_PROCEDURAL_VISUAL"] = "false"


def _local_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    return sovereign.build_theme_metadata(channel, previous)


def _enforce_local_voice(used: str) -> None:
    low = str(used or "").lower()
    if LOCAL_VOICE_LOCK_VERSION not in low:
        raise RuntimeError(f"VOICE_SOVEREIGN_LOCK: proveedor local inesperado: {used}")
    if any(marker in low for marker in ("gemini", "algenib", "kokoro", "espeak", "fallback")):
        raise RuntimeError(f"VOICE_SOVEREIGN_LOCK: se detecto una voz no soberana: {used}")


def _apply_sovereign_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    spiritual_audio.apply_spiritual_audio(video, out, channel, meta, duration, seed)
    used = str(meta.get("tts_provider_used") or "")
    _enforce_local_voice(used)
    meta["voice_profile"] = LOCAL_VOICE_PROFILE
    meta["voice_brand"] = LOCAL_VOICE_BRAND
    meta["voice_identity_locked"] = True
    meta["voice_lock_version"] = LOCAL_VOICE_LOCK_VERSION
    meta["voice_expected_provider"] = "Piper local / Voz de Luz Local"
    meta["voice_remote_ai_used"] = False
    meta["sovereign_ai_version"] = sovereign.ENGINE_VERSION


def configure() -> None:
    _configure_offline_env()
    status = sovereign.readiness()
    if not status["reference_fallback_ready"]:
        raise RuntimeError("VISUAL_SOVEREIGN_LOCK: el banco de referencias no esta listo.")
    if not status["voice_local_ready"]:
        raise RuntimeError(
            "VOICE_LOCAL_MODEL_MISSING: instalar los pesos Piper locales antes de activar publicacion soberana."
        )

    pipeline.generate_metadata = _local_metadata
    pipeline.attach_visual_pack = fast.attach_visual_pack_v3
    spiritual_image._download = sovereign.generate_visual
    spiritual_image._animate = fast._fast_animate

    spiritual_audio.make_spiritual_spanish_voice = sovereign_voice.make_voice
    spiritual_tts.make_spiritual_spanish_voice = sovereign_voice.make_voice
    spiritual_audio._fit_text_for_natural_short_voice = sovereign_voice.fit_script
    spiritual_audio._enforce_voice_identity = _enforce_local_voice
    spiritual_audio.EXPECTED_VOICE = LOCAL_VOICE_BRAND
    spiritual_audio.EXPECTED_PROFILE = LOCAL_VOICE_PROFILE
    spiritual_audio.VOICE_LOCK_VERSION = LOCAL_VOICE_LOCK_VERSION

    # hf_primary_router imported the audio function by value, so replace that
    # reference too. Visual/video remote paths are disabled by environment.
    hf_primary_router.apply_spiritual_audio = _apply_sovereign_audio


def main() -> dict:
    configure()
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
