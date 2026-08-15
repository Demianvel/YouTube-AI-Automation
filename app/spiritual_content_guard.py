from __future__ import annotations

import re
import unicodedata


_SPIRITUAL_ANCHORS = (
    "dios", "jesus", "jesucristo", "cristo", "biblia", "biblico", "evangelio",
    "salmo", "oracion", "fe", "gracia", "espiritu santo", "senor", "mesias",
    "mateo", "marcos", "lucas", "juan", "romanos", "filipenses", "isaias",
    "genesis", "daniel", "apocalipsis", "reyes", "zacarías", "zacarías",
    "miqueas", "jonas", "noe", "elias", "jerusalen", "cristiana", "cristiano",
)

_FORBIDDEN_EXTERNAL_SOURCES = (
    "wikipedia", "wikimedia", "commons", "pexels", "pixabay", "unsplash",
    "tiktok", "instagram", "facebook", "shutterstock", "getty", "stock footage",
    "stock video", "archivo de terceros", "third-party footage",
)

_OFF_TOPIC_TERMS = (
    "elecciones", "partido politico", "politica partidaria", "presidente actual",
    "futbol", "formula 1", "criptomoneda", "bitcoin", "casino", "apuestas",
    "pornografia", "contenido sexual", "desnudez", "drogas recreativas",
    "narcotrafico", "armas de fuego", "gore", "sangre explicita",
    "celebridad", "chisme", "noticias de famosos",
)

_DECEPTIVE_TERMS = (
    "si no compartes", "si no compartís", "comparte para recibir un milagro",
    "comparti para recibir un milagro", "dios te hara rico", "dios te hará rico",
    "milagro garantizado", "cura garantizada", "dinero garantizado",
    "esto te pasara hoy", "esto te pasará hoy", "profecia para hoy",
    "profecía para hoy", "mensaje urgente de dios", "dios me revelo",
    "dios me reveló", "si ignoras esto", "si ignorás esto",
)

_ALLOWED_TAGS = (
    "dios", "jesus", "jesucristo", "cristo", "biblia", "fe", "oracion",
    "esperanza", "paz", "amor", "evangelio", "salmos", "reflexion cristiana",
    "dios habla hoy", "shorts",
)


def _normalize(value: object) -> str:
    text = " ".join(str(value or "").split()).lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _contains_any(text: str, terms: tuple[str, ...]) -> list[str]:
    normalized = _normalize(text)
    hits: list[str] = []
    for term in terms:
        if _normalize(term) in normalized:
            hits.append(term)
    return hits


def _editorial_text(metadata: dict) -> str:
    chunks = [
        metadata.get("topic", ""), metadata.get("content_family", ""),
        metadata.get("hook", ""), metadata.get("title", ""),
        metadata.get("description", ""), metadata.get("cta", ""),
    ]
    chunks.extend(metadata.get("tags") or [])
    chunks.extend(metadata.get("hashtags") or [])
    for scene in metadata.get("scenes") or []:
        chunks.extend([
            scene.get("narration", ""), scene.get("visual_prompt", ""),
            scene.get("stock_query", ""),
        ])
    return " ".join(str(x or "") for x in chunks)


def _assert_spiritual_scope(metadata: dict) -> None:
    editorial = _editorial_text(metadata)
    if not _contains_any(editorial, _SPIRITUAL_ANCHORS):
        raise RuntimeError(
            "BLOQUEADO POR GUARDIA EDITORIAL: el contenido no esta claramente relacionado con Dios, Jesus o la Biblia."
        )

    external = _contains_any(editorial, _FORBIDDEN_EXTERNAL_SOURCES)
    if external:
        raise RuntimeError(
            "BLOQUEADO POR GUARDIA EDITORIAL: se detecto una fuente externa prohibida: " + ", ".join(external)
        )

    off_topic = _contains_any(editorial, _OFF_TOPIC_TERMS)
    if off_topic:
        raise RuntimeError(
            "BLOQUEADO POR GUARDIA EDITORIAL: se detecto contenido ajeno al canal: " + ", ".join(off_topic)
        )

    deceptive = _contains_any(editorial, _DECEPTIVE_TERMS)
    if deceptive:
        raise RuntimeError(
            "BLOQUEADO POR GUARDIA EDITORIAL: se detecto lenguaje enganoso o manipulador: " + ", ".join(deceptive)
        )


