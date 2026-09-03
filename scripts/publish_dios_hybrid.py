from __future__ import annotations

import os
from pathlib import Path

from app import pipeline, spiritual_audio, spiritual_tts
from app.qwen_voice import generate_qwen_premium_voice
import scripts.publish_dios_locked as locked


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


def configure_hybrid_publisher() -> None:
    locked.configure_locked_publisher()
    # Override only the narrator function. All visual identity, SEO, YouTube and
    # freshness locks remain exactly those of the canonical locked publisher.
    spiritual_audio.make_spiritual_spanish_voice = _premium_hybrid_voice
    spiritual_tts.make_spiritual_spanish_voice = _premium_hybrid_voice


def main() -> dict:
    configure_hybrid_publisher()
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
