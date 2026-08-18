from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.youtube import _youtube_for_channel

ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILES = (
    ROOT / "state" / "history.jsonl",
    ROOT / "state" / "dioshablahoyia_long_history.jsonl",
)
CHANNELS_PATH = ROOT / "config" / "channels.json"
REPORT_PATH = ROOT / "state" / "dioshablahoyia_video_audit.json"


def _load_channel() -> dict:
    data = json.loads(CHANNELS_PATH.read_text(encoding="utf-8"))
    return data["dioshablahoyia"]


def _history_rows() -> list[dict]:
    rows: list[dict] = []
    for path in HISTORY_FILES:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
            except Exception:
                continue
            if item.get("channel") != "dioshablahoyia":
                continue
            if item.get("status") != "uploaded":
                continue
            video_id = str(item.get("video_id") or "").strip()
            if not video_id:
                continue
            rows.append(item)
    return rows


def _chunks(values: list[str], size: int = 50):
    for index in range(0, len(values), size):
        yield values[index:index + size]


def main() -> None:
    channel = _load_channel()
    youtube = _youtube_for_channel(channel)
    rows = _history_rows()

    by_id: dict[str, dict] = {}
    for row in rows:
        by_id[str(row["video_id"])] = row
    history_ids = list(by_id)

    current: dict[str, dict] = {}
    for batch in _chunks(history_ids):
        response = youtube.videos().list(
            part="id,snippet,status,contentDetails",
            id=",".join(batch),
            maxResults=50,
        ).execute()
        for item in response.get("items") or []:
            status = item.get("status") or {}
            snippet = item.get("snippet") or {}
            current[item["id"]] = {
                "video_id": item["id"],
                "title": snippet.get("title"),
                "published_at": snippet.get("publishedAt"),
                "privacy_status": status.get("privacyStatus"),
                "upload_status": status.get("uploadStatus"),
                "made_for_kids": status.get("madeForKids"),
                "duration": (item.get("contentDetails") or {}).get("duration"),
            }

    missing: list[dict] = []
    for video_id in history_ids:
        if video_id in current:
            continue
        old = by_id[video_id]
        missing.append({
            "video_id": video_id,
            "title_in_history": old.get("title"),
            "created_at_in_history": old.get("created_at"),
            "content_type": "long" if old.get("long_form") or old.get("expected_minutes") else "short_or_standard",
        })

    channel_info = youtube.channels().list(
        part="id,snippet,statistics,contentDetails",
        mine=True,
    ).execute()
    item = (channel_info.get("items") or [{}])[0]
    statistics = item.get("statistics") or {}

    privacy_counts = Counter(str(value.get("privacy_status") or "unknown") for value in current.values())
    upload_counts = Counter(str(value.get("upload_status") or "unknown") for value in current.values())

    report = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "channel_id": item.get("id"),
        "channel_title": (item.get("snippet") or {}).get("title"),
        "channel_custom_url": (item.get("snippet") or {}).get("customUrl"),
        "youtube_reported_public_video_count": int(statistics.get("videoCount") or 0),
        "history_uploaded_unique_ids": len(history_ids),
        "history_ids_currently_returned_by_owner_api": len(current),
        "history_ids_missing_from_owner_api": len(missing),
        "privacy_counts_for_history_ids": dict(privacy_counts),
        "upload_status_counts_for_history_ids": dict(upload_counts),
        "missing_history_videos": missing,
        "current_history_videos": sorted(current.values(), key=lambda row: row.get("published_at") or "", reverse=True),
        "audit_mode": "read_only_no_delete_no_update_no_privacy_change",
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "history_ids": len(history_ids),
        "returned": len(current),
        "missing": len(missing),
        "privacy": dict(privacy_counts),
        "youtube_public_count": report["youtube_reported_public_video_count"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
