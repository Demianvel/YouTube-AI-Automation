from __future__ import annotations

from pathlib import Path

from app import pipeline, spiritual_image, youtube as youtube_module
from app.spiritual_free_media import download_fresh_free_image
import scripts.publish_dios_fast as fast


def _local_first_download(prompt: str, out: Path, seed: int) -> str:
    """Emergency zero-HF path: fresh local variants first, then unused free media."""
    local_errors: list[str] = []
    for attempt in range(36):
        retry_seed = int(seed) + attempt * 104729
        try:
            provider = spiritual_image._local_reference(out, retry_seed)
            accepted = fast._accept_local_variant(provider)
            if accepted:
                return accepted
            local_errors.append(f"variante ya usada: {provider}")
        except Exception as exc:
            local_errors.append(str(exc))

    free_errors: list[str] = []
    for attempt in range(12):
        retry_seed = int(seed) + 4_000_003 + attempt * 104729
        try:
            provider = download_fresh_free_image(prompt, out, retry_seed)
            if fast._source_was_used(provider):
                free_errors.append(f"fuente ya usada: {fast._remote_source_marker(provider)}")
                continue
            return provider + ":fresh_nonrepeat_emergency_fallback"
        except Exception as exc:
            free_errors.append(str(exc))

    raise RuntimeError(
        "EMERGENCY_FRESH_VISUAL_EXHAUSTED: no se encontro variante local o fuente libre inedita. "
        f"local={' | '.join(local_errors[-5:])}; free={' | '.join(free_errors[-5:])}"
    )


def _natural_algenib_voice_guard(channel: dict, metadata: dict, video_path: Path) -> None:
    """Use the same natural continuity policy already approved upstream.

    The permanent narrator remains Gemini/Algenib. A naturally shorter narration
    may cover >=82% of a 60s Short and leave the tail to music/silence; the voice
    is never slowed or replaced. This wrapper changes only the stale final
    continuity threshold in the emergency path.
    """
    if not youtube_module._is_spiritual_channel(channel):
        return

    if youtube_module._is_native_gemini_clip(metadata):
        if not youtube_module._has_audio_stream(video_path):
            raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: Gemini devolvio un video sin stream de audio.")
        metadata["voice_continuity_guard_mode"] = "native_audiovisual_clip_audio_stream_verified"
        return

    passed = metadata.get("voice_continuity_passed")
    coverage_raw = metadata.get("voice_coverage_ratio")
    longest_raw = metadata.get("longest_voice_silence_seconds")
    coverage = float(coverage_raw if coverage_raw is not None else 0.0)
    longest = float(longest_raw if longest_raw is not None else 999.0)

    if passed is not True or coverage < 0.82 or longest > 2.2:
        raise RuntimeError(
            "BLOQUEADO ANTES DE YOUTUBE: la narracion espiritual no supero la continuidad natural Algenib "
            f"(passed={passed}, coverage={coverage:.1%}, longest_silence={longest:.2f}s)."
        )

    if not youtube_module._has_audio_stream(video_path):
        raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: el Short espiritual no contiene stream de audio.")

    metadata["voice_continuity_guard_mode"] = "natural_algenib_82pct_tail_music_no_voice_slowdown"
    metadata["voice_continuity_upload_threshold"] = 0.82


# publish_dios_fast already installs metadata, voice and animation patches on import.
# Override only the image path and the stale final continuity threshold for this
# zero-HF emergency route. Voice provider/identity remains locked by the workflow.
spiritual_image._download = _local_first_download
youtube_module._enforce_spiritual_voice_guard = _natural_algenib_voice_guard


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
