from __future__ import annotations

import argparse
import json
import os

from . import spiritual_long_pipeline as base
from .spiritual_long_local_metadata import generate_local_long_metadata
from .spiritual_long_runner import run as enhanced_run
from .spiritual_tts import make_spiritual_spanish_voice


def _service_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return any(token in text for token in (
        "429", "RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT", "503", "UNAVAILABLE", "HIGH DEMAND", "404 NOT_FOUND",
    ))


def run(minutes: int, publish: bool = False) -> dict:
    original_metadata = base._generate_metadata
    original_voice = base.make_natural_spanish_voice

    def resilient(channel: dict, requested_minutes: int) -> dict:
        if not os.getenv("GEMINI_API_KEY", "").strip():
            print("GEMINI_API_KEY no disponible; usando guionista biblico local resiliente.")
            return generate_local_long_metadata(channel, requested_minutes)
        try:
            return original_metadata(channel, requested_minutes)
        except Exception as exc:
            if not _service_error(exc):
                raise
            print(f"Gemini long-form no disponible ({exc}); usando guionista biblico local resiliente.")
            return generate_local_long_metadata(channel, requested_minutes)

    base._generate_metadata = resilient
    # The enhanced runner captures base.make_natural_spanish_voice at runtime,
    # so install the chunk-safe spiritual TTS before entering it. This prevents
    # Kokoro from truncating a multi-minute section to its first ~20 seconds.
    base.make_natural_spanish_voice = make_spiritual_spanish_voice
    try:
        return enhanced_run(minutes, publish=publish)
    finally:
        base._generate_metadata = original_metadata
        base.make_natural_spanish_voice = original_voice


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[5, 10, 15, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.minutes, publish=args.publish), ensure_ascii=False))


if __name__ == "__main__":
    main()
