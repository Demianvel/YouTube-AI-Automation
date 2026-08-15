from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.workers.divine_publisher_4x10 import (
    DAILY_LONG_TARGET,
    DAILY_SHORT_TARGET,
    LONG_VIDEO_TIMES,
    SHORT_TIMES,
    WORKER,
)

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
SHORT_HISTORY = ROOT / "state" / "history.jsonl"
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        items.append(row)
    return items


def _local_day(value: str):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(TZ).date()
    except Exception:
        return None


def _is_uploaded(row: dict) -> bool:
    status = str(row.get("status") or row.get("publish_status") or "").lower()
    video_id = str(row.get("video_id") or "").strip()
    return status in {"uploaded", "published", "success"} or bool(video_id)


def main() -> None:
    now = datetime.now(TZ)
    today = now.date()

    short_expected = sum(1 for slot in SHORT_TIMES if slot <= now.time())
    short_actual = sum(
        1
        for row in _rows(SHORT_HISTORY)
        if str(row.get("channel")) == "dioshablahoyia"
        and _is_uploaded(row)
        and _local_day(str(row.get("created_at") or "")) == today
    )

    long_expected = sum(1 for slot in LONG_VIDEO_TIMES if slot <= now.time())
    long_actual = sum(
        1
        for row in _rows(LONG_HISTORY)
        if _is_uploaded(row)
        and _local_day(str(row.get("created_at") or row.get("published_at") or "")) == today
    )

    result = {
        "worker": WORKER["name"],
        "local_time": now.isoformat(),
        "daily_short_target": DAILY_SHORT_TARGET,
        "daily_long_target": DAILY_LONG_TARGET,
        "short_expected": short_expected,
        "short_actual": short_actual,
        "short_missing": max(0, short_expected - short_actual),
        "long_expected": long_expected,
        "long_actual": long_actual,
        "long_missing": max(0, long_expected - long_actual),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
