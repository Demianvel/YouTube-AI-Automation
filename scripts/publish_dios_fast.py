from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from app import pipeline
from app import spiritual_image
from app import spiritual_tts
from app.fast_spiritual_metadata import build_fast_metadata
from app.generator_resilient import _local_metadata
from app.spiritual_free_media import download_fresh_free_image


def _fast_local_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    metadata = _local_metadata(channel, previous)
    metadata = build_fast_metadata(metadata, channel, previous)
    print(
        f"Modo rapido: guion local NUEVO sobre {metadata.get('bible_reference')} para reservar Gemini exclusivamente para Voz de Luz/Algenib."
    )
    return metadata


def _fast_animate(source: Path, out: Path, duration: int, index: int) -> None:
    fps = 24
    frames = max(1, duration * fps)
    zoom_rate = 0.00072 + (index % 4) * 0.00006
    x_modes = (
        "iw/2-(iw/zoom/2)",
        "min(iw-iw/zoom,(iw-iw/zoom)*on/max(1,duration*24))",
        "max(0,(iw-iw/zoom)*(1-on/max(1,duration*24)))",
    )
    y_modes = (
        "ih/2-(ih/zoom/2)",
        "min(ih-ih/zoom,(ih-ih/zoom)*on/max(1,duration*24))",
        "max(0,(ih-ih/zoom)*(1-on/max(1,duration*24)))",
    )
    x_expr = x_modes[index % len(x_modes)]
    y_expr = y_modes[(index // 2) % len(y_modes)]
    vf = (
        "scale=1620:2880:force_original_aspect_ratio=increase,"
        "crop=1620:2880,"
        f"zoompan=z='min(zoom+{zoom_rate:.5f},1.085)':x='{x_expr}':y='{y_expr}':d={frames}:s=1080x1920:fps={fps},"
        "setsar=1,eq=contrast=1.02:saturation=1.04:brightness=0.003"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
            "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )


_ORIGINAL_DOWNLOAD = spiritual_image._download
_ORIGINAL_GEMINI_VOICE = spiritual_tts._gemini_spiritual_voice


def _fresh_download(prompt: str, out: Path, seed: int) -> str:
    """Use FLUX first; never keep the repeated local-reference fallback in strict fast mode."""
    original_provider = ""
    original_error: Exception | None = None
    try:
        original_provider = _ORIGINAL_DOWNLOAD(prompt, out, seed)
        if not original_provider.startswith("local_project_jesus_reference"):
            return original_provider
        print("El generador termino en referencia local repetible; reemplazando por una imagen gratuita NUEVA.")
    except Exception as exc:
        original_error = exc
        print(f"Generador visual principal no disponible ({exc}); buscando imagen gratuita NUEVA.")

    try:
        provider = download_fresh_free_image(prompt, out, seed)
        return provider + ":fresh_nonrepeat_fallback"
    except Exception as fresh_exc:
        strict = os.getenv("SPIRITUAL_REQUIRE_FRESH_VISUAL", "true").lower().strip() == "true"
        if strict:
            raise RuntimeError(
                f"Se rechazo publicar una escena repetida. FLUX/local={original_provider or original_error}; fresh-free={fresh_exc}"
            ) from fresh_exc
        if original_provider:
            return original_provider
        raise


def _quota_resilient_gemini_voice(path: Path, text: str) -> str:
    """Keep Voz de Luz/Algenib fixed; wait once for Gemini's 429 window instead of changing voice."""
    try:
        return _ORIGINAL_GEMINI_VOICE(path, text)
    except Exception as exc:
        message = str(exc)
        upper = message.upper()
        if "429" not in upper and "QUOTA" not in upper and "TOO_MANY_REQUESTS" not in upper:
            raise

        match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", message, flags=re.IGNORECASE)
        suggested = float(match.group(1)) if match else 55.0
        wait_seconds = max(12.0, min(75.0, suggested + 2.0))
        print(
            f"Gemini TTS alcanzo su ventana de cuota; esperando {wait_seconds:.1f}s y reintentando la MISMA Voz de Luz/Algenib."
        )
        time.sleep(wait_seconds)
        return _ORIGINAL_GEMINI_VOICE(path, text)


pipeline.generate_metadata = _fast_local_metadata
spiritual_image._download = _fresh_download
spiritual_image._animate = _fast_animate
spiritual_tts._gemini_spiritual_voice = _quota_resilient_gemini_voice

if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
