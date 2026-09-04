from __future__ import annotations

import base64
import hashlib
import json
import os
import random
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SHORT_HISTORY = ROOT / "state" / "history.jsonl"
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"

OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"
OPENAI_IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"

SYMBOLIC_MOTIFS = (
    "recurring fully synthetic photoreal Jesus standing beside calm living water at sunrise, compassionate expression, realistic linen clothing, premium live-action biblical cinema, no resemblance to any real person",
    "recurring fully synthetic photoreal Jesus walking on a quiet stone path between olive trees at golden hour, reverent premium cinematic realism, no resemblance to any real person",
    "simple wooden cross on a high hill as storm clouds open to warm natural light, photoreal cinematic symbolism",
    "open Bible on weathered olive wood beside a warm clay oil lamp, shallow depth of field, premium photoreal devotional cinema, no readable text",
    "ancient stone doorway opening from shadow toward a bright green valley, symbolic new beginning, premium photoreal biblical atmosphere",
    "calm sea after a storm reflecting golden sunlight beneath dramatic clouds, subtle distant cross silhouette, cinematic realism",
    "white dove flying above a river valley after rain, realistic anatomy, soft mist and natural sunlight, symbolic peace",
    "small lamb resting safely beside an adult sheep in a green field, distant hills and warm evening light, symbolic shepherd imagery",
    "hands resting in quiet prayer beside a Bible and candle, intimate natural light, realistic skin, no identifiable person",
    "powerful waterfall in a green canyon with sunlight catching natural spray, symbolic renewal and hope, cinematic realism",
    "lonely mountain road reaching a brilliant sunrise, universal human silhouette from behind, hope and purpose, no identifiable real person",
    "empty modest church interior with natural rays of light crossing wooden pews, reverent cinematic realism",
    "rain ending over a vast valley with a subtle natural rainbow and fresh mist, symbolic covenant and hope, premium photoreal landscape",
    "star-filled desert night with one warm oil lamp in foreground and distant mountains, quiet biblical atmosphere, premium cinematic realism",
    "small boat on calm water before sunrise with distant mountains, symbolic trust and journey, photoreal cinematic frame",
    "olive branches moving gently in wind beside simple bread and a clay cup, biblical everyday symbolism, premium realistic photography",
    "warm sunlight entering an old forest and illuminating mist between trees, symbolic divine presence, premium photoreal cinema",
    "snowy mountains and still fjord under northern lights, awe of creation, premium photoreal cinematic landscape",
)

