from __future__ import annotations

import json
import os
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
PUBLISHER = ROOT / "scripts" / "publish_dios_premium_v5.py"


def _slot_attempts() -> int:
    try:
        value = int(os.getenv("DIOS_SOVEREIGN_SLOT_ATTEMPTS", "3"))
    except ValueError:
        value = 3
    return max(1, min(5, value))


def _manual_force_one() -> bool:
    explicit = os.getenv("DIOS_FORCE_ONE_PREMIUM_V5", "").strip().lower() == "true"
    # This workflow only receives push events for its dedicated manual trigger file,
    # so a push means the owner explicitly asked for a fresh premium-v5 piece.
    trigger_push = os.getenv("GITHUB_EVENT_NAME", "").strip().lower() == "push"
    return explicit or trigger_push


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
    print(f"Checkpoint premium soberano: {len(new_lines)} nuevo(s) Short(s).", flush=True)
    return len(new_lines)


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    baseline = HISTORY.read_text(encoding="utf-8").splitlines()
    checkpoint(baseline)

    actual = today_uploaded_count()
    force_one = _manual_force_one()
    normal_missing = max(0, DAILY_TARGET - actual)
    missing = max(1 if force_one else 0, normal_missing)
    completion_target = max(DAILY_TARGET, actual + 1) if force_one and normal_missing == 0 else DAILY_TARGET
    attempts_per_slot = _slot_attempts()

    print(f"Shorts confirmados hoy en Argentina: {actual}/{DAILY_TARGET}", flush=True)
    print(f"Faltan por objetivo diario: {normal_missing}", flush=True)
    print(f"Forzar una pieza premium v5 por trigger manual: {force_one}", flush=True)
    print(f"Piezas a generar en este run: {missing}", flush=True)
    print(f"Intentos de calidad permitidos por plaza: {attempts_per_slot}", flush=True)

    for index in range(1, missing + 1):
        print(f"=== Plaza premium soberana {index}/{missing} ===", flush=True)
        published = False
        for attempt in range(1, attempts_per_slot + 1):
            print(
                f"Generando candidato {attempt}/{attempts_per_slot} para la plaza {index}/{missing}",
                flush=True,
            )
            result = subprocess.run([sys.executable, str(PUBLISHER)], cwd=ROOT, check=False)
            checkpoint(baseline)
            if result.returncode == 0:
                published = True
                print(
                    f"Plaza {index}/{missing} publicada correctamente con candidato {attempt}.",
                    flush=True,
                )
                break
            print(
                f"Candidato {attempt}/{attempts_per_slot} rechazado por un guard o error de generacion; "
                "se intentara una pieza nueva sin bajar los controles de calidad.",
                file=sys.stderr,
                flush=True,
            )

        if not published:
            print(
                f"No se obtuvo un candidato valido para la plaza {index} despues de "
                f"{attempts_per_slot} intentos. Se detiene sin duplicar ni degradar calidad.",
                file=sys.stderr,
            )
            return 1

    checkpoint(baseline)
    confirmed = today_uploaded_count()
    print(f"Total confirmado hoy: {confirmed}. Objetivo de este run: {completion_target}.", flush=True)
    return 0 if confirmed >= completion_target else 1


if __name__ == "__main__":
    raise SystemExit(main())
