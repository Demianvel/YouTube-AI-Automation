from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .spiritual_tts import make_spiritual_spanish_voice
from .premium_audio import make_premium_original_music
from .spiritual_continuity import ensure_spoken_text, fit_and_validate_spiritual_voice
from .spiritual_voice import polish_voice

VOICE_LOCK_VERSION = "voz-de-luz-algenib-v3-natural-fixed"
EXPECTED_VOICE = "Algenib"
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
        "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy", "-movflags", "+faststart", str(temp),
    ], check=True)
    if temp.exists() and temp.stat().st_size > 50_000:
        temp.replace(path)


def _enforce_voice_identity(used: str) -> None:
    if os.getenv("SPIRITUAL_REQUIRE_PRIMARY_VOICE", "false").lower().strip() != "true":
        return
    value = str(used or "")
    low = value.lower()
    if "gemini" not in low or f":{EXPECTED_VOICE.lower()}:" not in low or "fallback" in low:
        raise RuntimeError(
            "VOICE_IDENTITY_GUARD: se rechazo publicar porque la narracion no usa "
            f"Voz de Luz/{EXPECTED_VOICE} como voz primaria. Provider recibido: {value or 'vacio'}"
        )


def _fit_text_for_natural_short_voice(text: str, duration: int, seed: int) -> tuple[str, dict]:
    """Fit the script to the permanent natural Algenib cadence, never vice versa.

    Empirical runs of Voz de Luz/Algenib include natural breaths and pauses, so a
    60 s Short now targets roughly 117-126 spoken words. This keeps the narrator
    natural and avoids perceptible time stretching. If a draft is too long we
    retain complete phrases and the spiritual closing; the voice is never sped up.
    """
    clean = " ".join(str(text or "").split()).strip()
    max_words = max(36, int(float(duration) * 2.10))
    min_words = max(32, int(float(duration) * 1.95))
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
        clean, expansion = ensure_spoken_text(clean, duration, seed=seed, words_per_minute=124)

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
        "voice_rate_policy": "fixed_natural_algenib_empirical_117_126_words_per_60s_no_slow_stretch",
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
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ], check=True)

    _cta_overlay(out, duration)
    meta["tts_provider_used"] = used
    meta["voice_profile"] = EXPECTED_PROFILE
    meta["voice_identity_locked"] = True
    meta["voice_lock_version"] = VOICE_LOCK_VERSION
    meta["voice_expected_provider"] = f"Gemini TTS/{EXPECTED_VOICE}"
    meta["voice_delivery"] = "permanent_natural_cadence_same_track_no_slow_stretch"
    meta["voice_cadence_locked"] = True
    meta["voice_slow_stretch_forbidden"] = True
    meta["music_variant"] = music_variant
    meta["audio_source"] = "unique_spiritual_voice_plus_low_original_music"
    meta["cta_overlay"] = "SUSCRIBITE | COMPARTI | AMEN"
