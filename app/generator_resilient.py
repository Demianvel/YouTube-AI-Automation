from __future__ import annotations

import os

from . import generator as base


FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")


def generate_metadata(channel: dict, previous: list[dict], retries: int = 5):
    try:
        return base.generate_metadata(channel, previous, retries=retries)
    except RuntimeError as exc:
        message = str(exc).upper()
        temporary = any(token in message for token in ("503", "UNAVAILABLE", "HIGH DEMAND", "429", "RESOURCE_EXHAUSTED"))
        if not temporary:
            raise

        primary = base.TEXT_MODEL
        if FALLBACK_MODEL == primary:
            raise

        print(f"Gemini principal {primary} saturado; reintentando con respaldo {FALLBACK_MODEL}.")
        base.TEXT_MODEL = FALLBACK_MODEL
        try:
            return base.generate_metadata(channel, previous, retries=max(3, retries))
        finally:
            base.TEXT_MODEL = primary
