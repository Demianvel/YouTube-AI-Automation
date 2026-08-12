from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone

from .channel_analytics import analytics_digest, collect_channel_analytics
from .config import HISTORY_FILE, OUTPUT_DIR, load_channel
from .generator import generate_metadata
from .history import append_history, read_history
from .performance import enrich_history_with_youtube_stats
from .video import generate_short
from .youtube import upload_video


def _write_metadata(workdir, metadata: dict) -> None:
    (workdir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _auto_brotavida_mode(previous: list[dict]) -> str:
    """Explore all 3 formats, then favor modes with stronger VPH/engagement."""
    modes = ("asmr", "music", "voice")
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for row in previous:
        mode = str(row.get("content_mode") or "").strip()
        if mode in modes and row.get("status") == "uploaded":
            by_mode[mode].append(row)

    # Require enough experiments before optimizing aggressively.
    counts = {mode: len(by_mode[mode]) for mode in modes}
    if min(counts.values(), default=0) < 2:
        return min(modes, key=lambda m: counts[m])

    def score(rows: list[dict]) -> float:
        recent = rows[-8:]
        values = []
        for row in recent:
            vph = float(row.get("vph") or 0)
            like_rate = float(row.get("like_rate") or 0)
            comment_rate = float(row.get("comment_rate") or 0)
            share_rate = float(row.get("share_rate") or 0)
            sub_rate = float(row.get("subscriber_gain_rate") or 0)
            values.append(
                math.log1p(max(0.0, vph))
                + 18.0 * like_rate
                + 45.0 * comment_rate
                + 60.0 * share_rate
                + 90.0 * sub_rate
            )
        return sum(values) / max(1, len(values))

    ranked = sorted(modes, key=lambda m: score(by_mode[m]), reverse=True)
    # 75% exploitation, 25% exploration based on UTC hour/day parity.
    marker = datetime.now(timezone.utc).timetuple().tm_yday + datetime.now(timezone.utc).hour
    if marker % 4 == 0:
        return ranked[1 if len(ranked) > 1 else 0]
    return ranked[0]


def _apply_content_mode(channel_slug: str, channel: dict, requested: str, previous: list[dict]) -> str:
    mode = (requested or "auto").lower().strip()
    if channel_slug == "dineroclaro":
        channel["audio_mode"] = "voice_music"
        return "voice"

    if channel_slug != "brotavida":
        return "voice" if channel.get("audio_mode") != "music_only" else "music"

    if mode == "auto":
        mode = _auto_brotavida_mode(previous)
    if mode == "asmr":
        channel["audio_mode"] = "asmr"
        return "asmr"
    if mode == "music":
        channel["audio_mode"] = "music_only"
        return "music"
    if mode == "voice":
        channel["audio_mode"] = "voice_music"
        return "voice"
    raise ValueError(f"content_mode no soportado para BrotaVida: {requested}")


def run(channel_slug: str, dry_run: bool = False, content_mode: str = "auto") -> dict:
    channel = load_channel(channel_slug)
    previous = read_history(HISTORY_FILE, channel=channel_slug, limit=100)

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
        "topic": metadata.get("topic"),
        "title": metadata.get("title"),
        "video_id": video_id,
        "status": status,
    }
    append_history(HISTORY_FILE, record)
    print(json.dumps(record, ensure_ascii=False))
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, choices=["brotavida", "dineroclaro", "envikids"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--content-mode", default="auto", choices=["auto", "asmr", "music", "voice"])
    args = parser.parse_args()
    run(args.channel, dry_run=args.dry_run, content_mode=args.content_mode)


if __name__ == "__main__":
    main()
