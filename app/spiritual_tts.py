from __future__ import annotations

import base64
import os
import re
import subprocess
import time
import wave
from pathlib import Path

from .audio import continuous_speech_text


# Permanent original voice identity for Dios Habla Hoy.
# Algenib is the single stable male base voice. Content type may change semantic
# emphasis, but never narrator identity, cadence, pitch, accent or vocal texture.
MALE_GEMINI_VOICE_DEFAULT = "Algenib"
MALE_KOKORO_VOICE_DEFAULT = "em_alex"
SPIRITUAL_VOICE_PROFILE = "voz_de_luz_serena_original_v1"
VOICE_BRAND_NAME = "Voz de Luz"
VOICE_LOCK_VERSION = "voz-de-luz-algenib-v3-natural-fixed"
REFERENCE_MODE = "fixed_original_identity_no_speaker_clone"


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
    story_markers = (
        "evangelio", "parábola", "parabola", "discípulos", "discipulos", "pedro",
        "moisés", "moises", "david", "daniel", "noé", "noe", "abraham", "pablo",
    )
    prayer_markers = (
        "señor,", "senor,", "padre,", "dios, te", "te pedimos", "te pido",
        "gracias, dios", "gracias señor", "gracias senor", "en tus manos",
    )
    if any(marker in clean for marker in story_markers):
        return "biblical_story"
    if any(marker in clean for marker in prayer_markers):
        return "prayer"
    return "biblical_reflection"


def _director_notes(mode: str) -> str:
    """Keep one permanent cadence; mode changes meaning/emphasis only."""
    semantic = {
        "night_prayer": "Keep the emotional emphasis gentle and comforting, appropriate for evening listening.",
        "prayer": "Keep the emotional emphasis sincere, close and compassionate, as a guided prayer.",
        "biblical_story": "Keep the emotional emphasis clear and engaging, with subtle narrative interest.",
        "biblical_reflection": "Keep the emotional emphasis thoughtful, warm and conversational.",
    }.get(mode, "Keep the emotional emphasis thoughtful, warm and conversational.")
    return (
        "Use the permanent channel cadence for every format: a natural conversational flow at roughly "
        "134 to 142 words per minute. Most phrase pauses should feel like normal human breathing, roughly "
        "120 to 280 milliseconds, with an occasional meaningful transition never intentionally exceeding "
        "about 400 milliseconds. Do not slow down for prayer or night content and do not speed up for stories. "
        "Keep speaking rate, perceived age, accent, pitch register, vocal texture, resonance and speaking distance fixed. "
        + semantic
    )


def _brand_master(path: Path) -> None:
    """Apply the permanent Voz de Luz broadcast master to every provider."""
    if not path.exists():
        return
    temp = path.with_name(path.stem + ".voz-de-luz-master.wav")
    filters = (
        "highpass=f=50,"
        "lowpass=f=10500,"
        "equalizer=f=105:t=q:w=0.80:g=1.35,"
        "equalizer=f=175:t=q:w=0.95:g=0.65,"
        "equalizer=f=330:t=q:w=1.10:g=-0.45,"
        "equalizer=f=2450:t=q:w=1.00:g=0.78,"
        "equalizer=f=5200:t=q:w=1.15:g=-0.55,"
        "acompressor=threshold=-23dB:ratio=1.42:attack=18:release=190:makeup=1.15,"
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
        print(f"No se pudo aplicar el master Voz de Luz ({exc}); se conserva la voz original.")
        temp.unlink(missing_ok=True)


def _locked_gemini_voice() -> str:
    requested = os.getenv("GEMINI_TTS_VOICE", MALE_GEMINI_VOICE_DEFAULT).strip() or MALE_GEMINI_VOICE_DEFAULT
    locked = os.getenv("SPIRITUAL_VOICE_LOCKED", "true").lower().strip() == "true"
    if locked and requested.lower() != MALE_GEMINI_VOICE_DEFAULT.lower():
        raise RuntimeError(
            f"VOICE_LOCK: GEMINI_TTS_VOICE={requested} no coincide con la voz fija {MALE_GEMINI_VOICE_DEFAULT}."
        )
    return MALE_GEMINI_VOICE_DEFAULT


def _is_gemini_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ("429", "quota", "resource_exhausted", "too_many_requests"))


