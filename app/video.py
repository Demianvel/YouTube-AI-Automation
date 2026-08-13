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
W, H, FPS = 1080, 1920, 30


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


def _wrap(draw, text: str, font, max_width: int, max_lines: int = 4):
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
    return lines[:max_lines]


def _rounded_card(draw: ImageDraw.ImageDraw, box, radius=34, fill=(20, 31, 47), outline=(55, 75, 100)):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def _finance(frame: Image.Image, progress: float, meta: dict) -> None:
    """Premium vertical finance explainer: animated cards, metrics and scene-aware motion."""
    draw = ImageDraw.Draw(frame)
    seed = _seed(meta)
    scenes = meta.get("scenes") or []
    scene_count = max(1, len(scenes))
    scaled = min(0.999999, max(0.0, progress)) * scene_count
    scene_index = min(scene_count - 1, int(scaled))
    local = scaled - scene_index
    ease = local * local * (3 - 2 * local)

    # Ambient premium background accents.
    for i in range(7):
        phase = (seed % 97) * 0.01 + i * 0.83
        cx = int(W * (0.10 + (i % 4) * 0.27) + math.sin(progress * math.tau + phase) * 24)
        cy = int(260 + i * 225 + math.cos(progress * math.tau * 0.7 + phase) * 22)
        r = 34 + (i % 3) * 12
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(20 + i*3, 42 + i*3, 62 + i*3))

    # Header badge.
    _rounded_card(draw, (70, 76, 430, 150), radius=28, fill=(26, 43, 62), outline=(63, 88, 114))
    badge_font = _font(34, True)
    draw.text((100, 96), "DINERO CLARO", font=badge_font, fill=(235, 242, 249))

    # Main hook / title.
    hook = (meta.get("hook") or meta.get("title") or "Una idea clara").strip()
    title_font = _font(72, True)
    y = 205
    for line in _wrap(draw, hook, title_font, W - 140, max_lines=3):
        draw.text((70, y), line, font=title_font, fill=(247, 249, 252))
        y += 86

    # Central glass-style card.
    card_top = max(500, y + 45)
    card_bottom = min(H - 330, card_top + 820)
    _rounded_card(draw, (70, card_top, W-70, card_bottom), radius=44, fill=(18, 28, 43), outline=(65, 91, 119))

    # Animated bar chart varies by topic/scene.
    baseline = card_bottom - 150
    bar_area_h = min(500, card_bottom - card_top - 280)
    bar_w = 120
    gap = 64
    start_x = 135
    base_vals = [0.38, 0.61, 0.82, 0.70]
    for i, val in enumerate(base_vals):
        topic_shift = ((seed >> (i * 4)) & 7) / 60.0
        target = min(0.94, val + topic_shift + scene_index * 0.025)
        stagger = max(0.0, min(1.0, ease * 1.30 - i * 0.10))
        h = int(bar_area_h * target * stagger)
        x = start_x + i * (bar_w + gap)
        draw.rounded_rectangle((x, baseline-h, x+bar_w, baseline), radius=28,
                               fill=(49 + i*18, 137 + i*7, 193 - i*12))
        glow_h = max(10, int(h * 0.12))
        draw.rounded_rectangle((x+12, baseline-h+12, x+bar_w-12, baseline-h+12+glow_h), radius=16,
                               fill=(118 + i*12, 193, 230 - i*8))

    # Coin / decision indicators.
    coin_y = card_top + 120
    for i in range(3):
        pulse = 1.0 + 0.08 * math.sin((progress * 3.2 + i * 0.4) * math.tau)
        rr = int((42 + i * 5) * pulse)
        cx = W - 220 - i * 115
        draw.ellipse((cx-rr, coin_y-rr, cx+rr, coin_y+rr), fill=(229, 183 - i*10, 72 + i*8))
        draw.ellipse((cx-rr+8, coin_y-rr+8, cx+rr-8, coin_y+rr-8), outline=(255, 225, 139), width=4)

    # Scene progress markers.
    marker_y = H - 230
    usable = W - 140
    seg_w = (usable - (scene_count - 1) * 18) / scene_count
    for i in range(scene_count):
        x1 = 70 + i * (seg_w + 18)
        x2 = x1 + seg_w
        active = i < scene_index or (i == scene_index and local > 0.06)
        fill = (94, 184, 227) if active else (55, 70, 88)
        draw.rounded_rectangle((int(x1), marker_y, int(x2), marker_y + 18), radius=9, fill=fill)

    # Small scene caption from narration for a creator-like explainer feel.
    if scenes and scene_index < len(scenes):
        caption = " ".join(str(scenes[scene_index].get("narration") or "").split())
        if caption:
            cap_font = _font(38, False)
            cap_y = card_bottom + 55
            for line in _wrap(draw, caption, cap_font, W - 150, max_lines=2):
                draw.text((75, cap_y), line, font=cap_font, fill=(200, 211, 223))
                cap_y += 50


