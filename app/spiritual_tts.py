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
# It is inspired only by broad delivery qualities found in the two user-provided
# references: intimate warmth + gentle authority. It never clones or impersonates
# an identifiable speaker. Algenib remains the stable male base voice.
MALE_GEMINI_VOICE_DEFAULT = "Algenib"
MALE_KOKORO_VOICE_DEFAULT = "em_alex"
SPIRITUAL_VOICE_PROFILE = "voz_de_luz_serena_original_v1"
VOICE_BRAND_NAME = "Voz de Luz"
VOICE_LOCK_VERSION = "voz-de-luz-algenib-v2"
REFERENCE_MODE = "two_reference_style_blend_no_speaker_clone"


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
            "Deliver it as a peaceful night prayer at roughly 118 to 128 words per minute. "
            "Use soft downward endings and comfortable pauses of about 300 to 650 milliseconds. "
            "Do not change speaker identity, perceived age, accent, vocal texture or pitch register."
        )
    if mode == "prayer":
        return (
            "Deliver it as a sincere guided prayer at roughly 122 to 134 words per minute. "
            "Sound intimate, reverent and compassionate with calm conviction and natural breathing. "
            "Change pacing only; never change speaker identity, perceived age, accent, vocal texture or pitch register."
        )
    if mode == "biblical_story":
        return (
            "Deliver it as a premium biblical storyteller at roughly 136 to 148 words per minute. "
            "Maintain clear narrative progression, excellent articulation and subtle wonder. "
            "Change pacing only; never change speaker identity, perceived age, accent, vocal texture or pitch register."
        )
    return (
        "Deliver it as a thoughtful biblical reflection at roughly 128 to 140 words per minute. "
        "Use a fluid conversational rhythm, clear Scripture emphasis and short organic pauses. "
        "Change pacing only; never change speaker identity, perceived age, accent, vocal texture or pitch register."
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
Use the Algenib ADULT MALE voice for the entire narration. Create one stable, original vocal identity for Dios Habla Hoy called Voz de Luz. It may combine broad qualities from two style references—intimate warmth and gentle authority—but must not imitate, clone, identify or reproduce any real speaker.

### VOICE CONSISTENCY LOCK — {VOICE_LOCK_VERSION}
This must sound like the SAME narrator used in every previous and future Dios Habla Hoy upload. Keep the same perceived age, baritone register, vocal texture, speaking distance, neutral Latin-American Spanish accent, resonance and calm energy. Prayer, story, reflection and night-prayer modes may change ONLY pacing, pauses and emphasis. They must never sound like a different man, a different age, a different accent, a different pitch register or a different vocal character.

### VOCAL IDENTITY
Original mature male baritone with a natural fundamental center around 90 to 105 Hz. Warm chest resonance, relaxed throat, lightly textured human timbre, clear consonants and open vowels. Neutral Latin-American Spanish with excellent diction and professional locution. The sound is serene, luminous, compassionate and close, as if speaking personally to one listener.

### EMOTIONAL BALANCE
Blend the tenderness and fluidity of a comforting reflection with the calm authority of a biblical narrator. Communicate peace, tranquility, faith, hope, love, safety and reverence. Keep strength without hardness and spirituality without theatrical solemnity.

### DELIVERY MODE
{mode}
{_director_notes(mode)}

### PERMANENT SPEECH RULES
Use natural breaths and mostly short pauses between phrases, with an occasional longer pause only at a meaningful transition. Maintain smooth phrase linking, precise articulation and a pleasant conversational flow. Give subtle heartfelt emphasis to Dios, Jesús, Señor, Biblia, fe, amor, paz, esperanza and consuelo. Finish sentences with soft controlled downward cadences. Avoid whispering, shouting, growling, exaggerated bass, sing-song rhythm, robotic spacing, commercial-announcer energy, movie-trailer drama, fake preacher cadence, cathedral echo or long empty silences.

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
            return f"{model}:{voice}:{SPIRITUAL_VOICE_PROFILE}:{mode}:{VOICE_LOCK_VERSION}"
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(attempt * 2)

    raise RuntimeError(f"Gemini TTS fallo despues de 3 intentos: {last_error}")


def _kokoro_chunked_voice(path: Path, text: str) -> None:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

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

    pause = np.zeros(max(1, int(24000 * 0.024)), dtype=np.float32)
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
