from __future__ import annotations

import hashlib
import math
import os
import random
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from .dios_visual_integrity import fingerprint_image, fresh_against_persisted_history

ENGINE_VERSION = "dhh-sovereign-visual-diversity-v3"


def scene_index_from_path(path: Path) -> int:
    match = re.search(r"spiritual_generated_(\d+)", path.stem)
    if match:
        return max(1, int(match.group(1)))
    digits = re.findall(r"\d+", path.stem)
    return max(1, int(digits[-1])) if digits else 1


def _mixed_seed(seed: int, scene_index: int, attempt: int) -> int:
    run = os.getenv("GITHUB_RUN_ID", "local")
    raw = f"{ENGINE_VERSION}|{run}|{int(seed)}|{scene_index}|{attempt}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16) & 0x7FFFFFFF


def _family(prompt: str, scene_index: int, seed: int) -> str:
    low = str(prompt or "").lower()
    if any(token in low for token in ("aurora", "norway", "norwegian", "fjord", "arctic", "lofoten", "tromso")):
        return "aurora_fjord"
    if any(token in low for token in ("ocean", "sea", "water", "river", "lake", "storm")):
        return "water_light"
    if any(token in low for token in ("forest", "olive", "tree", "garden", "wheat", "field")):
        return "living_creation"
    if any(token in low for token in ("desert", "road", "path", "wilderness")):
        return "hope_path"
    if any(token in low for token in ("bible", "scripture", "cross", "dove", "lamp", "faith")):
        return "faith_symbol"
    families = ("aurora_fjord", "water_light", "living_creation", "hope_path", "faith_symbol", "mountain_dawn")
    return families[(scene_index * 7 + seed) % len(families)]


