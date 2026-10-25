from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from . import render_quality
from .spiritual_tts import configured_gemini_voice, is_configured_gemini_provider, make_spiritual_spanish_voice
from .premium_audio import make_premium_original_music
from .spiritual_continuity import ensure_spoken_text, fit_and_validate_spiritual_voice
from .spiritual_voice import polish_voice

VOICE_LOCK_VERSION = "voz-de-luz-v5-configured-serene"
EXPECTED_VOICE = "Algieba"  # default only; the configured DIOS_TTS_VOICE chain is enforced
EXPECTED_PROFILE = "voz_de_luz_serena_original_v1"


def _cta_overlay(path: Path, duration: int) -> None:
    if os.getenv("SPIRITUAL_CTA_OVERLAY", "true").lower().strip() != "true":
        return
    start = max(0.0, float(duration) - 7.0)
    temp = path.with_name(path.stem + ".cta.mp4")
    font = os.getenv("SPIRITUAL_CTA_FONT", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    vf = (
        f"drawbox=x=iw*0.11:y=ih*0.79:w=iw*0.78:h=150:color=black@0.62:t=fill:enable='between(t,{start:.2f},{float(duration):.2f})',"
        f"drawtext=fontfile='{font}':text='SUSCRIBITE  |  COMPARTI  |  AMEN':fontcolor=white:fontsize=48:"
        f"x=(w-text_w)/2:y=h*0.82:enable='between(t,{start:.2f},{float(duration):.2f})'"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
        "-vf", vf, *render_quality.video_encode_args(),
        "-c:a", "copy", "-movflags", "+faststart", str(temp),
    ], check=True)
    if temp.exists() and temp.stat().st_size > 50_000:
        temp.replace(path)


def _enforce_voice_identity(used: str) -> None:
    if os.getenv("SPIRITUAL_REQUIRE_PRIMARY_VOICE", "false").lower().strip() != "true":
        return
    value = str(used or "")
    low = value.lower()
    if is_configured_gemini_provider(value):
        return
    qwen_ok = os.getenv("SPIRITUAL_ALLOW_QWEN_BACKUP", "false").lower().strip() == "true"
    if qwen_ok and "voz_de_luz_qwen_backup" in low and "kokoro" not in low:
        return
    raise RuntimeError(
        "VOICE_IDENTITY_GUARD: se rechazo publicar porque la narracion no usa "
        f"Voz de Luz/{configured_gemini_voice()} (o el respaldo Qwen autorizado). Provider recibido: {value or 'vacio'}"
    )


def narration_word_budget(duration: float) -> tuple[int, int]:
    """(max_words, min_words) for the Voz de Luz narration.

    DIOS_NARRATION_WPM sets the target pace. The default (126) reproduces the
    historical 117-126 words per 60 s budget; the orchestrator sets a slower,
    serene pace (110). The minimum keeps ~93% of the maximum.
    """
    try:
        wpm = float(os.getenv("DIOS_NARRATION_WPM", "126"))
    except ValueError:
        wpm = 126.0
    wpm = max(80.0, min(150.0, wpm))
    seconds = max(8.0, float(duration))
    max_words = max(36, int(seconds * wpm / 60.0))
    min_words = max(32, int(round(max_words * 0.93)))
    return max_words, min_words


