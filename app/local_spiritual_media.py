from __future__ import annotations

import os
import random
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


LOCAL_MEDIA_ENGINE_VERSION = "dios-local-media-v1"
LOCAL_VOICE_PROFILE = "voz_de_luz_local_original_v1"
LOCAL_KOKORO_VOICE = "em_alex"


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def generate_original_spiritual_image(
    prompt: str,
    out: Path,
    seed: int,
    target_size: tuple[int, int] = (1080, 1920),
) -> str:
    """Generate an original spiritual/cinematic image entirely on the runner.

    No remote model, API, stock library or previous channel frame is used. The
    output is deterministic from a per-scene seed plus a nanosecond salt so two
    invocations never intentionally reuse the same source frame.
    """
    width, height = target_size
    unique_seed = int(seed) ^ int(time.time_ns() & 0xFFFFFFFF)
    rng = random.Random(unique_seed)

    palettes = (
        ((9, 23, 49), (78, 116, 151), (244, 190, 117)),
        ((18, 34, 49), (59, 92, 99), (221, 178, 118)),
        ((27, 20, 54), (88, 73, 126), (238, 174, 118)),
        ((8, 38, 52), (42, 103, 112), (235, 198, 129)),
        ((36, 33, 42), (102, 88, 93), (230, 184, 122)),
        ((20, 31, 26), (72, 105, 77), (238, 196, 127)),
    )
    top, middle, horizon_color = palettes[unique_seed % len(palettes)]
    horizon = int(height * rng.uniform(0.46, 0.63))

    image = Image.new("RGB", (width, height), top)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        if y <= horizon:
            t = y / max(1, horizon)
            color = tuple(_lerp(top[i], middle[i], t) for i in range(3))
        else:
            t = (y - horizon) / max(1, height - horizon)
            base = tuple(_lerp(middle[i], horizon_color[i], min(1.0, t * 0.55)) for i in range(3))
            color = tuple(max(0, int(c * (1.0 - 0.33 * t))) for c in base)
        draw.line((0, y, width, y), fill=color)

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    gx = rng.randint(int(width * 0.18), int(width * 0.82))
    gy = rng.randint(int(height * 0.13), int(height * 0.45))
    base_radius = max(24, int(min(width, height) * 0.24))
    for factor, alpha in ((1.0, 24), (0.66, 45), (0.35, 90), (0.15, 180)):
        radius = max(12, int(base_radius * factor))
        glow_draw.ellipse((gx - radius, gy - radius, gx + radius, gy + radius), fill=(255, 222, 164, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(max(16, int(min(width, height) * 0.038))))
    image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(image)

    for _ in range(95):
        x = rng.randrange(width)
        y = rng.randrange(max(1, horizon))
        r = rng.choice((1, 1, 1, 2, 2, 3))
        a = rng.randint(80, 190)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(a, a, min(255, a + 25)))

    mountain_layers = (
        (horizon + int(height * 0.035), (58, 73, 78)),
        (horizon + int(height * 0.09), (40, 58, 62)),
        (horizon + int(height * 0.15), (27, 43, 47)),
    )
    step = max(55, width // 12)
    for layer_index, (base_y, fill) in enumerate(mountain_layers):
        points = [(0, height)]
        x = -step
        while x <= width + step:
            peak = base_y - rng.randint(
                max(55, int(height * (0.05 + layer_index * 0.012))),
                max(90, int(height * (0.17 + layer_index * 0.02))),
            )
            points.append((x, peak))
            x += step
        points.extend(((width, height), (0, height)))
        draw.polygon(points, fill=fill)

    text = str(prompt or "").lower()
    watery = any(word in text for word in ("water", "river", "sea", "lake", "fjord", "océano", "oceano", "mar", "río", "rio"))
    if watery or rng.random() < 0.58:
        water_top = int(height * 0.70)
        draw.rectangle((0, water_top, width, height), fill=(21, 55, 67))
        for y in range(water_top + 10, height, max(12, height // 95)):
            span = rng.randint(max(40, width // 14), max(80, width // 3))
            x = rng.randint(-40, max(-39, width - 20))
            shade = rng.randint(72, 135)
            draw.line((x, y, min(width, x + span), y), fill=(shade, min(255, shade + 18), min(255, shade + 24)), width=rng.choice((1, 2, 3)))

    path_center = rng.randint(int(width * 0.35), int(width * 0.65))
    path_top = horizon + rng.randint(max(30, int(height * 0.045)), max(55, int(height * 0.11)))
    draw.polygon(
        [
            (path_center - max(8, width // 38), path_top),
            (path_center + max(8, width // 38), path_top),
            (int(width * 0.88), height),
            (int(width * 0.12), height),
        ],
        fill=(102, 92, 72) if not watery else (48, 92, 103),
    )

    if any(word in text for word in ("cross", "cruz", "jesus", "jesús", "cristo")):
        cx = rng.randint(int(width * 0.22), int(width * 0.78))
        cy = rng.randint(int(height * 0.48), int(height * 0.65))
        scale = rng.randint(max(60, height // 19), max(90, height // 13))
        stem = max(8, scale // 7)
        draw.rounded_rectangle((cx - stem, cy - scale, cx + stem, cy + scale), radius=max(3, stem // 2), fill=(34, 29, 24))
        draw.rounded_rectangle((cx - int(scale * 0.72), cy - stem * 2, cx + int(scale * 0.72), cy), radius=max(3, stem // 2), fill=(34, 29, 24))

    if any(word in text for word in ("bible", "biblia", "scroll", "libro")):
        bx = rng.randint(int(width * 0.12), int(width * 0.48))
        by = rng.randint(int(height * 0.69), int(height * 0.82))
        page_w = max(90, width // 5)
        page_h = max(70, height // 12)
        draw.polygon([(bx, by), (bx + page_w, by - page_h // 5), (bx + page_w - 8, by + page_h), (bx, by + page_h + 22)], fill=(224, 210, 174))
        draw.polygon([(bx + page_w, by - page_h // 5), (bx + page_w * 2, by), (bx + page_w * 2, by + page_h + 22), (bx + page_w - 8, by + page_h)], fill=(210, 196, 161))
        draw.line((bx + page_w, by - page_h // 6, bx + page_w - 8, by + page_h), fill=(108, 84, 62), width=max(2, width // 220))

    if any(word in text for word in ("church", "chapel", "iglesia", "capilla")):
        bx = rng.randint(int(width * 0.14), int(width * 0.60))
        by = rng.randint(int(height * 0.63), int(height * 0.77))
        body_w = rng.randint(max(120, width // 5), max(170, width // 3))
        body_h = rng.randint(max(100, height // 10), max(150, height // 7))
        draw.rectangle((bx, by, bx + body_w, by + body_h), fill=(67, 62, 56))
        draw.polygon([(bx - 24, by), (bx + body_w // 2, by - body_h // 2), (bx + body_w + 24, by)], fill=(51, 46, 43))
        tower_w = max(34, body_w // 5)
        tower_x = bx + body_w // 2 - tower_w // 2
        draw.rectangle((tower_x, by - body_h, tower_x + tower_w, by), fill=(67, 62, 56))
        draw.polygon([(tower_x - 10, by - body_h), (tower_x + tower_w // 2, by - body_h - body_h // 3), (tower_x + tower_w + 10, by - body_h)], fill=(51, 46, 43))

    if any(word in text for word in ("dove", "bird", "pájaro", "pajaro", "gorrión", "gorrion")):
        for _ in range(rng.randint(1, 4)):
            bx = rng.randint(max(40, width // 10), width - max(40, width // 10))
            by = rng.randint(max(50, height // 9), max(80, horizon - max(30, height // 20)))
            wing = rng.randint(max(14, width // 45), max(22, width // 25))
            draw.arc((bx - wing, by - 10, bx, by + 20), 195, 345, fill=(225, 228, 226), width=max(2, width // 180))
            draw.arc((bx, by - 10, bx + wing, by + 20), 195, 345, fill=(225, 228, 226), width=max(2, width // 180))

    for _ in range(70):
        x = rng.randrange(width)
        base = rng.randint(int(height * 0.87), height)
        length = rng.randint(max(22, height // 55), max(50, height // 13))
        bend = rng.randint(-max(10, width // 38), max(10, width // 38))
        draw.line((x, base, x + bend, base - length), fill=(19, 43, 35), width=rng.choice((2, 3, 4)))

    mist = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mist_draw = ImageDraw.Draw(mist)
    for _ in range(8):
        my = rng.randint(max(0, horizon - 30), int(height * 0.84))
        mh = rng.randint(max(12, height // 80), max(24, height // 27))
        mist_draw.ellipse((-width // 6, my - mh, width + width // 6, my + mh), fill=(220, 226, 220, rng.randint(10, 28)))
    mist = mist.filter(ImageFilter.GaussianBlur(max(12, min(width, height) // 42)))
    image = Image.alpha_composite(image.convert("RGBA"), mist).convert("RGB")

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in {".jpg", ".jpeg"}:
        image.save(out, format="JPEG", quality=94, optimize=True)
    else:
        image.save(out, format="PNG", optimize=True)

    return f"local_original_procedural_cinematic/seed={unique_seed}/{LOCAL_MEDIA_ENGINE_VERSION}"


def _master_local_voice(path: Path) -> None:
    temp = path.with_name(path.stem + ".local-master.wav")
    filters = (
        "highpass=f=55,"
        "lowpass=f=10800,"
        "equalizer=f=115:t=q:w=0.85:g=1.1,"
        "equalizer=f=190:t=q:w=0.95:g=0.45,"
        "equalizer=f=2850:t=q:w=1.0:g=0.55,"
        "acompressor=threshold=-22dB:ratio=1.5:attack=16:release=170:makeup=1.1,"
        "loudnorm=I=-16.5:TP=-1.5:LRA=5.5"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-af", filters, "-ar", "48000", "-ac", "1", str(temp)],
        check=True,
    )
    if not temp.exists() or temp.stat().st_size < 1000:
        raise RuntimeError("El master local de voz no produjo un archivo valido.")
    temp.replace(path)


def _kokoro_voice(path: Path, text: str) -> str:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="e")
    try:
        speed = float(os.getenv("LOCAL_KOKORO_SPEED", "0.76"))
    except ValueError:
        speed = 0.76
    speed = max(0.72, min(0.84, speed))

    rendered: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(text, voice=LOCAL_KOKORO_VOICE, speed=speed):
        if audio is not None and len(audio):
            rendered.append(np.asarray(audio, dtype=np.float32))
    if not rendered:
        raise RuntimeError("Kokoro local no genero audio.")
    combined = np.concatenate(rendered)
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    if peak > 0.98:
        combined = combined * (0.96 / peak)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), combined, 24000, subtype="PCM_16")
    return f"local_kokoro:{LOCAL_KOKORO_VOICE}:speed={speed:.2f}:{LOCAL_VOICE_PROFILE}:{LOCAL_MEDIA_ENGINE_VERSION}"


def _espeak_voice(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        speed = int(os.getenv("LOCAL_ESPEAK_WPM", "132"))
    except ValueError:
        speed = 132
    speed = max(124, min(138, speed))
    subprocess.run(
        [
            "espeak-ng", "-v", "es-419", "-s", str(speed), "-p", "34", "-a", "165",
            "-g", "2", "-w", str(path), text,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("espeak-ng local no genero audio.")
    return f"local_espeak_ng:es-419:wpm={speed}:{LOCAL_VOICE_PROFILE}:{LOCAL_MEDIA_ENGINE_VERSION}"


def make_local_spiritual_voice(path: Path, text: str) -> str:
    """Generate narration without any paid/inference API.

    Kokoro is preferred for naturalness. Its local cadence is intentionally tuned
    for the channel's 60-second narration word budget. If its model assets are
    unavailable, espeak-ng is installed by the workflow and guarantees a
    no-network fallback with a slower, continuity-safe speaking rate.
    """
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        raise RuntimeError("No hay texto para la voz local.")

    try:
        used = _kokoro_voice(path, clean)
    except Exception as exc:
        print(f"Kokoro local no estuvo disponible ({exc}); usando voz local espeak-ng sin cuota.")
        used = _espeak_voice(path, clean)

    _master_local_voice(path)
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("El generador local de voz produjo un archivo invalido.")
    return used
