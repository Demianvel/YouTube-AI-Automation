from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone

from . import video as video_module
from .channel_analytics import analytics_digest, collect_channel_analytics
from .config import HISTORY_FILE, OUTPUT_DIR, load_channel
from .generator_resilient import generate_metadata
from .history import append_history, read_history
from .performance import enrich_history_with_youtube_stats
from .premium_audio import apply_audio as premium_apply_audio
from .hf_primary_router import generate_short
from .spiritual_content_guard import enforce_spiritual_topic_guard
from .spiritual_growth import enrich_short_growth
from .spiritual_quality import enforce_spiritual_metadata
from .spiritual_source_growth_engine import ground_and_optimize_spiritual_metadata
from .spiritual_uniqueness import validate_spiritual_uniqueness
from .spiritual_visual_library import enrich_metadata_visuals
from .visual_variety import attach_visual_pack
from .workers.divine_publisher_4x10 import mark_publish_metadata, validate_channel
from .youtube import upload_video

ACTIVE_SHORT_CHANNELS = {"brotavida", "dioshablahoyia"}
DISABLED_CHANNELS = {"dineroclaro", "envikids"}


def _write_metadata(workdir, metadata: dict) -> None:
    (workdir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _apply_content_mode(channel_slug: str, channel: dict, requested: str, previous: list[dict]) -> str:
    if channel_slug in DISABLED_CHANNELS:
        raise RuntimeError(f"Canal desactivado por configuracion: {channel_slug}")
    if channel_slug == "brotavida":
        channel["audio_mode"] = "asmr"
        channel["visual_mode"] = "real_botanical_timelapse"
        channel["require_real_video"] = True
        return "asmr"
    return "voice"


def _configure_spiritual_short(channel_slug: str, channel: dict) -> None:
    if channel_slug != "dioshablahoyia":
        return

    target_seconds = max(8, min(60, int(os.getenv("SPIRITUAL_SHORT_SECONDS", "8"))))
    scene_seconds = max(8, min(30, int(os.getenv("SPIRITUAL_SHORT_SCENE_SECONDS", "8"))))
    scenes = max(1, math.ceil(target_seconds / scene_seconds))
    while scenes * scene_seconds > 60 and scenes > 1:
        scenes -= 1
    channel["scene_seconds"] = scene_seconds
    channel["scenes_per_short"] = scenes
    channel["spiritual_short_target_seconds"] = scenes * scene_seconds


def run(channel_slug: str, dry_run: bool = False, content_mode: str = "auto") -> dict:
    if channel_slug not in ACTIVE_SHORT_CHANNELS:
        raise RuntimeError(
            f"Publicacion deshabilitada para {channel_slug}. Canales activos: {sorted(ACTIVE_SHORT_CHANNELS)}"
        )

    if channel_slug == "dioshablahoyia":
        validate_channel(channel_slug)

    channel = load_channel(channel_slug)
    _configure_spiritual_short(channel_slug, channel)
    previous = read_history(HISTORY_FILE, channel=channel_slug, limit=100)

    video_module.apply_audio = premium_apply_audio

    try:
        previous = enrich_history_with_youtube_stats(channel, previous)
    except Exception as exc:
        print(f"No se pudieron leer estadisticas publicas recientes; se continua con historial local: {exc}")

    try:
        snapshot = collect_channel_analytics(channel, days=90)
        channel["_analytics_digest"] = analytics_digest(snapshot)
        top_by_id = {
            str(row.get("video")): row
            for row in (snapshot.get("reports", {}).get("top_videos") or [])
            if row.get("video")
        }
        enriched = []
        for row in previous:
            item = dict(row)
            full = top_by_id.get(str(item.get("video_id") or ""))
            if full:
                item.update({
                    "shares": full.get("shares", 0),
                    "subscribersGained": full.get("subscribersGained", 0),
                    "share_rate": full.get("share_rate", 0),
                    "subscriber_gain_rate": full.get("subscriber_gain_rate", 0),
                    "averageViewPercentage": full.get("averageViewPercentage", 0),
                    "estimatedMinutesWatched": full.get("estimatedMinutesWatched", 0),
                })
            enriched.append(item)
        previous = enriched
    except Exception as exc:
        channel["_analytics_digest"] = "Analytics detallado no disponible en esta ejecucion; no inventar datos."
        print(f"YouTube Analytics detallado no disponible: {exc}")

    resolved_mode = _apply_content_mode(channel_slug, channel, content_mode, previous)
    metadata = generate_metadata(channel, previous)

    if channel_slug == "brotavida":
        metadata["content_family"] = "seed_to_plant_timelapse"
        metadata["audio_policy"] = "asmr_natural_foley_plus_optional_original_low_music_no_voice"
        metadata["real_botanical_timelapse_required"] = True
        metadata["no_synthetic_plant_visuals"] = True

    if channel_slug == "dioshablahoyia":
        metadata = enforce_spiritual_metadata(metadata, previous)
        metadata["target_short_seconds"] = int(channel["scenes_per_short"]) * int(channel["scene_seconds"])
        metadata["short_format"] = "vertical_native_cinematic_short"
        metadata = enrich_short_growth(metadata, previous)
        metadata = ground_and_optimize_spiritual_metadata(metadata, previous, content_type="short")
        metadata = enrich_metadata_visuals(metadata, content_type="short")
        metadata = attach_visual_pack(metadata, previous, content_type="short")
        metadata = validate_spiritual_uniqueness(metadata, previous)
        metadata = mark_publish_metadata(metadata, content_type="short")
        metadata = enforce_spiritual_topic_guard(metadata)

    metadata["content_mode"] = resolved_mode
    metadata["analytics_used"] = bool(channel.get("_analytics_digest"))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / channel_slug / stamp
    workdir.mkdir(parents=True, exist_ok=True)
    _write_metadata(workdir, metadata)

    video_path = generate_short(channel, metadata, workdir)
    _write_metadata(workdir, metadata)

    video_id = None
    status = "generated"
    if not dry_run:
        video_id = upload_video(channel, metadata, video_path)
        status = "uploaded"

    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel_slug,
        "handle": channel["handle"],
        "content_mode": resolved_mode,
        "content_family": metadata.get("content_family"),
        "topic": metadata.get("topic"),
        "title": metadata.get("title"),
        "bible_reference": metadata.get("bible_reference"),
        "seo_primary_keyword": metadata.get("seo_primary_keyword"),
        "source_grounded": metadata.get("source_grounded"),
        "script_hash": metadata.get("script_hash"),
        "narration_preview": metadata.get("narration_preview"),
        "uniqueness_gate_passed": metadata.get("uniqueness_gate_passed"),
        "visual_engine_version": metadata.get("visual_engine_version"),
        "visual_rotation_manifest": metadata.get("visual_rotation_manifest"),
        "visual_pack": metadata.get("visual_pack"),
        "visual_prompt_hashes": metadata.get("visual_prompt_hashes"),
        "generated_visual_provider": metadata.get("generated_visual_provider"),
        "character_reference_profile": metadata.get("character_reference_profile"),
        "text_to_video_engine": metadata.get("text_to_video_engine"),
        "worker_publisher": metadata.get("worker_publisher"),
        "worker_publisher_id": metadata.get("worker_publisher_id"),
        "video_id": video_id,
        "status": status,
        "comment_publish_status": metadata.get("comment_publish_status"),
        "comment_thread_id": metadata.get("comment_thread_id"),
        "comment_pin_status": metadata.get("comment_pin_status"),
    }
    append_history(HISTORY_FILE, record)
    print(json.dumps(record, ensure_ascii=False))
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, choices=["brotavida", "dioshablahoyia"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--content-mode", default="auto", choices=["auto", "asmr", "music", "voice"])
    args = parser.parse_args()
    run(args.channel, dry_run=args.dry_run, content_mode=args.content_mode)


if __name__ == "__main__":
    main()
