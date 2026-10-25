from __future__ import annotations

import base64
import os
import re
import subprocess
import time
import wave
from pathlib import Path


# Permanent narrator identity for Dios Habla Hoy: "Voz de Luz".
# The Gemini prebuilt voice is configurable (DIOS_TTS_VOICE, default Algieba,
# a smooth male voice) with an explicit fallback chain (default Schedar).
# Voz de Luz is always presented as a narrator reflecting on Scripture, never as
# the literal voice of God. Kokoro stays disabled; the local Qwen3-TTS backup is
# handled by the hybrid publisher only on Gemini quota errors.
DEFAULT_GEMINI_VOICE = "Algieba"
DEFAULT_GEMINI_VOICE_FALLBACKS = ("Schedar",)
DEFAULT_GEMINI_TTS_MODEL = "gemini-3.8-flash-tts"
DEFAULT_GEMINI_TTS_MODEL_FALLBACKS = ("gemini-3.1-flash-tts-preview",)
MALE_GEMINI_VOICE_DEFAULT = DEFAULT_GEMINI_VOICE  # compatibility alias
MALE_KOKORO_VOICE_DEFAULT = "em_alex"  # compatibility constant only; never used
SPIRITUAL_VOICE_PROFILE = "voz_de_luz_serena_original_v1"
VOICE_BRAND_NAME = "Voz de Luz"
VOICE_LOCK_VERSION = "voz-de-luz-v5-configured-serene"
REFERENCE_MODE = "fixed_original_identity_no_speaker_clone"


def _split_names(raw: str) -> list[str]:
    return [item.strip() for item in str(raw or "").replace(";", ",").split(",") if item.strip()]


def _valid_voice_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,40}", name or ""))


def configured_gemini_voice() -> str:
    """Primary narrator voice: DIOS_TTS_VOICE, then legacy GEMINI_TTS_VOICE, then Algieba."""
    for name in ("DIOS_TTS_VOICE", "GEMINI_TTS_VOICE"):
        value = os.getenv(name, "").strip()
        if value:
            if not _valid_voice_name(value):
                raise RuntimeError(f"VOICE_LOCK: {name}={value!r} no es un nombre de voz Gemini valido.")
            return value
    return DEFAULT_GEMINI_VOICE


def gemini_voice_chain() -> list[str]:
    """Configured voice first, then DIOS_TTS_VOICE_FALLBACKS (default: Schedar)."""
    chain = [configured_gemini_voice()]
    raw = os.getenv("DIOS_TTS_VOICE_FALLBACKS")
    fallbacks = _split_names(raw) if raw is not None else list(DEFAULT_GEMINI_VOICE_FALLBACKS)
    for voice in fallbacks:
        if _valid_voice_name(voice) and voice.lower() not in {v.lower() for v in chain}:
            chain.append(voice)
    return chain


def gemini_tts_models() -> list[str]:
    """GEMINI_TTS_MODEL first (default GA 3.8 flash TTS), then GEMINI_TTS_MODEL_FALLBACKS."""
    primary = os.getenv("GEMINI_TTS_MODEL", "").strip() or DEFAULT_GEMINI_TTS_MODEL
    models = _split_names(primary)
    raw = os.getenv("GEMINI_TTS_MODEL_FALLBACKS")
    fallbacks = _split_names(raw) if raw is not None else list(DEFAULT_GEMINI_TTS_MODEL_FALLBACKS)
    for model in fallbacks:
        if model not in models:
            models.append(model)
    return models


def is_configured_gemini_provider(used: str) -> bool:
    """True when a provider label comes from Gemini TTS with a voice of the configured chain."""
    low = str(used or "").lower()
    if "gemini" not in low or "kokoro" in low or "fallback" in low:
        return False
    return any(f":{voice.lower()}:" in low for voice in gemini_voice_chain())


