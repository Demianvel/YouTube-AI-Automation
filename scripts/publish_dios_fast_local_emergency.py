from __future__ import annotations

from pathlib import Path

from app import pipeline, spiritual_audio, spiritual_image, youtube as youtube_module
from app.local_spiritual_media import (
    LOCAL_MEDIA_ENGINE_VERSION,
    LOCAL_VOICE_PROFILE,
    generate_original_spiritual_image,
    make_local_spiritual_voice,
)
import scripts.publish_dios_fast as fast


VISUAL_DIVERSITY_VERSION = "dios-local-quota-free-v1"


def _local_visual_download(prompt: str, out: Path, seed: int) -> str:
    provider = generate_original_spiritual_image(prompt, out, seed, target_size=(1080, 1920))
    print(f"{VISUAL_DIVERSITY_VERSION}: visual original creado localmente: {provider}")
    return provider


def _local_voice_identity_guard(used: str) -> None:
    value = str(used or "").lower().strip()
    if not value.startswith("local_"):
        raise RuntimeError(
            "LOCAL_VOICE_LOCK: el publicador sin cuota solo acepta la voz generada localmente. "
            f"Provider recibido: {used or 'vacio'}"
        )


def _local_voice_youtube_guard(channel: dict, metadata: dict, video_path: Path) -> None:
    if not youtube_module._is_spiritual_channel(channel):
        return

    passed = metadata.get("voice_continuity_passed")
    coverage_raw = metadata.get("voice_coverage_ratio")
    longest_raw = metadata.get("longest_voice_silence_seconds")
    coverage = float(coverage_raw if coverage_raw is not None else 0.0)
    longest = float(longest_raw if longest_raw is not None else 999.0)

    if passed is not True or coverage < 0.82 or longest > 2.2:
        raise RuntimeError(
            "BLOQUEADO ANTES DE YOUTUBE: la voz local no supero continuidad natural "
            f"(passed={passed}, coverage={coverage:.1%}, longest_silence={longest:.2f}s)."
        )
    if not youtube_module._has_audio_stream(video_path):
        raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: el Short local no contiene stream de audio.")

    metadata["voice_continuity_guard_mode"] = "quota_free_local_voice_82pct"
    metadata["voice_continuity_upload_threshold"] = 0.82
    metadata["voice_profile"] = LOCAL_VOICE_PROFILE
    metadata["voice_identity_locked"] = True
    metadata["voice_expected_provider"] = "local quota-free TTS"
    metadata["local_media_engine"] = LOCAL_MEDIA_ENGINE_VERSION


# Reuse the mature local metadata/SEO selector and cinematic motion renderer from
# publish_dios_fast, but replace all visual acquisition and TTS with generators
# that run on the GitHub Actions machine. No Gemini/HF/Pexels inference call is
# needed to create the media for this publisher.
pipeline.generate_metadata = fast._fast_local_metadata
spiritual_image._download = _local_visual_download
spiritual_image._animate = fast._fast_animate
spiritual_audio.make_spiritual_spanish_voice = make_local_spiritual_voice
spiritual_audio._enforce_voice_identity = _local_voice_identity_guard
youtube_module._enforce_spiritual_voice_guard = _local_voice_youtube_guard


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
