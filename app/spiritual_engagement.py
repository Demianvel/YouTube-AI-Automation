from __future__ import annotations

import hashlib
import unicodedata


_OPENERS = (
    "🙏 Gracias por compartir este momento de fe.",
    "🕊️ Que esta reflexión deje una semilla de paz en tu día.",
    "📖 La Palabra también se vuelve vida cuando la llevamos a nuestras decisiones.",
    "🤍 Gracias por hacer una pausa para escuchar y reflexionar.",
    "🌿 Que este mensaje te ayude a respirar y volver a confiar.",
    "✨ Cada enseñanza bíblica puede abrir una forma nueva de mirar lo que vivimos.",
    "🙏 Que la serenidad de Dios acompañe lo que hoy llevás en el corazón.",
    "💛 Gracias por formar parte de una comunidad que busca fe, esperanza y amor.",
    "🕯️ Una palabra de esperanza puede iluminar un momento difícil.",
    "📖 Sigamos acercándonos a la Biblia con humildad y un corazón sincero.",
    "🌅 Que esta reflexión te acompañe más allá de estos minutos.",
    "🕊️ La paz también comienza con una pausa, una oración y un paso honesto.",
)

_PROMPTS = {
    "prayer": (
        "Podés dejar tu intención de oración con respeto en los comentarios.",
        "Contanos qué palabra necesitás presentar hoy delante de Dios.",
        "Escribí una intención breve por vos, tu familia o alguien que necesite fortaleza.",
        "Podés compartir qué carga querés entregar hoy en oración.",
        "Dejá en los comentarios una palabra de fe que quieras recordar esta semana.",
    ),
    "bible": (
        "Contanos qué parte del pasaje te ayudó a comprender algo nuevo.",
        "Podés escribir la enseñanza bíblica que más te acompañó hoy.",
        "¿Qué palabra del mensaje querés llevar a la práctica? Podés dejarla en los comentarios.",
        "Compartí con respeto qué versículo te brinda paz en este momento.",
        "Contanos qué tema de la Biblia te gustaría seguir profundizando.",
    ),
    "hope": (
        "Podés dejar una palabra de esperanza para otra persona que lea los comentarios.",
        "Contanos qué pequeño paso de fe podés dar hoy.",
        "Escribí una razón por la que todavía elegís confiar.",
        "Podés compartir qué enseñanza te ayuda a no rendirte.",
        "Dejá una frase de aliento para quien esté atravesando un día difícil.",
    ),
    "love": (
        "Contanos qué gesto concreto de amor podés ofrecer hoy.",
        "Podés compartir una forma sencilla de acompañar a alguien esta semana.",
        "Escribí qué enseñanza de Jesús querés reflejar en tus acciones.",
        "Dejá una palabra amable para quien necesite sentirse acompañado.",
        "Contanos cómo podés transformar esta reflexión en una acción de bien.",
    ),
    "general": (
        "Contanos qué parte del mensaje habló más a tu corazón.",
        "Podés escribir una palabra que resuma lo que te llevás de esta reflexión.",
        "Dejá en los comentarios una enseñanza que quieras recordar durante el día.",
        "Contanos con respeto qué tema te gustaría escuchar en una próxima reflexión.",
        "Podés compartir cómo esta palabra se conecta con tu vida cotidiana.",
    ),
}

_CLOSERS = (
    "Suscribite para seguir compartiendo reflexiones originales de Biblia, fe y esperanza.",
    "Compartilo solamente si pensás que puede acompañar a alguien, sin promesas ni presión.",
    "Gracias por ayudar a construir un espacio de respeto, oración y esperanza.",
    "Seguimos caminando juntos, un mensaje y una acción de bien a la vez.",
    "Que la conversación continúe con empatía y palabras que hagan bien.",
    "Volvé cuando necesites una pausa de serenidad y reflexión bíblica.",
    "Que Dios te conceda sabiduría, paz y un corazón dispuesto a amar.",
    "Gracias por escuchar, reflexionar y tratar a los demás con compasión.",
    "Que esta comunidad sea un lugar para acompañarnos con prudencia y fe.",
    "Guardá la enseñanza que te sirva y llevala a una acción concreta de amor.",
)


def _normalize(value: object) -> str:
    text = " ".join(str(value or "").split()).lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _category(seed_material: str) -> str:
    text = _normalize(seed_material)
    if any(word in text for word in ("oracion", "orar", "amen", "noche", "manana")):
        return "prayer"
    if any(word in text for word in ("biblia", "salmo", "evangelio", "mateo", "lucas", "juan", "romanos", "isaias")):
        return "bible"
    if any(word in text for word in ("amor", "perdon", "misericordia", "compasion", "projimo")):
        return "love"
    if any(word in text for word in ("esperanza", "miedo", "ansiedad", "prueba", "fortaleza", "cansado")):
        return "hope"
    return "general"


def _pick(values: tuple[str, ...], digest: str, block: int) -> str:
    start = block * 8
    return values[int(digest[start:start + 8], 16) % len(values)]


def engagement_comment(seed_material: str) -> str:
    """Build a safe, varied top-level comment without manipulative engagement claims."""
    material = str(seed_material or "")
    category = _category(material)
    digest = hashlib.sha256(f"voz-de-luz-engagement|{material}".encode("utf-8")).hexdigest()
    return " ".join((
        _pick(_OPENERS, digest, 0),
        _pick(_PROMPTS[category], digest, 1),
        _pick(_CLOSERS, digest, 2),
    ))