def safe_tts_chunks(text: str, max_words: int = 42, max_chars: int = 300) -> list[str]:
    """Compatibility helper retained for callers; no alternate TTS uses it."""
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
    semantic = {
        "night_prayer": "Keep the emotional emphasis gentle and comforting, appropriate for evening listening.",
        "prayer": "Keep the emotional emphasis sincere, close and compassionate, as a guided prayer.",
        "biblical_story": "Keep the emotional emphasis clear and tender, with subtle narrative interest.",
        "biblical_reflection": "Keep the emotional emphasis thoughtful, warm, loving and peaceful.",
    }.get(mode, "Keep the emotional emphasis thoughtful, warm, loving and peaceful.")
    return (
        "Use the permanent channel cadence for every format: a slow, unhurried, gentle pace of roughly "
        "105 to 120 words per minute. Leave soft, serene breathing pauses between phrases, usually 300 to 600 "
        "milliseconds, and never longer than about 800 milliseconds, so the narration still flows continuously. "
        "Keep speaking rate, perceived age, accent, pitch register, vocal texture, resonance and speaking distance fixed. "
        + semantic
    )


def _brand_master(path: Path) -> None:
    """Apply the permanent Voz de Luz broadcast master without changing identity."""
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
        print(f"No se pudo aplicar el master Voz de Luz ({exc}); se conserva la voz Algenib original.")
        temp.unlink(missing_ok=True)


def _locked_gemini_voice() -> str:
    """Return the configured narrator voice; the lock now means "configured voice only"."""
    locked = os.getenv("SPIRITUAL_VOICE_LOCKED", "true").lower().strip()
    if locked != "true":
        raise RuntimeError("VOICE_LOCK: SPIRITUAL_VOICE_LOCKED debe permanecer true para Dios Habla Hoy.")
    return configured_gemini_voice()


def _is_model_access_error(exc: Exception) -> bool:
    text = str(exc).lower()
    markers = (
        "404", "not_found", "not found", "permission_denied", "403", "is not supported",
        "unsupported", "invalid model", "does not have access", "not available", "restricted",
    )
    return any(marker in text for marker in markers)


def _is_gemini_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ("429", "quota", "resource_exhausted", "too_many_requests"))


def _gemini_retry_seconds(exc: Exception, default: float = 65.0) -> float:
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


def _voice_prompt(text: str, voice: str, mode: str) -> str:
    return f"""
Synthesize speech only. Do not read these directions aloud.

### PERMANENT CHANNEL NARRATOR — VOZ DE LUZ
Use the {voice} adult male voice for the entire narration. Voz de Luz is the original narrator of Dios Habla Hoy: a human-sounding storyteller who reflects on the Bible. Voz de Luz is NEVER the literal voice of God or of Jesus and must not sound like a divine proclamation. It must not imitate, clone, identify or reproduce any real speaker.

### VOICE CONSISTENCY LOCK — {VOICE_LOCK_VERSION}
This must sound like the SAME narrator in every Dios Habla Hoy upload. Keep the same perceived age, warm register, vocal texture, speaking distance, neutral Latin-American Spanish accent, resonance, pitch and calm energy. Prayer, story, reflection and night-prayer modes may change ONLY the emotional emphasis, never the speed, pause style, accent or vocal character.

### VOCAL IDENTITY
Smooth, soft, warm male voice with gentle chest resonance, relaxed throat, clear consonants and open vowels. Neutral Latin-American Spanish with excellent diction. The sound is serene, luminous, loving and close, as if speaking quietly and personally to one listener who needs peace.

### EMOTIONAL BALANCE
Calm, peaceful, tender and loving. Communicate paz, amor, esperanza, consuelo and confianza with soft reverence, without theatrical solemnity and without preacher intensity.

### DELIVERY MODE
{mode}
{_director_notes(mode)}

### PERMANENT SPEECH RULES
Speak slowly, softly and continuously. Link phrases smoothly with serene, natural breathing pauses that never become long empty gaps. Never drag vowels or stretch words artificially. Give subtle heartfelt emphasis to Dios, Jesús, Señor, Biblia, fe, amor, paz, esperanza and consuelo. Finish sentences with soft, gentle cadences. Avoid gravelly or raspy texture, whispering, shouting, growling, exaggerated bass, sing-song rhythm, robotic spacing, commercial-announcer energy, movie-trailer drama, fake preacher cadence and cathedral echo.

### TRANSCRIPT — SPEAK EXACTLY THIS TEXT
{text}
""".strip()


