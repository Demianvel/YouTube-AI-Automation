from __future__ import annotations

import math
import random
import struct
import subprocess
import wave
from pathlib import Path


def make_original_music(path: Path, duration: int, seed: int) -> None:
    """Create a simple original instrumental bed from synthesized tones."""
    sample_rate = 22050
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xB70A)
    roots = rng.sample([196.00, 220.00, 246.94, 261.63, 293.66], 4)
    phases = [rng.random() * math.tau for _ in range(4)]

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        chunk = bytearray()
        for i in range(total):
            t = i / sample_rate
            root = roots[int(t // 4) % len(roots)]
            chord = (
                math.sin(math.tau * root * t + phases[0]) * .42
                + math.sin(math.tau * root * 1.25 * t + phases[1]) * .25
                + math.sin(math.tau * root * 1.50 * t + phases[2]) * .20
                + math.sin(math.tau * (root / 2) * t + phases[3]) * .18
            )
            pulse_phase = t % 2.0
            pulse = math.exp(-4.0 * pulse_phase) * math.sin(math.tau * (root / 4) * t) * .12
            fade = min(1.0, t / 1.0, max(0.0, (duration - t) / 1.0))
            sample = max(-1.0, min(1.0, (chord + pulse) * .20 * fade))
            chunk += struct.pack("<h", int(sample * 32767))
            if len(chunk) >= 65536:
                wf.writeframes(chunk)
                chunk.clear()
        if chunk:
            wf.writeframes(chunk)


def make_spanish_voice(path: Path, text: str) -> None:
    speaker = "espeak-ng" if subprocess.run(
        ["bash", "-lc", "command -v espeak-ng"], capture_output=True
    ).returncode == 0 else "espeak"

    last_error = None
    for voice in ("es-la", "es"):
        try:
            subprocess.run(
                [speaker, "-v", voice, "-s", "150", "-p", "46", "-a", "175", "-w", str(path), text],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if path.exists() and path.stat().st_size > 1000:
                return
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"No se pudo generar la narracion en castellano: {last_error}")


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")
    music = out.with_name("original_music.wav")
    make_original_music(music, duration, seed)

    if mode == "music_only":
        # Hard guarantee for BrotaVida: generated music only, never narration.
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(video), "-i", str(music),
                "-filter_complex", "[1:a]volume=0.72[a]",
                "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(out),
            ],
            check=True,
        )
        return

    text = " ... ".join(
        s.get("narration", "").strip()
        for s in meta.get("scenes", [])
        if s.get("narration", "").strip()
    )
    if not text:
        raise RuntimeError("Dinero Claro requiere narracion y no se genero texto.")

    voice = out.with_name("narration.wav")
    make_spanish_voice(voice, text)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-i", str(music), "-i", str(voice),
            "-filter_complex",
            f"[1:a]volume=0.12[m];[2:a]highpass=f=100,lowpass=f=6500,acompressor,volume=1.25,apad=pad_dur={duration}[v];[m][v]amix=inputs=2:duration=first[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(out),
        ],
        check=True,
    )
