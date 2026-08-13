from __future__ import annotations

import math
import random
import struct
import wave
from pathlib import Path


def make_clay_asmr(path: Path, duration: int, seed: int) -> None:
    """Generate original soft clay/play-dough foley locally; no third-party audio."""
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xC1A7)

    squishes = sorted(
        rng.uniform(0.25, max(0.4, duration - 0.2))
        for _ in range(max(6, int(duration * 1.15)))
    )
    taps = sorted(
        rng.uniform(0.2, max(0.35, duration - 0.15))
        for _ in range(max(5, int(duration * 0.85)))
    )

    low = 0.0
    mid = 0.0
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buffer = bytearray()

        for i in range(total):
            t = i / sample_rate
            white = rng.uniform(-1.0, 1.0)
            low += 0.008 * (white - low)
            mid += 0.06 * (white - mid)

            # Soft rubbing/kneading bed.
            rub_mod = 0.55 + 0.45 * math.sin(math.tau * 0.42 * t + 0.7)
            rub = (mid - low) * (0.055 + 0.035 * rub_mod)
            body = low * 0.10

            squish = 0.0
            for event in squishes:
                dt = t - event
                if 0.0 <= dt < 0.24:
                    env = math.sin(math.pi * min(1.0, dt / 0.24)) ** 2
                    tone = 115.0 + 28.0 * math.sin(math.tau * 2.2 * dt)
                    squish += math.sin(math.tau * tone * dt) * env * 0.16
                    squish += (mid - low) * env * 0.08

            tap = 0.0
            for event in taps:
                dt = t - event
                if 0.0 <= dt < 0.055:
                    env = math.exp(-58.0 * dt)
                    tap += math.sin(math.tau * 520.0 * dt) * env * 0.08
                    tap += rng.uniform(-1.0, 1.0) * env * 0.035

            fade = min(1.0, t / 0.25, max(0.0, (duration - t) / 0.35))
            sample = (body + rub + squish + tap) * fade
            sample = max(-0.92, min(0.92, sample))
            buffer += struct.pack("<h", int(sample * 32767))

            if len(buffer) >= 65536:
                wf.writeframes(buffer)
                buffer.clear()

        if buffer:
            wf.writeframes(buffer)
