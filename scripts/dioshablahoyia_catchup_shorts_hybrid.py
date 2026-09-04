from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "history.jsonl"
RECORDS = Path("/tmp/dios-catchup/new-short-records.jsonl")
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DAILY_TARGET = 10
PUBLISHER = ROOT / "scripts" / "publish_dios_hybrid.py"


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


PUBLISH_ATTEMPTS = _env_int("DIOS_CATCHUP_PUBLISH_ATTEMPTS", 1, 1, 3)
RETRY_WAIT_SECONDS = _env_int("DIOS_CATCHUP_RETRY_WAIT_SECONDS", 0, 0, 75)


def _today_uploaded_count() -> int:
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
        video_id = str(row.get("video_id") or "").strip()
        if (
            row.get("channel") == "dioshablahoyia"
            and dt.astimezone(TZ).date() == today
            and video_id
        ):
            count += 1
    return count


def _checkpoint(baseline: list[str]) -> int:
    current = HISTORY.read_text(encoding="utf-8").splitlines()
    candidates = [line for line in current[len(baseline):] if line.strip()]
    confirmed: list[str] = []
    for line in candidates:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("channel") == "dioshablahoyia" and str(row.get("video_id") or "").strip():
            confirmed.append(line)
    RECORDS.write_text("".join(f"{line}\n" for line in confirmed), encoding="utf-8")
    print(f"Checkpoint persistible: {len(confirmed)} nuevo(s) Short(s) con video_id real.", flush=True)
    return len(confirmed)


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    baseline = HISTORY.read_text(encoding="utf-8").splitlines()
    _checkpoint(baseline)

    actual = _today_uploaded_count()
    missing = max(0, DAILY_TARGET - actual)
    print(f"Shorts confirmados hoy (Argentina): {actual}")
    print(f"Shorts faltantes para llegar a {DAILY_TARGET}: {missing}")
    print("Voz: Algenib primaria; Qwen3-TTS local solo ante cuota Gemini.", flush=True)

    for index in range(1, missing + 1):
        # Recount before each generation because persisted history may have moved
        # forward during recovery. This is the hard cap that prevents >10/day.
        current = _today_uploaded_count()
        if current >= DAILY_TARGET:
            print(f"Objetivo alcanzado durante la ejecucion: {current}/{DAILY_TARGET}.")
            break

        print(f"=== Recuperando Short {index} de {missing}; actual={current}/{DAILY_TARGET} ===", flush=True)
        success = False
        for attempt in range(1, PUBLISH_ATTEMPTS + 1):
            result = subprocess.run([sys.executable, str(PUBLISHER)], cwd=ROOT, check=False)
            _checkpoint(baseline)
            if result.returncode == 0:
                success = True
                break
            if attempt < PUBLISH_ATTEMPTS and RETRY_WAIT_SECONDS > 0:
                time.sleep(RETRY_WAIT_SECONDS)
        if not success:
            _checkpoint(baseline)
            print(f"No se pudo recuperar el Short {index} con el publisher premium hibrido.", file=sys.stderr)
            return 1

    count = _checkpoint(baseline)
    total = _today_uploaded_count()
    print(f"Nuevos registros preparados para persistir: {count}")
    print(f"Total confirmado hoy tras catch-up: {total}")
    if total > DAILY_TARGET:
        raise RuntimeError(f"DAILY_CAP_BREACH: {total}>{DAILY_TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
