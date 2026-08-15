from __future__ import annotations

import hashlib
import math

from .spiritual_engagement import engagement_comment


_EXPANSIONS = (
    "No hace falta tener todas las respuestas para dar el siguiente paso. La fe puede empezar de una manera sencilla: reconocer lo que sentimos, presentarlo delante de Dios y elegir actuar con paciencia, verdad y amor.",
    "La esperanza bíblica no consiste en negar los problemas. Nos invita a atravesarlos sin perder de vista el bien, buscando sabiduría para lo que podemos cambiar y serenidad para lo que todavía no comprendemos.",
    "Orar también puede ser hablar con sinceridad, sin frases perfectas. Podemos agradecer, pedir ayuda, recordar a quienes necesitan consuelo y dejar que esa oración nos mueva a tratar mejor a las personas que tenemos cerca.",
    "Cuando la mente se llena de preocupación, volver a una enseñanza bíblica puede ordenar el corazón. No para escapar de la realidad, sino para responder con más calma, responsabilidad, compasión y confianza.",
    "La fe se vuelve visible en decisiones pequeñas: escuchar antes de juzgar, perdonar cuando sea posible, ayudar sin buscar reconocimiento, decir la verdad con bondad y acompañar a quien está pasando un momento difícil.",
    "También podemos mirar la creación con gratitud. La vida, los animales, el cielo, el agua y la tierra pueden recordarnos nuestra responsabilidad de cuidar, compartir y hacer el bien con lo que está a nuestro alcance.",
    "Si hoy sentís que avanzás lentamente, recordá que la perseverancia también es una forma de esperanza. Un paso honesto, una conversación pendiente o una oración sencilla pueden abrir espacio para empezar de nuevo.",
    "La Biblia presenta muchas historias de personas que tuvieron miedo, dudas y cansancio. Su valor no está en mostrarlas como perfectas, sino en enseñarnos que la confianza, la humildad y la misericordia pueden crecer en medio de la dificultad.",
    "Una vida de fe no se mide solamente por lo que decimos. Se reconoce en cómo tratamos al prójimo, cómo respondemos cuando alguien necesita ayuda y cómo usamos nuestras palabras para construir en lugar de herir.",
    "Podés convertir este momento en una oración: pedí claridad para decidir, fortaleza para perseverar, humildad para reconocer errores y un corazón dispuesto a ser instrumento de paz para alguien más.",
    "Hay días en los que la respuesta no llega enseguida. En esos momentos, la espera puede transformarse en un espacio para aprender, ordenar prioridades y recordar que nuestra dignidad no depende de que todo salga como imaginábamos.",
    "Que esta reflexión no termine solamente al cerrar el video. Elegí una acción concreta de bien para hoy: llamar a alguien, pedir perdón, agradecer, compartir, ayudar o simplemente escuchar con atención a quien lo necesita.",
)


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _seed(metadata: dict) -> int:
    raw = f"{metadata.get('topic','')}|{metadata.get('title','')}|{metadata.get('bible_reference','')}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _title_variants(metadata: dict) -> list[str]:
    topic = _clean(metadata.get("topic")) or "fe y esperanza"
    base = _clean(metadata.get("title")) or f"Una reflexión de fe: {topic}"
    candidates = [
        base,
        f"Cuando necesitás paz: {topic}",
        f"Una reflexión bíblica para volver a confiar: {topic}",
        f"Fe y esperanza para este momento: {topic}",
    ]
    result: list[str] = []
    for title in candidates:
        title = title[:95].rstrip(" -:,.!")
        if title and title.lower() not in {x.lower() for x in result}:
            result.append(title)
        if len(result) == 3:
            break
    return result


def _repair_repetition(metadata: dict) -> None:
    scenes = list(metadata.get("scenes") or [])
    if not scenes:
        return
    seed = _seed(metadata)
    seen: set[str] = set()
    repairs = 0
    for index, scene in enumerate(scenes):
        narration = _clean(scene.get("narration"))
        key = narration.lower()
        if not narration or len(narration.split()) < 6 or key in seen:
            bridge = _EXPANSIONS[(seed + index * 7) % len(_EXPANSIONS)]
            narration = bridge
            repairs += 1
        seen.add(narration.lower())
        scene["narration"] = narration
    metadata["scenes"] = scenes
    metadata["repetitive_narration_repairs"] = repairs


