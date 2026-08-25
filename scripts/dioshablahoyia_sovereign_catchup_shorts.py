from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "history.jsonl"
RECORDS = Path("/tmp/dios-sovereign-catchup/new-short-records.jsonl")
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DAILY_TARGET = 10
PUBLISHER = ROOT / "scripts" / "publish_dios_sovereign.py"


def today_uploaded_count() -> int:
    if not HISTORY.exists():
        return 0
    today = datetime.now(TZ).date()
    count = 0
    for raw in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
            dt = datetime.fromisoformat(str(row.get("created_at", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        except Exception:
            continue
        if (
            row.get("channel") == "dioshablahoyia"
            and dt.astimezone(TZ).date() == today
            and (str(row.get("status") or "").lower() == "uploaded" or bool(row.get("video_id")))
        ):
            count += 1
    return count


def checkpoint(baseline: list[str]) -> int:
    current = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = [line for line in current[len(baseline):] if line.strip()]
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    RECORDS.write_text("".join(f"{line}\n" for line in new_lines), encoding="utf-8")
    print(f"Checkpoint soberano: {len(new_lines)} nuevo(s) Short(s).", flush=True)
    return len(new_lines)


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    baseline = HISTORY.read_text(encoding="utf-8").splitlines()
    checkpoint(baseline)

    actual = today_uploaded_count()
    missing = max(0, DAILY_TARGET - actual)
    print(f"Shorts confirmados hoy en Argentina: {actual}/{DAILY_TARGET}", flush=True)
    print(f"Faltan: {missing}", flush=True)

    for index in range(1, missing + 1):
        print(f"=== Short soberano {index}/{missing} ===", flush=True)
        result = subprocess.run([sys.executable, str(PUBLISHER)], cwd=ROOT, check=False)
        checkpoint(baseline)
        if result.returncode != 0:
            print(
                f"El Short soberano {index} fallo; se detiene para no duplicar ni publicar material degradado.",
                file=sys.stderr,
            )
            return result.returncode or 1

    checkpoint(baseline)
    print(f"Total confirmado hoy: {today_uploaded_count()}/{DAILY_TARGET}", flush=True)
    return 0 if today_uploaded_count() >= DAILY_TARGET else 1


if __name__ == "__main__":
    raise SystemExit(main())
