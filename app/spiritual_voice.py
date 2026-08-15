from __future__ import annotations

import os
import subprocess
from pathlib import Path


def enabled() -> bool:
    return os.getenv("SPIRITUAL_VOICE_PROFILE", "").strip().lower() in {
        "luminous_calm_v1",
        "luminous",
        "calm",
    }


def polish_voice(path: Path) -> str:
    """Create a stable warm/luminous channel voice master without impersonation.

    The processing is deliberately subtle: remove low rumble, add a little
    warmth/presence, compress gently, keep intelligibility, and add a tiny room
    reflection. It does not attempt to imitate any real person.
    """
    if not enabled() or not path.exists():
        return "unprocessed"

    temp = path.with_name(path.stem + ".luminous.wav")
    filters = (
        "highpass=f=58,"
        "lowpass=f=11800,"
        "equalizer=f=165:t=q:w=0.9:g=1.25,"
        "equalizer=f=2850:t=q:w=1.0:g=1.05,"
        "acompressor=threshold=-20dB:ratio=1.45:attack=14:release=165,"
        "aecho=0.82:0.10:34:0.022,"
        "loudnorm=I=-17:TP=-1.6:LRA=6"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
        "-af", filters, "-ar", "48000", "-ac", "1", str(temp),
    ], check=True)
    if not temp.exists() or temp.stat().st_size < 1000:
        temp.unlink(missing_ok=True)
        raise RuntimeError("El master de voz espiritual no produjo audio valido.")
    temp.replace(path)
    return "luminous_calm_v1"