def enforce_spiritual_topic_guard(metadata: dict) -> dict:
    """Lock Dios Habla Hoy IA to original Jesus/God/Bible content before rendering."""
    metadata = dict(metadata)
    scenes = [dict(scene) for scene in (metadata.get("scenes") or [])]

    for scene in scenes:
        visual = " ".join(str(scene.get("visual_prompt") or "").split()).strip()
        if not _contains_any(visual, _SPIRITUAL_ANCHORS):
            visual = (
                "Original synthetic cinematic representation of Jesus in a peaceful biblical reflection about God. "
                + visual
            ).strip()
        scene["visual_prompt"] = visual[:1900]
        # This field is kept only for schema compatibility. The spiritual channel
        # must not search or reuse third-party stock media.
        scene["stock_query"] = "original synthetic Jesus God Bible cinematic scene no stock media"

    metadata["scenes"] = scenes
    metadata["source_credits"] = []
    metadata["external_media_allowed"] = False
    metadata["wikipedia_allowed"] = False
    metadata["wikimedia_commons_allowed"] = False
    metadata["third_party_stock_allowed"] = False
    metadata["original_generated_media_only"] = True
    metadata["editorial_scope"] = "Jesus_Dios_Biblia_oracion_fe_only"
    metadata["youtube_safety_profile"] = "strict_spiritual_original_v1"
    metadata["contains_synthetic_media"] = True

    description = " ".join(str(metadata.get("description") or "").split()).strip()
    disclosure = (
        "Contenido cristiano original. La representación visual de Jesús es artística y generada digitalmente; "
        "no es una grabación literal de un hecho real."
    )
    if "representacion visual de jesus" not in _normalize(description):
        description = (description + "\n\n" + disclosure).strip()
    metadata["description"] = description[:4600]

    tags: list[str] = []
    for tag in metadata.get("tags") or []:
        clean = " ".join(str(tag).split()).strip()
        normalized = _normalize(clean)
        if clean and any(_normalize(allowed) in normalized for allowed in _ALLOWED_TAGS):
            tags.append(clean)
    for required in ("Dios", "Jesus", "Biblia", "Fe", "Oracion", "Dios Habla Hoy"):
        if _normalize(required) not in {_normalize(x) for x in tags}:
            tags.append(required)
    metadata["tags"] = tags[:15]

    hashtags = ["#Dios", "#Jesus", "#Biblia", "#Fe", "#Shorts"]
    metadata["hashtags"] = hashtags

    _assert_spiritual_scope(metadata)
    metadata["editorial_guard_passed"] = True
    return metadata


def validate_spiritual_upload_guard(metadata: dict) -> dict:
    """Final fail-closed check immediately before a spiritual upload."""
    _assert_spiritual_scope(metadata)

    credits = metadata.get("source_credits") or []
    if credits:
        raise RuntimeError(
            "BLOQUEADO ANTES DE YOUTUBE: Dios Habla Hoy IA no permite multimedia externa ni creditos de terceros."
        )

    providers = metadata.get("generated_visual_provider") or metadata.get("visual_providers") or []
    if not isinstance(providers, (list, tuple)):
        providers = [providers]
    provider_text = " ".join(str(x or "") for x in providers)
    external = _contains_any(provider_text, _FORBIDDEN_EXTERNAL_SOURCES)
    if external:
        raise RuntimeError(
            "BLOQUEADO ANTES DE YOUTUBE: el renderer intento usar una fuente visual externa prohibida: "
            + ", ".join(external)
        )

    if metadata.get("external_media_allowed") is True:
        raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: external_media_allowed no puede ser true en este canal.")

    metadata["youtube_safety_guard_passed"] = True
    metadata["youtube_safety_guard_mode"] = "fail_closed_original_spiritual_only"
    return metadata
