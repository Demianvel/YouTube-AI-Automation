from __future__ import annotations

import base64
import hashlib
import json
import os
import random
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.dios_realistic_visual_policy import (
    NEGATIVE_VISUAL_CLAUSE,
    VISUAL_POLICY_ID,
    shuffled_thumbnail_bundles,
)

ROOT = Path(__file__).resolve().parents[1]
SHORT_HISTORY = ROOT / "state" / "history.jsonl"
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"

OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"

STYLE_MODES = (
    "premium golden-hour devotional live-action cinema",
    "dramatic post-storm biblical photographic realism",
    "quiet Nordic blue-hour spiritual cinema",
    "high-contrast mountain sunrise hope with realistic atmosphere",
    "soft natural documentary-style biblical realism",
    "epic wide environmental biblical cinema with believable scale",
    "intimate shallow-depth realistic devotional portrait",
    "Nordic landscape editorial photography with reverent biblical subject",
    "natural cinematic realism inspired by high-end travel photography",
    "restrained northern-lights realism with accurate low-light exposure",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dhash(path: Path) -> str:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert("L").resize((17, 16), Image.Resampling.LANCZOS)
        px = list(image.getdata())
    value = 0
    for row in range(16):
        off = row * 17
        for col in range(16):
            value = (value << 1) | int(px[off + col] > px[off + col + 1])
    return f"{value:064x}"


def _hamming(a: str, b: str) -> int:
    try:
        return (int(a, 16) ^ int(b, 16)).bit_count()
    except Exception:
        return 10_000


def _history_rows(limit: int = 240) -> list[dict]:
    rows: list[dict] = []
    for path in (SHORT_HISTORY, LONG_HISTORY):
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines()[-limit:]:
            try:
                row = json.loads(raw)
            except Exception:
                continue
            if row.get("channel") == "dioshablahoyia":
                rows.append(row)
    return rows[-limit:]


def _history_fingerprints() -> tuple[set[str], list[str], set[str], set[str]]:
    exact: set[str] = set()
    perceptual: list[str] = []
    prompt_hashes: set[str] = set()
    style_ids: set[str] = set()
    for row in _history_rows():
        sha = str(row.get("thumbnail_sha256") or "").strip()
        dh = str(row.get("thumbnail_dhash") or "").strip()
        ph = str(row.get("thumbnail_prompt_hash") or "").strip()
        style = str(row.get("thumbnail_style_id") or row.get("thumbnail_layout_id") or "").strip()
        if sha:
            exact.add(sha)
        if dh:
            perceptual.append(dh)
        if ph:
            prompt_hashes.add(ph)
        if style:
            style_ids.add(style)
    return exact, perceptual, prompt_hashes, style_ids


def _seed(metadata: dict, content_type: str) -> int:
    raw = "|".join([
        "dios-auto-thumbnail-v5-realistic",
        content_type,
        str(metadata.get("title") or ""),
        str(metadata.get("topic") or ""),
        str(metadata.get("bible_reference") or ""),
        os.getenv("GITHUB_RUN_ID", ""),
        os.getenv("GITHUB_RUN_ATTEMPT", ""),
        os.getenv("GITHUB_RUN_NUMBER", ""),
    ])
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _prompt(
    metadata: dict,
    content_type: str,
    seed: int,
    prompt_history: set[str],
    style_history: set[str],
) -> tuple[str, str, str, dict[str, str]]:
    rng = random.Random(seed)
    styles = list(STYLE_MODES)
    rng.shuffle(styles)
    bundles = shuffled_thumbnail_bundles(seed)
    title = " ".join(str(metadata.get("title") or "").split())
    topic = " ".join(str(metadata.get("topic") or "").split())
    bible = " ".join(str(metadata.get("bible_reference") or "").split())
    aspect_label = "vertical 9:16" if content_type == "short" else "horizontal 16:9"

    for bundle in bundles:
        for style in styles:
            style_raw = "|".join([
                VISUAL_POLICY_ID,
                content_type,
                bundle["motif_id"],
                bundle["character_variant"],
                bundle["location_family"],
                bundle["lighting_mode"],
                bundle["composition_mode"],
                style,
            ])
            style_id = hashlib.sha256(style_raw.encode("utf-8")).hexdigest()[:16]
            if style_id in style_history:
                continue
            prompt = (
                "Create a completely new original AI-generated YouTube thumbnail for Dios Habla Hoy IA. "
                f"Format: {aspect_label}. Main visual concept: {bundle['motif']}. "
                f"Character treatment: {bundle['character']}. Location: {bundle['location']}. "
                f"Lighting: {bundle['lighting']}. Composition: {bundle['composition']}. Visual style: {style}. "
                "The image must look like a premium live-action cinematic photograph, not graphic design. "
                "Use believable human anatomy, natural skin pores, individual hair strands, realistic woven fabric, "
                "physically plausible clouds, water, mountains, trees, mist and photographic optics. "
                "Make the landscape beautiful and memorable: Norwegian fjords, Nordic mountains, alpine lakes, biblical valleys, "
                "Noah's Ark or other believable biblical environments are preferred when appropriate. "
                "Emotional goal: hope, peace, faith, beauty, curiosity and human relevance without fear or manipulation. "
                f"Context inspiration: title '{title}', topic '{topic}', biblical reference '{bible}'. "
                "Strong focal hierarchy and clean premium composition for a small mobile preview. "
                "No celebrity, no identifiable real person, no copyrighted character. "
                f"{NEGATIVE_VISUAL_CLAUSE}"
            )
            ph = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20]
            if ph not in prompt_history:
                return prompt, ph, style_id, bundle

    bundle = bundles[seed % len(bundles)]
    style = styles[seed % len(styles)]
    prompt = (
        f"New unique premium live-action biblical thumbnail variation {seed}. {bundle['motif']}. "
        f"{bundle['character']}. {bundle['location']}. {bundle['lighting']}. {bundle['composition']}. "
        f"{style}. {aspect_label}. {NEGATIVE_VISUAL_CLAUSE}"
    )
    return (
        prompt,
        hashlib.sha256(prompt.encode()).hexdigest()[:20],
        hashlib.sha256(f"fallback|{VISUAL_POLICY_ID}|{seed}|{content_type}".encode()).hexdigest()[:16],
        bundle,
    )


