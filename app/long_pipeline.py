from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .config import OUTPUT_DIR, load_channel
from .long_generator import generate_long_metadata
from .long_video import generate_long_video
from .youtube import upload_long_video


def run(channel_slug: str, publish: bool = False) -> dict:
    if channel_slug not in {"brotavida", "dineroclaro"}:
        raise ValueError("Long-form 5 min solo esta habilitado para brotavida y dineroclaro.")

    channel = load_channel(channel_slug)
    metadata = generate_long_metadata(channel)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / "long5min" / channel_slug / stamp
    workdir.mkdir(parents=True, exist_ok=True)

    metadata_file = workdir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    video_path = generate_long_video(channel, metadata, workdir)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    video_id = None
    status = "generated"
    if publish:
        video_id = upload_long_video(channel, metadata, video_path)
        status = "uploaded"

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel_slug,
        "handle": channel["handle"],
        "title": metadata.get("title"),
        "duration_seconds": metadata.get("duration_seconds", 300),
        "tts_provider_used": metadata.get("tts_provider_used"),
        "video_id": video_id,
        "status": status,
        "path": str(video_path),
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, choices=["brotavida", "dineroclaro"])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.channel, publish=args.publish)


if __name__ == "__main__":
    main()
