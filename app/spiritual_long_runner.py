from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from datetime import datetime, timezone

from . import spiritual_long_pipeline as base
from .config import ROOT
from .hf_video import _safe_seed
from .history import similarity
from .spiritual_local_art import make_spiritual_art

HISTORY_FILE = ROOT / "state" / "dioshablahoyia_long_history.jsonl"

_TITLE_TEMPLATES = (
    "{topic} | Reflexión bíblica y oración",
    "Cuando necesitás paz: {topic}",
    "Biblia, fe y esperanza: {topic}",
    "Una oración para este momento: {topic}",
    "Encontrar fortaleza en Dios: {topic}",
    "Un tiempo de oración y reflexión: {topic}",
    "{topic}: esperanza para tiempos difíciles",
    "Volver a confiar: {topic}",
)

_VISUAL_MOTIFS = (
    "medium close-up of the recurring fictional Jesus character speaking softly toward camera with subtle natural mouth and jaw movement, compassionate eye contact and one slow open-hand gesture",
    "wide tracking shot of the recurring fictional Jesus character walking along a mountain path while speaking calmly, robe and mantle moving in a light breeze",
    "lakeside medium shot of the recurring fictional Jesus character speaking with restrained facial movement and a gentle open-palm gesture, water moving behind him",
    "olive grove at golden hour, the recurring fictional Jesus character speaks naturally with calm eye contact and small hand gestures, leaves moving in the wind",
    "riverbank close-up, the recurring fictional Jesus character speaks peacefully toward camera, subtle head movement and breathing, flowing water and warm light",
    "sunrise valley dolly shot, the recurring fictional Jesus character walks slowly toward camera while speaking, soft clouds and rays changing naturally",
    "stone courtyard with ancient-inspired architecture, the recurring fictional Jesus character speaks serenely with restrained gestures and realistic fabric movement",
    "mountain overlook at sunset, the recurring fictional Jesus character speaks reflectively, briefly looks to the horizon, then returns eye contact to camera",
    "quiet meadow after light rain, the recurring fictional Jesus character speaks gently while walking, grasses moving and soft sun breaking through clouds",
    "shoreline at dawn, the recurring fictional Jesus character speaks with a peaceful expression and slow natural hand motion, waves and sky moving behind him",
)


