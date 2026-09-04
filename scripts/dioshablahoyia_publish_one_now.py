from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "history.jsonl"
RECORDS = Path("/tmp/dios-one-premium/new-short-records.jsonl")
PUBLISHER = ROOT / "scripts" / "publish_dios_hybrid.py"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DAILY_CAP = 10


def _today_rows() -> list[dict]:
    if not HISTORY.exists():
        return []
    today = datetime.now(TZ).date()
    rows: list[dict] = []
    for raw in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
            dt = datetime.fromisoformat(str(row.get("created_at") or "").replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if (
            row.get("channel") == "dioshablahoyia"
            and dt.astimezone(TZ).date() == today
            and str(row.get("video_id") or "").strip()
        ):
            rows.append(row)
    return rows


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    RECORDS.parent.mkdir(parents=True, exist_ok=True)

    baseline_lines = HISTORY.read_text(encoding="utf-8").splitlines()
    before_ids = {str(r.get("video_id")) for r in _today_rows() if r.get("video_id")}
    before_count = len(before_ids)
    print(f"CONFIRMED_BEFORE={before_count}", flush=True)

    if before_count >= DAILY_CAP:
        print(f"DAILY_CAP_REACHED={before_count}/{DAILY_CAP}; no se publica otro Short.", flush=True)
        RECORDS.write_text("", encoding="utf-8")
        return 0

    result = subprocess.run([sys.executable, str(PUBLISHER)], cwd=ROOT, check=False)

    current_lines = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = [line for line in current_lines[len(baseline_lines):] if line.strip()]
    confirmed: list[str] = []
    seen: set[str] = set()
    new_video_id = ""

    for line in new_lines:
        try:
            row = json.loads(line)
        except Exception:
            continue
        video_id = str(row.get("video_id") or "").strip()
        if row.get("channel") != "dioshablahoyia" or not video_id or video_id in before_ids or video_id in seen:
            continue
        seen.add(video_id)
        confirmed.append(line)
        if not new_video_id:
            new_video_id = video_id

    RECORDS.write_text("".join(f"{line}\n" for line in confirmed[:1]), encoding="utf-8")

    if new_video_id:
        print(f"UPLOAD_CONFIRMADO={new_video_id}", flush=True)
        print("EXACT_ONE_SHORT_SUCCESS=true", flush=True)
        return 0

    print(f"Publisher returncode={result.returncode} pero no aparecio un video_id nuevo.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
