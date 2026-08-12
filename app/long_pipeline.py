from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .channel_analytics import analytics_digest, collect_channel_analytics
from .config import OUTPUT_DIR, load_channel
from .long_generator import generate_long_metadata
from .long_video import generate_long_video
from .thumbnail import generate_thumbnail_variants
from .youtube import upload_long_video


def _compact_artifact(workdir: Path) -> None:
    keep = {
        "video_5min.mp4",
        "metadata.json",
        "result.json",
        "thumbnail_1.jpg",
        "thumbnail_2.jpg",
        "thumbnail_3.jpg",
    }
    for path in workdir.iterdir():
        if path.is_file() and path.name not in keep:
            path.unlink(missing_ok=True)


def run(channel_slug: str, publish: bool = False) -> dict:
    if channel_slug not in {"brotavida", "dineroclaro"}:
        raise ValueError("Long-form 5 min solo esta habilitado para brotavida y dineroclaro.")

    channel = load_channel(channel_slug)
    try:
        snapshot = collect_channel_analytics(channel, days=90)
        channel["_analytics_digest"] = analytics_digest(snapshot)
    except Exception as exc:
        channel["_analytics_digest"] = "Analytics detallado no disponible en esta ejecucion; no inventar datos."
        print(f"Analytics long-form no disponible: {exc}")

    metadata = generate_long_metadata(channel)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / "long5min" / channel_slug / stamp
    workdir.mkdir(parents=True, exist_ok=True)

    metadata_file = workdir / "metadata.json"
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    video_path = generate_long_video(channel, metadata, workdir)
    thumbnails = generate_thumbnail_variants(video_path, metadata, workdir)
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    video_id = None
    status = "generated"
    if publish:
        video_id = upload_long_video(channel, metadata, video_path, thumbnail_path=thumbnails[0])
        status = "uploaded"

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": channel_slug,
        "handle": channel["handle"],
        "title": metadata.get("title"),
        "title_variants": metadata.get("title_variants"),
        "duration_seconds": metadata.get("duration_seconds", 300),
        "tts_provider_used": metadata.get("tts_provider_used"),
        "analytics_used": bool(channel.get("_analytics_digest")),
        "video_id": video_id,
        "status": status,
        "path": str(video_path),
        "thumbnail_default": str(thumbnails[0]),
        "thumbnail_ab_candidates": [str(p) for p in thumbnails],
        "ab_note": "YouTube Studio permite probar hasta 3 titulos/miniaturas en videos largos elegibles; el Data API solo fija una miniatura por vez.",
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    _compact_artifact(workdir)
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
