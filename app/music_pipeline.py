from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .channel_analytics import analytics_digest, collect_channel_analytics
from .config import OUTPUT_DIR, load_channel
from .music_audio import generate_original_electronic_track
from .music_generator import generate_music_metadata
from .music_video import render_music_video
from .thumbnail import generate_thumbnail_variants
from .youtube import upload_long_video, upload_video


def run(minutes: int, publish: bool = False) -> dict:
    channel = load_channel("demianvelo")
    try:
        snapshot = collect_channel_analytics(channel, days=90)
        channel["_analytics_digest"] = analytics_digest(snapshot)
    except Exception as exc:
        channel["_analytics_digest"] = "Analytics no disponible; explorar estilos de forma equilibrada y no inventar preferencias."
        print(f"DemianVelo Analytics no disponible: {exc}")

    meta = generate_music_metadata(channel, minutes)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / "demianvelo" / f"{minutes}min" / stamp
    workdir.mkdir(parents=True, exist_ok=True)

    music = workdir / f"demianvelo_original_{minutes}min.wav"
    seed = abs(hash(f"{meta.get('title')}|{stamp}")) & 0x7FFFFFFF
    generate_original_electronic_track(
        music,
        int(meta["duration_seconds"]),
        seed,
        bpm=int(meta.get("bpm") or 128),
        style=str(meta.get("music_style") or "progressive_house"),
        faith_theme=bool(meta.get("faith_theme")),
    )
    video = render_music_video(meta, music, workdir)

    thumbnails = []
    if minutes > 1:
        thumbnails = generate_thumbnail_variants(video, meta, workdir)

    video_id = None
    status = "generated"
    if publish:
        if minutes == 1:
            video_id = upload_video(channel, meta, video)
        else:
            video_id = upload_long_video(
                channel,
                meta,
                video,
                thumbnail_path=thumbnails[0] if thumbnails else None,
                expected_minutes=minutes,
            )
        status = "uploaded"

    meta_file = workdir / "metadata.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": "demianvelo",
        "handle": channel["handle"],
        "minutes": minutes,
        "title": meta.get("title"),
        "music_style": meta.get("music_style"),
        "faith_theme": meta.get("faith_theme"),
        "bpm": meta.get("bpm"),
        "video_id": video_id,
        "status": status,
        "video": str(video),
        "music": str(music),
        "analytics_used": bool(channel.get("_analytics_digest")),
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[1, 5, 10, 30])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.minutes, publish=args.publish)


if __name__ == "__main__":
    main()
