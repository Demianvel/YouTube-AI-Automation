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
from .spiritual_continuity import ensure_spoken_text, fit_and_validate_spiritual_voice
from .spiritual_engagement import engagement_comment
from .spiritual_long_resilience import apply_long_cta_overlay, create_thumbnail_candidates, download_landscape_image
from .spiritual_voice import polish_voice

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

_LONG_CTA = (
    "Antes de terminar, llevá esta reflexión a una acción concreta de bien. Si este mensaje te acompañó, "
    "podés suscribirte para recibir nuevas oraciones y reflexiones, compartirlo con alguien que hoy necesite esperanza "
    "y, si querés, escribir Amén o dejar tu intención de oración en los comentarios. Que la fe nos ayude a escuchar, "
    "acompañar, perdonar, compartir y hacer el bien cada día."
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
    value = int(hashlib.sha256(f"spiritual-long-v6|{minutes}|{marker}".encode()).hexdigest()[:8], 16)
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
    meta["spiritual_quality_profile"] = "premium_long_live_action_photoreal_v6_continuous_voice"
    meta["synthetic_character_disclosure"] = True
    meta["character_is_fictional_artistic_representation"] = True
    meta["photoreal_human_required"] = True
    meta["no_cartoon_no_3d_animation"] = True
    meta["continuous_speech_requested"] = True
    meta["voice_continuity_required"] = True
    meta["minimum_voice_coverage_ratio"] = 0.96
    meta["lip_sync_requested"] = True
    meta["full_body_motion_requested"] = True
    meta["growth_strategy"] = "hook_progression_biblical_value_payoff_packaging_variants_without_false_clickbait"
    meta["retention_structure"] = {
        "opening": "human need or question in first 15 seconds",
        "development": "new biblical/practical insight in each section",
        "payoff": "prayer plus practical act of faith or compassion",
        "ending": "gentle subscribe/comment/share CTA linked to doing good",
    }
    meta["pinned_comment_candidate"] = engagement_comment(
        f"long|{minutes}|{meta.get('topic','')}|{meta.get('title','')}|{_run_seed(minutes)}"
    )

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
    if "suscrib" not in description.lower():
        description += "\n\nSuscribite para nuevas reflexiones, compartí este mensaje con respeto y dejá tu intención de oración si querés. Que la fe también se convierta en acciones de bien hacia los demás."
    meta["description"] = description[:4700].strip()

    seed = _run_seed(minutes)
    sections = list(meta.get("sections") or [])
    per_section_seconds = (minutes * 60.0) / max(1, len(sections))
    voice_plans: list[dict] = []
    for index, section in enumerate(sections):
        narration = " ".join(str(section.get("narration") or "").split())
        narration, stats = ensure_spoken_text(
            narration,
            per_section_seconds,
            seed=seed + index * 17,
            words_per_minute=126,
        )
        section["narration"] = narration
        stats["section"] = index + 1
        voice_plans.append(stats)

        motif = _VISUAL_MOTIFS[(seed + index * 3) % len(_VISUAL_MOTIFS)]
        environment = _REAL_ENVIRONMENTS[((seed // 5) + index * 2) % len(_REAL_ENVIRONMENTS)]
        original = " ".join(str(section.get("visual_prompt") or "").split())
        section["visual_prompt"] = (
            f"{motif}, filmed in a {environment}. {original}. SAME recurring identity in all sections: adult Middle Eastern/Mediterranean-looking synthetic man, shoulder-length wavy dark-brown hair, groomed full brown beard, hazel-brown eyes, natural skin pores and individual hair strands, ivory or cream woven linen robe and beige mantle. "
            "Premium live-action cinema, realistic anatomy, five fingers per hand, natural hands arms head torso hips knees legs and walking balance, realistic cloth and environmental physics, photographic optics, natural depth of field and physically plausible lighting. "
            "Continuous believable speech performance suitable for audio-driven lip-sync. ABSOLUTELY NO cartoon, illustration, painting, anime, stylized 3D, game character, plastic CGI skin, doll face, frozen pose, malformed hands, readable text, subtitles, logo, watermark or celebrity likeness."
        )[:1900]
    if sections:
        final_narration = " ".join(str(sections[-1].get("narration") or "").split())
        if "suscrib" not in final_narration.lower():
            sections[-1]["narration"] = f"{final_narration} {_LONG_CTA}".strip()
    meta["sections"] = sections
    meta["section_voice_plans"] = voice_plans
    meta["cta_spoken"] = _LONG_CTA
    return meta


def run(minutes: int, publish: bool = False) -> dict:
    previous = _read_history()
    original_picker = base._pick_reference_seed
    original_generate = base._generate_metadata
    original_seed = base._seed
    original_visual = base._visual_for_section
    original_voice = base.make_natural_spanish_voice
    original_fit = base.fit_voice_to_duration
    original_thumbnail = base._thumbnail
    original_assemble = base._assemble
    captured: dict = {}

    base._pick_reference_seed = _reference_picker(previous)

    def safe_base_seed(meta: dict, index: int) -> int:
        return _safe_seed(original_seed(meta, index))

    def generate(channel: dict, requested_minutes: int) -> dict:
        meta = original_generate(channel, requested_minutes)
        meta = _enhance_metadata(meta, previous, requested_minutes)
        captured["meta"] = meta
        return meta

    def luminous_voice(path, text: str) -> str:
        used = original_voice(path, text)
        profile = polish_voice(path)
        return used if profile == "unprocessed" else f"{used}+{profile}"

    def strict_fit(path, target_seconds: float) -> None:
        stats = fit_and_validate_spiritual_voice(path, target_seconds)
        meta = captured.get("meta") or {}
        meta.update(stats)
        meta["voice_delivery"] = "single_continuous_full_duration_validated_track"

    def resilient_visual(meta: dict, section: dict, index: int, workdir, ai_slots: int, duration: int):
        prompt = section["visual_prompt"]
        require_live = os.getenv("SPIRITUAL_REQUIRE_LIVE_ACTION", "true").lower().strip() == "true"
        allow_still = os.getenv("SPIRITUAL_ALLOW_STILL_FALLBACK", "true").lower().strip() == "true"

        if index < ai_slots:
            ai_clip = workdir / f"spiritual_ai_key_{index + 1}.mp4"
            try:
                provider = base._try_text_to_video(prompt, ai_clip, safe_base_seed(meta, index))
                extended = workdir / f"spiritual_visual_{index + 1}.mp4"
                base._landscape_loop_video(ai_clip, extended, duration, index)
                return extended, provider
            except Exception as exc:
                if require_live and not allow_still:
                    raise
                print(f"T2V long no disponible en seccion {index + 1} ({exc}); usando imagen HF fotorrealista animada.")
        elif require_live and not allow_still:
            raise RuntimeError(f"Seccion {index + 1} fuera de slots T2V y fallback deshabilitado")

        image = workdir / f"spiritual_image_{index + 1}.jpg"
        visual = workdir / f"spiritual_visual_{index + 1}.mp4"
        provider = download_landscape_image(prompt, image, safe_base_seed(meta, index), base._character_style())
        base._image_motion(image, visual, duration, index)
        return visual, f"{provider} + cinematic motion fallback"

    def thumbnail_variants(video, workdir):
        primary, candidates = create_thumbnail_candidates(video, workdir)
        meta = captured.get("meta") or {}
        meta["thumbnail_variants"] = candidates
        meta["thumbnail_ab_note"] = "three candidates generated for YouTube Studio Test & Compare when available"
        return primary

    def assemble_with_cta(meta: dict, channel: dict, workdir, requested_minutes: int):
        video = original_assemble(meta, channel, workdir, requested_minutes)
        apply_long_cta_overlay(video, requested_minutes * 60)
        meta["cta_overlay"] = "SUSCRIBITE | COMPARTI | AMEN"
        return video

    base._seed = safe_base_seed
    base._generate_metadata = generate
    base._visual_for_section = resilient_visual
    base.make_natural_spanish_voice = luminous_voice
    base.fit_voice_to_duration = strict_fit
    base._thumbnail = thumbnail_variants
    base._assemble = assemble_with_cta
    try:
        result = base.run(minutes, publish=publish)
    finally:
        base._pick_reference_seed = original_picker
        base._generate_metadata = original_generate
        base._seed = original_seed
        base._visual_for_section = original_visual
        base.make_natural_spanish_voice = original_voice
        base.fit_voice_to_duration = original_fit
        base._thumbnail = original_thumbnail
        base._assemble = original_assemble

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
    result["title_variants"] = meta.get("title_variants") or []
    result["thumbnail_variants"] = meta.get("thumbnail_variants") or []
    result["pinned_comment_candidate"] = meta.get("pinned_comment_candidate")
    result["voice_continuity_passed"] = meta.get("voice_continuity_passed")
    result["voice_coverage_ratio"] = meta.get("voice_coverage_ratio")
    result["longest_voice_silence_seconds"] = meta.get("longest_voice_silence_seconds")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[5, 10, 15, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    result = run(args.minutes, publish=args.publish)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
