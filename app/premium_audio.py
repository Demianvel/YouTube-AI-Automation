from __future__ import annotations

import math
import random
import struct
import subprocess
import wave
from pathlib import Path

from .audio import make_botanical_asmr, make_natural_spanish_voice


def make_premium_original_music(path: Path, duration: int, seed: int, mood: str = "calm") -> str:
    """Generate one of several deterministic original instrumental beds.

    Every content seed selects a different harmonic palette, melody, pulse and timbre.
    No third-party music or copyrighted recording is used.
    """
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0x51A7C0DE)

    palettes = [
        {
            "name": "organic_glass",
            "chords": [(261.63, 329.63, 392.00), (220.00, 261.63, 329.63), (174.61, 220.00, 261.63), (196.00, 246.94, 293.66)],
            "melody": [392.00, 440.00, 523.25, 659.25, 523.25, 440.00, 392.00, 329.63],
            "beat": 0.72,
        },
        {
            "name": "warm_growth",
            "chords": [(293.66, 369.99, 440.00), (246.94, 293.66, 369.99), (220.00, 277.18, 329.63), (261.63, 329.63, 392.00)],
            "melody": [440.00, 493.88, 587.33, 493.88, 440.00, 369.99, 329.63, 369.99],
            "beat": 0.84,
        },
        {
            "name": "clean_creator",
            "chords": [(196.00, 246.94, 293.66), (220.00, 261.63, 329.63), (246.94, 311.13, 369.99), (174.61, 220.00, 261.63)],
            "melody": [293.66, 369.99, 392.00, 493.88, 392.00, 369.99, 329.63, 293.66],
            "beat": 0.62,
        },
        {
            "name": "soft_future",
            "chords": [(329.63, 392.00, 493.88), (293.66, 369.99, 440.00), (261.63, 329.63, 392.00), (220.00, 277.18, 329.63)],
            "melody": [523.25, 493.88, 440.00, 392.00, 440.00, 523.25, 659.25, 523.25],
            "beat": 0.68,
        },
        {
            "name": "earthy_minimal",
            "chords": [(174.61, 220.00, 261.63), (196.00, 246.94, 293.66), (164.81, 207.65, 246.94), (220.00, 261.63, 329.63)],
            "melody": [261.63, 293.66, 329.63, 392.00, 329.63, 293.66, 246.94, 261.63],
            "beat": 0.90,
        },
    ]
    palette = palettes[seed % len(palettes)]
    phases = [rng.random() * math.tau for _ in range(6)]
    pulse_depth = 0.028 if mood == "calm" else 0.045
    pluck_level = 0.10 if mood == "calm" else 0.13

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buf = bytearray()
        for i in range(total):
            t = i / sample_rate
            chord_index = min(len(palette["chords"]) - 1, int((t / max(duration, 0.01)) * len(palette["chords"])))
            chord = palette["chords"][chord_index]

            pad = 0.0
            for j, freq in enumerate(chord):
                pad += math.sin(math.tau * freq * t + phases[j]) * (0.15 - j * 0.02)
                pad += math.sin(math.tau * freq * 2 * t + phases[j]) * 0.018

            beat_len = palette["beat"]
            beat = int(t / beat_len)
            note = palette["melody"][beat % len(palette["melody"])]
            local = t % beat_len
            env = math.exp(-5.2 * local)
            pluck = (
                math.sin(math.tau * note * t + phases[3]) * pluck_level
                + math.sin(math.tau * note * 2 * t + phases[4]) * 0.026
            ) * env

            pulse = math.sin(math.tau * (1.0 / max(0.35, beat_len * 2)) * t + phases[5]) * pulse_depth
            air = math.sin(math.tau * note * 3 * t) * math.exp(-7.8 * (t % (beat_len * 2))) * 0.012

            fade = min(1.0, t / 0.35, max(0.0, (duration - t) / 0.45))
            sample = max(-1.0, min(1.0, (pad + pluck + pulse + air) * 0.36 * fade))
            buf += struct.pack("<h", int(sample * 32767))
            if len(buf) >= 65536:
                wf.writeframes(buf)
                buf.clear()
        if buf:
            wf.writeframes(buf)

    return palette["name"]


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")
    meta["audio_mode_used"] = mode

    if mode == "asmr":
        asmr = out.with_name("botanical_asmr.wav")
        music = out.with_name("botanical_ambient_music.wav")
        make_botanical_asmr(asmr, duration, seed)
        variant = make_premium_original_music(music, duration, seed ^ 0xA54D, mood="calm")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-i", str(asmr), "-i", str(music),
            "-filter_complex",
            "[1:a]highpass=f=45,lowpass=f=12000,loudnorm=I=-18:TP=-2:LRA=8[a1];"
            "[2:a]volume=0.105,lowpass=f=8500[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=1[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
        ], check=True)
        meta["tts_provider_used"] = "none"
        meta["music_variant"] = variant
        meta["audio_source"] = "botanical_asmr_plus_low_original_ambient_music"
        return

    if mode == "music_only":
        music = out.with_name("premium_original_music.wav")
        variant = make_premium_original_music(music, duration, seed, mood="calm")
        fade_in = min(0.28, max(0.05, duration * 0.10))
        fade_out = min(0.65, max(0.05, duration * 0.18))
        fade_out_start = max(0.0, duration - fade_out)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(music),
            "-filter_complex", f"[1:a]afade=t=in:st=0:d={fade_in:.2f},afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f},volume=0.66[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ], check=True)
        meta["tts_provider_used"] = "none"
        meta["music_variant"] = variant
        meta["audio_source"] = "varied_original_instrumental_generated_in_repo"
        return

    text = " ".join(
        scene.get("narration", "").strip()
        for scene in meta.get("scenes", [])
        if scene.get("narration", "").strip()
    )
    if not text:
        raise RuntimeError("El canal requiere narracion y no se genero texto.")

    voice_path = out.with_name("narration_professional_es.wav")
    used = make_natural_spanish_voice(voice_path, text)
    music = out.with_name("creator_background_music.wav")
    variant = make_premium_original_music(music, duration, seed ^ 0xD1E0, mood="creator")

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video), "-i", str(voice_path), "-i", str(music),
        "-filter_complex",
        f"[1:a]highpass=f=68,lowpass=f=11000,acompressor=threshold=-19dB:ratio=1.65:attack=9:release=135,loudnorm=I=-16:TP=-1.5:LRA=7,apad=pad_dur={duration}[v];"
        "[2:a]volume=0.027,lowpass=f=9000[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ], check=True)
    meta["tts_provider_used"] = used
    meta["music_variant"] = variant
    meta["audio_source"] = "professional_latam_spanish_voice_plus_low_original_music"
