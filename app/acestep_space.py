from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client


SPACE_ID = os.getenv("ACESTEP_HF_SPACE", "ACE-Step/Ace-Step-v1.5").strip()
MODEL = os.getenv("ACESTEP_HF_MODEL", "acestep-v15-xl-turbo").strip()


def _path_from_file_ref(value) -> Path | None:
    if value is None:
        return None
    if hasattr(value, "path"):
        p = Path(str(value.path))
        return p if p.exists() else None
    if isinstance(value, dict):
        for key in ("path", "name"):
            if value.get(key):
                p = Path(str(value[key]))
                if p.exists():
                    return p
    if isinstance(value, str):
        p = Path(value)
        return p if p.exists() else None
    return None


def generate_song_space(
    out: Path,
    *,
    prompt: str,
    lyrics: str,
    duration_seconds: int,
    bpm: int,
    vocal_language: str = "es",
) -> None:
    """Generate an original song through the official ACE-Step 1.5 HF Space.

    The public Space runs on Hugging Face ZeroGPU. If HF_TOKEN is configured it is
    passed to Gradio so the request can use the authenticated user's Space quota.
    No token is printed or written to disk by this module.
    """
    token = os.getenv("HF_TOKEN", "").strip() or None
    client = Client(SPACE_ID, token=token, verbose=False)

    duration = max(10, min(600, int(duration_seconds)))
    tempo = max(30, min(300, int(bpm)))

    # Parameters mirror the current official /generation_wrapper endpoint.
    # Keep batch_size=1 to minimize ZeroGPU usage while preserving XL Turbo quality.
    args = [
        MODEL,
        "custom",
        "",
        vocal_language,
        prompt,
        lyrics or "[Instrumental]",
        tempo,
        "",
        "4",
        vocal_language,
        8,
        7.0,
        True,
        "-1",
        None,
        duration,
        1,
        None,
        "",
        0.0,
        -1,
        "Fill the audio semantic mask based on the given conditions:",
        1.0,
        "text2music",
        False,
        0.0,
        1.0,
        3.0,
        "ode",
        "",
        "flac",
        0.80,
        True,
        2.0,
        0,
        0.90,
        "NO USER INPUT",
        True,
        True,
        True,
        False,
        True,
        False,
        False,
        0.5,
        8,
        None,
        [],
        False,
    ]

    result = client.predict(*args, api_name="/generation_wrapper")
    values = list(result) if isinstance(result, (list, tuple)) else [result]

    source = None
    for value in values[:8]:
        source = _path_from_file_ref(value)
        if source and source.stat().st_size > 100_000:
            break
    if source is None and len(values) > 8 and isinstance(values[8], (list, tuple)):
        for value in values[8]:
            source = _path_from_file_ref(value)
            if source and source.stat().st_size > 100_000:
                break
    if source is None:
        raise RuntimeError("ACE-Step ZeroGPU termino sin devolver un archivo de audio utilizable.")

    out.parent.mkdir(parents=True, exist_ok=True)
    # The official Space exposes MP3/FLAC. The rest of this pipeline expects WAV,
    # so decode and normalize explicitly instead of saving FLAC bytes with .wav.
    if out.suffix.lower() == ".wav":
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s24le", str(out),
        ], check=True)
    else:
        shutil.copyfile(source, out)

    if not out.exists() or out.stat().st_size < 100_000:
        raise RuntimeError("ACE-Step ZeroGPU devolvio un archivo de audio invalido.")