def _gradient(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int], rng: random.Random) -> Image.Image:
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    a = np.array(top, dtype=np.float32)[None, None, :]
    b = np.array(bottom, dtype=np.float32)[None, None, :]
    rgb = a * (1.0 - y) + b * y
    rgb = np.repeat(rgb, width, axis=1)
    noise = rng.normalvariate(0.0, 1.0)
    texture = np.random.default_rng(rng.randrange(1, 2**31 - 1)).normal(0.0, 2.6 + abs(noise), (height, width, 1))
    rgb = np.clip(rgb + texture, 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def _draw_mountains(draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random, *, snowy: bool) -> None:
    for layer in range(4):
        base = int(height * (0.54 + layer * 0.055))
        peaks = 5 + layer * 2
        pts: list[tuple[int, int]] = [(0, base)]
        peak_points: list[tuple[int, int]] = []
        for i in range(peaks + 1):
            x = int(width * i / peaks)
            variance = int(height * (0.09 + rng.random() * 0.11) / (1.0 + layer * 0.45))
            yy = base - variance
            pts.append((x, yy))
            peak_points.append((x, yy))
        pts.extend([(width, height), (0, height)])
        shade = 36 + layer * 16
        color = (shade, shade + 16, shade + 25)
        draw.polygon(pts, fill=color)
        if snowy and layer < 3:
            for x, yy in peak_points[1:-1]:
                cap = max(14, int(width * (0.035 + rng.random() * 0.02)))
                draw.polygon([(x, yy), (x - cap, yy + cap), (x + cap, yy + cap)], fill=(215, 226, 230))


def _draw_water(draw: ImageDraw.ImageDraw, width: int, height: int, rng: random.Random, *, dark: bool = False) -> None:
    horizon = int(height * 0.64)
    draw.rectangle((0, horizon, width, height), fill=(24, 61, 78) if dark else (67, 126, 145))
    for i in range(55):
        yy = rng.randrange(horizon + 4, height)
        span = rng.randrange(max(10, width // 18), max(18, width // 4))
        x = rng.randrange(-span, width)
        alpha_color = (112, 170, 184) if dark else (154, 205, 210)
        draw.line((x, yy, min(width, x + span), yy), fill=alpha_color, width=1 + (i % 2))


def _aurora_layer(width: int, height: int, rng: random.Random) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for band in range(4):
        pts: list[tuple[int, int]] = []
        base = int(height * (0.17 + band * 0.055))
        amp = int(height * (0.025 + rng.random() * 0.03))
        phase = rng.random() * math.pi * 2
        for x in range(-20, width + 21, 18):
            yy = base + int(math.sin(x / 75.0 + phase) * amp)
            pts.append((x, yy))
        color = (78, 255, 172, 72) if band % 2 == 0 else (126, 116, 255, 48)
        draw.line(pts, fill=color, width=max(9, width // 28))
    return layer.filter(ImageFilter.GaussianBlur(radius=max(9, width // 55)))


def _light_rays(width: int, height: int, rng: random.Random) -> Image.Image:
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    source_x = rng.randrange(int(width * 0.18), int(width * 0.82))
    source_y = int(height * 0.12)
    for _ in range(7):
        end_x = source_x + rng.randrange(-width // 2, width // 2)
        draw.polygon(
            [(source_x - 3, source_y), (source_x + 3, source_y), (end_x + width // 9, height), (end_x - width // 9, height)],
            fill=(255, 221, 152, rng.randrange(10, 24)),
        )
    return layer.filter(ImageFilter.GaussianBlur(radius=max(5, width // 80)))


def _cinematic_symbolic_base(width: int, height: int, seed: int, prompt: str, scene_index: int) -> tuple[Image.Image, str]:
    rng = random.Random(seed)
    family = _family(prompt, scene_index, seed)

    if family == "aurora_fjord":
        image = _gradient(width, height, (8, 17, 38), (59, 91, 113), rng)
        image = Image.alpha_composite(image.convert("RGBA"), _aurora_layer(width, height, rng)).convert("RGB")
        draw = ImageDraw.Draw(image)
        _draw_mountains(draw, width, height, rng, snowy=True)
        _draw_water(draw, width, height, rng, dark=True)
    elif family == "water_light":
        image = _gradient(width, height, (69, 104, 143), (236, 181, 105), rng)
        draw = ImageDraw.Draw(image)
        _draw_mountains(draw, width, height, rng, snowy=False)
        _draw_water(draw, width, height, rng)
        image = Image.alpha_composite(image.convert("RGBA"), _light_rays(width, height, rng)).convert("RGB")
    elif family == "living_creation":
        image = _gradient(width, height, (70, 107, 132), (224, 184, 111), rng)
        draw = ImageDraw.Draw(image)
        horizon = int(height * 0.58)
        draw.rectangle((0, horizon, width, height), fill=(47, 91, 55))
        for _ in range(65):
            x = rng.randrange(0, width)
            trunk_top = rng.randrange(int(height * 0.28), horizon)
            crown = rng.randrange(max(12, width // 35), max(24, width // 16))
            draw.line((x, horizon + rng.randrange(0, height // 5), x, trunk_top), fill=(51, 47, 34), width=max(2, width // 170))
            draw.ellipse((x - crown, trunk_top - crown, x + crown, trunk_top + crown), fill=(39, rng.randrange(83, 120), 52))
        image = Image.alpha_composite(image.convert("RGBA"), _light_rays(width, height, rng)).convert("RGB")
    elif family == "hope_path":
        image = _gradient(width, height, (56, 88, 126), (238, 181, 103), rng)
        draw = ImageDraw.Draw(image)
        _draw_mountains(draw, width, height, rng, snowy=False)
        ground = int(height * 0.66)
        draw.rectangle((0, ground, width, height), fill=(126, 101, 66))
        center = rng.randrange(int(width * 0.38), int(width * 0.62))
        draw.polygon([(center - 10, ground), (center + 10, ground), (int(width * 0.86), height), (int(width * 0.14), height)], fill=(198, 169, 121))
        image = Image.alpha_composite(image.convert("RGBA"), _light_rays(width, height, rng)).convert("RGB")
    elif family == "faith_symbol":
        image = _gradient(width, height, (42, 71, 105), (236, 178, 94), rng)
        draw = ImageDraw.Draw(image)
        _draw_mountains(draw, width, height, rng, snowy=False)
        hill_y = int(height * 0.73)
        draw.ellipse((-width // 3, hill_y, width + width // 3, height + height // 4), fill=(45, 65, 48))
        cx = rng.randrange(int(width * 0.34), int(width * 0.66))
        top = int(height * 0.43)
        bottom = int(height * 0.76)
        bar_y = int(height * 0.54)
        thick = max(5, width // 55)
        draw.rectangle((cx - thick, top, cx + thick, bottom), fill=(58, 42, 30))
        draw.rectangle((cx - width // 11, bar_y - thick, cx + width // 11, bar_y + thick), fill=(58, 42, 30))
        image = Image.alpha_composite(image.convert("RGBA"), _light_rays(width, height, rng)).convert("RGB")
    else:
        image = _gradient(width, height, (71, 111, 153), (242, 186, 104), rng)
        draw = ImageDraw.Draw(image)
        _draw_mountains(draw, width, height, rng, snowy=True)
        foreground = int(height * 0.72)
        draw.rectangle((0, foreground, width, height), fill=(58, 97, 64))
        image = Image.alpha_composite(image.convert("RGBA"), _light_rays(width, height, rng)).convert("RGB")

    # Atmospheric bokeh makes every seed materially different without text or logos.
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for _ in range(32):
        radius = rng.randrange(max(2, width // 220), max(5, width // 70))
        x = rng.randrange(-radius, width + radius)
        y = rng.randrange(0, height)
        odraw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 225, 166, rng.randrange(6, 22)))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(2, width // 170)))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    return image, family


def _feather_mask(size: tuple[int, int], seed: int) -> Image.Image:
    width, height = size
    rng = random.Random(seed)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    margin_x = max(6, width // 45)
    margin_y = max(6, height // 55)
    draw.rounded_rectangle(
        (margin_x, margin_y, width - margin_x, height - margin_y),
        radius=max(24, width // 10),
        fill=236,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(16, width // 18)))
    # Subtle asymmetric vignette keeps repeated character identity but changes composition.
    if rng.random() > 0.5:
        mask = ImageOps.mirror(mask)
    return mask


def _reference_composite(reference: Path, width: int, height: int, seed: int, prompt: str, scene_index: int) -> tuple[Image.Image, str]:
    background, family = _cinematic_symbolic_base(width, height, seed ^ 0x51A9, prompt, scene_index)
    rng = random.Random(seed)
    with Image.open(reference) as opened:
        source = ImageOps.exif_transpose(opened).convert("RGB")
        panel_w = int(width * rng.uniform(0.70, 0.84))
        panel_h = int(height * rng.uniform(0.62, 0.78))
        panel = ImageOps.fit(
            source,
            (panel_w, panel_h),
            method=Image.Resampling.LANCZOS,
            centering=(rng.uniform(0.44, 0.56), rng.uniform(0.38, 0.54)),
        )
        panel = ImageEnhance.Contrast(panel).enhance(rng.uniform(1.02, 1.11))
        panel = ImageEnhance.Color(panel).enhance(rng.uniform(0.94, 1.08))
        panel = ImageEnhance.Brightness(panel).enhance(rng.uniform(0.94, 1.04))
        mask = _feather_mask(panel.size, seed)
        x = int((width - panel_w) * rng.uniform(0.20, 0.80))
        y = int(height * rng.uniform(0.13, 0.24))
        frame = background.copy()
        frame.paste(panel, (x, y), mask)

    # Warm cinematic grade and edge vignette.
    vignette = Image.new("L", (width, height), 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse((-width // 3, -height // 5, width + width // 3, height + height // 5), fill=225)
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=max(25, width // 18)))
    dark = Image.new("RGB", (width, height), (10, 14, 20))
    frame = Image.composite(frame, dark, vignette)
    frame = ImageEnhance.Sharpness(frame).enhance(1.06)
    return frame, family


def _current_dhashes(out: Path) -> list[str]:
    values: list[str] = []
    for candidate in sorted(out.parent.glob("spiritual_generated_*.jpg")):
        if candidate == out or not candidate.exists():
            continue
        try:
            values.append(fingerprint_image(candidate)["dhash"])
        except Exception:
            continue
    return values


def render_unique_scene(
    out: Path,
    prompt: str,
    seed: int,
    *,
    references: list[Path],
    width: int,
    height: int,
    max_attempts: int = 9,
) -> str:
    """Render a unique local cinematic scene and self-check it before video assembly.

    Scene 1 keeps the recurring human Jesus representation through a feathered
    reference composite. Remaining scenes are original local symbolic/nature
    renders, which makes a 6-scene Short visually diverse without consuming a
    remote image/video inference service.
    """
    scene_index = scene_index_from_path(out)
    use_reference = scene_index == 1 and bool(references)
    current = _current_dhashes(out)
    nearest_seen = -1

    for attempt in range(max_attempts):
        candidate_seed = _mixed_seed(seed, scene_index, attempt)
        if use_reference:
            reference = references[candidate_seed % len(references)]
            image, family = _reference_composite(reference, width, height, candidate_seed, prompt, scene_index)
            source = f"reference-composite/reference:{reference.name}"
        else:
            image, family = _cinematic_symbolic_base(width, height, candidate_seed, prompt, scene_index)
            source = "procedural-symbolic-original"

        image = image.resize((width, height), Image.Resampling.LANCZOS)
        image = ImageEnhance.Contrast(image).enhance(1.035)
        image = ImageEnhance.Sharpness(image).enhance(1.04)
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out, format="JPEG", quality=95, subsampling=0, optimize=True)

        fresh, signature, distance = fresh_against_persisted_history(out, current)
        nearest_seen = distance
        if fresh:
            return (
                f"{ENGINE_VERSION}/{source}/family:{family}/scene:{scene_index}/"
                f"seed:{candidate_seed}/fresh-distance:{distance}/dhash:{signature['dhash']}"
            )

    raise RuntimeError(
        f"FRESH_VISUAL_GENERATION: no se logro una escena local suficientemente distinta "
        f"para scene={scene_index} despues de {max_attempts} intentos; distancia={nearest_seen}."
    )
