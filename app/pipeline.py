from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .config import HISTORY_FILE, OUTPUT_DIR, load_channel
from .generator import generate_metadata
from .history import append_history, read_history
from .video import generate_short
from .youtube import upload_video


def _write_metadata(workdir, metadata: dict) -> None:
    (workdir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _apply_content_mode(channel_slug: str, channel: dict, requested: str) -> str:
    mode = (requested or "auto").lower().strip()
    if channel_slug == "dineroclaro":
        channel["audio_mode"] = "voice_music"
        return "voice"

    if channel_slug != "brotavida":
        return "voice" if channel.get("audio_mode") != "music_only" else "music"

    if mode == "auto":
        current = channel.get("audio_mode", "music_only")
        return "asmr" if current == "asmr" else ("voice" if current == "voice_music" else "music")
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
    resolved_mode = _apply_content_mode(channel_slug, channel, content_mode)
    previous = read_history(HISTORY_FILE, channel=channel_slug, limit=80)
    metadata = generate_metadata(channel, previous)
    metadata["content_mode"] = resolved_mode

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
