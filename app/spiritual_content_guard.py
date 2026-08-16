from __future__ import annotations

import hashlib
import unicodedata


_SPIRITUAL_ANCHORS = (
    "dios", "jesus", "jesucristo", "cristo", "biblia", "biblico", "evangelio",
    "salmo", "oracion", "fe", "gracia", "espiritu santo", "senor", "mesias",
    "mateo", "marcos", "lucas", "juan", "romanos", "filipenses", "isaias",
    "genesis", "daniel", "apocalipsis", "reyes", "zacarias", "miqueas",
    "jonas", "noe", "elias", "jerusalen", "cristiana", "cristiano",
)

_FORBIDDEN_EXTERNAL_SOURCES = (
    "wikipedia", "wikimedia", "commons", "pexels", "pixabay", "unsplash",
    "tiktok", "instagram", "facebook", "shutterstock", "getty", "stock footage",
    "stock video", "archivo de terceros", "third-party footage",
)

_OFF_TOPIC_TERMS = (
    "elecciones", "partido politico", "politica partidaria", "presidente actual",
    "futbol", "formula 1", "criptomoneda", "bitcoin", "casino", "apuestas",
    "celebridad", "chisme", "noticias de famosos", "videojuego", "review de producto",
)

_SAFETY_BLOCK_TERMS = (
    "pornografia", "contenido sexual explicito", "desnudez sexual", "abuso sexual",
    "autolesion", "como suicidarse", "metodo de suicidio", "odio contra",
    "supremacia racial", "terrorismo", "como fabricar explosivos", "como fabricar armas",
    "venta de drogas", "narcotrafico", "armas de fuego", "gore", "decapitacion",
    "tortura grafica", "sangre explicita", "maltrato animal", "estafa", "phishing",
)

_DECEPTIVE_TERMS = (
    "si no compartes", "si no compartís", "comparte para recibir un milagro",
    "comparti para recibir un milagro", "dios te hara rico", "dios te hará rico",
    "milagro garantizado", "cura garantizada", "dinero garantizado",
    "esto te pasara hoy", "esto te pasará hoy", "profecia para hoy",
    "profecía para hoy", "mensaje urgente de dios", "dios me revelo",
    "dios me reveló", "si ignoras esto", "si ignorás esto",
)

