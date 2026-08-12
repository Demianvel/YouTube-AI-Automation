from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .channel_analytics import analytics_digest, collect_channel_analytics
from .config import OUTPUT_DIR, load_channel
from .kids_extended_generator import generate_extended_short_metadata
from .kids_extended_video import render_extended_short
from .youtube import upload_video


def _compact(workdir: Path, minutes: int) -> None:
    keep = {
        f"envikids_short_{minutes}min.mp4",
        "metadata.json",
        "result.json",
    }
    for path in workdir.iterdir():
        if path.is_file() and path.name not in keep:
            path.unlink(missing_ok=True)


def run(minutes: int, publish: bool = False) -> dict:
    channel = load_channel("envikids")
    try:
        snapshot = collect_channel_analytics(channel, days=90)
        channel["_analytics_digest"] = analytics_digest(snapshot)
    except Exception as exc:
        channel["_analytics_digest"] = "Analytics no disponible; no inventar preferencias de audiencia."
        print(f"EnViKids Analytics no disponible: {exc}")

    meta = generate_extended_short_metadata(channel, minutes)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / "envikids-extended-shorts" / f"{minutes}min" / stamp
    workdir.mkdir(parents=True, exist_ok=True)
    metadata_file = workdir / "metadata.json"
    metadata_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    video = render_extended_short(meta, workdir)
    video_id = None
    status = "generated"
    if publish:
        video_id = upload_video(channel, meta, video)
        status = "uploaded"

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": "envikids",
        "handle": channel["handle"],
        "duration_minutes": minutes,
        "title": meta.get("title"),
        "tts_provider_used": meta.get("tts_provider_used"),
        "video_id": video_id,
        "status": status,
        "path": str(video),
        "made_for_kids": True,
        "format": "youtube_short_vertical_9_16",
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    _compact(workdir, minutes)
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[1, 2, 3])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.minutes, publish=args.publish)


if __name__ == "__main__":
    main()
