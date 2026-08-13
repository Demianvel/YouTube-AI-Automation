from __future__ import annotations

import math
import random
import struct
import subprocess
import wave
from pathlib import Path

from .audio import make_natural_spanish_voice


def make_clean_botanical_asmr(path: Path, duration: int, seed: int) -> str:
    """Create sparse, clean botanical foley without a continuous noise floor.

    The soundscape uses discrete water drops, leaf-brush events and soft soil
    granules. There is intentionally no constant white-noise/rain/static layer.
    """
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xB07A5A)

    drop_times = sorted(rng.uniform(0.45, max(0.55, duration - 0.35)) for _ in range(max(4, int(duration * 0.7))))
    leaf_times = sorted(rng.uniform(0.65, max(0.75, duration - 0.45)) for _ in range(max(2, int(duration * 0.35))))
    soil_times = sorted(rng.uniform(0.35, max(0.45, duration - 0.30)) for _ in range(max(3, int(duration * 0.45))))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buf = bytearray()

        for i in range(total):
            t = i / sample_rate
            sample = 0.0

            # Very low warm room tone made from harmonics, not broadband noise.
            sample += math.sin(math.tau * 92.0 * t) * 0.004
            sample += math.sin(math.tau * 184.0 * t + 0.4) * 0.0025

            # Clear water droplets with a short natural pitch fall.
            for event in drop_times:
                dt = t - event
                if 0.0 <= dt < 0.22:
                    env = math.exp(-22.0 * dt)
                    freq = 1450.0 - 720.0 * min(1.0, dt / 0.22)
                    sample += math.sin(math.tau * freq * dt) * env * 0.20
                    sample += math.sin(math.tau * freq * 1.55 * dt + 0.2) * env * 0.045

            # Short leaf-brush textures. Noise exists only inside these brief
            # events, shaped by a smooth envelope, so it sounds like foliage
            # instead of television static.
            for idx, event in enumerate(leaf_times):
                dt = t - event
                if 0.0 <= dt < 0.32:
                    x = dt / 0.32
                    env = math.sin(math.pi * x) ** 2
                    local_rng = random.Random(seed + idx * 1000003 + i // 5)
                    texture = local_rng.uniform(-1.0, 1.0)
                    shimmer = math.sin(math.tau * (520.0 + idx * 73.0) * dt) * 0.35
                    sample += (texture * 0.050 + shimmer * 0.018) * env

            # Soil/granule movement: damped low taps and tiny high clicks.
            for idx, event in enumerate(soil_times):
                dt = t - event
                if 0.0 <= dt < 0.18:
                    env = math.exp(-30.0 * dt)
                    base = 125.0 + (idx % 4) * 27.0
                    sample += math.sin(math.tau * base * dt) * env * 0.075
                    sample += math.sin(math.tau * (1800.0 + idx * 110.0) * dt) * env * 0.018

            fade = min(1.0, t / 0.18, max(0.0, (duration - t) / 0.25))
            sample = max(-0.88, min(0.88, sample * fade))
            buf += struct.pack("<h", int(sample * 32767))
            if len(buf) >= 65536:
                wf.writeframes(buf)
                buf.clear()
        if buf:
            wf.writeframes(buf)

    return "clean_water_leaf_soil_foley"


def make_premium_original_music(path: Path, duration: int, seed: int, mood: str = "calm") -> str:
    """Generate varied original instrumental beds with no third-party recording."""
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0x51A7C0DE)

    palettes = [
        {"name": "organic_glass", "chords": [(261.63,329.63,392.00),(220.00,261.63,329.63),(174.61,220.00,261.63),(196.00,246.94,293.66)], "melody": [392.00,440.00,523.25,659.25,523.25,440.00,392.00,329.63], "beat": 0.72},
        {"name": "warm_growth", "chords": [(293.66,369.99,440.00),(246.94,293.66,369.99),(220.00,277.18,329.63),(261.63,329.63,392.00)], "melody": [440.00,493.88,587.33,493.88,440.00,369.99,329.63,369.99], "beat": 0.84},
        {"name": "clean_creator", "chords": [(196.00,246.94,293.66),(220.00,261.63,329.63),(246.94,311.13,369.99),(174.61,220.00,261.63)], "melody": [293.66,369.99,392.00,493.88,392.00,369.99,329.63,293.66], "beat": 0.62},
        {"name": "soft_future", "chords": [(329.63,392.00,493.88),(293.66,369.99,440.00),(261.63,329.63,392.00),(220.00,277.18,329.63)], "melody": [523.25,493.88,440.00,392.00,440.00,523.25,659.25,523.25], "beat": 0.68},
        {"name": "earthy_minimal", "chords": [(174.61,220.00,261.63),(196.00,246.94,293.66),(164.81,207.65,246.94),(220.00,261.63,329.63)], "melody": [261.63,293.66,329.63,392.00,329.63,293.66,246.94,261.63], "beat": 0.90},
        {"name": "morning_sprout", "chords": [(246.94,311.13,369.99),(277.18,329.63,415.30),(220.00,277.18,329.63),(293.66,369.99,440.00)], "melody": [369.99,415.30,493.88,554.37,493.88,415.30,369.99,311.13], "beat": 0.76},
        {"name": "quiet_garden", "chords": [(220.00,261.63,329.63),(196.00,246.94,293.66),(233.08,293.66,349.23),(174.61,220.00,261.63)], "melody": [329.63,349.23,392.00,440.00,392.00,349.23,293.66,329.63], "beat": 0.96},
        {"name": "fresh_leaves", "chords": [(261.63,329.63,415.30),(293.66,369.99,466.16),(246.94,311.13,392.00),(220.00,277.18,349.23)], "melody": [415.30,466.16,523.25,622.25,523.25,466.16,415.30,349.23], "beat": 0.66},
    ]
    palette = palettes[seed % len(palettes)]
    phases = [rng.random() * math.tau for _ in range(6)]
    pulse_depth = 0.018 if mood == "calm" else 0.038
    pluck_level = 0.085 if mood == "calm" else 0.12

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
                pad += math.sin(math.tau * freq * t + phases[j]) * (0.13 - j * 0.018)
                pad += math.sin(math.tau * freq * 2 * t + phases[j]) * 0.014

            beat_len = palette["beat"]
            beat = int(t / beat_len)
            note = palette["melody"][beat % len(palette["melody"])]
            local = t % beat_len
            env = math.exp(-5.2 * local)
            pluck = (
                math.sin(math.tau * note * t + phases[3]) * pluck_level
                + math.sin(math.tau * note * 2 * t + phases[4]) * 0.020
            ) * env

            pulse = math.sin(math.tau * (1.0 / max(0.35, beat_len * 2)) * t + phases[5]) * pulse_depth
            air = math.sin(math.tau * note * 3 * t) * math.exp(-7.8 * (t % (beat_len * 2))) * 0.009

            fade = min(1.0, t / 0.35, max(0.0, (duration - t) / 0.45))
            sample = max(-1.0, min(1.0, (pad + pluck + pulse + air) * 0.34 * fade))
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
        asmr = out.with_name("botanical_clean_asmr.wav")
        music = out.with_name("botanical_ambient_music.wav")
        asmr_variant = make_clean_botanical_asmr(asmr, duration, seed)
        music_variant = make_premium_original_music(music, duration, seed ^ 0xA54D, mood="calm")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-i", str(asmr), "-i", str(music),
            "-filter_complex",
            "[1:a]highpass=f=60,lowpass=f=10500,acompressor=threshold=-22dB:ratio=1.35:attack=12:release=170,loudnorm=I=-20:TP=-2.2:LRA=10[a1];"
            "[2:a]volume=0.055,lowpass=f=7600[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=1[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
        ], check=True)
        meta["tts_provider_used"] = "none"
        meta["asmr_variant"] = asmr_variant
        meta["music_variant"] = music_variant
        meta["audio_source"] = "clean_botanical_foley_plus_subtle_original_ambient_music"
        return

    if mode == "music_only":
        music = out.with_name("premium_original_music.wav")
        variant = make_premium_original_music(music, duration, seed, mood="calm")
        fade_in = min(0.28, max(0.05, duration * 0.10))
        fade_out = min(0.65, max(0.05, duration * 0.18))
        fade_out_start = max(0.0, duration - fade_out)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(music),
            "-filter_complex", f"[1:a]afade=t=in:st=0:d={fade_in:.2f},afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f},volume=0.58[a]",
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
