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

_REAL_ENVIRONMENTS = (
    "real alpine green valley at golden sunrise, clear river, distant snow mountains and natural atmospheric haze",
    "real Nordic mountain landscape beneath a vivid aurora borealis, cold night air, natural stars and subtle snow",
    "real warm desert dunes at sunrise, wind moving fine sand and physically plausible long shadows",
    "real Mediterranean olive grove at golden hour, natural leaves and branches moving in a light breeze",
    "real rocky ocean coastline at dawn, natural waves, sea spray and moving clouds",
    "real high mountain ridge at sunset, layered valleys and cinematic atmospheric perspective",
    "real forest clearing after rain, wet leaves, mist and sun rays passing through moving branches",
    "real lakeside meadow with wildflowers, moving water and warm late-afternoon sunlight",
    "real snowy mountain pass, visible cold breath, wind moving robe fabric and natural blue-hour light",
    "real canyon riverbank with detailed rock, flowing water and warm sunset light",
)

_VISUAL_MOTIFS = (
    "live-action medium close-up of the recurring photoreal synthetic Jesus character speaking continuously toward camera, natural lips jaw cheeks blinking breathing and small head movement",
    "live-action full-body tracking shot of the recurring photoreal synthetic Jesus character walking while speaking continuously, realistic legs balance robe movement and one calm open-hand gesture",
    "live-action waist-up moving shot of the recurring photoreal synthetic Jesus character speaking continuously and extending one hand naturally toward camera, realistic fingers wrist elbow and shoulder",
    "live-action three-quarter body shot of the recurring photoreal synthetic Jesus character turning slightly while speaking, both hands moving naturally and realistic weight shifting through hips and legs",
    "live-action intimate close-up of the recurring photoreal synthetic Jesus character speaking continuously with natural eye focus facial micro-expression and restrained nodding",
    "live-action wide cinematic shot of the recurring photoreal synthetic Jesus character walking through the environment while speaking, natural arm swing posture steps and moving fabric",
    "live-action medium shot of the recurring photoreal synthetic Jesus character speaking and gently raising then lowering one hand, natural shoulder elbow wrist and finger articulation",
    "live-action full-body dolly shot of the recurring photoreal synthetic Jesus character slowly approaching camera while speaking continuously, realistic knees feet torso balance and robe folds",
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
    value = int(hashlib.sha256(f"spiritual-long-v4|{minutes}|{marker}".encode()).hexdigest()[:8], 16)
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
        return (fresh + old)[: min(10, len(refs))]

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
    meta["spiritual_quality_profile"] = "premium_long_live_action_photoreal_v4"
    meta["synthetic_character_disclosure"] = True
    meta["character_is_fictional_artistic_representation"] = True
    meta["photoreal_human_required"] = True
    meta["no_cartoon_no_3d_animation"] = True
    meta["continuous_speech_requested"] = True
    meta["lip_sync_requested"] = True
    meta["full_body_motion_requested"] = True

    refs = []
    for section in meta.get("sections") or []:
        ref = " ".join(str(section.get("bible_reference") or "").split())
        if ref and ref not in refs:
            refs.append(ref)
    meta["bible_references_used"] = refs

    description = str(meta.get("description") or "").strip()
    if refs:
        description += "\n\nReferencias bíblicas tratadas: " + ", ".join(refs[:8]) + "."
    if "representación humana digital" not in description.lower() and "representacion humana digital" not in description.lower():
        description += "\n\nLa figura de Jesús es una representación humana digital fotorrealista generada con IA; no es una grabación de una persona real."
    meta["description"] = description[:4700].strip()

    seed = _run_seed(minutes)
    sections = list(meta.get("sections") or [])
    for index, section in enumerate(sections):
        motif = _VISUAL_MOTIFS[(seed + index * 3) % len(_VISUAL_MOTIFS)]
        environment = _REAL_ENVIRONMENTS[((seed // 5) + index * 2) % len(_REAL_ENVIRONMENTS)]
        original = " ".join(str(section.get("visual_prompt") or "").split())
        section["visual_prompt"] = (
            f"{motif}, filmed in a {environment}. {original}. SAME recurring identity in all sections: adult Middle Eastern/Mediterranean-looking synthetic man, shoulder-length wavy dark-brown hair, groomed full brown beard, hazel-brown eyes, natural skin pores and individual hair strands, ivory or cream woven linen robe and beige mantle. "
            "Premium live-action cinema, realistic anatomy, five fingers per hand, natural hands arms head torso hips knees legs and walking balance, realistic cloth and environmental physics, photographic optics, natural depth of field and physically plausible lighting. "
            "Continuous believable speech performance suitable for audio-driven lip-sync. ABSOLUTELY NO cartoon, illustration, painting, anime, stylized 3D, game character, plastic CGI skin, doll face, frozen pose, malformed hands, readable text, subtitles, logo, watermark or celebrity likeness."
        )[:1900]
    meta["sections"] = sections
    return meta


def run(minutes: int, publish: bool = False) -> dict:
    previous = _read_history()
    original_picker = base._pick_reference_seed
    original_generate = base._generate_metadata
    original_seed = base._seed
    captured: dict = {}

    base._pick_reference_seed = _reference_picker(previous)

    def safe_base_seed(meta: dict, index: int) -> int:
        return _safe_seed(original_seed(meta, index))

    def generate(channel: dict, requested_minutes: int) -> dict:
        meta = original_generate(channel, requested_minutes)
        meta = _enhance_metadata(meta, previous, requested_minutes)
        captured["meta"] = meta
        return meta

    base._seed = safe_base_seed
    base._generate_metadata = generate
    try:
        result = base.run(minutes, publish=publish)
    finally:
        base._pick_reference_seed = original_picker
        base._generate_metadata = original_generate
        base._seed = original_seed

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
