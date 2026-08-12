from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .config import HISTORY_FILE, OUTPUT_DIR, load_channel
from .generator import generate_metadata
from .history import append_history, read_history
from .video import generate_short
from .youtube import upload_video


def run(channel_slug: str, dry_run: bool = False) -> dict:
    channel = load_channel(channel_slug)
    previous = read_history(HISTORY_FILE, channel=channel_slug, limit=80)
    metadata = generate_metadata(channel, previous)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / channel_slug / stamp
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    video_path = generate_short(channel, metadata, workdir)
    video_id = None
    status = "generated"
    if not dry_run:
        video_id = upload_video(channel, metadata, video_path)
        status = "uploaded"

    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel_slug,
        "handle": channel["handle"],
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
    parser.add_argument("--channel", required=True, choices=["brotavida", "dineroclaro"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.channel, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