# Six safe SEO families rotate with the actual subject. Each pack stays well
# below YouTube's 500-character API cost, leaving room for one or two specific
# tags derived from the biblical reference and topic of each upload.
_TAG_PACKS = {
    "peace": (
        "Dios", "Jesús", "Biblia", "Paz de Dios", "Serenidad en Dios",
        "Esperanza cristiana", "Reflexión bíblica para el alma",
        "Palabra de Dios para hoy", "Fe en momentos difíciles",
        "Oración para encontrar paz", "Confianza en Dios cada día",
        "Jesús trae paz al corazón", "Mensajes cristianos de esperanza",
        "Dios Habla Hoy", "Amor de Dios", "Descanso en Dios",
        "Versículos de fe y consuelo", "Shorts cristianos",
    ),
    "prayer": (
        "Dios", "Jesús", "Biblia", "Oración cristiana", "Oración de la mañana",
        "Oración de la noche", "Oración para dormir en paz",
        "Fe y esperanza en Dios", "Palabra de Dios para hoy",
        "Reflexión cristiana diaria", "Jesucristo y la Biblia",
        "Paz interior con Dios", "Oración para la familia",
        "Confianza en el Señor", "Dios Habla Hoy",
        "Mensajes de amor y consuelo", "Versículos bíblicos", "Shorts de oración",
    ),
    "jesus": (
        "Dios", "Jesús", "Jesucristo", "Biblia", "Enseñanzas de Jesús",
        "Palabras de Jesús", "Evangelio de Jesucristo", "Reflexión sobre Jesús",
        "Fe en Cristo", "Amor de Dios", "Esperanza en Jesucristo",
        "Jesús es el buen pastor", "Camino verdad y vida",
        "Mensaje cristiano para hoy", "Biblia y fe", "Dios Habla Hoy",
        "Videos cristianos", "Shorts cristianos",
    ),
    "bible": (
        "Dios", "Jesús", "Biblia", "Palabra de Dios", "Reflexión bíblica",
        "Estudio bíblico breve", "Versículos bíblicos", "Evangelio para hoy",
        "Enseñanzas de la Biblia", "Fe esperanza y amor", "Promesas bíblicas",
        "Historias de la Biblia", "Jesucristo en la Biblia",
        "Mensaje cristiano diario", "Paz y consuelo espiritual",
        "Dios Habla Hoy", "Videos de fe", "Shorts bíblicos",
    ),
    "strength": (
        "Dios", "Jesús", "Biblia", "Fortaleza espiritual",
        "Fe en tiempos difíciles", "Esperanza cuando todo duele",
        "Dios acompaña tu camino", "Confianza en Dios", "Oración por fortaleza",
        "Paz en la tormenta", "Jesús sostiene al cansado",
        "Palabra de aliento cristiana", "Reflexión para no rendirse",
        "Amor y cuidado de Dios", "Versículos de esperanza",
        "Dios Habla Hoy", "Mensajes cristianos", "Shorts de fe",
    ),
    "love": (
        "Dios", "Jesús", "Biblia", "Amor de Dios", "Misericordia de Dios",
        "Perdón y nuevo comienzo", "Jesús y el amor al prójimo",
        "Gracia de Dios", "Reflexión cristiana sobre el amor",
        "Fe esperanza y caridad", "Palabra de Dios para el corazón",
        "Compasión cristiana", "Evangelio y misericordia",
        "Oración por paz y amor", "Dios Habla Hoy",
        "Enseñanzas de Jesucristo", "Videos cristianos", "Shorts cristianos",
    ),
}


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


def _youtube_tag_cost(tags: tuple[str, ...] | list[str]) -> int:
    if not tags:
        return 0
    content = sum(len(tag) + (2 if " " in tag else 0) for tag in tags)
    return content + len(tags) - 1


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

    unsafe = _contains_any(editorial, _SAFETY_BLOCK_TERMS)
    if unsafe:
        raise RuntimeError(
            "BLOQUEADO POR SEGURIDAD YOUTUBE: se detecto contenido sensible o dañino fuera del perfil pacifico del canal: "
            + ", ".join(unsafe)
        )

    deceptive = _contains_any(editorial, _DECEPTIVE_TERMS)
    if deceptive:
        raise RuntimeError(
            "BLOQUEADO POR GUARDIA EDITORIAL: se detecto lenguaje enganoso o manipulador: " + ", ".join(deceptive)
        )


def _tag_family(metadata: dict) -> str:
    text = _normalize(" ".join(str(metadata.get(key) or "") for key in (
        "topic", "content_family", "title", "description", "bible_reference"
    )))
    if any(word in text for word in ("oracion", "orar", "noche", "manana", "amen")):
        return "prayer"
    if any(word in text for word in ("perdon", "misericordia", "amor", "compasion", "projimo")):
        return "love"
    if any(word in text for word in ("cansado", "miedo", "prueba", "tormenta", "fortaleza", "dolor")):
        return "strength"
    if any(word in text for word in ("jesus", "jesucristo", "cristo", "mesias", "pastor")):
        return "jesus"
    if any(word in text for word in ("paz", "serenidad", "descanso", "ansiedad", "esperanza")):
        return "peace"
    return "bible"


def _dynamic_tags(metadata: dict) -> list[str]:
    family = _tag_family(metadata)
    tags = list(_TAG_PACKS[family])
    candidates = []
    reference = " ".join(str(metadata.get("bible_reference") or "").split())[:55]
    topic = " ".join(str(metadata.get("content_family") or metadata.get("topic") or "").split())[:65]
    if reference:
        candidates.append(f"Reflexión sobre {reference}")
    if topic:
        candidates.append(topic)

    normalized = {_normalize(tag) for tag in tags}
    for candidate in candidates:
        if _normalize(candidate) in normalized:
            continue
        trial = tags + [candidate]
        if _youtube_tag_cost(trial) <= 500:
            tags.append(candidate)
            normalized.add(_normalize(candidate))
    return tags


