from __future__ import annotations

import math
import random
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100


def _midi(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


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
    """Generate an original stereo electronic instrumental without third-party samples.

    The synthesis is deterministic from seed and streamed in 1-second blocks so 30-minute
    tracks do not require large amounts of RAM. It intentionally uses only generated waveforms
    and noise; no copyrighted recordings or loops are embedded.
    """
    duration_seconds = max(8, int(duration_seconds))
    bpm = max(90, min(150, int(bpm)))
    rng = random.Random(seed)

    if faith_theme:
        progression = [57, 64, 61, 62]  # A - E - C# - D feel, warm/hopeful
        scale = [0, 2, 4, 7, 9]
    elif "techno" in style:
        progression = [45, 48, 43, 50]
        scale = [0, 3, 5, 7, 10]
    elif "future" in style:
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
            bar_index = np.floor(t / bar).astype(np.int64)
            section_index = np.floor(t / section).astype(np.int64)

            # Arrangement: progressive build/drop/break variation rather than a single loop.
            sec_phase = np.mod(t, section) / section
            drop_gate = ((section_index % 4) != 2).astype(np.float32)
            build = np.clip(sec_phase * 1.35, 0.15, 1.0)
            break_pad = np.where((section_index % 4) == 2, 1.15, 0.75).astype(np.float32)

            # Kick with pitch drop and exponential envelope.
            kick_env = np.exp(-beat_pos * 15.0)
            kick_freq = 46.0 + 68.0 * np.exp(-beat_pos * 24.0)
            kick = np.sin(2 * np.pi * kick_freq * beat_pos) * kick_env * 0.72 * drop_gate

            # Snare/clap on beats 2 and 4, generated noise only.
            beat_in_bar = np.mod(beat_index, 4)
            snare_phase = np.mod(t - beat, bar / 2.0)
            snare_env = np.exp(-np.maximum(snare_phase, 0) * 22.0)
            snare_mask = ((beat_in_bar == 1) | (beat_in_bar == 3)).astype(np.float32)
            noise = np.random.default_rng(seed + sec * 9973).standard_normal(n).astype(np.float32)
            snare = noise * snare_env * snare_mask * 0.105 * drop_gate

            # Hi-hats at eighth notes.
            eighth = beat / 2.0
            hat_phase = np.mod(t, eighth)
            hat_env = np.exp(-hat_phase * 75.0)
            hats = noise * hat_env * 0.035 * (0.55 + 0.45 * build)

            # Bass follows chord roots, side-chained by kick.
            chord_idx = np.mod(np.floor(t / (bar * 2)).astype(np.int64), len(progression))
            roots = np.take(np.array(progression, dtype=np.int32), chord_idx)
            bass_freq = 440.0 * np.power(2.0, (roots - 69) / 12.0)
            saw = 2.0 * np.mod(t * bass_freq, 1.0) - 1.0
            bass = (0.68 * saw + 0.32 * np.sin(2 * np.pi * bass_freq * t)) * 0.19
            sidechain = 0.42 + 0.58 * np.clip(beat_pos / (beat * 0.55), 0.0, 1.0)
            bass *= sidechain * drop_gate

            # Pad triads. Every block recomputes frequencies from the active chord.
            pad = np.zeros(n, dtype=np.float32)
            chord_notes = [0, 4 if faith_theme or "progressive" in style else 3, 7]
            for interval, pan_phase in zip(chord_notes, [0.0, 0.7, 1.4]):
                f = 440.0 * np.power(2.0, ((roots + 12 + interval) - 69) / 12.0)
                pad += np.sin(2 * np.pi * f * t + pan_phase).astype(np.float32) * 0.043
            pad *= break_pad * (0.70 + 0.30 * np.sin(np.pi * sec_phase))

            # Lead motif varies every two bars and every section.
            motif_step = np.mod(np.floor(t / eighth).astype(np.int64), 8)
            motif = np.array([0, 2, 4, 2, 7, 4, 2, 9], dtype=np.int32)
            note_offset = np.take(motif, motif_step)
            lead_note = roots + lead_octave + lead_offset + note_offset
            lead_freq = 440.0 * np.power(2.0, (lead_note - 69) / 12.0)
            pluck_env = np.exp(-hat_phase * (7.0 if "future" in style else 10.0))
            lead = (
                np.sin(2 * np.pi * lead_freq * t)
                + 0.28 * np.sin(2 * np.pi * lead_freq * 2.0 * t)
            ) * pluck_env * 0.070 * build
            lead *= np.where((section_index % 4) == 2, 0.38, 1.0)

            # A slow atmospheric tone gives Christian/ambient variants more space.
            atmosphere = np.sin(2 * np.pi * (110.0 if faith_theme else 82.41) * t) * 0.016
            if faith_theme:
                atmosphere += np.sin(2 * np.pi * 220.0 * t + 0.35) * 0.009

            mono = kick + snare + hats + bass + pad + lead + atmosphere

            # Global intro/outro and section transitions.
            intro = np.clip(t / min(12.0, duration_seconds * 0.15), 0.0, 1.0)
            outro = np.clip((duration_seconds - t) / min(10.0, duration_seconds * 0.12), 0.0, 1.0)
            global_env = np.minimum(intro, outro)
            mono *= global_env

            # Simple stereo widening generated from phase-related components, no external FX samples.
            width = 0.10 * np.sin(2 * np.pi * 0.17 * t)
            left = _soft_clip(mono * (1.0 + width) + pad * 0.10)
            right = _soft_clip(mono * (1.0 - width) - pad * 0.10)
            stereo = np.stack([left, right], axis=1)
            pcm = np.clip(stereo * 32767.0, -32768, 32767).astype("<i2")
            wf.writeframes(pcm.tobytes())

    if not path.exists() or path.stat().st_size < 100_000:
        raise RuntimeError("No se pudo generar una pista musical valida.")
