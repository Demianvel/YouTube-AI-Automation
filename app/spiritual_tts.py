from __future__ import annotations

import base64
import os
import re
import subprocess
import time
import wave
from pathlib import Path

from .audio import continuous_speech_text


# Canonical channel voice. This is deliberately not selected dynamically:
# every Dios Habla Hoy narration asks for the same Gemini male voice.
MALE_GEMINI_VOICE_DEFAULT = "Gacrux"
MALE_KOKORO_VOICE_DEFAULT = "em_alex"
SPIRITUAL_VOICE_PROFILE = "gacrux_biblical_narrator_v1"


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


def _delivery_mode(text: str) -> str:
    forced = os.getenv("SPIRITUAL_NARRATION_STYLE", "auto").strip().lower()
    if forced in {"prayer", "night_prayer", "biblical_story", "biblical_reflection"}:
        return forced
    clean = " ".join(str(text or "").lower().split())
    prayer_markers = (
        "señor,", "senor,", "padre,", "dios, te", "te pedimos", "te pido",
        "gracias, dios", "gracias señor", "gracias senor", "en tus manos",
        "nuestra oración", "nuestra oracion", "amén", "amen",
    )
    story_markers = (
        "evangelio", "parábola", "parabola", "discípulos", "discipulos", "pedro",
        "moisés", "moises", "david", "daniel", "noé", "noe", "abraham", "pablo",
    )
    if any(marker in clean for marker in prayer_markers):
        return "prayer"
    if any(marker in clean for marker in story_markers):
        return "biblical_story"
    return "biblical_reflection"


def _director_notes(mode: str) -> str:
    if mode == "night_prayer":
        return (
            "Deliver it as a peaceful night prayer: intimate, reassuring and slightly slower, as if accompanying one listener before sleep. "
            "Use gentle downward phrasing, warm breath support and short natural pauses. Keep excellent intelligibility and end with calm spiritual resolution."
        )
    if mode == "prayer":
        return (
            "Deliver it as a sincere guided prayer: close, compassionate and reverent, speaking with calm conviction rather than performance. "
            "Let petitions, gratitude and words of hope breathe naturally, while keeping the flow continuous and emotionally restrained."
        )
    if mode == "biblical_story":
        return (
            "Deliver it as a premium biblical storyteller: clear narrative progression, warm authority, subtle wonder and excellent diction. "
            "Give names and biblical references careful articulation; build interest through meaning, not theatrical suspense or shouting."
        )
    return (
        "Deliver it as a thoughtful biblical narrator: warm, trustworthy and contemplative, with clear emphasis on Scripture, hope and practical meaning. "
        "Maintain an intimate one-to-one tone and a fluid pace suitable for sustained listening."
    )


def _brand_master(path: Path) -> None:
    """Apply one stable broadcast master to primary and fallback voices."""
    if not path.exists():
        return
    temp = path.with_name(path.stem + ".brand-master.wav")
    filters = (
        "highpass=f=58,"
        "lowpass=f=12200,"
        "equalizer=f=145:t=q:w=0.90:g=1.25,"
        "equalizer=f=280:t=q:w=1.10:g=0.45,"
        "equalizer=f=2600:t=q:w=1.00:g=1.05,"
        "equalizer=f=6500:t=q:w=1.30:g=-0.45,"
        "acompressor=threshold=-21dB:ratio=1.45:attack=14:release=160:makeup=1.15,"
        "loudnorm=I=-16.5:TP=-1.5:LRA=5.5"
    )
    try:
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
            "-af", filters, "-ar", "48000", "-ac", "1", str(temp),
        ], check=True)
        if temp.exists() and temp.stat().st_size > 1000:
            temp.replace(path)
        else:
            temp.unlink(missing_ok=True)
    except Exception as exc:
        print(f"No se pudo aplicar el master biblico de voz ({exc}); se conserva la voz original.")
        temp.unlink(missing_ok=True)


def _gemini_spiritual_voice(path: Path, text: str) -> str:
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY para Gemini TTS.")

    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview").strip()
    # Hard lock: preserve the same narrator identity used by the reference Shorts.
    voice = MALE_GEMINI_VOICE_DEFAULT
    mode = _delivery_mode(text)
    client = genai.Client(api_key=api_key)
    prompt = f"""
Synthesize speech only. Do not read these directions aloud.

### NON-NEGOTIABLE CHANNEL VOICE IDENTITY
Use the Gacrux ADULT MALE voice for the complete narration. Keep exactly the same masculine vocal identity from beginning to end and across every episode. Never switch to a female, child, androgynous, comic, aggressive, commercial-announcer or character voice.

### SIGNATURE AUDIO PROFILE
Warm low male baritone, mature human tone, intimate and emotionally present. Natural Latin-American Spanish pronunciation, neutral enough for the whole Spanish-speaking audience. The voice must communicate peace, love, hope, compassion, closeness and serenity. Sound like a premium biblical narrator speaking to one person, never robotic, never like an advertisement and never shouted.

### DELIVERY MODE
{mode}
{_director_notes(mode)}

### PERMANENT DIRECTION
Speak fluidly with soft confidence, gentle warmth and excellent diction. Keep pauses short and organic. Avoid theatrical preaching, exaggerated bass, fake solemnity, artificial cathedral echo, whispering, sing-song cadence or synthetic rhythm. Give subtle heartfelt emphasis to Dios, Jesús, Biblia, fe, amor, paz, esperanza and consuelo without overacting. Preserve natural breaths and sentence endings.

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
            return f"{model}:{voice}:{SPIRITUAL_VOICE_PROFILE}:{mode}"
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)

    raise RuntimeError(f"Gemini TTS fallo despues de 3 intentos: {last_error}")


def _kokoro_chunked_voice(path: Path, text: str) -> None:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    # One fixed male emergency fallback. It is mastered with the same channel EQ
    # so provider outages do not change gender, loudness or overall presentation.
    voice = MALE_KOKORO_VOICE_DEFAULT
    speed = float(os.getenv("KOKORO_SPEED", "0.93"))
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
    """Generate the fixed Dios Habla Hoy male narrator with a safe fixed fallback."""
    provider = os.getenv("TTS_PROVIDER", "gemini_tts").lower().strip()
    mode = _delivery_mode(text)
    if provider in {"gemini", "gemini_tts", "gemini-tts"}:
        try:
            used = _gemini_spiritual_voice(path, text)
        except Exception as exc:
            print(f"Gemini TTS no disponible ({exc}); usando respaldo masculino fijo Kokoro.")
            _kokoro_chunked_voice(path, text)
            used = f"kokoro:{MALE_KOKORO_VOICE_DEFAULT}:{SPIRITUAL_VOICE_PROFILE}:{mode}:fallback"
    else:
        _kokoro_chunked_voice(path, text)
        used = f"kokoro:{MALE_KOKORO_VOICE_DEFAULT}:{SPIRITUAL_VOICE_PROFILE}:{mode}:forced"

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"{used} genero un archivo de voz espiritual invalido.")
    _brand_master(path)
    return used