from __future__ import annotations

import json
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
LOCKED_PUBLISHER = ROOT / "scripts" / "publish_dios_locked.py"


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
        status = str(row.get("status") or "").lower()
        if (
            row.get("channel") == "dioshablahoyia"
            and dt.astimezone(TZ).date() == today
            and (status == "uploaded" or bool(row.get("video_id")))
        ):
            count += 1
    return count


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    baseline = HISTORY.read_text(encoding="utf-8").splitlines()

    actual = _today_uploaded_count()
    missing = max(0, DAILY_TARGET - actual)
    print(f"Shorts publicados hoy (Argentina): {actual}")
    print(f"Shorts faltantes para llegar a {DAILY_TARGET}: {missing}")

    for index in range(1, missing + 1):
        print(f"=== Recuperando Short {index} de {missing} ===", flush=True)
        success = False
        for attempt in range(1, 4):
            print(
                f"Intento {attempt}/3: Voz de Luz / Algenib obligatoria y Jesus realista guiado por referencia obligatorio",
                flush=True,
            )
            result = subprocess.run(
                [sys.executable, str(LOCKED_PUBLISHER)],
                cwd=ROOT,
                check=False,
            )
            if result.returncode == 0:
                success = True
                break
            if attempt < 3:
                print(
                    "Fallo temporal; esperando 75 s sin cambiar voz, sin usar Kokoro y sin sustituir la identidad visual.",
                    flush=True,
                )
                time.sleep(75)
        if not success:
            print(
                f"No se pudo recuperar el Short {index} sin violar la voz fija o la identidad visual realista.",
                file=sys.stderr,
            )
            return 1

    current = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = current[len(baseline) :]
    RECORDS.write_text(
        "".join(f"{line}\n" for line in new_lines if line.strip()),
        encoding="utf-8",
    )
    print(f"Nuevos registros preparados para persistir: {len(new_lines)}")
    print(f"Total publicado hoy tras catch-up: {_today_uploaded_count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