def _kids(frame: Image.Image, progress: float, meta: dict, seed: int) -> None:
    draw = ImageDraw.Draw(frame)
    t = progress * math.tau
    for i in range(5):
        cx = int((100 + i * 220 + progress * 150) % (W + 240)) - 120
        cy = 180 + (i % 2) * 120
        for dx, dy, r in [(-50, 10, 48), (0, -10, 64), (58, 12, 44)]:
            draw.ellipse((cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r), fill=(248, 251, 255))
    draw.rectangle((0, H - 500, W, H), fill=(109, 199, 106))
    bounce = int(math.sin(t * 2) * 28)
    cx, cy = W // 2, H - 760 + bounce
    draw.ellipse((cx - 215, cy - 200, cx + 215, cy + 215), fill=(255, 202, 79), outline=(239, 161, 51), width=12)
    draw.ellipse((cx - 105, cy - 50, cx - 45, cy + 10), fill=(35, 47, 64))
    draw.ellipse((cx + 45, cy - 50, cx + 105, cy + 10), fill=(35, 47, 64))
    smile_y = cy + 70
    draw.arc((cx - 80, smile_y - 45, cx + 80, smile_y + 65), 10, 170, fill=(120, 70, 55), width=10)
    for i in range(8):
        angle = t + i * math.tau / 8
        sx = int(cx + math.cos(angle) * (310 + (i % 3) * 26))
        sy = int(cy + math.sin(angle) * (275 + (i % 2) * 22))
        r = 10 + (i % 3) * 3
        draw.ellipse((sx-r, sy-r, sx+r, sy+r), fill=(255, 245, 150))


def _procedural(channel: dict, meta: dict, out: Path) -> None:
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
        base = _gradient((13, 22, 34), (6, 12, 21))
    silent = out.with_name("visual_only.mp4")
    command = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
        "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
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
    meta["render_quality"] = "1080x1920_30fps_premium"
    apply_audio(silent, out, channel, meta, duration, seed)


def _real_stock(channel: dict, metadata: dict, workdir: Path, final: Path) -> None:
    if os.getenv("PEXELS_API_KEY", "").strip():
        try:
            generate_pexels_short(channel, metadata, workdir, final, apply_audio)
            metadata["render_quality"] = "1080x1920_30fps_real_stock"
            return
        except Exception as exc:
            print(f"Pexels no disponible ({exc}); usando Wikimedia Commons.")
    generate_wikimedia_short(channel, metadata, workdir, final, apply_audio)
    metadata["render_quality"] = "1080x1920_30fps_real_commons"


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    final = workdir / "short.mp4"
    visual_mode = channel.get("visual_mode", "")

    if "kids" in visual_mode:
        try:
            generate_pollinations_kids_short(channel, metadata, workdir, final, apply_audio)
            metadata["render_quality"] = "generated_kids_premium"
            return final
        except Exception as exc:
            print(f"Generacion 3D externa no disponible ({exc}); usando fallback infantil local.")
            _procedural(channel, metadata, final)
            return final

    if "mixed_finance" in visual_mode:
        if _seed(metadata) % 2 == 0:
            _procedural(channel, metadata, final)
            metadata["visual_source"] = "animated_original_premium"
            return final
        try:
            _real_stock(channel, metadata, workdir, final)
            metadata["visual_source"] = "real_business_broll"
            return final
        except Exception as exc:
            print(f"B-roll real no disponible ({exc}); usando animacion financiera original premium.")
            _procedural(channel, metadata, final)
            metadata["visual_source"] = "animated_original_premium_fallback"
            return final

    if VIDEO_PROVIDER == "real_stock":
        _real_stock(channel, metadata, workdir, final)
    elif VIDEO_PROVIDER == "pexels":
        generate_pexels_short(channel, metadata, workdir, final, apply_audio)
    elif VIDEO_PROVIDER == "wikimedia":
        generate_wikimedia_short(channel, metadata, workdir, final, apply_audio)
    elif VIDEO_PROVIDER == "procedural":
        _procedural(channel, metadata, final)
    else:
        raise ValueError(f"VIDEO_PROVIDER no soportado: {VIDEO_PROVIDER}")
    return final
