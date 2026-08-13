from __future__ import annotations

import math
import random
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100


def _soft_clip(x: np.ndarray) -> np.ndarray:
    return np.tanh(x * 1.15) * 0.92


def generate_original_electronic_track(
    path: Path,
    duration_seconds: int,
    seed: int,
    bpm: int = 128,
    style: str = "progressive_house",
    faith_theme: bool = False,
) -> None:
    """Original stereo fallback synthesizer with no third-party samples.

    This is the always-available CPU engine. For sung vocals and higher-fidelity song generation,
    DemianVelo can switch to the optional ACE-Step 1.5 engine. The fallback still differentiates
    EDM, RKT, trap and pop rhythmic/harmonic profiles rather than using one loop for every style.
    """
    duration_seconds = max(8, int(duration_seconds))
    style = str(style or "progressive_house").lower()
    bpm = max(85, min(150, int(bpm)))
    rng = random.Random(seed)

    rkt = "rkt" in style
    trap = "trap" in style
    pop = "pop" in style
    techno = "techno" in style
    future = "future" in style

    if faith_theme:
        progression = [57, 64, 61, 62]
        scale = [0, 2, 4, 7, 9]
    elif trap:
        progression = [45, 48, 52, 43]
        scale = [0, 3, 5, 7, 10]
    elif rkt:
        progression = [50, 53, 48, 55]
        scale = [0, 2, 3, 5, 7, 10]
    elif pop:
        progression = [48, 55, 57, 53]
        scale = [0, 2, 4, 7, 9, 11]
    elif techno:
        progression = [45, 48, 43, 50]
        scale = [0, 3, 5, 7, 10]
    elif future:
        progression = [48, 55, 52, 57]
        scale = [0, 2, 4, 7, 9, 11]
    else:
        progression = [48, 55, 57, 53]
        scale = [0, 2, 4, 7, 9]

    beat = 60.0 / bpm
    bar = beat * 4.0
    section = max(8.0 * bar, 12.0)
    lead_offset = rng.choice(scale)
    lead_octave = rng.choice([12, 24])

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)

        for sec in range(duration_seconds):
            n = min(SAMPLE_RATE, int((duration_seconds - sec) * SAMPLE_RATE))
            t = sec + np.arange(n, dtype=np.float32) / SAMPLE_RATE
            beat_pos = np.mod(t, beat)
            beat_index = np.floor(t / beat).astype(np.int64)
            section_index = np.floor(t / section).astype(np.int64)
            sec_phase = np.mod(t, section) / section
            drop_gate = ((section_index % 4) != 2).astype(np.float32)
            build = np.clip(sec_phase * 1.35, 0.15, 1.0)
            break_pad = np.where((section_index % 4) == 2, 1.15, 0.75).astype(np.float32)

            noise = np.random.default_rng(seed + sec * 9973).standard_normal(n).astype(np.float32)
            beat_in_bar = np.mod(beat_index, 4)

            # Kick profile: heavier/rounder in RKT, sparser in trap, straight in EDM/pop.
            kick_env = np.exp(-beat_pos * (11.0 if rkt else 15.0))
            kick_freq = (42.0 if rkt or trap else 46.0) + (76.0 if rkt else 68.0) * np.exp(-beat_pos * 24.0)
            kick = np.sin(2 * np.pi * kick_freq * beat_pos) * kick_env
            if trap:
                kick_mask = ((beat_in_bar == 0) | ((beat_in_bar == 2) & (np.mod(beat_index, 8) == 6))).astype(np.float32)
                kick *= kick_mask * 0.78
            else:
                kick *= (0.82 if rkt else 0.72) * drop_gate

            # Snare/clap profile.
            snare_phase = np.mod(t - beat, bar / 2.0)
            snare_env = np.exp(-np.maximum(snare_phase, 0) * (18.0 if rkt else 22.0))
            if trap:
                snare_mask = (beat_in_bar == 2).astype(np.float32)
            else:
                snare_mask = ((beat_in_bar == 1) | (beat_in_bar == 3)).astype(np.float32)
            snare = noise * snare_env * snare_mask * (0.14 if rkt else 0.105) * drop_gate

            # Hats: fast rolls in trap, energetic offbeats in RKT, cleaner in pop.
            hat_div = 4.0 if trap else (2.0 if not rkt else 3.0)
            hat_step = beat / hat_div
            hat_phase = np.mod(t, hat_step)
            hat_env = np.exp(-hat_phase * (95.0 if trap else 75.0))
            hats = noise * hat_env * (0.042 if trap or rkt else 0.032) * (0.55 + 0.45 * build)

            chord_idx = np.mod(np.floor(t / (bar * 2)).astype(np.int64), len(progression))
            roots = np.take(np.array(progression, dtype=np.int32), chord_idx)
            bass_freq = 440.0 * np.power(2.0, (roots - 69) / 12.0)
            saw = 2.0 * np.mod(t * bass_freq, 1.0) - 1.0
            sine_bass = np.sin(2 * np.pi * bass_freq * t)
            if trap or rkt:
                bass = (0.28 * saw + 0.72 * sine_bass) * (0.25 if rkt else 0.23)
            else:
                bass = (0.68 * saw + 0.32 * sine_bass) * 0.19
            sidechain = 0.42 + 0.58 * np.clip(beat_pos / (beat * 0.55), 0.0, 1.0)
            bass *= sidechain * drop_gate

            pad = np.zeros(n, dtype=np.float32)
            majorish = faith_theme or pop or "progressive" in style
            chord_notes = [0, 4 if majorish else 3, 7]
            for interval, pan_phase in zip(chord_notes, [0.0, 0.7, 1.4]):
                f = 440.0 * np.power(2.0, ((roots + 12 + interval) - 69) / 12.0)
                pad += np.sin(2 * np.pi * f * t + pan_phase).astype(np.float32) * (0.050 if pop else 0.043)
            pad *= break_pad * (0.70 + 0.30 * np.sin(np.pi * sec_phase))

            eighth = beat / 2.0
            motif_step = np.mod(np.floor(t / eighth).astype(np.int64), 8)
            if rkt:
                motif = np.array([0, 0, 3, 5, 7, 5, 3, 10], dtype=np.int32)
            elif trap:
                motif = np.array([0, 3, 0, 7, 5, 3, 10, 7], dtype=np.int32)
            elif pop:
                motif = np.array([0, 2, 4, 7, 4, 9, 7, 4], dtype=np.int32)
            else:
                motif = np.array([0, 2, 4, 2, 7, 4, 2, 9], dtype=np.int32)
            note_offset = np.take(motif, motif_step)
            lead_note = roots + lead_octave + lead_offset + note_offset
            lead_freq = 440.0 * np.power(2.0, (lead_note - 69) / 12.0)
            pluck_env = np.exp(-np.mod(t, eighth) * (6.0 if pop else 8.0 if future else 10.0))
            lead = (
                np.sin(2 * np.pi * lead_freq * t)
                + 0.28 * np.sin(2 * np.pi * lead_freq * 2.0 * t)
            ) * pluck_env * (0.082 if pop or rkt else 0.070) * build
            lead *= np.where((section_index % 4) == 2, 0.38, 1.0)

            # RKT percussion accent / generated tom-like sine hit.
            accent_phase = np.mod(t + beat * 0.5, beat)
            accent = np.sin(2 * np.pi * 165.0 * accent_phase) * np.exp(-accent_phase * 24.0) * (0.08 if rkt else 0.0)

            atmosphere = np.sin(2 * np.pi * (110.0 if faith_theme else 82.41) * t) * 0.016
            if faith_theme:
                atmosphere += np.sin(2 * np.pi * 220.0 * t + 0.35) * 0.009

            mono = kick + snare + hats + bass + pad + lead + accent + atmosphere
            intro = np.clip(t / min(12.0, duration_seconds * 0.15), 0.0, 1.0)
            outro = np.clip((duration_seconds - t) / min(10.0, duration_seconds * 0.12), 0.0, 1.0)
            mono *= np.minimum(intro, outro)

            width = 0.10 * np.sin(2 * np.pi * 0.17 * t)
            left = _soft_clip(mono * (1.0 + width) + pad * 0.10)
            right = _soft_clip(mono * (1.0 - width) - pad * 0.10)
            stereo = np.stack([left, right], axis=1)
            pcm = np.clip(stereo * 32767.0, -32768, 32767).astype("<i2")
            wf.writeframes(pcm.tobytes())

    if not path.exists() or path.stat().st_size < 100_000:
        raise RuntimeError("No se pudo generar una pista musical valida.")
