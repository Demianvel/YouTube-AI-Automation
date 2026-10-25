"""Central render-quality settings for the Dios Habla Hoy IA Short path.

Default: vertical 1080x1920 with high-quality x264 (CRF 18) and AAC 192k.
``DIOS_RENDER_4K=true`` switches the Short timeline to 2160x3840; it is kept as
an explicit opt-in switch only (the orchestrator leaves it ``false``).
All values are read from the environment at call time so a workflow can tune
them without code changes, and every helper falls back to safe defaults.
"""
from __future__ import annotations

import os

SHORT_1080 = (1080, 1920)
SHORT_4K = (2160, 3840)
_ALLOWED_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"}


def _env(name: str, default: str) -> str:
    return str(os.getenv(name, default) or default).strip()


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_env(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def render_4k_enabled() -> bool:
    return _env("DIOS_RENDER_4K", "false").lower() == "true"


def short_size() -> tuple[int, int]:
    return SHORT_4K if render_4k_enabled() else SHORT_1080


def short_fps() -> int:
    return _env_int("DIOS_RENDER_FPS", 30, 24, 60)


def x264_crf() -> int:
    return _env_int("DIOS_RENDER_CRF", 18, 14, 28)


def x264_preset() -> str:
    default = "fast" if render_4k_enabled() else "medium"
    value = _env("DIOS_RENDER_PRESET", default).lower()
    return value if value in _ALLOWED_PRESETS else default


def oversample() -> float:
    """Zoompan oversampling factor. 2x at 1080p (historical), 1.25x at 4K for CPU time."""
    try:
        default = 1.25 if render_4k_enabled() else 2.0
        value = float(_env("DIOS_RENDER_OVERSAMPLE", str(default)))
    except ValueError:
        value = 2.0
    return max(1.1, min(2.0, value))


def audio_bitrate() -> str:
    default = "256k" if render_4k_enabled() else "192k"
    value = _env("DIOS_AUDIO_BITRATE", default).lower()
    try:
        kbps = int(value.rstrip("k"))
    except ValueError:
        return default
    return f"{max(192, min(320, kbps))}k"


def video_encode_args() -> list[str]:
    """x264 arguments for every Short re-encode (scene clips, concat, overlays)."""
    return [
        "-c:v", "libx264", "-preset", x264_preset(), "-crf", str(x264_crf()),
        "-profile:v", "high", "-pix_fmt", "yuv420p",
    ]


def quality_label() -> str:
    width, height = short_size()
    return f"{width}x{height}_{short_fps()}fps_x264_crf{x264_crf()}_{x264_preset()}_aac{audio_bitrate()}"
