from __future__ import annotations

import hashlib


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


def _ensure_three_minute_narration(metadata: dict) -> None:
    scenes = list(metadata.get("scenes") or [])
    if not scenes:
        return
    target_words = int(metadata.get("target_narration_words") or 365)
    current_words = sum(len(_clean(scene.get("narration")).split()) for scene in scenes)
    if current_words >= target_words:
        return

    seed = _seed(metadata)
    cursor = 0
    while current_words < target_words and cursor < len(scenes) * 4:
        index = cursor % len(scenes)
        expansion = _EXPANSIONS[(seed + cursor * 5) % len(_EXPANSIONS)]
        existing = _clean(scenes[index].get("narration"))
        scenes[index]["narration"] = f"{existing} {expansion}".strip()
        current_words += len(expansion.split())
        cursor += 1
    metadata["scenes"] = scenes
    metadata["narration_word_target"] = target_words
    metadata["narration_words_after_growth"] = current_words


def enrich_short_growth(metadata: dict, previous: list[dict] | None = None) -> dict:
    previous = previous or []
    metadata["title_variants"] = _title_variants(metadata)
    metadata["retention_structure"] = {
        "opening": "hook in first 1-2 seconds with a relatable need, question or promise of useful reflection",
        "middle": "progressive biblical reflection with new visual or narrative beat every scene",
        "payoff": "practical prayer, hope or action that resolves the opening idea",
        "ending": "gentle subscribe/comment/share CTA connected to doing good, never coercive",
    }
    metadata["growth_strategy"] = "original_hook_progression_payoff_packaging_test_without_false_clickbait"
    metadata["target_narration_words"] = 365
    _ensure_three_minute_narration(metadata)

    scenes = list(metadata.get("scenes") or [])
    cta = (
        "Si esta reflexión te acompañó, podés suscribirte para recibir nuevos mensajes de fe, "
        "compartirla con alguien a quien pueda hacerle bien y, si querés, escribir Amén o dejar tu intención en los comentarios. "
        "Que la palabra nos impulse siempre a compartir, ayudar y hacer el bien."
    )
    if scenes:
        last = _clean(scenes[-1].get("narration"))
        if "suscrib" not in last.lower():
            scenes[-1]["narration"] = f"{last} {cta}".strip()
    metadata["scenes"] = scenes
    metadata["cta_spoken"] = cta
    metadata["pinned_comment_candidate"] = (
        "🙏 Si este mensaje te ayudó, podés dejar tu intención de oración o escribir Amén. "
        "Compartilo con alguien que hoy necesite fe y esperanza, y suscribite para seguir construyendo una comunidad que busque hacer el bien."
    )

    description = str(metadata.get("description") or "").strip()
    footer = "Suscribite, compartí este mensaje con respeto y dejá tu intención de oración si querés. Que la fe también se transforme en acciones de bien hacia los demás."
    if "suscrib" not in description.lower():
        description = f"{description}\n\n{footer}".strip()
    metadata["description"] = description[:4700]
    metadata["recent_packaging_count"] = len(previous[-20:])
    return metadata
