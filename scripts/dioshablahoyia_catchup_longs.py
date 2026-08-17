from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"
RECORDS = Path("/tmp/dios-catchup/new-long-records.jsonl")
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
TARGETS = {
    10: "biblical_story",
    15: "prayer",
    20: "biblical_reflection",
    30: "night_prayer",
}


def _uploaded_today() -> set[int]:
    result: set[int] = set()
    if not HISTORY.exists():
        return result
    today = datetime.now(TZ).date()
    for raw in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
            dt = datetime.fromisoformat(str(row.get("created_at", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            minutes = int(row.get("minutes", 0))
        except Exception:
            continue
        if dt.astimezone(TZ).date() == today and row.get("status") == "uploaded" and minutes in TARGETS:
            result.add(minutes)
    return result


def _publish(minutes: int) -> bool:
    env = os.environ.copy()
    env["SPIRITUAL_NARRATION_STYLE"] = TARGETS[minutes]
    for attempt in range(1, 4):
        print(
            f"Publicando {minutes} min ({TARGETS[minutes]}) — intento {attempt}/3 — Voz de Luz/Algenib y visual fresco obligatorios",
            flush=True,
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "publish_dios_long_fresh.py"),
                "--minutes",
                str(minutes),
                "--publish",
            ],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if result.returncode == 0:
            return True
        if attempt < 3:
            print("Fallo temporal; esperando 90 s sin cambiar voz ni reutilizar visuales.", flush=True)
            time.sleep(90)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, choices=sorted(TARGETS))
    args = parser.parse_args()

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    baseline = HISTORY.read_text(encoding="utf-8").splitlines()

    uploaded = _uploaded_today()
    targets = [args.minutes] if args.minutes else list(TARGETS)
    missing = [minutes for minutes in targets if minutes not in uploaded]
    print(f"Largos ya publicados hoy (Argentina): {sorted(uploaded)}")
    print(f"Duraciones a recuperar: {missing}")

    for minutes in missing:
        if not _publish(minutes):
            print(
                f"No se pudo publicar {minutes} min respetando Voz de Luz y visual fresco.",
                file=sys.stderr,
            )
            current = HISTORY.read_text(encoding="utf-8").splitlines()
            new_lines = current[len(baseline) :]
            RECORDS.write_text("".join(f"{line}\n" for line in new_lines if line.strip()), encoding="utf-8")
            return 1

    current = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = current[len(baseline) :]
    RECORDS.write_text("".join(f"{line}\n" for line in new_lines if line.strip()), encoding="utf-8")
    print(f"Nuevos largos preparados para persistir: {len(new_lines)}")
    print(f"Duraciones completas hoy: {sorted(_uploaded_today())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
