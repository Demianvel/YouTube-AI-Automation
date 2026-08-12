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
    """Generate local Spanish narration with Kokoro-82M open weights."""
    if os.getenv("TTS_PROVIDER", "kokoro").lower().strip() != "kokoro":
        raise RuntimeError("TTS_PROVIDER debe ser 'kokoro' para la voz local gratuita.")

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice = os.getenv("KOKORO_VOICE", "em_alex").strip() or "em_alex"
    speed = float(os.getenv("KOKORO_SPEED", "0.95"))

    pipeline = KPipeline(lang_code="e")
    chunks: list[np.ndarray] = []

    # Kokoro suele rendir mejor con frases completas y no con fragmentos de pocas palabras.
    for _graphemes, _phonemes, audio in pipeline(
        text,
        voice=voice,
        speed=speed,
        split_pattern=r"(?<=[.!?])\s+",
    ):
        if audio is not None and len(audio):
            chunks.append(np.asarray(audio, dtype=np.float32))

    if not chunks:
        raise RuntimeError("Kokoro no genero audio en español.")

    pause = np.zeros(int(24000 * 0.16), dtype=np.float32)
    joined: list[np.ndarray] = []
    for index, chunk in enumerate(chunks):
        if index:
            joined.append(pause)
        joined.append(chunk)

    combined = np.concatenate(joined)
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    if peak > 0.98:
        combined = combined * (0.96 / peak)

    sf.write(str(path), combined, 24000, subtype="PCM_16")
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Kokoro genero un archivo de voz invalido.")


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")

    if mode == "music_only":
        music = out.with_name("pleasant_original_music.wav")
        make_pleasant_original_music(music, duration, seed)
        fade_in = min(0.30, max(0.05, duration * 0.12))
        fade_out = min(0.75, max(0.05, duration * 0.20))
        fade_out_start = max(0.0, duration - fade_out)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-i", str(music),
            "-filter_complex",
            f"[1:a]afade=t=in:st=0:d={fade_in:.2f},afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f},volume=0.72[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ], check=True)
        return

    text = " ".join(
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
        f"[1:a]highpass=f=70,lowpass=f=9000,acompressor=threshold=-18dB:ratio=1.9:attack=12:release=160,loudnorm=I=-16:TP=-1.5:LRA=8,apad=pad_dur={duration}[v];"
        "[2:a]volume=0.045[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ], check=True)