def _dynamic_hashtags(metadata: dict) -> list[str]:
    supplied = [str(tag).strip() for tag in (metadata.get("hashtags") or []) if str(tag).strip()]
    result: list[str] = []
    for tag in supplied:
        clean = tag if tag.startswith("#") else f"#{tag}"
        if clean.lower() not in {x.lower() for x in result}:
            result.append(clean)
        if len(result) >= 5:
            break

    mandatory = ["#Dios", "#Shorts"]
    if not any(tag.lower() in {"#jesus", "#jesucristo", "#cristo"} for tag in result):
        mandatory.insert(1, "#Jesus")
    if not any(tag.lower() in {"#biblia", "#palabradedios", "#reflexionbiblica"} for tag in result):
        mandatory.insert(-1, "#Biblia")

    for tag in mandatory:
        if tag.lower() not in {x.lower() for x in result}:
            if len(result) >= 5:
                result.pop()
            result.append(tag)
    return result[:5]


def enforce_spiritual_topic_guard(metadata: dict) -> dict:
    """Lock the channel to safe original spiritual content without flattening variety."""
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
        scene["stock_query"] = "original synthetic Jesus God Bible cinematic scene no stock media"

    metadata["scenes"] = scenes
    metadata["source_credits"] = []
    metadata["external_media_allowed"] = False
    metadata["wikipedia_allowed"] = False
    metadata["wikimedia_commons_allowed"] = False
    metadata["third_party_stock_allowed"] = False
    metadata["original_generated_media_only"] = True
    metadata["editorial_scope"] = "Jesus_Dios_Biblia_oracion_fe_only"
    metadata["youtube_safety_profile"] = "strict_spiritual_original_v3_dynamic"
    metadata["youtube_policy_categories_checked"] = [
        "spam_deception", "sexual_content", "self_harm", "violent_graphic_content",
        "dangerous_content", "hate_harassment", "regulated_goods", "external_reused_media",
    ]
    metadata["contains_synthetic_media"] = True
    metadata["voice_profile"] = "voz_de_luz_serena_original_v1"
    metadata["voice_brand"] = "Voz de Luz"

    description = str(metadata.get("description") or "").strip()
    disclosure = (
        "Contenido cristiano original. La representación visual de Jesús es artística y generada digitalmente; "
        "no es una grabación literal de un hecho real."
    )
    if "representacion visual de jesus" not in _normalize(description):
        description = (description + "\n\n" + disclosure).strip()
    metadata["description"] = description[:4600]

    tags = _dynamic_tags(metadata)
    metadata["tags"] = tags
    metadata["youtube_tag_character_cost"] = _youtube_tag_cost(tags)
    metadata["youtube_tag_limit"] = 500
    metadata["youtube_tag_family"] = _tag_family(metadata)
    metadata["hashtags"] = _dynamic_hashtags(metadata)

    _assert_spiritual_scope(metadata)
    metadata["editorial_guard_passed"] = True
    metadata["editorial_guard_preserved_dynamic_metadata"] = True
    return metadata


def validate_spiritual_upload_guard(metadata: dict) -> dict:
    """Final fail-closed check immediately before a spiritual upload."""
    _assert_spiritual_scope(metadata)

    tags = tuple(str(x) for x in (metadata.get("tags") or []))
    tag_cost = _youtube_tag_cost(tags)
    if tag_cost > 500:
        raise RuntimeError(
            f"BLOQUEADO ANTES DE YOUTUBE: las etiquetas exceden 500 caracteres API ({tag_cost})."
        )
    metadata["youtube_tag_character_cost"] = tag_cost

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
    metadata["youtube_safety_guard_mode"] = "fail_closed_original_spiritual_only_v3_dynamic"
    return metadata
