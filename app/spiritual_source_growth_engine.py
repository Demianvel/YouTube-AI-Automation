from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote_plus


# Editorial opportunities only; never guarantees of reach or virality.
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

MARKET_SIGNAL_PATH = Path("state/dioshablahoyia_market_signals.json")

REFERENCE_POOL = (
    "Salmo 23", "Salmo 27", "Salmo 46", "Salmo 91:1-2", "Isaías 41:10",
    "Mateo 5:1-12", "Mateo 6:25-34", "Mateo 11:28-30", "Marcos 4:35-41",
    "Lucas 15:1-7", "Juan 3:16-17", "Juan 14:27", "Romanos 8:26-28",
    "Filipenses 4:6-7", "1 Corintios 13:4-8",
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
    "milagro garantizado", "dios te hará rico", "dios te hara rico",
    "si no compartes", "si ignoras esto", "esto te pasará hoy",
    "esto te pasara hoy", "mensaje urgente de dios", "profecía para hoy",
    "profecia para hoy",
)

_SHORT_TITLE_TEMPLATES = (
    "{topic} | Una enseñanza bíblica para hoy",
    "Cuando el corazón necesita descanso | {reference}",
    "Dios sigue presente en el proceso | {reference}",
    "Una luz para atravesar este momento | {reference}",
    "Jesús trae serenidad al corazón cansado",
    "Lo que la Biblia enseña cuando nada parece cambiar",
    "Volver a confiar paso a paso | {reference}",
    "Una palabra de esperanza para el día de hoy",
    "Fe para seguir caminando aun sin ver el resultado",
    "El silencio no significa ausencia | Reflexión cristiana",
    "Esta enseñanza puede ayudarte a recuperar la calma | {reference}",
    "Dios obra también en los procesos que no entendemos",
    "Una oración breve para ordenar el corazón",
    "Jesús conoce la carga que hoy llevás | {reference}",
    "La paz de Dios en medio de la incertidumbre",
    "No estás solo en esta etapa | Mensaje de fe",
    "Volver a empezar con esperanza y misericordia",
    "Una enseñanza de Jesús para transformar este día",
    "La Biblia y el valor de confiar un día a la vez",
    "{keyword}: una reflexión serena basada en {reference}",
    "Respirá y recordá esta verdad bíblica | {reference}",
    "Una promesa de esperanza, sin miedo ni presión | {reference}",
    "Cómo sostener la fe cuando el camino se hace difícil",
    "{topic} | Fe, paz y esperanza",
)

_LONG_TITLE_TEMPLATES = (
    "{topic} | Reflexión bíblica y oración",
    "{reference}: una enseñanza para recuperar la paz y la esperanza",
    "Cuando el corazón necesita a Dios | Reflexión sobre {reference}",
    "{keyword}: Biblia, contexto y aplicación para la vida",
    "Volver a confiar en Dios | Una reflexión profunda sobre {topic}",
    "{topic}: historia, enseñanza y oración",
    "Fe para el camino | Estudio y reflexión sobre {reference}",
    "Una pausa para escuchar la Palabra | {topic}",
    "Cómo llevar esta enseñanza bíblica a la vida cotidiana | {reference}",
    "Dios, Jesús y la esperanza que permanece | {topic}",
    "Una reflexión cristiana serena para fortalecer el corazón",
    "{topic} | Un recorrido de fe, paz y amor",
)

_HOOK_TEMPLATES = (
    "Si hoy necesitás paz, esta enseñanza de {reference} puede acompañarte.",
    "Hay momentos en los que el corazón se cansa; la Biblia nos orienta en {reference}.",
    "Antes de seguir, regalate un momento para respirar y recordar el mensaje de {reference}.",
    "Cuando no entendemos el proceso, {reference} nos ayuda a volver a mirar con fe.",
    "Esta reflexión no promete soluciones mágicas: ofrece una enseñanza bíblica para caminar con esperanza.",
    "Tal vez hoy no necesites más ruido, sino una palabra serena basada en {reference}.",
    "¿Cómo seguir confiando cuando nada cambia rápido? Empecemos por {reference}.",
    "Jesús no niega nuestras cargas; nos enseña a atravesarlas de otra manera.",
    "Una pausa breve puede ayudarnos a escuchar lo que la preocupación no deja ver.",
    "La fe no elimina todas las preguntas, pero puede darnos un próximo paso.",
    "En {reference} encontramos una verdad sencilla para este momento.",
    "Respirá con calma: esta enseñanza bíblica puede ayudarte a ordenar el corazón.",
)

