from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def available() -> bool:
    if os.getenv("LTX2_ENABLED", "false").lower() != "true":
        return False
    if not shutil.which("nvidia-smi"):
        return False
    required = [
        "LTX2_REPO_ROOT",
        "LTX2_CHECKPOINT",
        "LTX2_SPATIAL_UPSAMPLER",
        "LTX2_GEMMA_ROOT",
    ]
    return all(os.getenv(name, "").strip() for name in required)


def generate_clip(
    prompt: str,
    out: Path,
    *,
    seconds: int = 8,
    portrait: bool = False,
    seed: int = 10,
    native_4k: bool = True,
) -> Path:
    """Run the official Lightricks LTX-2 distilled CLI on a CUDA runner.

    Standard GitHub-hosted ubuntu runners do not have a suitable NVIDIA GPU. This adapter is
    therefore opt-in and intended for a self-hosted/paid GPU runner with official LTX-2 weights.
    When unavailable, callers must fall back to the existing real-video/image pipelines.
    """
    if not available():
        raise RuntimeError("LTX-2 no esta disponible: requiere LTX2_ENABLED=true, CUDA y rutas de modelos oficiales.")

    root = Path(os.environ["LTX2_REPO_ROOT"]).expanduser().resolve()
    checkpoint = Path(os.environ["LTX2_CHECKPOINT"]).expanduser().resolve()
    upsampler = Path(os.environ["LTX2_SPATIAL_UPSAMPLER"]).expanduser().resolve()
    gemma = Path(os.environ["LTX2_GEMMA_ROOT"]).expanduser().resolve()
    for path in (root, checkpoint, upsampler, gemma):
        if not path.exists():
            raise RuntimeError(f"LTX-2 ruta inexistente: {path}")

    # LTX frame counts follow 8n+1. At 30fps, 241 frames is ~8 seconds.
    seconds = max(2, min(10, int(seconds)))
    frames = max(9, ((seconds * 30) // 8) * 8 + 1)
    if native_4k:
        width, height = ((2160, 3840) if portrait else (3840, 2160))
    else:
        width, height = ((1080, 1920) if portrait else (1920, 1080))

    python_bin = root / ".venv/bin/python"
    if not python_bin.exists():
        python_bin = Path(sys.executable)

    out.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(python_bin), "-m", "ltx_pipelines.distilled",
        "--checkpoint-path", str(checkpoint),
        "--spatial-upsampler-path", str(upsampler),
        "--gemma-root", str(gemma),
        "--prompt", prompt,
        "--output-path", str(out),
        "--width", str(width),
        "--height", str(height),
        "--frame-rate", "30",
        "--num-frames", str(frames),
        "--seed", str(int(seed)),
        "--offload", os.getenv("LTX2_OFFLOAD", "cpu"),
    ]
    quant = os.getenv("LTX2_QUANTIZATION", "").strip()
    if quant:
        command.extend(["--quantization", quant])
    if os.getenv("LTX2_ENHANCE_PROMPT", "true").lower() == "true":
        command.append("--enhance-prompt")

    subprocess.run(command, cwd=root, check=True)
    if not out.exists() or out.stat().st_size < 100_000:
        raise RuntimeError("LTX-2 no produjo un clip valido.")
    return out
