from __future__ import annotations

import base64
import os
import re
import time
import wave
from pathlib import Path

from .audio import continuous_speech_text, make_natural_spanish_voice


def safe_tts_chunks(text: str, max_words: int = 42, max_chars: int = 300) -> list[str]:
    """Split long spiritual prose into safe TTS units without losing words."""
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


def _write_pcm_wave(path: Path, pcm: bytes, rate: int = 24000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def _gemini_spiritual_voice(path: Path, text: str) -> str:
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY para Gemini TTS.")

    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview").strip()
    voice = os.getenv("GEMINI_TTS_VOICE", "Gacrux").strip() or "Gacrux"
    client = genai.Client(api_key=api_key)
    prompt = f"""
Synthesize speech only. Do not read these directions aloud.

### AUDIO PROFILE
Adult male narrator with a warm low baritone, mature human tone, intimate and emotionally present. Natural Latin-American Spanish pronunciation. The performance should feel cinematic and peaceful, with subtle breath and warmth, never robotic, never like an advertisement, never shouted.

### SCENE
A compassionate spiritual message delivered directly to one listener in a quiet natural landscape at golden hour. The emotional qualities are peace, love, hope, closeness, serenity and sincere human warmth.

### DIRECTOR'S NOTES
Speak slowly but fluidly, with soft confidence and excellent diction. Keep pauses short and organic. Avoid theatrical preaching, exaggerated bass, artificial cathedral echo, whispering, or synthetic cadence. Let key hopeful words carry gentle emotion without overacting.

### TRANSCRIPT — SPEAK EXACTLY THIS TEXT
{text}
""".strip()

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            interaction = client.interactions.create(
                model=model,
                input=prompt,
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice}]},
            )
            output_audio = getattr(interaction, "output_audio", None)
            data = getattr(output_audio, "data", None) if output_audio is not None else None
            if not data:
                raise RuntimeError("Gemini TTS no devolvio audio.")
            _write_pcm_wave(path, base64.b64decode(data), rate=24000)
            return f"{model}:{voice}"
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)

    raise RuntimeError(f"Gemini TTS fallo despues de 3 intentos: {last_error}")


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
    """Generate spiritual narration with Gemini TTS primary and resilient fallbacks."""
    provider = os.getenv("TTS_PROVIDER", "gemini_tts").lower().strip()
    if provider in {"gemini", "gemini_tts", "gemini-tts"}:
        try:
            used = _gemini_spiritual_voice(path, text)
        except Exception as exc:
            print(f"Gemini TTS no disponible ({exc}); usando Kokoro como respaldo.")
            _kokoro_chunked_voice(path, text)
            used = "kokoro-spiritual-fallback-from-gemini"
    elif provider == "kokoro":
        _kokoro_chunked_voice(path, text)
        used = "kokoro-spiritual-chunked-continuous"
    else:
        used = make_natural_spanish_voice(path, text)

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"{used} genero un archivo de voz espiritual invalido.")
    return used