STYLE_MODES = (
    "golden-hour devotional cinema",
    "dramatic post-storm biblical realism",
    "quiet blue-hour spiritual cinema",
    "high-contrast sunrise hope",
    "soft natural window-light realism",
    "epic wide environmental biblical cinema",
    "intimate shallow-depth devotional portrait",
    "documentary-style realistic faith imagery",
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


def _history_rows(limit: int = 180) -> list[dict]:
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
        "dios-auto-thumbnail-v3",
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
) -> tuple[str, str, str]:
    rng = random.Random(seed)
    candidates = list(SYMBOLIC_MOTIFS)
    styles = list(STYLE_MODES)
    rng.shuffle(candidates)
    rng.shuffle(styles)
    title = " ".join(str(metadata.get("title") or "").split())
    topic = " ".join(str(metadata.get("topic") or "").split())
    bible = " ".join(str(metadata.get("bible_reference") or "").split())
    aspect_label = "vertical 9:16" if content_type == "short" else "horizontal 16:9"

    for motif_index, motif in enumerate(candidates):
        for style_index, style in enumerate(styles):
            style_id = hashlib.sha256(
                f"{style}|{motif_index}|{style_index}|{content_type}".encode()
            ).hexdigest()[:16]
            if style_id in style_history:
                continue
            prompt = (
                "Create a completely new original AI-generated YouTube thumbnail for Dios Habla Hoy IA. "
                f"Format: {aspect_label}. Subject: {motif}. Visual style: {style}. "
                "Emotional goal: hope, peace, faith, curiosity and human relevance without fear or manipulation. "
                f"Context inspiration: title '{title}', topic '{topic}', biblical reference '{bible}'. "
                "Premium photoreal cinematic quality, physically plausible light, natural skin/material detail, strong focal hierarchy, "
                "clear subject separation, attractive composition for a small mobile preview. No text, no captions, no logo, no watermark, "
                "no celebrity, no identifiable real person, no copyrighted character, no plastic CGI, no cartoon."
            )
            ph = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20]
            if ph not in prompt_history:
                return prompt, ph, style_id

    fallback_style = styles[seed % len(styles)]
    fallback_motif = candidates[(seed // 7) % len(candidates)]
    prompt = f"{fallback_motif}; {fallback_style}; unique variation {seed}; {aspect_label}; no text"
    return (
        prompt,
        hashlib.sha256(prompt.encode()).hexdigest()[:20],
        hashlib.sha256(f"fallback|{seed}|{content_type}".encode()).hexdigest()[:16],
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
        if "thumbnail" in path.name.lower():
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
        center_x = 0.30 + rng.random() * 0.40
        center_y = 0.30 + rng.random() * 0.40
        frame = ImageOps.fit(src, target, method=Image.Resampling.LANCZOS, centering=(center_x, center_y))
        if variant % 5 == 1:
            frame = ImageOps.mirror(frame)
        frame = ImageEnhance.Contrast(frame).enhance(1.05 + 0.025 * (variant % 4))
        frame = ImageEnhance.Color(frame).enhance(1.03 + 0.02 * ((variant + 1) % 4))
        frame = ImageEnhance.Sharpness(frame).enhance(1.08 + 0.04 * (variant % 3))
        if variant % 3 == 0:
            soft = frame.filter(ImageFilter.GaussianBlur(radius=7))
            frame = Image.blend(soft, frame, 0.94)
        out.parent.mkdir(parents=True, exist_ok=True)
        _save_youtube_safe_jpeg(frame, out, 87 if content_type == "short" else 91)


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
    prompt, prompt_hash, style_id = _prompt(
        metadata, content_type, seed, prompt_history, style_history
    )
    metadata["thumbnail_prompt"] = prompt
    metadata["thumbnail_prompt_hash"] = prompt_hash
    metadata["thumbnail_style_id"] = style_id
    metadata["thumbnail_aspect"] = "9:16" if content_type == "short" else "16:9"
    metadata["thumbnail_ai_policy"] = "openai_gpt_image_first_then_fresh_visual_fallback"

    source = workdir / f"thumbnail_ai_source_{content_type}.png"
    provider = ""
    try:
        provider = _openai_image(prompt, source, content_type)
    except Exception as exc:
        metadata["thumbnail_openai_fallback_reason"] = f"{type(exc).__name__}: {exc}"[:500]
        candidates = _candidate_sources(workdir)
        if candidates:
            source = candidates[seed % len(candidates)]
            provider = "fresh_video_visual_fallback"
        elif video_path is not None and video_path.exists():
            source = workdir / f"thumbnail_video_frame_{content_type}.jpg"
            _video_frame(video_path, source)
            provider = "fresh_video_frame_fallback"
        else:
            raise RuntimeError("No hay fuente disponible para generar miniatura automatica")

    out = workdir / ("youtube_thumbnail_9x16.jpg" if content_type == "short" else "youtube_thumbnail_16x9.jpg")
    threshold = max(8, int(os.getenv("SPIRITUAL_THUMBNAIL_DHASH_MIN_DISTANCE", "20")))
    best_distance = -1
    best: tuple[str, str, int] | None = None

    for variant in range(18):
        _compose(source, out, content_type, seed, variant)
        sha = _sha256(out)
        dh = _dhash(out)
        distance = min((_hamming(dh, old) for old in dh_history), default=10_000)
        if distance > best_distance and sha not in exact_history:
            best_distance = distance
            best = (sha, dh, variant)
        if sha not in exact_history and distance > threshold:
            metadata["thumbnail_status"] = "generated_unique"
            metadata["thumbnail_sha256"] = sha
            metadata["thumbnail_dhash"] = dh
            metadata["thumbnail_nearest_distance"] = distance
            metadata["thumbnail_layout_id"] = f"{content_type}-layout-{variant}"
            metadata["thumbnail_provider"] = provider
            metadata["thumbnail_source"] = source.name
            metadata["thumbnail_unique_policy"] = "sha256+dhash+prompt+style rotation"
            return out

    if best is None:
        raise RuntimeError("No se pudo producir una miniatura candidata valida")
    sha, dh, variant = best
    _compose(source, out, content_type, seed, variant)
    metadata["thumbnail_status"] = "generated_best_unique_available"
    metadata["thumbnail_sha256"] = sha
    metadata["thumbnail_dhash"] = dh
    metadata["thumbnail_nearest_distance"] = best_distance
    metadata["thumbnail_layout_id"] = f"{content_type}-layout-{variant}"
    metadata["thumbnail_provider"] = provider
    metadata["thumbnail_source"] = source.name
    metadata["thumbnail_unique_policy"] = "sha256+dhash+prompt+style rotation"
    return out
