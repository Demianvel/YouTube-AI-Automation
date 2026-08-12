from __future__ import annotations

import hashlib
import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .audio import apply_audio
from .botanical import draw_plant
from .pexels_video import generate_pexels_short
from .pollinations_image import generate_pollinations_kids_short
from .wikimedia_video import generate_wikimedia_short

VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "real_stock").lower().strip()
W, H, FPS = 720, 1280, 15


def _font(size: int, bold: bool = False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _seed(meta: dict) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{meta.get('hook','')}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        draw.line((0, y, W, y), fill=color)
    return img


def _wrap(draw, text: str, font, max_width: int):
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            current = trial
        elif current:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:5]


def _finance(frame: Image.Image, progress: float, meta: dict) -> None:
    draw = ImageDraw.Draw(frame)
    baseline, width, gap, start = H - 250, 105, 55, 90
    for i, val in enumerate([.44, .66, .88, .76]):
        local = max(0, min(1, progress * 1.4 - i * .08))
        height, x = int(520 * val * local), start + i * (width + gap)
        draw.rounded_rectangle((x, baseline - height, x + width, baseline), radius=22, fill=(54 + i * 18, 142, 190 - i * 14))
    hook = (meta.get("hook") or meta.get("title") or "Dinero claro").strip()
    font = _font(50, True)
    y = 90
    for line in _wrap(draw, hook, font, W - 100):
        box = draw.textbbox((0, 0), line, font=font)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), line, font=font, fill=(245, 248, 252))
        y += 62


def _kids(frame: Image.Image, progress: float, meta: dict, seed: int) -> None:
    """Bright local fallback; primary EnViKids path uses generated images."""
    draw = ImageDraw.Draw(frame)
    t = progress * math.tau
    # soft clouds
    for i in range(5):
        cx = int((80 + i * 150 + progress * 100) % (W + 180)) - 90
        cy = 130 + (i % 2) * 85
        for dx, dy, r in [(-35, 8, 34), (0, -7, 45), (40, 9, 31)]:
            draw.ellipse((cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r), fill=(248, 251, 255))
    # ground
    draw.rectangle((0, H - 330, W, H), fill=(109, 199, 106))
    # cute fictional round character
    bounce = int(math.sin(t * 2) * 20)
    cx, cy = W // 2, H - 520 + bounce
    draw.ellipse((cx - 145, cy - 135, cx + 145, cy + 145), fill=(255, 202, 79), outline=(239, 161, 51), width=8)
    draw.ellipse((cx - 72, cy - 35, cx - 30, cy + 7), fill=(35, 47, 64))
    draw.ellipse((cx + 30, cy - 35, cx + 72, cy + 7), fill=(35, 47, 64))
    smile_y = cy + 45
    draw.arc((cx - 55, smile_y - 30, cx + 55, smile_y + 45), 10, 170, fill=(120, 70, 55), width=7)
    # moving stars/sparkles
    for i in range(8):
        angle = t + i * math.tau / 8
        sx = int(cx + math.cos(angle) * (210 + (i % 3) * 18))
        sy = int(cy + math.sin(angle) * (185 + (i % 2) * 15))
        r = 7 + (i % 3) * 2
        draw.ellipse((sx-r, sy-r, sx+r, sy+r), fill=(255, 245, 150))


def _procedural(channel: dict, meta: dict, out: Path) -> None:
    """Local fallback. Production prefers real stock or generated media."""
    duration = int(channel["scenes_per_short"]) * int(channel["scene_seconds"])
    frames, seed = duration * FPS, _seed(meta)
    visual_mode = channel.get("visual_mode", "")
    botanical = "botanical" in visual_mode
    kids = "kids" in visual_mode
    if botanical:
        base = _gradient((150, 211, 229), (229, 242, 210))
    elif kids:
        base = _gradient((108, 196, 255), (237, 249, 255))
    else:
        base = _gradient((17, 27, 40), (9, 16, 27))
    silent = out.with_name("visual_only.mp4")
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent),
    ]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for n in range(frames):
            progress = n / max(1, frames - 1)
            frame = base.copy()
            if botanical:
                draw_plant(frame, progress, seed, n, meta, W, H)
            elif kids:
                _kids(frame, progress, meta, seed)
            else:
                _finance(frame, progress, meta)
            if not proc.stdin:
                raise RuntimeError("ffmpeg cerro la entrada antes de tiempo")
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg procedural renderer fallo")
    apply_audio(silent, out, channel, meta, duration, seed)


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    final = workdir / "short.mp4"
    visual_mode = channel.get("visual_mode", "")

    if "kids" in visual_mode:
        try:
            generate_pollinations_kids_short(channel, metadata, workdir, final, apply_audio)
            return final
        except Exception as exc:
            print(f"Generacion 3D externa no disponible ({exc}); usando fallback infantil local.")
            _procedural(channel, metadata, final)
            return final

    if VIDEO_PROVIDER == "real_stock":
        if os.getenv("PEXELS_API_KEY", "").strip():
            try:
                generate_pexels_short(channel, metadata, workdir, final, apply_audio)
                return final
            except Exception as exc:
                print(f"Pexels no disponible ({exc}); usando Wikimedia Commons.")
        generate_wikimedia_short(channel, metadata, workdir, final, apply_audio)
    elif VIDEO_PROVIDER == "pexels":
        generate_pexels_short(channel, metadata, workdir, final, apply_audio)
    elif VIDEO_PROVIDER == "wikimedia":
        generate_wikimedia_short(channel, metadata, workdir, final, apply_audio)
    elif VIDEO_PROVIDER == "procedural":
        _procedural(channel, metadata, final)
    else:
        raise ValueError(f"VIDEO_PROVIDER no soportado: {VIDEO_PROVIDER}")
    return final
