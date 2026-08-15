from __future__ import annotations

import hashlib

_COMMENT_VARIANTS = (
    "🙏 Si esta reflexión te acompañó, suscribite para recibir nuevas oraciones y mensajes de fe. Podés escribir Amén o dejar tu intención de oración, y compartir este video con alguien que hoy necesite esperanza.",
    "✨ Que este mensaje se convierta también en una acción de bien. Suscribite, contanos en los comentarios qué palabra te ayudó hoy y compartilo con una persona a la que pueda hacerle bien.",
    "🕊️ Si querés, dejá tu intención de oración en los comentarios. Suscribite para seguir compartiendo Biblia, fe y esperanza, y enviá este mensaje a alguien que necesite un poco de paz hoy.",
    "🙏 Gracias por compartir este momento de oración. Si te hizo bien, podés suscribirte, comentar Amén o una intención por la que quieras que oremos, y compartir la reflexión con respeto.",
    "💛 La fe también se demuestra acompañando a otros. Suscribite para nuevas reflexiones, comentá qué enseñanza te llevás y compartí este video con alguien que pueda necesitar consuelo.",
    "📖 Sigamos aprendiendo de la Biblia juntos. Suscribite, dejá en comentarios la reflexión o intención que tengas en el corazón y compartí este mensaje para que llegue a más personas con respeto y esperanza.",
    "🌿 Si este mensaje te dio calma, suscribite para recibir nuevas oraciones. Podés comentar Amén o contar por quién querés pedir hoy, y compartirlo con alguien a quien una palabra de esperanza pueda ayudar.",
    "🤍 Que la palabra no termine cuando termina el video. Suscribite, compartí una intención en los comentarios y enviá esta reflexión a alguien con quien quieras sembrar paz, fe y una acción concreta de bien.",
    "🙏 Si hoy necesitabas escuchar algo así, podés suscribirte al canal, escribir Amén o dejar tu intención de oración y compartir el video con una persona que también necesite fortaleza.",
    "✨ Construyamos una comunidad que ore y también haga el bien. Suscribite, contanos qué parte te habló al corazón y compartí esta reflexión con alguien que pueda recibirla con esperanza.",
    "🕊️ Gracias por estar acá. Suscribite para nuevas reflexiones bíblicas, dejá tu intención de oración si querés y compartí este mensaje con respeto para que pueda acompañar a alguien más.",
    "💫 Si esta oración te acompañó, suscribite para seguir creciendo en fe. Comentá Amén o una intención que quieras poner en oración y compartí el video con quien hoy necesite una palabra de aliento.",
)


def engagement_comment(seed_material: str) -> str:
    raw = hashlib.sha256(str(seed_material).encode("utf-8")).hexdigest()
    index = int(raw[:8], 16) % len(_COMMENT_VARIANTS)
    return _COMMENT_VARIANTS[index]
