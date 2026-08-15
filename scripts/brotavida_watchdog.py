from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
HISTORY = ROOT / "state" / "history.jsonl"
SLOTS = [time(9, 30), time(13, 30), time(17, 30), time(21, 30)]


def _rows() -> list[dict]:
    if not HISTORY.exists():
        return []
    rows: list[dict] = []
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


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
    expected = sum(1 for slot in SLOTS if slot <= now.time())
    uploaded = sum(
        1
        for row in _rows()
        if str(row.get("channel")) == "brotavida"
        and str(row.get("status")) == "uploaded"
        and _local_day(str(row.get("created_at") or "")) == now.date()
    )
    print(json.dumps({
        "local_time": now.isoformat(),
        "expected": expected,
        "uploaded": uploaded,
        "missing": max(0, expected - uploaded),
        "daily_goal": 4,
        "slots": [slot.strftime("%H:%M") for slot in SLOTS],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
