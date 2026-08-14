from __future__ import annotations

import math
import subprocess
from pathlib import Path

from .spiritual_local_art import make_spiritual_art


def make_landscape_speaking_clip(out: Path, duration: int, seed: int, index: int = 0) -> Path:
    """Create a keyless 1920x1080 clip with visible restrained speaking motion.

    This is a last-resort visual fallback for long-form videos. It intentionally
    uses a stylized original fictional character rather than imitating a real actor.
    """
    width, height = 1920, 1080
    temp = out.parent / f"long_talking_{index + 1}"
    temp.mkdir(parents=True, exist_ok=True)
    states = [0, 1, 2, 1, 0, 1, 0, 2]
    images: list[Path] = []
    for state_index, mouth in enumerate(states):
        image = temp / f"state_{state_index}.png"
        make_spiritual_art(image, width, height, seed, index=index, mouth_open=mouth)
        images.append(image)

    frame_duration = 0.24
    repeats = max(1, int(math.ceil(duration / (frame_duration * len(states)))))
    manifest = temp / "talking_concat.txt"
    lines: list[str] = []
    for _ in range(repeats):
        for image in images:
            lines.append(f"file '{image.resolve()}'")
            lines.append(f"duration {frame_duration:.3f}")
    lines.append(f"file '{images[-1].resolve()}'")
    manifest.write_text("\n".join(lines), encoding="utf-8")

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-t", str(duration),
        "-vf", "fps=30,setsar=1,eq=contrast=1.025:saturation=1.04:brightness=0.003,unsharp=5:5:0.10:5:5:0",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(out),
    ], check=True)
    if not out.exists() or out.stat().st_size < 100_000:
        raise RuntimeError("El clip espiritual largo con habla visible no pudo generarse.")
    return out
