from __future__ import annotations

import hashlib
import re
from urllib.parse import quote_plus


# Curated from current Spanish YouTube keyword research (vidIQ, 2026-08-15).
# These are editorial opportunities, never guarantees of reach or virality.
KEYWORD_OPPORTUNITIES = (
    {"keyword": "Dios", "volume": 83.13, "competition": 56.2, "score": 67.40, "ar_volume": 38756},
    {"keyword": "Biblia", "volume": 85.47, "competition": 42.4, "score": 74.32, "ar_volume": 23104},
    {"keyword": "Jesucristo", "volume": 72.75, "competition": 31.0, "score": 71.25, "ar_volume": 2989},
    {"keyword": "Salmo 91", "volume": 86.78, "competition": 59.0, "score": 68.47, "ar_volume": 6750},
    {"keyword": "oración para dormir", "volume": 75.58, "competition": 38.5, "score": 69.95, "ar_volume": 5644},
    {"keyword": "salmos para dormir", "volume": 77.06, "competition": 42.0, "score": 69.43, "ar_volume": 5479},
    {"keyword": "palabra de Dios", "volume": 73.79, "competition": 40.0, "score": 68.28, "ar_volume": 2926},
    {"keyword": "oración poderosa", "volume": 72.51, "competition": 58.5, "score": 60.11, "ar_volume": 3003},
    {"keyword": "oración de la noche", "volume": 80.52, "competition": 74.0, "score": 58.71, "ar_volume": 2554},
)

REFERENCE_POOL = (
    "Salmo 23",
    "Salmo 27",
    "Salmo 46",
    "Salmo 91:1-2",
    "Isaías 41:10",
    "Mateo 5:1-12",
    "Mateo 6:25-34",
    "Mateo 11:28-30",
    "Marcos 4:35-41",
    "Lucas 15:1-7",
    "Juan 3:16-17",
    "Juan 14:27",
    "Romanos 8:26-28",
    "Filipenses 4:6-7",
    "1 Corintios 13:4-8",
)

_TOPIC_REFERENCES = (
    (r"ansiedad|preocup|mente|calma", "Filipenses 4:6-7"),
    (r"dormir|noche|descanso|insomnio", "Salmo 4:8"),
    (r"miedo|temor|fortaleza", "Isaías 41:10"),
    (r"tormenta|tempestad", "Marcos 4:35-41"),
    (r"cansad|carga|agotad", "Mateo 11:28-30"),
    (r"amor|perd[oó]n|paciencia", "1 Corintios 13:4-8"),
    (r"pastor|camino|valle", "Salmo 23"),
    (r"refugio|protecci[oó]n", "Salmo 91:1-2"),
    (r"orar|oraci[oó]n|sin palabras", "Romanos 8:26-28"),
    (r"paz", "Juan 14:27"),
)