def _gemini_retry_seconds(exc: Exception, default: float = 65.0) -> float:
    """Honor Gemini RetryInfo instead of hammering the same quota window."""
    text = str(exc)
    patterns = (
        r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"retrydelay[^0-9]*([0-9]+(?:\.[0-9]+)?)s",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return max(15.0, min(120.0, float(match.group(1)) + 8.0))
    return max(15.0, min(120.0, float(default)))


def _gemini_spiritual_voice(path: Path, text: str) -> str:
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY para Gemini TTS.")

    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview").strip()
    voice = _locked_gemini_voice()
    mode = _delivery_mode(text)
    client = genai.Client(api_key=api_key)
    prompt = f"""
Synthesize speech only. Do not read these directions aloud.

### PERMANENT CHANNEL VOICE — VOZ DE LUZ
Use the Algenib ADULT MALE voice for the entire narration. Create one stable, original vocal identity for Dios Habla Hoy called Voz de Luz. It must not imitate, clone, identify or reproduce any real speaker.

### VOICE CONSISTENCY LOCK — {VOICE_LOCK_VERSION}
This must sound like the SAME narrator used in every previous and future Dios Habla Hoy upload. Keep the same perceived age, baritone register, vocal texture, speaking distance, neutral Latin-American Spanish accent, resonance, pitch and calm energy. Prayer, story, reflection and night-prayer modes may change ONLY semantic and emotional emphasis. They must NOT change speaking speed, pause style, cadence, perceived age, accent, pitch register, vocal texture or vocal character.

### VOCAL IDENTITY
Original mature male baritone with warm chest resonance, relaxed throat, lightly textured human timbre, clear consonants and open vowels. Neutral Latin-American Spanish with excellent diction and professional but natural locution. The sound is serene, luminous, compassionate and close, as if speaking personally to one listener.

### EMOTIONAL BALANCE
Blend tenderness, fluidity and calm authority. Communicate peace, faith, hope, love, safety and reverence without theatrical solemnity.

### DELIVERY MODE
{mode}
{_director_notes(mode)}

### PERMANENT SPEECH RULES
Speak naturally and continuously. Link phrases smoothly. Use normal human breaths and short organic pauses; do not create long reflective gaps. Never drag vowels or stretch words to fill time. Never slow the speech to make the narration match a target duration. Give subtle heartfelt emphasis to Dios, Jesús, Señor, Biblia, fe, amor, paz, esperanza and consuelo. Finish sentences with soft controlled cadences. Avoid whispering, shouting, growling, exaggerated bass, sing-song rhythm, robotic spacing, commercial-announcer energy, movie-trailer drama, fake preacher cadence, cathedral echo or long empty silences.

### TRANSCRIPT — SPEAK EXACTLY THIS TEXT
{text}
""".strip()

    try:
        configured_attempts = int(os.getenv("GEMINI_TTS_MAX_ATTEMPTS", "4"))
    except ValueError:
        configured_attempts = 4
    max_attempts = max(2, min(6, configured_attempts))

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
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
            return f"{model}:{voice}:{SPIRITUAL_VOICE_PROFILE}:{mode}:{VOICE_LOCK_VERSION}"
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break

            if _is_gemini_quota_error(exc):
                wait_seconds = _gemini_retry_seconds(exc)
                print(
                    "Gemini TTS marco limite de cuota; "
                    f"esperando {wait_seconds:.1f}s antes del intento {attempt + 1}/{max_attempts} "
                    f"con la MISMA {VOICE_BRAND_NAME}/{voice}."
                )
                time.sleep(wait_seconds)
            else:
                wait_seconds = min(15.0, 2.5 * attempt)
                print(
                    f"Gemini TTS fallo temporalmente ({exc}); reintento {attempt + 1}/{max_attempts} "
                    f"en {wait_seconds:.1f}s sin cambiar la voz."
                )
                time.sleep(wait_seconds)

    raise RuntimeError(f"Gemini TTS fallo despues de {max_attempts} intentos: {last_error}")


def _kokoro_chunked_voice(path: Path, text: str) -> None:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice = MALE_KOKORO_VOICE_DEFAULT
    speed = 1.0
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

    pause = np.zeros(max(1, int(24000 * 0.018)), dtype=np.float32)
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
    """Generate the permanent original Voz de Luz narrator with a safe male fallback."""
    provider = os.getenv("TTS_PROVIDER", "gemini_tts").lower().strip()
    mode = _delivery_mode(text)
    require_primary = os.getenv("SPIRITUAL_REQUIRE_PRIMARY_VOICE", "false").lower().strip() == "true"
    if provider in {"gemini", "gemini_tts", "gemini-tts"}:
        try:
            used = _gemini_spiritual_voice(path, text)
        except Exception as exc:
            if require_primary:
                raise RuntimeError(
                    f"La ejecucion exige la voz primaria {VOICE_BRAND_NAME}/{MALE_GEMINI_VOICE_DEFAULT}; Gemini TTS no estuvo disponible: {exc}"
                ) from exc
            print(f"Gemini TTS no disponible ({exc}); usando respaldo masculino fijo Kokoro con master Voz de Luz.")
            _kokoro_chunked_voice(path, text)
            used = f"kokoro:{MALE_KOKORO_VOICE_DEFAULT}:{SPIRITUAL_VOICE_PROFILE}:{mode}:fallback"
    else:
        if require_primary:
            raise RuntimeError(
                f"La ejecucion exige TTS primario Gemini/{MALE_GEMINI_VOICE_DEFAULT}, pero TTS_PROVIDER={provider}."
            )
        _kokoro_chunked_voice(path, text)
        used = f"kokoro:{MALE_KOKORO_VOICE_DEFAULT}:{SPIRITUAL_VOICE_PROFILE}:{mode}:forced"

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"{used} genero un archivo de voz espiritual invalido.")

    if require_primary:
        low = used.lower()
        if "gemini" not in low or f":{MALE_GEMINI_VOICE_DEFAULT.lower()}:" not in low or "fallback" in low:
            raise RuntimeError(f"VOICE_LOCK: proveedor de voz inesperado: {used}")

    _brand_master(path)
    return used
