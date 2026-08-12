from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

W, H = 1280, 720


def _font(size: int, bold: bool = True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _extract(video: Path, second: int, out: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-ss", str(second), "-i", str(video),
            "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
            str(out),
        ],
        check=True,
    )


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int = 3) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            current = trial
        elif current:
            lines.append(current)
            current = word
            if len(lines) >= max_lines - 1:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines[:max_lines]


def _render(frame: Path, text: str, out: Path, variant: int) -> None:
    img = Image.open(frame).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.06)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Strong but clean contrast block; each variant changes placement.
    if variant == 0:
        box = (35, 360, 880, 680)
    elif variant == 1:
        box = (400, 55, 1245, 380)
    else:
        box = (35, 60, 910, 390)
    draw_overlay.rounded_rectangle(box, radius=34, fill=(0, 0, 0, 155))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    font = _font(72, True)
    small = _font(31, True)
    clean_text = " ".join(str(text or "").strip().split())[:90]
    lines = _wrap(draw, clean_text, font, box[2] - box[0] - 70, max_lines=3)
    total_h = len(lines) * 88
    y = box[1] + max(30, (box[3] - box[1] - total_h) // 2)
    for line in lines:
        draw.text((box[0] + 35, y), line, font=font, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0))
        y += 88

    # Tiny brand-neutral marker for visual hierarchy, not a logo.
    draw.rounded_rectangle((W - 205, H - 72, W - 28, H - 24), radius=18, fill=(255, 255, 255))
    draw.text((W - 186, H - 64), "VIDEO 5 MIN", font=small, fill=(18, 18, 18))

    img.save(out, "JPEG", quality=91, optimize=True)
    if out.stat().st_size > 1_900_000:
        img.save(out, "JPEG", quality=82, optimize=True)


def generate_thumbnail_variants(video: Path, metadata: dict, workdir: Path) -> list[Path]:
    texts = metadata.get("thumbnail_texts") or []
    title_variants = metadata.get("title_variants") or []
    fallback = metadata.get("title") or "Video nuevo"
    while len(texts) < 3:
        idx = len(texts)
        texts.append(title_variants[idx] if idx < len(title_variants) else fallback)

    seconds = [38, 148, 258]
    outputs: list[Path] = []
    for index in range(3):
        frame = workdir / f"thumbnail_frame_{index + 1}.jpg"
        out = workdir / f"thumbnail_{index + 1}.jpg"
        _extract(video, seconds[index], frame)
        _render(frame, texts[index], out, index)
        frame.unlink(missing_ok=True)
        outputs.append(out)
    metadata["thumbnail_variants"] = [str(p) for p in outputs]
    return outputs
