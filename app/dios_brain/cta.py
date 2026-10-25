"""CTA rotator agent: soft, varied calls to action (spoken + description).

Never conditional engagement bait ("si no compartís..."), never promises.
Rotation avoids the CTAs used in the last two uploads; when the analyst has
enough data it prefers the best performing variant (UCB1).
"""
from __future__ import annotations

from . import analyst

CTA_VARIANTS: dict[str, dict[str, str]] = {
    "amen": {
        "spoken": "Si lo recibís, escribí Amén.",
        "description": "Si este mensaje te habló al corazón, escribí «Amén» en los comentarios.",
    },
    "guardar": {
        "spoken": "Guardalo para cuando lo necesites.",
        "description": "Guardá este Short para volver a él cuando lo necesites.",
    },
    "compartir": {
        "spoken": "Compartilo con alguien que lo necesite.",
        "description": "Compartilo con alguien que hoy necesite esta palabra.",
    },
    "suscribir": {
        "spoken": "Suscribite para tu mensaje diario.",
        "description": "Suscribite a Dios Habla Hoy IA para recibir tu mensaje diario de fe.",
    },
    "intencion": {
        "spoken": "Dejá tu intención de oración en los comentarios.",
        "description": "Dejá tu intención de oración en los comentarios.",
    },
}
CTA_ORDER = tuple(CTA_VARIANTS)


def choose_cta(previous: list[dict], seed: int, growth: dict | None = None) -> tuple[str, dict[str, str], str]:
    uploaded = [row for row in previous or [] if str(row.get("status") or "").lower() == "uploaded"]
    recent = [str(row.get("brain_cta_id") or "") for row in uploaded[-2:]]
    exclude = {item for item in recent if item}
    winner = analyst.choose_arm(list(CTA_ORDER), previous, "brain_cta_id", exclude=exclude, growth=growth)
    if winner:
        return winner, CTA_VARIANTS[winner], "bandit_ucb1"
    start = seed % len(CTA_ORDER)
    for step in range(len(CTA_ORDER)):
        cta_id = CTA_ORDER[(start + step) % len(CTA_ORDER)]
        if cta_id not in exclude:
            return cta_id, CTA_VARIANTS[cta_id], "rotation"
    cta_id = CTA_ORDER[start]
    return cta_id, CTA_VARIANTS[cta_id], "rotation"