def _fit_text_for_natural_short_voice(text: str, duration: int, seed: int) -> tuple[str, dict]:
    """Fit the script to the permanent natural Algenib cadence, never vice versa.

    Empirical runs of Voz de Luz/Algenib include natural breaths and pauses, so a
    60 s Short now targets roughly 117-126 spoken words. This keeps the narrator
    natural and avoids perceptible time stretching. If a draft is too long we
    retain complete phrases and the spiritual closing; the voice is never sped up.
    """
    clean = " ".join(str(text or "").split()).strip()
    max_words, min_words = narration_word_budget(duration)
    original_words = len(clean.split())

    if original_words > max_words:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
        closing = ""
        if sentences and any(token in sentences[-1].lower() for token in ("amén", "amen", "dios", "señor", "esperanza")):
            closing = sentences.pop()

        selected: list[str] = []
        used_words = 0
        reserve = len(closing.split()) if closing else 0
        budget = max(24, max_words - reserve)
        for sentence in sentences:
            count = len(sentence.split())
            if selected and used_words + count > budget:
                continue
            if count > budget and not selected:
                words = sentence.split()[:budget]
                sentence = " ".join(words).rstrip(" ,;:") + "."
                count = len(words)
            if used_words + count <= budget:
                selected.append(sentence)
                used_words += count
        if closing:
            selected.append(closing)
        clean = " ".join(selected).strip()

    expansion = {
        "target_words": min_words,
        "final_words": len(clean.split()),
        "continuity_expansions": 0,
    }
    if len(clean.split()) < min_words:
        fill_wpm = max(60, int(round(min_words * 60.0 / max(1.0, float(duration)) / 0.98)))
        clean, expansion = ensure_spoken_text(clean, duration, seed=seed, words_per_minute=fill_wpm)

    words = clean.split()
    if len(words) > max_words:
        clean = " ".join(words[:max_words]).rstrip(" ,;:")
        if not re.search(r"[.!?]$", clean):
            clean += "."

    final_words = len(clean.split())
    return clean, {
        **expansion,
        "original_words": original_words,
        "final_words": final_words,
        "natural_voice_word_budget_min": min_words,
        "natural_voice_word_budget_max": max_words,
        "script_adjusted_for_fixed_voice_cadence": final_words != original_words,
        "voice_rate_policy": f"voz_de_luz_serene_{max_words}_words_per_{int(duration)}s_no_slow_stretch",
    }


def apply_spiritual_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    text = " ".join(
        str(scene.get("narration") or "").strip()
        for scene in (meta.get("scenes") or [])
        if str(scene.get("narration") or "").strip()
    )
    if not text:
        raise RuntimeError("El Short espiritual requiere narracion continua.")

    text, text_stats = _fit_text_for_natural_short_voice(text, duration, seed)
    meta["spoken_text_continuity"] = text_stats
    meta["spoken_text_final_words"] = text_stats["final_words"]
    meta["spoken_text_used_for_tts"] = text

    precomputed = str(meta.get("_precomputed_voice_path") or "").strip()
    precomputed_provider = str(meta.get("_precomputed_tts_provider") or "").strip()
    voice_path = Path(precomputed) if precomputed else out.with_name("spiritual_voice_master.wav")

    if precomputed and voice_path.exists():
        used = precomputed_provider or "precomputed-spiritual-voice"
    else:
        used = make_spiritual_spanish_voice(voice_path, text)
        master = polish_voice(voice_path)
        if master != "unprocessed":
            used = f"{used}+{master}"

    _enforce_voice_identity(used)

    continuity = fit_and_validate_spiritual_voice(voice_path, duration)
    meta.update(continuity)

    music = out.with_name("spiritual_original_background.wav")
    music_variant = make_premium_original_music(music, duration, seed ^ 0xD105, mood="calm")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video), "-i", str(voice_path), "-i", str(music),
        "-filter_complex",
        f"[1:a]highpass=f=62,lowpass=f=11500,acompressor=threshold=-19dB:ratio=1.55:attack=11:release=155,loudnorm=I=-16:TP=-1.5:LRA=6,apad=pad_dur={duration}[v];"
        "[2:a]volume=0.022,lowpass=f=8200[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0.4[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", render_quality.audio_bitrate(), "-ar", "48000", "-movflags", "+faststart", str(out),
    ], check=True)

    _cta_overlay(out, duration)
    meta["tts_provider_used"] = used
    meta["voice_profile"] = EXPECTED_PROFILE
    meta["voice_identity_locked"] = True
    meta["voice_lock_version"] = VOICE_LOCK_VERSION
    meta["voice_expected_provider"] = f"Gemini TTS/{configured_gemini_voice()}"
    meta["voice_brand"] = "Voz de Luz"
    meta["voice_is_literal_voice_of_god"] = False
    meta["audio_bitrate"] = render_quality.audio_bitrate()
    meta["voice_delivery"] = "permanent_natural_cadence_same_track_no_slow_stretch"
    meta["voice_cadence_locked"] = True
    meta["voice_slow_stretch_forbidden"] = True
    meta["music_variant"] = music_variant
    meta["audio_source"] = "unique_spiritual_voice_plus_low_original_music"
    meta["cta_overlay"] = "SUSCRIBITE | COMPARTI | AMEN"
