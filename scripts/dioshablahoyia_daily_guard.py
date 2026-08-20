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
NEW_RECORDS = Path("/tmp/dios-daily-guard/new-short-records.jsonl")
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
DAILY_TARGET = 10


def today_uploaded_count() -> int:
    if not HISTORY.exists():
        return 0

    today = datetime.now(TZ).date()
    count = 0
    for raw in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
            if row.get("channel") != "dioshablahoyia":
                continue
            status = str(row.get("status") or "").lower()
            if status != "uploaded" and not row.get("video_id"):
                continue
            stamp = str(row.get("created_at") or "").strip()
            if not stamp:
                continue
            moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=ZoneInfo("UTC"))
            if moment.astimezone(TZ).date() == today:
                count += 1
        except Exception:
            continue
    return count


def _publisher_script() -> str:
    if os.getenv("DIOS_GUARD_LOCAL_ONLY", "").lower().strip() == "true":
        return "publish_dios_fast_local_emergency.py"
    return "publish_dios_fast.py"


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    NEW_RECORDS.parent.mkdir(parents=True, exist_ok=True)

    baseline = HISTORY.read_text(encoding="utf-8").splitlines()
    current = today_uploaded_count()
    publisher = _publisher_script()
    print(f"GUARDIA DIARIA: {current}/{DAILY_TARGET} Shorts subidos hoy en Argentina.")
    print(f"Publicador de esta pasada: {publisher}")

    if current >= DAILY_TARGET:
        NEW_RECORDS.write_text("", encoding="utf-8")
        print("Objetivo diario cumplido. No se genera ni se publica contenido extra.")
        return 0

    while current < DAILY_TARGET:
        before = current
        missing = DAILY_TARGET - before
        print(
            f"Faltan {missing} Shorts. Se intenta uno con Voz de Luz / Algenib obligatoria; "
            "nunca se permite otra voz.",
            flush=True,
        )

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / publisher)],
            cwd=ROOT,
            check=False,
        )
        current = today_uploaded_count()

        # If the upload was recorded even though a later non-critical step returned
        # non-zero, never retry blindly: that could create a duplicate.
        if current > before:
            print(f"Short confirmado. Total del dia: {current}/{DAILY_TARGET}", flush=True)
            if current < DAILY_TARGET:
                time.sleep(45 if publisher == "publish_dios_fast_local_emergency.py" else 75)
            continue

        if result.returncode != 0:
            print(
                "La publicacion fallo antes de quedar registrada. Se detiene esta pasada para no gastar "
                "cuota ni duplicar; el siguiente control automatico volvera a verificar los faltantes.",
                file=sys.stderr,
            )
            break

        print(
            "El publicador termino sin error pero el historial no aumento. Se detiene por seguridad para "
            "evitar una subida duplicada.",
            file=sys.stderr,
        )
        break

    all_lines = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = all_lines[len(baseline) :]
    NEW_RECORDS.write_text(
        "".join(f"{line}\n" for line in new_lines if line.strip()),
        encoding="utf-8",
    )

    final_count = today_uploaded_count()
    print(f"GUARDIA DIARIA FINAL: {final_count}/{DAILY_TARGET}")
    return 0 if final_count >= DAILY_TARGET else 1


if __name__ == "__main__":
    raise SystemExit(main())
