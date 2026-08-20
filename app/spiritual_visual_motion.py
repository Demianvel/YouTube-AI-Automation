from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


MOTION_PROFILE_NAMES = (
    "center_slow_push",
    "pan_left_to_right",
    "pan_right_to_left",
    "tilt_top_to_bottom",
    "tilt_bottom_to_top",
    "diagonal_top_left_to_bottom_right",
    "diagonal_top_right_to_bottom_left",
    "diagonal_bottom_left_to_top_right",
    "diagonal_bottom_right_to_top_left",
    "slow_pull_back",
    "offcenter_left_push",
    "offcenter_right_push",
)


def _digest(source: Path, salt: str = "") -> int:
    h = hashlib.sha256()
    try:
        with source.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
    except Exception:
        h.update(str(source).encode("utf-8"))
    h.update(str(salt).encode("utf-8"))
    return int(h.hexdigest()[:16], 16)


def motion_profile(source: Path, index: int = 0, salt: str = "") -> tuple[int, str]:
    value = _digest(source, f"{salt}|{index}")
    profile = value % len(MOTION_PROFILE_NAMES)
    return profile, MOTION_PROFILE_NAMES[profile]


def _zoom_expr(profile: int, frames: int) -> str:
    if profile == 9:
        return f"max(1.0,1.105-0.105*on/max(1,{frames - 1}))"
    rates = (0.00046, 0.00055, 0.00053, 0.00049, 0.00051, 0.00052, 0.00050, 0.00054, 0.00048, 0.00045, 0.00058, 0.00057)
    cap = (1.085, 1.105, 1.105, 1.095, 1.095, 1.11, 1.11, 1.11, 1.11, 1.105, 1.12, 1.12)[profile]
    return f"min(zoom+{rates[profile]:.5f},{cap:.3f})"


def _xy_expr(profile: int, frames: int) -> tuple[str, str]:
    progress = f"on/max(1,{frames - 1})"
    center_x = "iw/2-(iw/zoom/2)"
    center_y = "ih/2-(ih/zoom/2)"
    left_to_right = f"min(iw-iw/zoom,(iw-iw/zoom)*{progress})"
    right_to_left = f"max(0,(iw-iw/zoom)*(1-{progress}))"
    top_to_bottom = f"min(ih-ih/zoom,(ih-ih/zoom)*{progress})"
    bottom_to_top = f"max(0,(ih-ih/zoom)*(1-{progress}))"

    profiles = (
        (center_x, center_y),
        (left_to_right, center_y),
        (right_to_left, center_y),
        (center_x, top_to_bottom),
        (center_x, bottom_to_top),
        (left_to_right, top_to_bottom),
        (right_to_left, top_to_bottom),
        (left_to_right, bottom_to_top),
        (right_to_left, bottom_to_top),
        (center_x, center_y),
        ("max(0,(iw-iw/zoom)*0.22)", center_y),
        ("min(iw-iw/zoom,(iw-iw/zoom)*0.78)", center_y),
    )
    return profiles[profile]


def render_still_motion(
    source: Path,
    out: Path,
    duration: int,
    index: int,
    *,
    width: int,
    height: int,
    fps: int,
    preset: str = "veryfast",
    crf: int = 19,
    salt: str = "",
) -> str:
    frames = max(1, int(round(float(duration) * fps)))
    profile, label = motion_profile(source, index=index, salt=salt)
    zoom_expr = _zoom_expr(profile, frames)
    x_expr, y_expr = _xy_expr(profile, frames)

    digest = _digest(source, f"grade|{salt}|{index}")
    contrast = 1.015 + ((digest >> 4) % 5) * 0.006
    saturation = 1.025 + ((digest >> 8) % 6) * 0.007
    brightness = -0.003 + ((digest >> 12) % 7) * 0.001
    sharpen = 0.10 + ((digest >> 16) % 4) * 0.04

    scale_w = width * 2
    scale_h = height * 2
    vf = (
        f"scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
        f"crop={scale_w}:{scale_h},"
        f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={width}x{height}:fps={fps},"
        f"setsar=1,eq=contrast={contrast:.3f}:saturation={saturation:.3f}:brightness={brightness:.3f},"
        f"unsharp=5:5:{sharpen:.2f}:5:5:0"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
            "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", preset,
            "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )
    return label