RISKY_PACKAGING = (
    "milagro garantizado",
    "dios te hará rico",
    "dios te hara rico",
    "si no compartes",
    "si ignoras esto",
    "esto te pasará hoy",
    "esto te pasara hoy",
    "mensaje urgente de dios",
    "profecía para hoy",
    "profecia para hoy",
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _seed(metadata: dict) -> int:
    raw = "|".join(
        (
            _clean(metadata.get("topic")),
            _clean(metadata.get("title")),
            _clean(metadata.get("bible_reference")),
        )
    )
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _reference(metadata: dict) -> str:
    current = _clean(metadata.get("bible_reference"))
    if current:
        return current
    haystack = " ".join(
        (
            _clean(metadata.get("topic")),
            _clean(metadata.get("title")),
            _clean(metadata.get("description")),
        )
    ).lower()
    for pattern, reference in _TOPIC_REFERENCES:
        if re.search(pattern, haystack, re.IGNORECASE):
            return reference
    return REFERENCE_POOL[_seed(metadata) % len(REFERENCE_POOL)]


def _biblegateway_url(reference: str) -> str:
    # BibleGateway is used as a human-verifiable reference link only. The
    # automation intentionally does not scrape or republish its translation text.
    return f"https://www.biblegateway.com/passage/?search={quote_plus(reference)}&version=RVR1960"


def _select_keyword(metadata: dict) -> dict:
    haystack = " ".join(
        (
            _clean(metadata.get("topic")),
            _clean(metadata.get("title")),
            _clean(metadata.get("bible_reference")),
        )
    ).lower()
    preferences: list[str] = []
    if "91" in haystack or "refugio" in haystack or "protecci" in haystack:
        preferences += ["Salmo 91", "Dios", "Biblia"]
    if "dorm" in haystack or "noche" in haystack:
        preferences += ["oración para dormir", "salmos para dormir", "oración de la noche"]
    if "jes" in haystack or "cristo" in haystack:
        preferences += ["Jesucristo", "Biblia"]
    if "oraci" in haystack or "orar" in haystack:
        preferences += ["oración poderosa", "palabra de Dios"]
    preferences += ["Biblia", "Dios", "Jesucristo"]
    by_name = {row["keyword"]: row for row in KEYWORD_OPPORTUNITIES}
    for name in preferences:
        if name in by_name:
            return dict(by_name[name])
    return dict(KEYWORD_OPPORTUNITIES[0])


def _safe_title_variants(metadata: dict, keyword: str, reference: str, content_type: str) -> list[str]:
    topic = _clean(metadata.get("topic")) or "fe y esperanza"
    base = _clean(metadata.get("title"))
    if content_type == "short":
        candidates = [
            f"Cuando necesitás paz: {reference}",
            f"Una oración para hoy basada en {reference}",
            f"{keyword}: una palabra bíblica para este momento",
            base,
        ]
        limit = 90
    else:
        candidates = [
            f"{reference}: una oración para recuperar la paz y la esperanza",
            f"Cuando el corazón necesita a Dios | Reflexión y oración sobre {reference}",
            f"{keyword}: reflexión bíblica y oración para fortalecer tu fe",
            base,
        ]
        limit = 100

    out: list[str] = []
    for candidate in candidates:
        candidate = _clean(candidate)[:limit].rstrip(" -:,.!")
        lower = candidate.lower()
        if not candidate or any(risky in lower for risky in RISKY_PACKAGING):
            continue
        if lower not in {x.lower() for x in out}:
            out.append(candidate)
        if len(out) >= 3:
            break
    return out


def _hook_variants(reference: str) -> list[str]:
    return [
        f"Si hoy necesitás paz, esta enseñanza de {reference} puede acompañarte.",
        f"Hay momentos en los que el corazón se cansa. La Biblia nos orienta en {reference}.",
        f"Antes de seguir, regalate un minuto para orar y recordar el mensaje de {reference}.",
    ]


def _thumbnail_concepts(reference: str, content_type: str) -> list[str]:
    # Shorts cannot run YouTube native thumbnail A/B tests. These candidates are
    # for pre-publish scoring/cover selection; long-form candidates can be used
    # in YouTube Studio's native Test & Compare feature.
    if content_type == "short":
        return [
            f"close emotional cinematic portrait of the recurring synthetic Jesus character at sunrise, calm eye contact, visual theme of {reference}, no text, 9:16",
            f"wide cinematic scene of the recurring synthetic Jesus character beside still water and warm light, peaceful visual theme of {reference}, no text, 9:16",
            f"medium shot of the recurring synthetic Jesus character with an open hand gesture, dramatic but peaceful natural light, theme {reference}, no text, 9:16",
        ]
    return [
        f"cinematic close portrait of the recurring synthetic Jesus character, strong eye contact, one clear emotional focal point, theme {reference}, no text, 16:9",
        f"wide premium cinematic biblical landscape with the recurring synthetic Jesus character as the single focal subject, theme {reference}, no text, 16:9",
        f"medium cinematic prayer moment, recurring synthetic Jesus character in warm directional light, high contrast focal subject, theme {reference}, no text, 16:9",
    ]


def ground_and_optimize_spiritual_metadata(
    metadata: dict,
    previous: list[dict] | None = None,
    *,
    content_type: str = "short",
) -> dict:
    previous = previous or []
    reference = _reference(metadata)
    metadata["bible_reference"] = reference
    metadata["script_source_policy"] = "verified_reference_plus_original_paraphrase_no_automatic_biblegateway_scraping"
    metadata["source_references"] = [
        {
            "name": "BibleGateway",
            "type": "bible_reference",
            "reference": reference,
            "url": _biblegateway_url(reference),
            "usage": "reference_only_original_script_paraphrase",
        }
    ]
    metadata["source_grounded"] = True
    metadata["source_grounding_note"] = (
        "El guion debe ser original y fiel al sentido general de la referencia; no atribuir citas textuales "
        "inventadas a Dios o a Jesús y no copiar automáticamente traducciones protegidas."
    )

    keyword = _select_keyword(metadata)
    metadata["seo_primary_keyword"] = keyword["keyword"]
    metadata["seo_keyword_signal"] = keyword
    metadata["seo_research_snapshot"] = "vidIQ Spanish/Argentina keyword research 2026-08-15"

    titles = _safe_title_variants(metadata, keyword["keyword"], reference, content_type)
    if titles:
        metadata["title"] = titles[0]
    metadata["title_variants"] = titles
    metadata["hook_variants"] = _hook_variants(reference)
    metadata["thumbnail_candidates"] = _thumbnail_concepts(reference, content_type)

    metadata["algorithm_strategy"] = {
        "appeal": "clear human need + specific biblical reference + honest emotional promise",
        "engagement": "fast opening, narrative progression, no filler, calm continuous voice",
        "satisfaction": "resolve the opening with a useful biblical reflection or prayer instead of manipulative clickbait",
        "learning_loop": "prefer themes/titles that improve retention, shares, comments and subscriber-gain rate in this channel's own analytics",
    }
    metadata["trend_pattern"] = "specific_need_plus_scripture_plus_emotional_payoff_truthful"
    metadata["growth_kpis"] = [
        "views_per_hour",
        "average_view_percentage",
        "watch_time",
        "share_rate",
        "comment_rate",
        "subscriber_gain_rate",
    ]
    metadata["viral_guarantee"] = False
    metadata["no_deceptive_clickbait"] = True
    metadata["recent_learning_examples"] = len(previous[-30:])

    if content_type == "short":
        metadata["native_youtube_ab_test_available"] = False
        metadata["ab_strategy"] = "prepublish_score_3_title_hook_cover_candidates_then_learn_from_channel_metrics"
    else:
        metadata["native_youtube_ab_test_available"] = True
        metadata["ab_strategy"] = "generate_3_title_and_thumbnail_candidates_for_youtube_studio_test_and_compare"

    description = _clean(metadata.get("description"))
    source_line = f"Referencia para profundizar: {reference} — BibleGateway."
    if reference.lower() not in description.lower():
        description = f"{description}\n\n{source_line}".strip()
    metadata["description"] = description[:4700]
    return metadata
