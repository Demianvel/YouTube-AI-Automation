from __future__ import annotations

import os
import re
from pathlib import Path

from .audio import continuous_speech_text, make_natural_spanish_voice


def safe_tts_chunks(text: str, max_words: int = 42, max_chars: int = 300) -> list[str]:
    """Split long spiritual prose into safe TTS units without losing words.

    Kokoro can truncate very long single-sentence inputs. The spiritual pipeline
    intentionally removes dramatic pauses, so we chunk by word/character budget
    before synthesis and join the audio with only a tiny transition gap.
    """
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return []

    tokens = re.findall(r"\S+", clean)
    chunks: list[str] = []
    current: list[str] = []
    current_chars = 0

    for token in tokens:
        projected_chars = current_chars + (1 if current else 0) + len(token)
        if current and (len(current) >= max_words or projected_chars > max_chars):
            chunks.append(" ".join(current))
            current = []
            current_chars = 0
        current.append(token)
        current_chars += (1 if current_chars else 0) + len(token)

    if current:
        chunks.append(" ".join(current))
    return chunks


def _kokoro_chunked_voice(path: Path, text: str) -> None:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice = os.getenv("KOKORO_VOICE", "em_alex").strip() or "em_alex"
    speed = float(os.getenv("KOKORO_SPEED", "0.94"))
    pipeline = KPipeline(lang_code="e")
    rendered: list[np.ndarray] = []

    chunks = safe_tts_chunks(text)
    if not chunks:
        raise RuntimeError("No hay texto para la narracion espiritual.")

    for index, chunk in enumerate(chunks, start=1):
        flowing = continuous_speech_text(chunk)
        piece_count = 0
        for _graphemes, _phonemes, audio in pipeline(
            flowing,
            voice=voice,
            speed=speed,
            split_pattern=r"(?<=[.!?])\s+",
        ):
            if audio is not None and len(audio):
                rendered.append(np.asarray(audio, dtype=np.float32))
                piece_count += 1
        if piece_count == 0:
            raise RuntimeError(f"Kokoro no genero audio para el fragmento espiritual {index}/{len(chunks)}.")

    # 14 ms is perceptually continuous, but avoids clicks at concatenation points.
    pause = np.zeros(max(1, int(24000 * 0.014)), dtype=np.float32)
    joined: list[np.ndarray] = []
    for index, audio in enumerate(rendered):
        if index:
            joined.append(pause)
        joined.append(audio)

    combined = np.concatenate(joined)
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    if peak > 0.98:
        combined = combined * (0.96 / peak)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), combined, 24000, subtype="PCM_16")


def make_spiritual_spanish_voice(path: Path, text: str) -> str:
    """Generate full-length spiritual narration while preserving other TTS options."""
    provider = os.getenv("TTS_PROVIDER", "kokoro").lower().strip()
    if provider == "kokoro":
        _kokoro_chunked_voice(path, text)
        used = "kokoro-spiritual-chunked-continuous"
    else:
        used = make_natural_spanish_voice(path, text)

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"{used} genero un archivo de voz espiritual invalido.")
    return used