def _read_history(limit: int = 30) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    rows: list[dict] = []
    for raw in HISTORY_FILE.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def _append_history(item: dict) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def _run_seed(minutes: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or datetime.now(timezone.utc).isoformat()
    value = int(hashlib.sha256(f"spiritual-long-v2|{minutes}|{marker}".encode()).hexdigest()[:8], 16)
    return _safe_seed(value)


def _reference_picker(previous: list[dict]):
    recent_refs: set[str] = set()
    for row in previous[-10:]:
        for ref in row.get("references") or []:
            if str(ref).strip():
                recent_refs.add(str(ref).strip().lower())

    def pick(minutes: int) -> list[dict]:
        refs = list(base._references())
        seed = _run_seed(minutes)
        rng = random.Random(seed ^ 0xB1B1E)
        fresh = [item for item in refs if str(item.get("reference", "")).strip().lower() not in recent_refs]
        old = [item for item in refs if item not in fresh]
        rng.shuffle(fresh)
        rng.shuffle(old)
        ordered = fresh + old
        return ordered[: min(10, len(ordered))]

    return pick


def _safe_title(meta: dict, previous: list[dict], minutes: int) -> tuple[str, list[str]]:
    topic = " ".join(str(meta.get("topic") or "Fe, Biblia y esperanza").split())
    original = " ".join(str(meta.get("title") or "").split()).strip()
    seed = _run_seed(minutes)

    risky = (
        "dios te dice",
        "jesus te dice",
        "mensaje urgente de dios",
        "profecia para hoy",
        "esto pasara hoy",
        "si no ves esto",
        "antes de que sea tarde",
    )
    old_titles = [str(row.get("title") or "") for row in previous if str(row.get("title") or "").strip()]

    def acceptable(title: str) -> bool:
        low = title.lower()
        if any(term in low for term in risky):
            return False
        return not any(similarity(title, old) >= 0.68 for old in old_titles[-20:])

    candidates: list[str] = []
    if original:
        candidates.append(original[:95])
    for step in range(len(_TITLE_TEMPLATES)):
        template = _TITLE_TEMPLATES[(seed + step) % len(_TITLE_TEMPLATES)]
        candidates.append(template.format(topic=topic)[:95])

    chosen = next((title for title in candidates if acceptable(title)), candidates[-1])
    variants: list[str] = []
    for title in candidates:
        clean = title.rstrip(" -:,.!")
        if clean and clean not in variants and not any(similarity(clean, v) > 0.88 for v in variants):
            variants.append(clean)
        if len(variants) == 3:
            break
    while len(variants) < 3:
        variants.append(chosen)
    return chosen.rstrip(" -:,.!"), variants[:3]


def _enhance_metadata(meta: dict, previous: list[dict], minutes: int) -> dict:
    title, variants = _safe_title(meta, previous, minutes)
    meta["title"] = title
    meta["title_variants"] = variants
    meta["spiritual_quality_profile"] = "premium_long_varied_truthful_v2"
    meta["synthetic_character_disclosure"] = True
    meta["character_is_fictional_artistic_representation"] = True

    refs = []
    for section in meta.get("sections") or []:
        ref = " ".join(str(section.get("bible_reference") or "").split())
        if ref and ref not in refs:
            refs.append(ref)
    meta["bible_references_used"] = refs

    description = str(meta.get("description") or "").strip()
    if refs:
        description += "\n\nReferencias bíblicas tratadas: " + ", ".join(refs[:8]) + "."
    if "representación artística" not in description.lower() and "representacion artistica" not in description.lower():
        description += "\n\nLa imagen de Jesús es una representación artística ficticia generada para acompañar esta reflexión."
    meta["description"] = description[:4700].strip()

    seed = _run_seed(minutes)
    sections = list(meta.get("sections") or [])
    for index, section in enumerate(sections):
        motif = _VISUAL_MOTIFS[(seed + index * 3) % len(_VISUAL_MOTIFS)]
        original = " ".join(str(section.get("visual_prompt") or "").split())
        section["visual_prompt"] = (
            f"{motif}. {original}. Keep the recurring fictional character identity consistent while making this section's setting, camera distance, gesture and movement visibly different from neighboring sections. "
            "Premium cinematic realism, natural facial micro-expressions, no exaggerated lip motion, no readable text, no subtitles, no logo, no watermark, no celebrity likeness."
        )[:1600]
    meta["sections"] = sections
    return meta


def run(minutes: int, publish: bool = False) -> dict:
    previous = _read_history()
    original_picker = base._pick_reference_seed
    original_generate = base._generate_metadata
    original_seed = base._seed
    original_download = base._download_image
    captured: dict = {}

    base._pick_reference_seed = _reference_picker(previous)

    def safe_base_seed(meta: dict, index: int) -> int:
        return _safe_seed(original_seed(meta, index))

    def resilient_download(prompt: str, out, seed: int) -> None:
        key = os.getenv("POLLINATIONS_API_KEY", "").strip()
        if key:
            try:
                original_download(prompt, out, _safe_seed(seed))
                return
            except Exception as exc:
                print(f"Imagen IA externa no disponible ({exc}); usando arte espiritual local original.")
        else:
            print("POLLINATIONS_API_KEY ausente; usando arte espiritual local original sin depender de una API externa.")
        make_spiritual_art(out, base.W, base.H, _safe_seed(seed), index=_safe_seed(seed) % 9, mouth_open=0)

    def generate(channel: dict, requested_minutes: int) -> dict:
        meta = original_generate(channel, requested_minutes)
        meta = _enhance_metadata(meta, previous, requested_minutes)
        captured["meta"] = meta
        return meta

    base._seed = safe_base_seed
    base._download_image = resilient_download
    base._generate_metadata = generate
    try:
        result = base.run(minutes, publish=publish)
    finally:
        base._pick_reference_seed = original_picker
        base._generate_metadata = original_generate
        base._seed = original_seed
        base._download_image = original_download

    meta = captured.get("meta") or {}
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": "dioshablahoyia",
        "content_type": "long",
        "minutes": minutes,
        "topic": meta.get("topic"),
        "title": result.get("title") or meta.get("title"),
        "references": meta.get("bible_references_used") or [],
        "video_id": result.get("video_id"),
        "status": result.get("status"),
    }
    _append_history(record)
    result["anti_repeat_history"] = str(HISTORY_FILE)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[10, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    result = run(args.minutes, publish=args.publish)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
