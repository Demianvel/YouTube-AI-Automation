from __future__ import annotations

from .long_generator_base import generate_long_metadata as _base_generate
from .topic_rotation import choose_topic_family


def generate_long_metadata(channel: dict, previous: list[dict] | None = None) -> dict:
    previous = previous or []
    text = f"{channel.get('handle','')} {channel.get('display_name','')}".lower()
    if "brotavida" in text:
        slug = "brotavida"
    elif "dineroclaro" in text or "dinero claro" in text:
        slug = "dineroclaro"
    else:
        raise ValueError("Canal long-form no reconocido")

    family = choose_topic_family(slug, previous, salt="long5min")
    analytics = channel.get("_analytics_digest") or ""
    channel["_analytics_digest"] = (
        "REGLA EDITORIAL PRIORITARIA PARA ESTA EJECUCION: "
        f"el tema debe pertenecer a '{family}'. No repetir una historia, ejemplo, titulo o estructura reciente. "
        "Analytics puede mejorar gancho y ritmo, pero no cambiar esta familia tematica.\n\n"
        + analytics
    )

    data = _base_generate(channel)
    data["content_family"] = family
    return data
