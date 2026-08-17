from __future__ import annotations

import subprocess
from pathlib import Path

from app import pipeline
from app import spiritual_image
from app.generator_resilient import _local_metadata


def _fast_local_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    metadata = _local_metadata(channel, previous)
    metadata["metadata_provider"] = str(metadata.get("metadata_provider") or "local") + ":fast_voice_quota_reserved"
    print("Modo rapido: metadata local para reservar la cuota Gemini exclusivamente para Voz de Luz/Algenib.")
    return metadata


def _fast_download(prompt: str, out: Path, seed: int) -> str:
    del prompt
    provider = spiritual_image._local_reference(out, seed)
    return provider + ":fast_no_network"


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


pipeline.generate_metadata = _fast_local_metadata
spiritual_image._download = _fast_download
spiritual_image._animate = _fast_animate

if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
