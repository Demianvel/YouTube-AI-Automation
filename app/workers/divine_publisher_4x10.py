from __future__ import annotations

from datetime import time

WORKER = {
    "id": "divine_publisher_4x10",
    "name": "Publicador Reino 4x10",
    "role": "planificacion_publicacion_youtube",
    "owner": "publishing",
}

ACTIVE_CHANNEL = "dioshablahoyia"
DAILY_SHORT_TARGET = 10
DAILY_LONG_TARGET = 4

SHORT_TIMES = [
    time(7, 30), time(9, 0), time(10, 30), time(12, 0), time(13, 30),
    time(15, 0), time(16, 30), time(18, 0), time(19, 30), time(21, 0),
]

LONG_VIDEO_TIMES = [time(8, 0), time(12, 0), time(16, 0), time(20, 0)]
LONG_VIDEO_MINUTES = [10, 15, 20, 30]


def validate_channel(channel_slug: str) -> None:
    if channel_slug != ACTIVE_CHANNEL:
        raise RuntimeError(
            f"{WORKER['name']} solo tiene permiso de publicacion para {ACTIVE_CHANNEL}; recibido: {channel_slug}"
        )


def publication_plan() -> dict:
    return {
        "worker": WORKER["name"],
        "channel": ACTIVE_CHANNEL,
        "shorts_per_day": DAILY_SHORT_TARGET,
        "long_videos_per_day": DAILY_LONG_TARGET,
        "short_times_argentina": [slot.strftime("%H:%M") for slot in SHORT_TIMES],
        "long_times_argentina": [slot.strftime("%H:%M") for slot in LONG_VIDEO_TIMES],
        "long_video_minutes": LONG_VIDEO_MINUTES,
        "anti_duplicate": True,
        "serialize_recovery_runs": True,
    }


def mark_publish_metadata(meta: dict, *, content_type: str) -> dict:
    meta["worker_publisher"] = WORKER["name"]
    meta["worker_publisher_id"] = WORKER["id"]
    meta["publication_content_type"] = content_type
    meta["daily_short_target"] = DAILY_SHORT_TARGET
    meta["daily_long_target"] = DAILY_LONG_TARGET
    meta["publisher_channel_lock"] = ACTIVE_CHANNEL
    return meta
