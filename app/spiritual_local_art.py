from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw


def _lerp(a: int, b: int, t: float) -> int:
    return int(a * (1.0 - t) + b * t)


def make_spiritual_art(
    path: Path,
    width: int,
    height: int,
    seed: int,
    index: int = 0,
    mouth_open: int = 0,
) -> Path:
    """Create an original illustrated spiritual scene without external APIs.

    This is intentionally stylized rather than photorealistic. It is a reliable
    last-resort renderer when hosted AI services are unavailable.
    """
    rng = random.Random(int(seed) ^ (index * 1009))
    portrait = height >= width
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Golden sky gradient.
    top = (70 + index * 4 % 20, 105, 150)
    bottom = (247, 184, 92)
    horizon = int(height * (0.58 if portrait else 0.62))
    for y in range(height):
        t = min(1.0, y / max(1, horizon))
        color = tuple(_lerp(top[c], bottom[c], t) for c in range(3))
        draw.line((0, y, width, y), fill=color)

    # Sun and soft halo rings.
    sun_x = int(width * (0.73 if index % 2 == 0 else 0.27))
    sun_y = int(height * (0.22 if portrait else 0.24))
    sun_r = max(18, int(min(width, height) * 0.055))
    for mul, alpha_color in ((3.1, (255, 205, 115)), (2.2, (255, 221, 146)), (1.45, (255, 237, 185))):
        r = int(sun_r * mul)
        draw.ellipse((sun_x-r, sun_y-r, sun_x+r, sun_y+r), fill=alpha_color)
    draw.ellipse((sun_x-sun_r, sun_y-sun_r, sun_x+sun_r, sun_y+sun_r), fill=(255, 248, 215))

    # Layered mountains.
    for layer, color in enumerate(((72, 91, 105), (82, 109, 101), (91, 128, 94))):
        base_y = int(height * (0.56 + layer * 0.045))
        pts = [(0, base_y)]
        peaks = 6 if portrait else 9
        for p in range(peaks + 1):
            x = int(width * p / peaks)
            peak = base_y - int(height * (0.07 + 0.06 * rng.random()) / (layer + 1))
            pts.append((x, peak))
        pts.extend([(width, height), (0, height)])
        draw.polygon(pts, fill=color)

    # Meadow / river foreground.
    draw.rectangle((0, int(height * 0.70), width, height), fill=(79, 126, 65))
    river_left = int(width * (0.54 if portrait else 0.60))
    river_top = int(height * 0.67)
    river = [
        (river_left, river_top),
        (int(width * 0.78), river_top),
        (int(width * 0.91), height),
        (int(width * 0.56), height),
    ]
    draw.polygon(river, fill=(120, 176, 188))
    for k in range(8):
        yy = int(river_top + (height - river_top) * (k + 1) / 9)
        x1 = int(width * (0.60 + 0.015 * k))
        x2 = int(width * (0.76 + 0.02 * k))
        draw.line((x1, yy, x2, yy), fill=(190, 219, 211), width=max(1, width // 500))

    # Character geometry. Different scene index changes placement subtly.
    cx = int(width * (0.45 + (index % 3 - 1) * 0.035))
    head_y = int(height * (0.35 if portrait else 0.38))
    head_r = int(min(width, height) * (0.105 if portrait else 0.092))
    skin = (190, 132, 91)
    hair = (61, 39, 28)
    beard = (69, 43, 29)
    robe = (236, 224, 198)
    mantle = (135, 54, 54) if index % 4 == 1 else (201, 181, 147)

    # Halo glow behind head.
    halo_r = int(head_r * 1.55)
    draw.ellipse((cx-halo_r, head_y-halo_r, cx+halo_r, head_y+halo_r), fill=(248, 211, 130))

    # Body robe and mantle.
    shoulder_y = head_y + int(head_r * 0.82)
    body_bottom = int(height * (0.91 if portrait else 0.98))
    body_half = int(width * (0.27 if portrait else 0.18))
    draw.polygon([
        (cx-int(body_half*0.55), shoulder_y),
        (cx-int(body_half), body_bottom),
        (cx+int(body_half), body_bottom),
        (cx+int(body_half*0.55), shoulder_y),
    ], fill=robe)
    draw.polygon([
        (cx+int(head_r*0.45), shoulder_y),
        (cx+int(body_half*0.93), body_bottom),
        (cx+int(body_half*0.25), body_bottom),
        (cx+int(head_r*0.05), shoulder_y),
    ], fill=mantle)

    # Arms: one gentle open-hand gesture.
    arm_y = shoulder_y + int(head_r * 1.2)
    hand_side = -1 if index % 2 == 0 else 1
    elbow_x = cx + hand_side * int(body_half * 0.72)
    hand_x = cx + hand_side * int(body_half * 1.28)
    hand_y = arm_y - int(head_r * 0.20)
    arm_w = max(8, int(head_r * 0.34))
    draw.line((cx + hand_side*int(head_r*0.45), shoulder_y+int(head_r*0.4), elbow_x, arm_y, hand_x, hand_y), fill=robe, width=arm_w)
    hand_r = max(5, int(head_r * 0.17))
    draw.ellipse((hand_x-hand_r, hand_y-hand_r, hand_x+hand_r, hand_y+hand_r), fill=skin)

    # Hair mass, face, beard.
    hair_r = int(head_r * 1.10)
    draw.ellipse((cx-hair_r, head_y-hair_r, cx+hair_r, head_y+hair_r), fill=hair)
    face_rx = int(head_r * 0.73)
    face_ry = int(head_r * 0.88)
    draw.ellipse((cx-face_rx, head_y-face_ry, cx+face_rx, head_y+face_ry), fill=skin)
    beard_top = head_y + int(head_r * 0.30)
    draw.pieslice((cx-int(head_r*0.70), beard_top-int(head_r*0.12), cx+int(head_r*0.70), head_y+int(head_r*1.02)), 0, 180, fill=beard)
    draw.polygon([
        (cx-int(head_r*0.58), beard_top),
        (cx+int(head_r*0.58), beard_top),
        (cx+int(head_r*0.38), head_y+int(head_r*0.90)),
        (cx, head_y+int(head_r*1.08)),
        (cx-int(head_r*0.38), head_y+int(head_r*0.90)),
    ], fill=beard)

    # Eyes and brows.
    eye_y = head_y - int(head_r * 0.16)
    eye_dx = int(head_r * 0.28)
    eye_r = max(2, int(head_r * 0.055))
    for ex in (cx-eye_dx, cx+eye_dx):
        draw.ellipse((ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r), fill=(54, 47, 38))
        draw.line((ex-int(head_r*0.12), eye_y-int(head_r*0.13), ex+int(head_r*0.12), eye_y-int(head_r*0.10)), fill=hair, width=max(2, head_r//30))

    # Nose.
    draw.line((cx, head_y-int(head_r*0.05), cx-int(head_r*0.03), head_y+int(head_r*0.17)), fill=(151, 99, 73), width=max(2, head_r//32))

    # Mouth state gives a tiny speaking effect in the local fallback.
    mouth_y = head_y + int(head_r * 0.29)
    mouth_w = int(head_r * 0.27)
    if mouth_open <= 0:
        draw.arc((cx-mouth_w, mouth_y-int(head_r*0.04), cx+mouth_w, mouth_y+int(head_r*0.09)), 8, 172, fill=(97, 51, 43), width=max(2, head_r//24))
    else:
        mouth_h = int(head_r * (0.055 + 0.035 * min(2, mouth_open)))
        draw.ellipse((cx-mouth_w, mouth_y-mouth_h, cx+mouth_w, mouth_y+mouth_h), fill=(83, 42, 39))
        draw.arc((cx-mouth_w, mouth_y-mouth_h, cx+mouth_w, mouth_y+mouth_h), 5, 175, fill=(148, 79, 69), width=max(2, head_r//30))

    # A few warm particles for cinematic depth.
    for _ in range(30 if portrait else 22):
        px = rng.randrange(0, width)
        py = rng.randrange(int(height*0.12), int(height*0.88))
        rr = rng.randint(max(1, width//900), max(2, width//450))
        draw.ellipse((px-rr, py-rr, px+rr, py+rr), fill=(250, 220, 151))

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=94)
    return path


def make_local_speaking_clip(out: Path, duration: int, seed: int, index: int = 0) -> Path:
    """Create a keyless vertical clip where the original character visibly speaks.

    Four locally drawn mouth states are alternated at a restrained cadence. The
    animation is not phoneme-level lip sync; it is a reliable visible-speaking
    fallback paired with the actual narration track later in the pipeline.
    """
    width, height = 1080, 1920
    temp = out.parent / f"local_spiritual_{index + 1}"
    temp.mkdir(parents=True, exist_ok=True)
    states = [0, 1, 2, 1, 0, 1, 0, 2]
    images: list[Path] = []
    for state_index, mouth in enumerate(states):
        image = temp / f"state_{state_index}.png"
        make_spiritual_art(image, width, height, seed, index=index, mouth_open=mouth)
        images.append(image)

    frame_duration = 0.22
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
        "-t", str(duration), "-vf", "fps=30,setsar=1,eq=contrast=1.02:saturation=1.04:brightness=0.003",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(out),
    ], check=True)
    if not out.exists() or out.stat().st_size < 50_000:
        raise RuntimeError("El fallback espiritual local no produjo un clip valido.")
    return out
