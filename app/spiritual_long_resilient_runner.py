from __future__ import annotations

import argparse
import json
import os

from . import spiritual_long_pipeline as base
from . import spiritual_long_runner as enhanced
from .spiritual_long_local_metadata import generate_local_long_metadata
from .spiritual_source_growth_engine import ground_and_optimize_spiritual_metadata
from .spiritual_tts import make_spiritual_spanish_voice
from .workers.celestial_cinema_engine import mark_render_metadata, render_directive
from .workers.divine_publisher_4x10 import mark_publish_metadata
from .workers.peace_motion_director import apply_director_requirements, performance_directive


def _service_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return any(token in text for token in (
        "429", "RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT", "503", "UNAVAILABLE", "HIGH DEMAND", "404 NOT_FOUND",
    ))


def _direct_long_metadata(meta: dict, minutes: int) -> dict:
    mark_render_metadata(meta, format_name=f"long_horizontal_16x9_{minutes}min")
    apply_director_requirements(meta)
    mark_publish_metadata(meta, content_type="long_video")

    render_block = render_directive(meta, vertical=False)
    for section in meta.get("sections") or []:
        narration = " ".join(str(section.get("narration") or "").split()).strip()
        existing = " ".join(str(section.get("visual_prompt") or "").split()).strip()
        performance = performance_directive(narration[:1000])
        section["visual_prompt"] = (
            f"{render_block}\n\n{existing}\n\n{performance}\n\n"
            "Long-form continuity rule: preserve exactly the same recurring synthetic character identity, "
            "wardrobe family and facial proportions across all generated sections. Prefer genuine moving video "
            "with continuous human body performance over animated still images whenever a video model is available."
        )[:4800]

    meta["worker_chain"] = [
        "Motor Celestial Cinema",
        "Director Paz Viva",
        "Publicador Reino 4x10",
    ]
    meta["worker_chain_separated"] = True
    return meta


def run(minutes: int, publish: bool = False) -> dict:
    original_metadata = base._generate_metadata
    original_voice = base.make_natural_spanish_voice
    original_enhance = enhanced._enhance_metadata

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

    def directed_enhance(meta: dict, previous: list[dict], requested_minutes: int) -> dict:
        enhanced_meta = original_enhance(meta, previous, requested_minutes)
        enhanced_meta = ground_and_optimize_spiritual_metadata(
            enhanced_meta,
            previous,
            content_type="long",
        )
        return _direct_long_metadata(enhanced_meta, requested_minutes)

    base._generate_metadata = resilient
    base.make_natural_spanish_voice = make_spiritual_spanish_voice
    enhanced._enhance_metadata = directed_enhance
    try:
        return enhanced.run(minutes, publish=publish)
    finally:
        base._generate_metadata = original_metadata
        base.make_natural_spanish_voice = original_voice
        enhanced._enhance_metadata = original_enhance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[5, 10, 15, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.minutes, publish=args.publish), ensure_ascii=False))


if __name__ == "__main__":
    main()
