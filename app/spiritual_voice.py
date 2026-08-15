from __future__ import annotations

import os
import subprocess
from pathlib import Path


def enabled() -> bool:
    return os.getenv("SPIRITUAL_VOICE_PROFILE", "").strip().lower() in {
        "luminous_calm_v1",
        "luminous_calm_v2",
        "luminous",
        "calm",
    }


def polish_voice(path: Path) -> str:
    """Create a stable warm/luminous channel voice master without impersonation.

    V2 keeps the narration intimate and intelligible: low-rumble removal,
    restrained warmth, a small presence lift, gentle compression/de-essing by
    band shaping, very short room reflection and broadcast-safe loudness. It
    intentionally does not imitate any real speaker or claim to reproduce a
    literal divine voice.
    """
    if not enabled() or not path.exists():
        return "unprocessed"

    temp = path.with_name(path.stem + ".luminous-v2.wav")
    filters = (
        "highpass=f=55,"
        "lowpass=f=12200,"
        "equalizer=f=145:t=q:w=0.85:g=1.55,"
        "equalizer=f=310:t=q:w=1.10:g=0.70,"
        "equalizer=f=2450:t=q:w=1.00:g=1.20,"
        "equalizer=f=6100:t=q:w=1.30:g=-0.55,"
        "acompressor=threshold=-21dB:ratio=1.55:attack=12:release=155:makeup=1.25,"
        "aecho=0.84:0.09:29:0.018,"
        "loudnorm=I=-16.5:TP=-1.5:LRA=5.5"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
        "-af", filters, "-ar", "48000", "-ac", "1", str(temp),
    ], check=True)
    if not temp.exists() or temp.stat().st_size < 1000:
        temp.unlink(missing_ok=True)
        raise RuntimeError("El master de voz espiritual no produjo audio valido.")
    temp.replace(path)
    return "luminous_calm_v2"
