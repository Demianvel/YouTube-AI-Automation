from __future__ import annotations

import base64
import os
import re
import subprocess
import time
import wave
from pathlib import Path

from .audio import continuous_speech_text


# Canonical Dios Habla Hoy channel voice.
# The user reference Short bm6LxLsrMbE is treated as a STYLE reference only:
# we do not clone or impersonate an identifiable speaker. Algenib is the fixed
# Gemini male base voice used to reproduce the requested deep biblical tone.
MALE_GEMINI_VOICE_DEFAULT = "Algenib"
MALE_KOKORO_VOICE_DEFAULT = "em_alex"
SPIRITUAL_VOICE_PROFILE = "algenib_deep_biblical_narrator_bm6_reference_v2"
REFERENCE_STYLE_VIDEO_ID = "bm6LxLsrMbE"


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
            "Deliver it as a peaceful night prayer with a deep, warm and reassuring baritone. "
            "Use a slightly slower pace, gentle downward sentence endings, natural breath support and short organic pauses. "
            "The listener should feel accompanied before sleep, never frightened or pressured."
        )
    if mode == "prayer":
        return (
            "Deliver it as a sincere guided prayer: intimate, reverent and compassionate, with calm conviction. "
            "Keep the lower register warm and present, let gratitude and petitions breathe naturally, and avoid theatrical preaching."
        )
    if mode == "biblical_story":
        return (
            "Deliver it as a premium biblical storyteller with deep male resonance, controlled gravity and clear narrative progression. "
            "Use subtle wonder, excellent diction and deliberate emphasis on names and Scripture references, without movie-trailer exaggeration."
        )
    return (
        "Deliver it as a thoughtful biblical narrator: deep, warm, trustworthy and contemplative. "
        "Maintain a calm one-to-one tone, clear Scripture emphasis and a measured fluid pace suitable for sustained listening."
    )


def _brand_master(path: Path) -> None:
    """Apply one stable broadcast master to primary and fallback voices."""
    if not path.exists():
        return
    temp = path.with_name(path.stem + ".brand-master.wav")
    filters = (
        "highpass=f=54,"
        "lowpass=f=11800,"
        "equalizer=f=125:t=q:w=0.85:g=1.45,"
        "equalizer=f=190:t=q:w=0.95:g=0.65,"
        "equalizer=f=330:t=q:w=1.10:g=-0.55,"
        "equalizer=f=2350:t=q:w=1.00:g=0.85,"
        "equalizer=f=6200:t=q:w=1.25:g=-0.70,"
        "acompressor=threshold=-22dB:ratio=1.50:attack=15:release=170:makeup=1.18,"
        "loudnorm=I=-16.5:TP=-1.5:LRA=5.2"
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
    voice = MALE_GEMINI_VOICE_DEFAULT
    mode = _delivery_mode(text)
    client = genai.Client(api_key=api_key)
    prompt = f"""
Synthesize speech only. Do not read these directions aloud.

### FIXED CHANNEL VOICE
Use the Algenib ADULT MALE voice for the complete narration. Keep the same masculine vocal identity from beginning to end and across every Dios Habla Hoy Short and long-form video. The requested YouTube reference is a style target only; do not imitate or claim to reproduce any identifiable real speaker.

### SIGNATURE BIBLICAL AUDIO PROFILE
Deep warm male baritone with a lightly textured/gravelly character, mature human tone, controlled low resonance and clear intelligibility. Natural neutral Latin-American Spanish pronunciation. The delivery must communicate peace, faith, hope, compassion, reverence and closeness. It should sound like a premium biblical narrator speaking personally to one listener, never robotic, never commercial, never shouted and never like a movie trailer.

### DELIVERY MODE
{mode}
{_director_notes(mode)}

### PERMANENT DIRECTION
Keep a measured but fluid rhythm. Use short organic pauses and natural breaths. Favor calm authority over dramatic intensity. Keep the chest resonance present without forcing artificial bass. Give subtle heartfelt emphasis to Dios, Jesús, Señor, Biblia, fe, amor, paz, esperanza and consuelo. Avoid whispering, fake solemnity, exaggerated preacher cadence, cathedral echo, sing-song rhythm, growling, harshness or synthetic pacing.

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

    # One fixed male emergency fallback. It receives the same channel master so
    # provider outages do not change gender, loudness or overall presentation.
    voice = MALE_KOKORO_VOICE_DEFAULT
    speed = float(os.getenv("KOKORO_SPEED", "0.91"))
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

    pause = np.zeros(max(1, int(24000 * 0.016)), dtype=np.float32)
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
    """Generate the fixed Dios Habla Hoy biblical narrator with a safe fixed fallback."""
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
