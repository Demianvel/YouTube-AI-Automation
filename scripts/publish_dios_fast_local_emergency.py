from __future__ import annotations

import math
import random
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from app import pipeline, spiritual_image, youtube as youtube_module
from app.spiritual_fresh_reference_bank import is_jesus_prompt, subject_prompt
import scripts.publish_dios_fast as fast


VISUAL_DIVERSITY_VERSION = "dios-zero-hf-diversity-v5-original-procedural-fallback"
PROCEDURAL_PROVIDER = "local_original_procedural_cinematic_v1"


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _procedural_cinematic_scene(prompt: str, out: Path, seed: int) -> str:
    """Create a new cinematic vertical scene from pixels generated locally.

    This is the last-resort path when every external free source is unavailable
    or already used. It never transforms an old channel image, so the visual
    source itself is original for this render.
    """
    unique_seed = int(seed) ^ int(time.time_ns() & 0xFFFFFFFF)
    rng = random.Random(unique_seed)
    width, height = 1080, 1920

    palettes = (
        ((9, 23, 49), (78, 116, 151), (244, 190, 117)),
        ((18, 34, 49), (59, 92, 99), (221, 178, 118)),
        ((27, 20, 54), (88, 73, 126), (238, 174, 118)),
        ((8, 38, 52), (42, 103, 112), (235, 198, 129)),
        ((36, 33, 42), (102, 88, 93), (230, 184, 122)),
    )
    top, middle, horizon_color = palettes[unique_seed % len(palettes)]
    horizon = int(height * rng.uniform(0.48, 0.62))

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
    gy = rng.randint(int(height * 0.16), int(height * 0.44))
    for radius, alpha in ((260, 25), (170, 45), (90, 90), (38, 180)):
        glow_draw.ellipse((gx - radius, gy - radius, gx + radius, gy + radius), fill=(255, 222, 164, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(42))
    image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(image)

    # Atmospheric specks are generated anew for every render.
    for _ in range(95):
        x = rng.randrange(width)
        y = rng.randrange(max(1, horizon))
        r = rng.choice((1, 1, 1, 2, 2, 3))
        a = rng.randint(80, 190)
        color = (a, a, min(255, a + 25))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

    # Layered mountain silhouettes with seed-specific geometry.
    mountain_layers = (
        (horizon + 70, (58, 73, 78)),
        (horizon + 170, (40, 58, 62)),
        (horizon + 285, (27, 43, 47)),
    )
    for layer_index, (base_y, fill) in enumerate(mountain_layers):
        points = [(0, height)]
        step = 90
        x = -step
        while x <= width + step:
            peak = base_y - rng.randint(90 + layer_index * 20, 330 + layer_index * 45)
            points.append((x, peak))
            x += step
        points.extend(((width, height), (0, height)))
        draw.polygon(points, fill=fill)

    text = prompt.lower()
    watery = any(word in text for word in ("water", "river", "sea", "lake", "fjord", "océano", "oceano", "mar", "río", "rio"))
    if watery or rng.random() < 0.58:
        water_top = int(height * 0.70)
        draw.rectangle((0, water_top, width, height), fill=(21, 55, 67))
        for y in range(water_top + 12, height, 20):
            span = rng.randint(80, 330)
            x = rng.randint(-40, width - 20)
            shade = rng.randint(72, 135)
            draw.line((x, y, min(width, x + span), y), fill=(shade, shade + 18, shade + 24), width=rng.choice((1, 2, 3)))

    # A path or river leading toward the light gives depth and motion-friendly composition.
    path_center = rng.randint(int(width * 0.35), int(width * 0.65))
    path_top = horizon + rng.randint(90, 210)
    draw.polygon(
        [
            (path_center - 28, path_top),
            (path_center + 28, path_top),
            (width * 0.88, height),
            (width * 0.12, height),
        ],
        fill=(102, 92, 72) if not watery else (48, 92, 103),
    )

    # Semantic symbols are simple original geometry, never copied assets.
    if any(word in text for word in ("cross", "cruz", "jesus", "jesús", "cristo")):
        cx = rng.randint(int(width * 0.22), int(width * 0.78))
        cy = rng.randint(int(height * 0.48), int(height * 0.64))
        scale = rng.randint(95, 145)
        draw.rounded_rectangle((cx - 18, cy - scale, cx + 18, cy + scale), radius=7, fill=(34, 29, 24))
        draw.rounded_rectangle((cx - int(scale * 0.72), cy - 38, cx + int(scale * 0.72), cy - 5), radius=7, fill=(34, 29, 24))

    if any(word in text for word in ("bible", "biblia", "scroll", "libro")):
        bx = rng.randint(int(width * 0.20), int(width * 0.52))
        by = rng.randint(int(height * 0.70), int(height * 0.82))
        draw.polygon([(bx, by), (bx + 210, by - 34), (bx + 202, by + 132), (bx, by + 156)], fill=(224, 210, 174))
        draw.polygon([(bx + 210, by - 34), (bx + 420, by), (bx + 420, by + 156), (bx + 202, by + 132)], fill=(210, 196, 161))
        draw.line((bx + 210, by - 28, bx + 202, by + 132), fill=(108, 84, 62), width=5)

    if any(word in text for word in ("church", "chapel", "iglesia", "capilla")):
        bx = rng.randint(int(width * 0.18), int(width * 0.62))
        by = rng.randint(int(height * 0.64), int(height * 0.76))
        body_w = rng.randint(220, 310)
        body_h = rng.randint(190, 260)
        draw.rectangle((bx, by, bx + body_w, by + body_h), fill=(67, 62, 56))
        draw.polygon([(bx - 35, by), (bx + body_w // 2, by - 120), (bx + body_w + 35, by)], fill=(51, 46, 43))
        tower_x = bx + body_w // 2 - 34
        draw.rectangle((tower_x, by - 205, tower_x + 68, by), fill=(67, 62, 56))
        draw.polygon([(tower_x - 16, by - 205), (tower_x + 34, by - 270), (tower_x + 84, by - 205)], fill=(51, 46, 43))

    if any(word in text for word in ("dove", "bird", "pájaro", "pajaro", "gorrión", "gorrion")):
        for _ in range(rng.randint(1, 4)):
            bx = rng.randint(120, width - 120)
            by = rng.randint(240, max(280, horizon - 100))
            wing = rng.randint(26, 48)
            draw.arc((bx - wing, by - 14, bx, by + 26), 195, 345, fill=(225, 228, 226), width=6)
            draw.arc((bx, by - 14, bx + wing, by + 26), 195, 345, fill=(225, 228, 226), width=6)

    # Foreground blades/branches add parallax detail for the existing motion renderer.
    for _ in range(70):
        x = rng.randrange(width)
        base = rng.randint(int(height * 0.87), height)
        length = rng.randint(35, 150)
        bend = rng.randint(-28, 28)
        draw.line((x, base, x + bend, base - length), fill=(19, 43, 35), width=rng.choice((2, 3, 4)))

    # Soft mist bands make the output less flat without introducing reused assets.
    mist = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mist_draw = ImageDraw.Draw(mist)
    for _ in range(8):
        my = rng.randint(horizon - 30, int(height * 0.84))
        mh = rng.randint(24, 72)
        mist_draw.ellipse((-180, my - mh, width + 180, my + mh), fill=(220, 226, 220, rng.randint(10, 28)))
    mist = mist.filter(ImageFilter.GaussianBlur(26))
    image = Image.alpha_composite(image.convert("RGBA"), mist).convert("RGB")

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in {".jpg", ".jpeg"}:
        image.save(out, format="JPEG", quality=94, optimize=True)
    else:
        image.save(out, format="PNG", optimize=True)

    print(f"{VISUAL_DIVERSITY_VERSION}: escena original local creada desde cero seed={unique_seed}")
    return f"{PROCEDURAL_PROVIDER}:seed={unique_seed}"


def _zero_hf_diverse_download(prompt: str, out: Path, seed: int) -> str:
    """Emergency acquisition with strict no-reuse and an original local fallback."""
    jesus_scene = is_jesus_prompt(subject_prompt(prompt))
    free_prompt = fast._symbolic_prompt_for_jesus(prompt) if jesus_scene else prompt

    errors: list[str] = []
    for batch in range(4):
        retry_seed = int(seed) + batch * 1_000_003
        try:
            provider = fast._fresh_free_media(free_prompt, out, retry_seed, attempts=32)
            if "local_project_jesus_reference" in provider:
                errors.append(f"se rechazo fuente local: {provider}")
                continue
            print(f"{VISUAL_DIVERSITY_VERSION}: fuente realmente nueva: {provider}")
            return provider + f":{VISUAL_DIVERSITY_VERSION}"
        except Exception as exc:
            errors.append(str(exc))

    # The old behavior stopped the whole Short here. V5 instead creates a new
    # source from scratch, preserving anti-repeat without depending on quota.
    try:
        return _procedural_cinematic_scene(free_prompt, out, int(seed)) + f":{VISUAL_DIVERSITY_VERSION}"
    except Exception as exc:
        errors.append(f"procedural={exc}")
        raise RuntimeError(
            "ZERO_HF_FRESH_VISUAL_EXHAUSTED: no se pudo obtener ni crear una fuente visual nueva. "
            + " | ".join(errors[-6:])
        ) from exc


def _natural_algenib_voice_guard(channel: dict, metadata: dict, video_path: Path) -> None:
    """Use the approved natural continuity policy without changing Voz de Luz/Algenib."""
    if not youtube_module._is_spiritual_channel(channel):
        return

    if youtube_module._is_native_gemini_clip(metadata):
        if not youtube_module._has_audio_stream(video_path):
            raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: Gemini devolvio un video sin stream de audio.")
        metadata["voice_continuity_guard_mode"] = "native_audiovisual_clip_audio_stream_verified"
        return

    passed = metadata.get("voice_continuity_passed")
    coverage_raw = metadata.get("voice_coverage_ratio")
    longest_raw = metadata.get("longest_voice_silence_seconds")
    coverage = float(coverage_raw if coverage_raw is not None else 0.0)
    longest = float(longest_raw if longest_raw is not None else 999.0)

    if passed is not True or coverage < 0.82 or longest > 2.2:
        raise RuntimeError(
            "BLOQUEADO ANTES DE YOUTUBE: la narracion espiritual no supero la continuidad natural Algenib "
            f"(passed={passed}, coverage={coverage:.1%}, longest_silence={longest:.2f}s)."
        )

    if not youtube_module._has_audio_stream(video_path):
        raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: el Short espiritual no contiene stream de audio.")

    metadata["voice_continuity_guard_mode"] = "natural_algenib_82pct_tail_music_no_voice_slowdown"
    metadata["voice_continuity_upload_threshold"] = 0.82


# publish_dios_fast already provides semantic scene rotation and cinematic motion.
# This emergency route overrides acquisition only: every scene must come from
# a genuinely different source, either a new free source or a locally generated
# original scene. Old local portraits remain forbidden.
spiritual_image._download = _zero_hf_diverse_download
youtube_module._enforce_spiritual_voice_guard = _natural_algenib_voice_guard


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
