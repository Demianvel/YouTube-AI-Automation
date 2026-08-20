from __future__ import annotations

from pathlib import Path

from app import pipeline, spiritual_image, youtube as youtube_module
from app.spiritual_fresh_reference_bank import is_jesus_prompt, subject_prompt
import scripts.publish_dios_fast as fast


def _zero_hf_diverse_download(prompt: str, out: Path, seed: int) -> str:
    """Zero-HF emergency path: fresh source first, never six crops of the same Jesus photo."""
    jesus_scene = is_jesus_prompt(subject_prompt(prompt))
    free_prompt = fast._symbolic_prompt_for_jesus(prompt) if jesus_scene else prompt

    try:
        provider = fast._fresh_free_media(free_prompt, out, seed, attempts=28)
        print(f"Zero-HF diversity v3: fuente nueva para escena: {provider}")
        return provider + ":zero_hf_diverse_first"
    except Exception as free_exc:
        print(f"Zero-HF: no se encontro fuente libre nueva ({free_exc}).")

    # A local Jesus reference is allowed only for an actual Jesus scene, once per
    # Short, and only if its base image has not appeared in recent channel history.
    if jesus_scene:
        errors: list[str] = []
        for attempt in range(36):
            retry_seed = int(seed) + (attempt + 1) * 130363
            try:
                provider = spiritual_image._local_reference(out, retry_seed)
                accepted = fast._accept_local_variant(provider)
                if accepted:
                    print(f"Zero-HF diversity v3: fallback local excepcional: {accepted}")
                    return accepted + ":zero_hf_last_resort"
                errors.append(f"base/variante reciente: {provider}")
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError(
            "ZERO_HF_FRESH_VISUAL_EXHAUSTED: se nego reutilizar retratos locales recientes. "
            + " | ".join(errors[-5:])
        )

    raise RuntimeError(
        "ZERO_HF_FRESH_VISUAL_EXHAUSTED: para una escena no-Jesus se rechazo reemplazarla con el mismo retrato local."
    )


def _natural_algenib_voice_guard(channel: dict, metadata: dict, video_path: Path) -> None:
    """Use the approved natural continuity policy without changing Voz de Luz/Algenib."""
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


# publish_dios_fast installs semantic rotation, voice and motion patches on import.
# Override only acquisition for zero-HF mode and the already-approved continuity
# threshold. This route never spends HF quota and does not recycle portrait crops.
spiritual_image._download = _zero_hf_diverse_download
youtube_module._enforce_spiritual_voice_guard = _natural_algenib_voice_guard


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
