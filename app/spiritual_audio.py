from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .audio import fit_voice_to_duration, make_natural_spanish_voice
from .premium_audio import make_premium_original_music
from .spiritual_voice import polish_voice


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


def apply_spiritual_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    text = " ".join(
        str(scene.get("narration") or "").strip()
        for scene in (meta.get("scenes") or [])
        if str(scene.get("narration") or "").strip()
    )
    if not text:
        raise RuntimeError("El Short espiritual requiere narracion continua.")

    precomputed = str(meta.get("_precomputed_voice_path") or "").strip()
    precomputed_provider = str(meta.get("_precomputed_tts_provider") or "").strip()
    voice_path = Path(precomputed) if precomputed else out.with_name("spiritual_voice_master.wav")

    if precomputed and voice_path.exists():
        used = precomputed_provider or "precomputed-spiritual-voice"
    else:
        used = make_natural_spanish_voice(voice_path, text)
        master = polish_voice(voice_path)
        if master != "unprocessed":
            used = f"{used}+{master}"
        fit_voice_to_duration(voice_path, duration)

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
    meta["voice_profile"] = os.getenv("SPIRITUAL_VOICE_PROFILE", "default")
    meta["voice_delivery"] = "continuous_tight_no_long_pauses_same_track_used_for_lipsync"
    meta["music_variant"] = music_variant
    meta["audio_source"] = "unique_spiritual_voice_plus_low_original_music"
    meta["cta_overlay"] = "SUSCRIBITE | COMPARTI | AMEN"