def _openai_image(prompt: str, out: Path, content_type: str) -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY no configurado")
    size = "1024x1536" if content_type == "short" else "1536x1024"
    response = requests.post(
        OPENAI_IMAGE_ENDPOINT,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": OPENAI_IMAGE_MODEL, "prompt": prompt, "size": size},
        timeout=(20, 240),
    )
    response.raise_for_status()
    payload = response.json()
    data = (payload.get("data") or [{}])[0]
    raw = data.get("b64_json")
    if raw:
        out.write_bytes(base64.b64decode(raw))
    elif data.get("url"):
        image_response = requests.get(data["url"], timeout=(20, 180))
        image_response.raise_for_status()
        out.write_bytes(image_response.content)
    else:
        raise RuntimeError("OpenAI Images no devolvio b64_json ni url")
    if not out.exists() or out.stat().st_size < 10_000:
        raise RuntimeError("OpenAI Images devolvio una imagen vacia o demasiado pequena")
    return f"OpenAI/{OPENAI_IMAGE_MODEL}"


def _candidate_sources(workdir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        files.extend(workdir.rglob(pattern))
    result: list[Path] = []
    for path in files:
        low = path.name.lower()
        if "thumbnail" in low or "icon" in low or "logo" in low or "symbol" in low or "triangle" in low:
            continue
        try:
            if path.stat().st_size >= 10_000:
                result.append(path)
        except OSError:
            continue
    return sorted(set(result))


def _video_frame(video_path: Path, out: Path) -> None:
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(video_path),
        "-frames:v", "1", "-q:v", "2", str(out),
    ], check=True)


def _save_youtube_safe_jpeg(frame: Image.Image, out: Path, initial_quality: int) -> None:
    for quality in (initial_quality, 84, 78, 72, 66, 60):
        frame.save(out, "JPEG", quality=quality, optimize=True, progressive=True)
        if out.stat().st_size <= 1_900_000:
            return
    raise RuntimeError(f"Miniatura demasiado pesada para YouTube: {out.stat().st_size} bytes")


def _compose(source: Path, out: Path, content_type: str, seed: int, variant: int) -> None:
    target = (1080, 1920) if content_type == "short" else (1280, 720)
    rng = random.Random(seed ^ (variant * 0x9E3779B1))
    with Image.open(source) as opened:
        src = ImageOps.exif_transpose(opened).convert("RGB")
        center_x = 0.27 + rng.random() * 0.46
        center_y = 0.28 + rng.random() * 0.44
        frame = ImageOps.fit(src, target, method=Image.Resampling.LANCZOS, centering=(center_x, center_y))
        if variant % 7 == 1:
            frame = ImageOps.mirror(frame)
        frame = ImageEnhance.Contrast(frame).enhance(1.04 + 0.02 * (variant % 4))
        frame = ImageEnhance.Color(frame).enhance(1.02 + 0.018 * ((variant + 1) % 4))
        frame = ImageEnhance.Sharpness(frame).enhance(1.08 + 0.035 * (variant % 3))
        if variant % 4 == 0:
            soft = frame.filter(ImageFilter.GaussianBlur(radius=6))
            frame = Image.blend(soft, frame, 0.95)
        out.parent.mkdir(parents=True, exist_ok=True)
        _save_youtube_safe_jpeg(frame, out, 88 if content_type == "short" else 91)