def _short_word_target(metadata: dict, words_per_minute: int = 126) -> int:
    """Return a calm, human narration budget that actually fits the Short."""
    seconds = float(metadata.get("target_short_seconds") or 8)
    seconds = max(4.0, min(60.0, seconds))
    return max(8, math.ceil((seconds / 60.0) * words_per_minute * 1.02))


def _truncate_words(text: str, limit: int) -> str:
    words = _clean(text).split()
    if len(words) <= limit:
        return " ".join(words)
    clipped = " ".join(words[:limit]).rstrip(",;:-")
    if clipped and clipped[-1] not in ".!?":
        clipped += "."
    return clipped


def _fit_short_narration(metadata: dict) -> None:
    """Fit narration to the real Short duration instead of a 3-minute script.

    The old growth path expanded every spiritual Short toward 390 words. For an
    8-second video that creates a voice track well over a minute, so the quality
    gate correctly blocks the upload. This function keeps a calm ~126 WPM budget
    and distributes it across the actual number of scenes.
    """
    scenes = list(metadata.get("scenes") or [])
    if not scenes:
        return

    target_words = _short_word_target(metadata)
    per_scene = max(4, math.ceil(target_words / len(scenes)))
    remaining = target_words

    for index, scene in enumerate(scenes):
        slots_left = len(scenes) - index
        allowance = max(4, min(per_scene, remaining - max(0, slots_left - 1) * 4))
        narration = _clean(scene.get("narration"))
        if not narration:
            narration = _EXPANSIONS[(_seed(metadata) + index * 7) % len(_EXPANSIONS)]
        scene["narration"] = _truncate_words(narration, allowance)
        remaining -= len(scene["narration"].split())

    metadata["scenes"] = scenes
    metadata["target_narration_words"] = target_words
    metadata["narration_word_target"] = target_words
    metadata["narration_words_after_growth"] = sum(
        len(_clean(scene.get("narration")).split()) for scene in scenes
    )
    metadata["narration_duration_policy"] = "duration_aware_short_126wpm"


def enrich_short_growth(metadata: dict, previous: list[dict] | None = None) -> dict:
    previous = previous or []
    metadata["title_variants"] = _title_variants(metadata)
    metadata["retention_structure"] = {
        "opening": "hook in first 1-2 seconds with a relatable need or clear spiritual promise",
        "middle": "one concise biblical idea matched to the available seconds",
        "payoff": "a short practical hope or reflection that resolves the opening",
        "ending": "CTA stays in description/pinned comment when the spoken time budget is too short",
    }
    metadata["growth_strategy"] = "original_hook_concise_biblical_payoff_without_false_clickbait"
    _repair_repetition(metadata)
    _fit_short_narration(metadata)

    # A long spoken CTA cannot fit naturally inside an 8-10 second Short.
    # Keep it available for packaging instead of forcing the TTS beyond the clip.
    cta = (
        "Si esta reflexión te acompañó, podés suscribirte para recibir nuevos mensajes de fe, "
        "compartirla con alguien a quien pueda hacerle bien y, si querés, escribir Amén o dejar tu intención en los comentarios. "
        "Que la palabra nos impulse siempre a compartir, ayudar y hacer el bien."
    )
    metadata["cta_spoken"] = ""
    metadata["cta_packaging"] = cta
    metadata["cta_mode"] = "description_and_pinned_comment_only"
    metadata["pinned_comment_candidate"] = engagement_comment(
        f"short|{metadata.get('topic','')}|{metadata.get('title','')}|{_seed(metadata)}"
    )

    description = str(metadata.get("description") or "").strip()
    footer = "Suscribite, compartí este mensaje con respeto y dejá tu intención de oración si querés. Que la fe también se transforme en acciones de bien hacia los demás."
    if "suscrib" not in description.lower():
        description = f"{description}\n\n{footer}".strip()
    metadata["description"] = description[:4700]
    metadata["recent_packaging_count"] = len(previous[-20:])
    return metadata
