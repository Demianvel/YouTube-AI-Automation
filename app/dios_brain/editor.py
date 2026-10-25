"""Quality editor agent: final gate for script + metadata before rendering.

Rejects packages that are repetitive vs recent uploads, too long/short,
misleading, or that break YouTube policies for this channel: claiming to be
God's literal voice, medical or financial promises, dated prophecies, and
engagement bait ("compartí o mala suerte"). It also keeps the synthetic-media
disclosure true (containsSyntheticMedia + description disclosure).
"""
from __future__ import annotations

import re

from .pillars import normalize

HARD_POLICY_PATTERNS: dict[str, tuple[str, ...]] = {
    "literal_voice_of_god": (
        r"\bsoy dios\b", r"\byo soy tu dios\b", r"\bdios te dice\b", r"\bjesus te dice\b",
        r"\bdios me dijo\b", r"\bdios me revelo\b", r"\besta es la voz de dios\b",
        r"\bla voz de dios te\b", r"\bdios te habla directamente\b", r"\bmensaje directo de dios\b",
        r"\bhabla dios\s*:", r"\bsoy jesus\b",
    ),
    "medical_promise": (
        r"\bte cura\b", r"\bcura tu\b", r"\bcura garantizada\b", r"\bsanacion garantizada\b",
        r"\bdeja(r|)? (tu|tus) (medicacion|medicamentos|tratamiento)\b", r"\bsin medicos\b",
        r"\bcancer\b", r"\bdiabetes\b",
    ),
    "financial_promise": (
        r"\bte hara rico\b", r"\bprosperidad garantizada\b", r"\bdinero garantizado\b",
        r"\btus deudas desaparecer", r"\bloteria\b", r"\brecibiras dinero\b", r"\bdinero\b", r"\briqueza\b",
    ),
    "dated_prophecy": (
        r"\bprofecia para (hoy|este|esta)\b", r"\bva a pasar el\b",
        r"\b\d{1,2} de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b",
        r"\bantes de que termine (el|la) (ano|semana|mes)\b", r"\ben las proximas \d+ (horas|dias)\b",
        r"\b(hoy|esta semana) recibiras\b", r"\bmilagro garantizado\b", r"\b20\d{2}\b",
    ),
    "engagement_bait": (
        r"\bmala suerte\b", r"\bsi no (compartes|compartis|comentas|comentas|lo compartis|escribis)\b",
        r"\bdale like o\b", r"\bsi ignoras esto\b", r"\bno ignores\b", r"\bno es casualidad que\b",
        r"\bcomparti(lo)? en \d+ grupos\b", r"\b\d+ anos de\b", r"\burgente\b", r"\bultimo aviso\b",
        r"\bcomparte para recibir\b", r"\bcomparti para recibir\b",
    ),
    "misleading_media": (
        r"\bvideo real de jesus\b", r"\bgrabacion real\b", r"\bno es ia\b", r"\bimagen real de dios\b",
    ),
}

MAX_TITLE = 70


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()


def script_text(metadata: dict) -> str:
    return " ".join(_clean(scene.get("narration")) for scene in metadata.get("scenes") or [])


def policy_violations(metadata: dict) -> list[str]:
    parts = [metadata.get("title"), metadata.get("description"), metadata.get("cta"), metadata.get("cta_spoken"), script_text(metadata)]
    text = normalize(" ".join(_clean(p) for p in parts))
    hits: list[str] = []
    for category, patterns in HARD_POLICY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                hits.append(f"{category}:{pattern}")
                break
    return hits


def review(metadata: dict, previous: list[dict], budget: tuple[int, int] | None = None) -> tuple[bool, list[str]]:
    reasons: list[str] = list(policy_violations(metadata))
    title = _clean(metadata.get("title"))
    if not (15 <= len(title) <= MAX_TITLE):
        reasons.append(f"title_length:{len(title)}")
    if title.isupper() or "!!" in title or "??" in title:
        reasons.append("title_shouting")

    scenes = metadata.get("scenes") or []
    if not scenes or any(len(_clean(s.get("narration")).split()) < 4 for s in scenes):
        reasons.append("empty_or_tiny_scene")
    words = len(script_text(metadata).split())
    if budget:
        max_words, min_words = budget
        if words > max_words + 3:
            reasons.append(f"script_too_long:{words}>{max_words}")
        if words < max(60, min_words - 15):
            reasons.append(f"script_too_short:{words}")
    hook = _clean(scenes[0].get("narration")) if scenes else ""
    first_sentence = re.split(r"(?<=[.!?])\s+", hook)[0] if hook else ""
    if len(first_sentence.split()) > 9:
        reasons.append("hook_not_in_first_2_seconds")

    description = _clean(metadata.get("description"))
    if len(description) > 4500:
        reasons.append("description_too_long")
    hashtags = [str(t) for t in metadata.get("hashtags") or []]
    if not (3 <= len(hashtags) <= 5) or "#shorts" not in {t.lower() for t in hashtags}:
        reasons.append("hashtags_invalid")
    if metadata.get("contains_synthetic_media") is False:
        reasons.append("synthetic_disclosure_disabled")

    uploaded = [r for r in previous or [] if str(r.get("status") or "").lower() == "uploaded"][-15:]
    script = normalize(script_text(metadata))[:1200]
    for row in uploaded:
        old_title = _clean(row.get("title"))
        if old_title and _similarity(title, old_title) >= 0.85:
            reasons.append(f"title_repeats_recent:{old_title[:40]}")
            break
    for row in uploaded:
        old = normalize(row.get("narration_preview"))
        if old and script and _similarity(script, old) >= 0.72:
            reasons.append("script_repeats_recent")
            break
    recent_hooks = [str(r.get("brain_hook_id") or "") for r in uploaded[-3:]]
    if metadata.get("brain_hook_id") and metadata.get("brain_hook_id") in recent_hooks:
        reasons.append("hook_repeats_recent")
    return (not reasons), reasons
