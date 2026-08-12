from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def enrich_history_with_youtube_stats(channel: dict, history: list[dict]) -> list[dict]:
    """Add lightweight public performance signals to recent uploaded history entries."""
    token_json = os.getenv(channel.get("token_env", ""), "").strip()
    if not token_json or not history:
        return history

    ids = [str(item.get("video_id") or "").strip() for item in history[-50:]]
    ids = [video_id for video_id in ids if video_id]
    if not ids:
        return history

    credentials = Credentials.from_authorized_user_info(json.loads(token_json), scopes=SCOPES)
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = youtube.videos().list(
        part="statistics",
        id=",".join(ids[:50]),
        maxResults=50,
    ).execute()

    stats_by_id: dict[str, dict] = {}
    for item in response.get("items", []):
        stats = item.get("statistics") or {}
        stats_by_id[item["id"]] = {
            "views": int(stats.get("viewCount") or 0),
            "likes": int(stats.get("likeCount") or 0),
            "comments": int(stats.get("commentCount") or 0),
        }

    now = datetime.now(timezone.utc)
    enriched: list[dict] = []
    for original in history:
        row = dict(original)
        video_id = str(row.get("video_id") or "")
        stats = stats_by_id.get(video_id)
        if stats:
            row.update(stats)
            created = _parse_time(row.get("created_at"))
            if created:
                age_hours = max(1.0, (now - created).total_seconds() / 3600.0)
                row["vph"] = round(stats["views"] / age_hours, 2)
            views = max(1, stats["views"])
            row["like_rate"] = round(stats["likes"] / views, 4)
            row["comment_rate"] = round(stats["comments"] / views, 4)
        enriched.append(row)
    return enriched