def _gemini_spiritual_voice(path: Path, text: str) -> str:
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(f"Falta GEMINI_API_KEY para {VOICE_BRAND_NAME}.")

    _locked_gemini_voice()
    voices = gemini_voice_chain()
    models = gemini_tts_models()
    mode = _delivery_mode(text)
    client = genai.Client(api_key=api_key)

    try:
        configured_attempts = int(os.getenv("GEMINI_TTS_MAX_ATTEMPTS", "4"))
    except ValueError:
        configured_attempts = 4
    max_attempts = max(2, min(6, configured_attempts))

    last_error: Exception | None = None
    quota_seen = False
    for voice in voices:
        prompt = _voice_prompt(text, voice, mode)
        for model in models:
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
                    if _is_gemini_quota_error(exc):
                        quota_seen = True
                    elif _is_model_access_error(exc):
                        print(f"Gemini TTS {model} no disponible para {voice} ({exc}); probando el siguiente modelo.")
                        break
                    if attempt >= max_attempts:
                        break
                    if _is_gemini_quota_error(exc):
                        wait_seconds = _gemini_retry_seconds(exc)
                        print(
                            "Gemini TTS marco limite de cuota; "
                            f"esperando {wait_seconds:.1f}s antes del intento {attempt + 1}/{max_attempts} "
                            f"con {VOICE_BRAND_NAME}/{voice} en {model}."
                        )
                    else:
                        wait_seconds = min(15.0, 2.5 * attempt)
                        print(
                            f"Gemini TTS fallo temporalmente ({exc}); reintento {attempt + 1}/{max_attempts} "
                            f"en {wait_seconds:.1f}s sin cambiar la voz."
                        )
                    time.sleep(wait_seconds)
        if quota_seen:
            # A quota wall is account-wide: switching voice would not help and the
            # hybrid publisher decides whether the local Qwen backup takes over.
            break
        print(f"{VOICE_BRAND_NAME}: la voz {voice} no pudo generarse; probando la siguiente voz configurada.")

    # Keep the quota marker in the message so the hybrid Qwen backup can detect it.
    marker = " [quota 429 RESOURCE_EXHAUSTED]" if quota_seen else ""
    raise RuntimeError(
        f"Gemini TTS fallo para voces {voices} y modelos {models}{marker}: {last_error}"
    )


def _kokoro_chunked_voice(path: Path, text: str) -> None:
    del path, text
    raise RuntimeError(
        "VOICE_LOCK: Kokoro esta deshabilitado permanentemente para Dios Habla Hoy; "
        "si Algenib no esta disponible la publicacion debe detenerse."
    )


def make_spiritual_spanish_voice(path: Path, text: str) -> str:
    """Generate only the configured Voz de Luz Gemini narrator (default Algieba -> Schedar)."""
    provider = os.getenv("TTS_PROVIDER", "gemini_tts").lower().strip()
    require_primary = os.getenv("SPIRITUAL_REQUIRE_PRIMARY_VOICE", "true").lower().strip()
    fallback_kokoro = os.getenv("TTS_FALLBACK_KOKORO", "false").lower().strip()

    if provider not in {"gemini", "gemini_tts", "gemini-tts"}:
        raise RuntimeError(
            f"VOICE_LOCK: TTS_PROVIDER={provider or 'vacio'} no esta permitido; se exige Gemini TTS/{configured_gemini_voice()}."
        )
    if require_primary != "true":
        raise RuntimeError("VOICE_LOCK: SPIRITUAL_REQUIRE_PRIMARY_VOICE debe permanecer true.")
    if fallback_kokoro != "false":
        raise RuntimeError("VOICE_LOCK: TTS_FALLBACK_KOKORO debe permanecer false.")

    used = _gemini_spiritual_voice(path, text)
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"{used} genero un archivo de voz espiritual invalido.")

    if not is_configured_gemini_provider(used):
        raise RuntimeError(f"VOICE_LOCK: proveedor de voz inesperado: {used}")

    _brand_master(path)
    return used