def build_auto_thumbnail(
    workdir: Path,
    metadata: dict,
    *,
    content_type: str,
    video_path: Path | None = None,
) -> Path:
    if content_type not in {"short", "long"}:
        raise ValueError("content_type debe ser short o long")

    seed = _seed(metadata, content_type)
    exact_history, dh_history, prompt_history, style_history = _history_fingerprints()
    prompt, prompt_hash, style_id, bundle = _prompt(
        metadata, content_type, seed, prompt_history, style_history
    )
    metadata["thumbnail_prompt"] = prompt
    metadata["thumbnail_prompt_hash"] = prompt_hash
    metadata["thumbnail_style_id"] = style_id
    metadata["thumbnail_aspect"] = "9:16" if content_type == "short" else "16:9"
    metadata["thumbnail_ai_policy"] = f"openai_gpt_image_first_{VISUAL_POLICY_ID}_no_abstract_geometry"
    metadata["thumbnail_scene_family"] = bundle["motif_id"]
    metadata["thumbnail_character_variant"] = bundle["character_variant"]
    metadata["thumbnail_location_family"] = bundle["location_family"]
    metadata["thumbnail_lighting_mode"] = bundle["lighting_mode"]
    metadata["thumbnail_composition_mode"] = bundle["composition_mode"]

    source = workdir / f"thumbnail_ai_source_{content_type}.png"
    provider = ""
    try:
        provider = _openai_image(prompt, source, content_type)
    except Exception as exc:
        metadata["thumbnail_openai_fallback_reason"] = f"{type(exc).__name__}: {exc}"[:500]
        candidates = _candidate_sources(workdir)
        if candidates:
            source = candidates[seed % len(candidates)]
            provider = "fresh_realistic_video_visual_fallback"
        elif video_path is not None and video_path.exists():
            source = workdir / f"thumbnail_video_frame_{content_type}.jpg"
            _video_frame(video_path, source)
            provider = "fresh_realistic_video_frame_fallback"
        else:
            raise RuntimeError("No hay fuente realista disponible para generar miniatura automatica")

    out = workdir / ("youtube_thumbnail_9x16.jpg" if content_type == "short" else "youtube_thumbnail_16x9.jpg")
    threshold = max(8, int(os.getenv("SPIRITUAL_THUMBNAIL_DHASH_MIN_DISTANCE", "20")))
    best_distance = -1
    best: tuple[str, str, int] | None = None

    for variant in range(24):
        _compose(source, out, content_type, seed, variant)
        sha = _sha256(out)
        dh = _dhash(out)
        distance = min((_hamming(dh, old) for old in dh_history), default=10_000)
        if distance > best_distance and sha not in exact_history:
            best_distance = distance
            best = (sha, dh, variant)
        if sha not in exact_history and distance > threshold:
            metadata["thumbnail_status"] = "generated_unique_realistic"
            metadata["thumbnail_sha256"] = sha
            metadata["thumbnail_dhash"] = dh
            metadata["thumbnail_nearest_distance"] = distance
            metadata["thumbnail_layout_id"] = f"{content_type}-realistic-layout-{variant}"
            metadata["thumbnail_provider"] = provider
            metadata["thumbnail_source"] = source.name
            metadata["thumbnail_unique_policy"] = "sha256+dhash+prompt+character+location+lighting+composition rotation"
            return out

    if best is None:
        raise RuntimeError("No se pudo producir una miniatura realista candidata valida")
    sha, dh, variant = best
    _compose(source, out, content_type, seed, variant)
    metadata["thumbnail_status"] = "generated_best_unique_realistic_available"
    metadata["thumbnail_sha256"] = sha
    metadata["thumbnail_dhash"] = dh
    metadata["thumbnail_nearest_distance"] = best_distance
    metadata["thumbnail_layout_id"] = f"{content_type}-realistic-layout-{variant}"
    metadata["thumbnail_provider"] = provider
    metadata["thumbnail_source"] = source.name
    metadata["thumbnail_unique_policy"] = "sha256+dhash+prompt+character+location+lighting+composition rotation"
    return out
