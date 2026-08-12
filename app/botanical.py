from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

PLANT_PROFILES = {
    "girasol": "sunflower",
    "tomate": "tomato",
    "poroto": "bean",
    "frijol": "bean",
    "maiz": "corn",
    "maíz": "corn",
    "frutilla": "strawberry",
    "fresa": "strawberry",
    "albahaca": "basil",
    "arveja": "pea",
    "guisante": "pea",
    "calabaza": "pumpkin",
    "zapallo": "pumpkin",
    "lavanda": "lavender",
    "rabano": "radish",
    "rábano": "radish",
}


def plant_profile(meta: dict) -> str:
    text = f"{meta.get('topic','')} {meta.get('title','')}".lower()
    for key, profile in PLANT_PROFILES.items():
        if key in text:
            return profile
    return "bean"


def _leaf(frame: Image.Image, x: int, y: int, size: int, angle: float, tone=(48, 142, 66)) -> None:
    sw, sh = max(30, size * 2), max(20, size)
    leaf = Image.new("RGBA", (sw + 28, sh + 28), (0, 0, 0, 0))
    d = ImageDraw.Draw(leaf)
    d.ellipse(
        (12, 12, sw + 12, sh + 12),
        fill=(*tone, 255),
        outline=(25, 92, 39, 255),
        width=max(2, size // 14),
    )
    d.arc(
        (22, 16, sw + 2, sh - 4),
        190,
        345,
        fill=(98, 190, 105, 220),
        width=max(2, size // 18),
    )
    d.line(
        (18, sh // 2 + 12, sw + 6, sh // 2 + 12),
        fill=(32, 105, 44, 220),
        width=max(2, size // 18),
    )
    leaf = leaf.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    frame.paste(leaf, (int(x - leaf.width / 2), int(y - leaf.height / 2)), leaf)


def _sphere(d: ImageDraw.ImageDraw, x: int, y: int, r: int, base, shadow=None) -> None:
    if shadow is None:
        shadow = tuple(max(0, int(c * 0.58)) for c in base)
    d.ellipse((x-r+5, y-r+7, x+r+7, y+r+9), fill=shadow)
    d.ellipse((x-r, y-r, x+r, y+r), fill=base)
    hr = max(3, r // 5)
    d.ellipse(
        (x-r//3-hr, y-r//3-hr, x-r//3+hr, y-r//3+hr),
        fill=tuple(min(255, c + 65) for c in base),
    )


def _roots(d: ImageDraw.ImageDraw, cx: int, sy: int, progress: float, seed: int) -> None:
    rp = min(1.0, max(0.0, progress))
    main_len = int(315 * rp)
    points = []
    for i in range(34):
        frac = i / 33
        x = cx + int(math.sin(frac * 8 + seed % 11) * (10 + 18 * frac))
        y = sy + int(main_len * frac)
        points.append((x, y))
    if len(points) > 1:
        d.line(points, fill=(220, 212, 166), width=10)
    rng = random.Random(seed)
    for j in range(10):
        frac = 0.18 + j * 0.065
        if frac > rp:
            break
        idx = min(len(points) - 1, int(frac * (len(points) - 1)))
        x, y = points[idx]
        side = -1 if j % 2 == 0 else 1
        length = int((45 + rng.randrange(55)) * rp)
        d.line((x, y, x + side * length, y + int(length * .55)), fill=(206, 199, 151), width=5)


def _mature_feature(frame: Image.Image, profile: str, cx: int, soil: int, top: int, sp: float, seed: int) -> None:
    if sp < 0.76:
        return
    d = ImageDraw.Draw(frame)
    q = min(1.0, (sp - 0.76) / 0.24)

    if profile == "sunflower":
        fy = max(150, top + 50)
        r = int(30 + 78 * q)
        for p in range(14):
            a = p * 2 * math.pi / 14
            px, py = cx + int(math.cos(a) * r * .72), fy + int(math.sin(a) * r * .72)
            pr = max(12, int(r * .34))
            d.ellipse((px-pr, py-pr, px+pr, py+pr), fill=(248, 191, 44), outline=(215, 142, 20), width=3)
        _sphere(d, cx, fy, max(18, int(r * .48)), (105, 72, 38), (64, 43, 24))

    elif profile == "tomato":
        for i in range(5):
            x = cx + (-1 if i % 2 == 0 else 1) * (65 + (i % 3) * 28)
            y = soil - 140 - i * 58
            r = int((20 + (i % 2) * 6) * q)
            if r > 3:
                _sphere(d, x, y, r, (210, 48, 42))
                d.line((x, y-r, x, y-r-18), fill=(45, 118, 48), width=5)

    elif profile == "strawberry":
        for i in range(4):
            x = cx + (-1 if i % 2 == 0 else 1) * (80 + i * 14)
            y = soil - 85 - i * 52
            r = int((18 + (i % 2) * 4) * q)
            if r > 3:
                _sphere(d, x, y, r, (202, 42, 48))

    elif profile == "corn":
        cob_h = int(150 * q)
        cob_w = int(50 * q)
        if cob_h > 10:
            x, y = cx + 48, soil - 260
            d.rounded_rectangle(
                (x-cob_w//2, y-cob_h//2, x+cob_w//2, y+cob_h//2),
                radius=max(6, cob_w//3),
                fill=(236, 199, 69),
                outline=(169, 139, 42),
                width=4,
            )

    elif profile in {"bean", "pea"}:
        for i in range(5):
            side = -1 if i % 2 == 0 else 1
            x = cx + side * (72 + (i % 2) * 25)
            y = soil - 130 - i * 75
            w = int(58 * q)
            h = int(18 * q)
            if w > 8:
                d.rounded_rectangle(
                    (x-w, y-h, x+w, y+h),
                    radius=max(3, h),
                    fill=(62, 153, 67),
                    outline=(35, 101, 42),
                    width=3,
                )

    elif profile == "pumpkin":
        r = int(74 * q)
        if r > 8:
            x, y = cx + 105, soil - r + 10
            _sphere(d, x, y, r, (226, 113, 28), (153, 69, 20))

    elif profile == "lavender":
        for side in (-1, 0, 1):
            x = cx + side * 55
            d.line((x, soil-90, x, top+70), fill=(61, 123, 62), width=6)
            for j in range(8):
                yy = top + 55 + j * 20
                rr = max(4, int(9 * q))
                _sphere(d, x + (j % 2) * 5, yy, rr, (118, 79, 166), (75, 47, 112))

    elif profile == "radish":
        r = int(56 * q)
        if r > 8:
            _sphere(d, cx, soil + 8, r, (195, 51, 70), (125, 34, 49))

    elif profile == "basil":
        for i in range(6):
            side = -1 if i % 2 == 0 else 1
            _leaf(frame, cx + side * 80, soil - 150 - i * 65, int(55 * q + 20), -25 * side, (50, 150, 70))


def draw_plant(frame: Image.Image, progress: float, seed: int, frame_no: int, meta: dict, width: int, height: int) -> None:
    d = ImageDraw.Draw(frame)
    soil = int(height * 0.60)
    profile = plant_profile(meta)

    for i in range(8):
        x = 40 + i * 95 + int(math.sin(seed + i) * 15)
        r = 45 + (i % 3) * 18
        d.ellipse((x-r, 230-r, x+r, 230+r), fill=(190, 226, 185))

    d.rectangle((0, soil, width, height), fill=(78, 52, 34))
    rng = random.Random(seed + frame_no // 10)
    for _ in range(70):
        x, y, r = rng.randrange(width), rng.randrange(soil, height), rng.randrange(1, 5)
        tone = rng.choice([(102, 72, 46), (119, 82, 51), (91, 63, 41)])
        d.ellipse((x-r, y-r, x+r, y+r), fill=tone)

    cx, sy = width // 2, soil + 72
    shadow_w = int(75 + progress * 120)
    d.ellipse((cx-shadow_w, soil-12, cx+shadow_w, soil+30), fill=(58, 42, 30))

    seed_scale = max(.18, 1 - progress * .86)
    sw, sh = int(78 * seed_scale), int(44 * seed_scale)
    if progress < .43:
        d.ellipse((cx-sw+8, sy-sh+9, cx+sw+10, sy+sh+11), fill=(72, 43, 25))
        d.ellipse((cx-sw, sy-sh, cx+sw, sy+sh), fill=(137, 87, 46), outline=(82, 48, 27), width=5)
        d.arc((cx-sw//2, sy-sh//2, cx+sw//2, sy+sh//2), 195, 340, fill=(192, 132, 74), width=4)

    if progress > .06:
        _roots(d, cx, sy, min(1, (progress-.06)/.34), seed)

    if progress <= .18:
        return

    sp = min(1, (progress - .18) / .64)
    stem_target = {
        "corn": 690, "sunflower": 650, "tomato": 540, "lavender": 500,
        "pumpkin": 270, "strawberry": 230, "radish": 280, "basil": 430,
        "bean": 500, "pea": 470,
    }.get(profile, 500)
    stem_h = int(stem_target * sp)
    top = soil - stem_h

    d.line((cx+6, soil+28, cx+6, top), fill=(34, 87, 38), width=22)
    d.line((cx, soil+28, cx, top), fill=(58, 137, 62), width=16)
    d.line((cx-4, soil+20, cx-4, top+12), fill=(93, 175, 93), width=4)

    count = 2 + int(sp * (10 if profile not in {"corn", "pumpkin"} else 7))
    for i in range(count):
        frac = (i + 1) / (count + 1)
        y = int(soil - stem_h * frac)
        side = -1 if i % 2 == 0 else 1
        size = 95 if profile == "corn" else 60 if profile in {"strawberry", "radish"} else 75 if profile == "pumpkin" else 52 + (i % 3) * 7
        x = cx + side * (105 if profile in {"corn", "pumpkin"} else 78 if profile in {"strawberry", "radish"} else 72 + (i % 2) * 24)
        angle = -58 * side if profile == "corn" else -25 * side + (i % 3) * 6
        d.line((cx, y, x, y+4), fill=(55, 126, 58), width=7)
        _leaf(frame, x, y, size, angle)

    _mature_feature(frame, profile, cx, soil, top, sp, seed)
