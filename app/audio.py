from __future__ import annotations

import math
import os
import random
import struct
import subprocess
import wave
from pathlib import Path


def make_pleasant_original_music(path: Path, duration: int, seed: int) -> None:
    """Gentle original instrumental bed: bright, warm and non-ominous."""
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xB70A)
    chords = [
        (261.63, 329.63, 392.00),
        (196.00, 246.94, 293.66),
        (174.61, 220.00, 261.63),
        (261.63, 329.63, 392.00),
    ]
    melody = [392.00, 440.00, 523.25, 440.00, 392.00, 329.63, 392.00, 523.25]
    phases = [rng.random() * math.tau for _ in range(5)]

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buffer = bytearray()
        for i in range(total):
            t = i / sample_rate
            chord_index = min(len(chords) - 1, int((t / max(duration, 0.01)) * len(chords)))
            chord = chords[chord_index]
            pad = 0.0
            for j, freq in enumerate(chord):
                pad += math.sin(math.tau * freq * t + phases[j]) * (0.20 - j * 0.025)
                pad += math.sin(math.tau * freq * 2 * t + phases[j]) * 0.025
            beat = int(t / 0.75)
            note = melody[beat % len(melody)]
            local = t % 0.75
            pluck_env = math.exp(-4.8 * local)
            pluck = (
                math.sin(math.tau * note * t + phases[3]) * 0.12
                + math.sin(math.tau * note * 2 * t + phases[4]) * 0.035
            ) * pluck_env
            sparkle_env = math.exp(-8.0 * (t % 1.5))
            sparkle = math.sin(math.tau * note * 3 * t) * sparkle_env * 0.018
            fade = min(1.0, t / 0.45, max(0.0, (duration - t) / 0.55))
            sample = max(-1.0, min(1.0, (pad + pluck + sparkle) * 0.30 * fade))
            buffer += struct.pack("<h", int(sample * 32767))
            if len(buffer) >= 65536:
                wf.writeframes(buffer)
                buffer.clear()
        if buffer:
            wf.writeframes(buffer)


def make_natural_spanish_voice(path: Path, text: str) -> None:
    """Generate local natural Spanish speech with open Kokoro weights."""
    provider = os.getenv("TTS_PROVIDER", "kokoro").lower().strip()
    if provider != "kokoro":
        raise RuntimeError("Produccion requiere TTS_PROVIDER=kokoro para evitar voz robotica.")

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice = os.getenv("KOKORO_VOICE", "ef_dora")
    speed = float(os.getenv("KOKORO_SPEED", "0.96"))
    pipeline = KPipeline(lang_code="e")

    chunks = []
    for _graphemes, _phonemes, audio in pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+"):
        if audio is not None and len(audio):
            chunks.append(np.asarray(audio, dtype=np.float32))
    if not chunks:
        raise RuntimeError("Kokoro no genero audio en castellano.")

    combined = np.concatenate(chunks)
    sf.write(str(path), combined, 24000, subtype="PCM_16")
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Kokoro genero un archivo de voz invalido.")


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")

    if mode == "music_only":
        music = out.with_name("pleasant_original_music.wav")
        make_pleasant_original_music(music, duration, seed)
        fade_out_start = max(0.0, duration - 0.8)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-i", str(music),
            "-filter_complex",
            f"[1:a]afade=t=in:st=0:d=0.30,afade=t=out:st={fade_out_start:.3f}:d=0.75,volume=0.72[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ], check=True)
        return

    text = " ... ".join(
        scene.get("narration", "").strip()
        for scene in meta.get("scenes", [])
        if scene.get("narration", "").strip()
    )
    if not text:
        raise RuntimeError("Dinero Claro requiere narracion y no se genero texto.")

    voice_path = out.with_name("narration_kokoro.wav")
    make_natural_spanish_voice(voice_path, text)
    music = out.with_name("finance_soft_music.wav")
    make_pleasant_original_music(music, duration, seed ^ 0xD1E0)

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video), "-i", str(voice_path), "-i", str(music),
        "-filter_complex",
        f"[1:a]highpass=f=70,lowpass=f=8500,acompressor=threshold=-18dB:ratio=2.0:attack=15:release=180,volume=1.05,apad=pad_dur={duration}[v];"
        "[2:a]volume=0.055[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ], check=True)
