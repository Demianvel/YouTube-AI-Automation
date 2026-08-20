from __future__ import annotations

from pathlib import Path

from app import pipeline, spiritual_image, youtube as youtube_module
from app.spiritual_fresh_reference_bank import is_jesus_prompt, subject_prompt
import scripts.publish_dios_fast as fast


VISUAL_DIVERSITY_VERSION = "dios-zero-hf-diversity-v4-no-local-reuse"


def _zero_hf_diverse_download(prompt: str, out: Path, seed: int) -> str:
    """Zero-HF emergency path using genuinely new sources only.

    A transformed crop of an old local portrait is still recognizably the same
    image to viewers. V4 therefore refuses local portrait reuse completely.
    """
    jesus_scene = is_jesus_prompt(subject_prompt(prompt))
    free_prompt = fast._symbolic_prompt_for_jesus(prompt) if jesus_scene else prompt

    errors: list[str] = []
    for batch in range(4):
        retry_seed = int(seed) + batch * 1_000_003
        try:
            provider = fast._fresh_free_media(free_prompt, out, retry_seed, attempts=32)
            if "local_project_jesus_reference" in provider:
                errors.append(f"se rechazo fuente local: {provider}")
                continue
            print(f"{VISUAL_DIVERSITY_VERSION}: fuente realmente nueva: {provider}")
            return provider + f":{VISUAL_DIVERSITY_VERSION}"
        except Exception as exc:
            errors.append(str(exc))

    raise RuntimeError(
        "ZERO_HF_FRESH_VISUAL_EXHAUSTED: no se encontro una fuente visual nueva. "
        "Se prefirio detener esta escena antes que repetir una fotografia anterior. "
        + " | ".join(errors[-6:])
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


# publish_dios_fast already provides semantic scene rotation and cinematic motion.
# This emergency route now overrides acquisition only: every scene must come from
# a genuinely different source. Local portrait crops are forbidden.
spiritual_image._download = _zero_hf_diverse_download
youtube_module._enforce_spiritual_voice_guard = _natural_algenib_voice_guard


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
