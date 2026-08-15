from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
SHORT_HISTORY = ROOT / "state" / "history.jsonl"
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"

SHORT_TIMES = [
    time(7, 30), time(9, 0), time(10, 30), time(12, 0), time(13, 30),
    time(15, 0), time(16, 30), time(18, 0), time(19, 30), time(21, 0),
]
LONG_SLOTS = [(time(8, 0), 10), (time(12, 0), 15), (time(16, 0), 20), (time(20, 0), 30)]


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


def main() -> None:
    now = datetime.now(TZ)
    today = now.date()
    short_expected = sum(1 for slot in SHORT_TIMES if slot <= now.time())
    short_actual = sum(
        1
        for row in _rows(SHORT_HISTORY)
        if str(row.get("channel")) == "dioshablahoyia"
        and str(row.get("status")) == "uploaded"
        and _local_day(str(row.get("created_at") or "")) == today
    )

    long_actual = {
        int(row.get("minutes"))
        for row in _rows(LONG_HISTORY)
        if str(row.get("channel")) == "dioshablahoyia"
        and str(row.get("status")) == "uploaded"
        and _local_day(str(row.get("created_at") or "")) == today
        and str(row.get("minutes") or "").isdigit()
    }
    long_expected = [minutes for slot, minutes in LONG_SLOTS if slot <= now.time()]
    long_missing = [minutes for minutes in long_expected if minutes not in long_actual]

    result = {
        "local_time": now.isoformat(),
        "short_expected": short_expected,
        "short_actual": short_actual,
        "short_missing": max(0, short_expected - short_actual),
        "long_expected": long_expected,
        "long_actual": sorted(long_actual),
        "long_missing": long_missing,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
