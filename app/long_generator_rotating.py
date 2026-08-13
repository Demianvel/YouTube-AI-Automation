from __future__ import annotations

from . import long_generator_base as _base
from .topic_rotation import choose_topic_family


def generate_long_metadata(channel: dict, previous: list[dict] | None = None, minutes: int = 10) -> dict:
    if minutes not in {10, 15}:
        raise ValueError("Long-form premium solo admite 10 o 15 minutos.")

    previous = previous or []
    text = f"{channel.get('handle','')} {channel.get('display_name','')}".lower()
    if "brotavida" in text:
        slug = "brotavida"
    elif "dineroclaro" in text or "dinero claro" in text:
        slug = "dineroclaro"
    else:
        raise ValueError("Canal long-form no reconocido")

    family = choose_topic_family(slug, previous, salt=f"long{minutes}min")
    analytics = channel.get("_analytics_digest") or ""
    channel["_analytics_digest"] = (
        "REGLA EDITORIAL PRIORITARIA PARA ESTA EJECUCION: "
        f"el tema debe pertenecer a '{family}'. No repetir una historia, ejemplo, titulo, estructura, especie o secuencia visual reciente. "
        "Analytics puede mejorar gancho y ritmo, pero no cambiar esta familia tematica.\n\n"
        + analytics
    )

    # El generador base usa estas constantes al construir y validar el JSON.
    _base.CHAPTER_SECONDS = 30
    _base.CHAPTERS = minutes * 2
    data = _base.generate_long_metadata(channel)
    data["content_family"] = family
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["chapter_seconds"] = 30
    return data