_THUMBNAIL_SHORT = (
    "close emotional cinematic portrait of the recurring synthetic Jesus character at sunrise, calm eye contact, visual theme of {reference}, no text, 9:16",
    "wide cinematic scene of the recurring synthetic Jesus character beside still water and warm light, peaceful visual theme of {reference}, no text, 9:16",
    "medium shot of the recurring synthetic Jesus character with an open hand gesture, peaceful natural light, theme {reference}, no text, 9:16",
    "full-body cinematic shot of the recurring synthetic Jesus character walking on a real mountain path at dawn, theme {reference}, no text, 9:16",
    "open Bible in natural golden light with the recurring synthetic Jesus character softly visible in the background, theme {reference}, no text, 9:16",
    "symbolic cross and luminous sky above a real valley, recurring synthetic Jesus character in side profile, theme {reference}, no text, 9:16",
)

_THUMBNAIL_LONG = (
    "cinematic close portrait of the recurring synthetic Jesus character, strong calm eye contact, one clear emotional focal point, theme {reference}, no text, 16:9",
    "wide premium cinematic biblical landscape with the recurring synthetic Jesus character as the focal subject, theme {reference}, no text, 16:9",
    "medium cinematic prayer moment, recurring synthetic Jesus character in warm directional light, theme {reference}, no text, 16:9",
    "open Bible and simple wooden cross in real sunrise light with Jesus in the middle distance, theme {reference}, no text, 16:9",
    "full-body walking shot of Jesus beside living water and olive trees, premium live-action cinema, theme {reference}, no text, 16:9",
    "reverent symbolic scene of hope with light breaking through storm clouds and Jesus in profile, theme {reference}, no text, 16:9",
)


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _seed(metadata: dict) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = "|".join((
        _clean(metadata.get("topic")), _clean(metadata.get("title")),
        _clean(metadata.get("bible_reference")), marker,
    ))
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _market_signals() -> dict:
    if not MARKET_SIGNAL_PATH.exists():
        return {}
    try:
        data = json.loads(MARKET_SIGNAL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _reference(metadata: dict) -> str:
    current = _clean(metadata.get("bible_reference"))
    if current:
        return current
    haystack = " ".join((
        _clean(metadata.get("topic")), _clean(metadata.get("title")),
        _clean(metadata.get("description")),
    )).lower()
    for pattern, reference in _TOPIC_REFERENCES:
        if re.search(pattern, haystack, re.IGNORECASE):
            return reference
    return REFERENCE_POOL[_seed(metadata) % len(REFERENCE_POOL)]


def _biblegateway_url(reference: str) -> str:
    return f"https://www.biblegateway.com/passage/?search={quote_plus(reference)}&version=RVR1960"


def _market_keyword_preferences(signals: dict, haystack: str) -> list[str]:
    mapping = {
        "dios": "Dios", "biblia": "Biblia", "jesús": "Jesucristo",
        "jesucristo": "Jesucristo", "salmo 91": "Salmo 91",
        "oración": "oración poderosa", "noche": "oración de la noche",
        "dormir": "oración para dormir", "salmos": "salmos para dormir",
    }
    out: list[str] = []
    for row in signals.get("top_terms") or []:
        term = _clean((row or {}).get("term")).lower()
        candidate = mapping.get(term)
        if not candidate:
            continue
        if term in ("noche", "dormir", "salmos", "salmo 91") and not any(
            x in haystack for x in ("noche", "dorm", "salmo", "91", "refugio", "protecci")
        ):
            continue
        if candidate not in out:
            out.append(candidate)
    return out


def _select_keyword(metadata: dict, signals: dict) -> dict:
    haystack = " ".join((
        _clean(metadata.get("topic")), _clean(metadata.get("title")),
        _clean(metadata.get("bible_reference")),
    )).lower()
    market_preferences = _market_keyword_preferences(signals, haystack)
    preferences: list[str] = list(market_preferences)
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
            result = dict(by_name[name])
            result["market_boosted"] = name in market_preferences
            return result
    return dict(KEYWORD_OPPORTUNITIES[0])


def _compact_topic(metadata: dict) -> str:
    topic = _clean(metadata.get("topic") or metadata.get("content_family") or "Fe, paz y esperanza")
    topic = re.sub(r"\([^)]{25,}\)", "", topic).strip(" -:,.!")
    return topic[:56].rstrip(" -:,.!") or "Fe, paz y esperanza"


def _safe_title_variants(
    metadata: dict,
    keyword: str,
    reference: str,
    content_type: str,
    previous: list[dict],
) -> list[str]:
    templates = _SHORT_TITLE_TEMPLATES if content_type == "short" else _LONG_TITLE_TEMPLATES
    limit = 90 if content_type == "short" else 100
    topic = _compact_topic(metadata)
    seed = _seed(metadata)
    recent = {_normalize(item.get("title", "")) for item in previous[-50:] if item.get("title")}
    candidates: list[str] = []

    for step in range(len(templates)):
        template = templates[(seed + step * 7) % len(templates)]
        candidate = _clean(template.format(
            topic=topic, reference=reference, keyword=keyword,
        ))[:limit].rstrip(" -:,.!")
        lower = candidate.lower()
        normalized = _normalize(candidate)
        if not candidate or normalized in recent or any(risky in lower for risky in RISKY_PACKAGING):
            continue
        if normalized not in {_normalize(value) for value in candidates}:
            candidates.append(candidate)
        if len(candidates) >= 3:
            return candidates

    base = _clean(metadata.get("title"))[:limit].rstrip(" -:,.!")
    if base and _normalize(base) not in recent and not any(risky in base.lower() for risky in RISKY_PACKAGING):
        candidates.append(base)

    fallback = f"{topic} | {reference}"[:limit].rstrip(" -:,.!")
    if _normalize(fallback) not in {_normalize(value) for value in candidates}:
        candidates.append(fallback)
    return candidates[:3]


def _hook_variants(metadata: dict, reference: str) -> list[str]:
    seed = _seed(metadata)
    out: list[str] = []
    for step in range(len(_HOOK_TEMPLATES)):
        hook = _HOOK_TEMPLATES[(seed + step * 5) % len(_HOOK_TEMPLATES)].format(reference=reference)
        if hook not in out:
            out.append(hook)
        if len(out) >= 3:
            break
    return out


def _thumbnail_concepts(metadata: dict, reference: str, content_type: str) -> list[str]:
    pool = _THUMBNAIL_SHORT if content_type == "short" else _THUMBNAIL_LONG
    seed = _seed(metadata)
    out: list[str] = []
    for step in range(len(pool)):
        prompt = pool[(seed + step * 5) % len(pool)].format(reference=reference)
        if prompt not in out:
            out.append(prompt)
        if len(out) >= 3:
            break
    return out


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
    metadata["source_references"] = [{
        "name": "BibleGateway",
        "type": "bible_reference",
        "reference": reference,
        "url": _biblegateway_url(reference),
        "usage": "reference_only_original_script_paraphrase",
    }]
    metadata["source_grounded"] = True
    metadata["source_grounding_note"] = (
        "El guion debe ser original y fiel al sentido general de la referencia; no atribuir citas textuales "
        "inventadas a Dios o a Jesús y no copiar automáticamente traducciones protegidas."
    )

    signals = _market_signals()
    keyword = _select_keyword(metadata, signals)
    metadata["seo_primary_keyword"] = keyword["keyword"]
    metadata["seo_keyword_signal"] = keyword
    metadata["seo_research_snapshot"] = "Spanish/Argentina channel keyword opportunity snapshot"
    metadata["market_signal_snapshot"] = {
        "generated_at": signals.get("generated_at"),
        "window_hours": signals.get("window_hours"),
        "videos_analyzed": signals.get("videos_analyzed"),
        "top_terms": (signals.get("top_terms") or [])[:6],
        "method": signals.get("method"),
    }

    titles = _safe_title_variants(
        metadata, keyword["keyword"], reference, content_type, previous,
    )
    if titles:
        metadata["title"] = titles[0]
    metadata["title_variants"] = titles
    metadata["hook_variants"] = _hook_variants(metadata, reference)
    metadata["thumbnail_candidates"] = _thumbnail_concepts(metadata, reference, content_type)
    metadata["recent_title_comparison_count"] = len(previous[-50:])
    metadata["seo_title_history_guard_passed"] = bool(titles)

    metadata["algorithm_strategy"] = {
        "appeal": "clear human need + specific biblical reference + honest emotional promise",
        "engagement": "fast opening, narrative progression, no filler, calm continuous voice",
        "satisfaction": "resolve the opening with a useful biblical reflection or prayer instead of manipulative clickbait",
        "learning_loop": "prefer themes and packaging that improve retention, shares, comments and subscriber-gain rate in this channel's own analytics",
    }
    metadata["trend_pattern"] = "specific_need_plus_scripture_plus_emotional_payoff_truthful_high_variety"
    metadata["growth_kpis"] = [
        "views_per_hour", "average_view_percentage", "watch_time",
        "share_rate", "comment_rate", "subscriber_gain_rate",
    ]
    metadata["viral_guarantee"] = False
    metadata["no_deceptive_clickbait"] = True
    metadata["recent_learning_examples"] = len(previous[-30:])

    if content_type == "short":
        metadata["native_youtube_ab_test_available"] = False
        metadata["ab_strategy"] = "prepublish_score_3_unique_title_hook_cover_candidates_then_learn_from_channel_metrics"
    else:
        metadata["native_youtube_ab_test_available"] = True
        metadata["ab_strategy"] = "generate_3_unique_title_and_thumbnail_candidates_for_youtube_studio_test_and_compare"

    description = str(metadata.get("description") or "").strip()
    source_line = f"Referencia para profundizar: {reference} — BibleGateway."
    if reference.lower() not in description.lower():
        description = f"{description}\n\n{source_line}".strip()
    metadata["description"] = description[:4700]
    return metadata
