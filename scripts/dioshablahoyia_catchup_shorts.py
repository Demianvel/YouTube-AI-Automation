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
LOCKED_PUBLISHER = ROOT / "scripts" / "publish_dios_locked.py"


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except Exception:
        value = default
    return max(minimum, min(maximum, value))


# Publishing takes priority over waiting on exhausted provider quota. The
# workflow can raise these values explicitly for transient incidents, but the
# normal recovery path tries once and immediately advances to the next locked
# Algenib model instead of sleeping through repeated quota failures.
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
        status = str(row.get("status") or "").lower()
        if (
            row.get("channel") == "dioshablahoyia"
            and dt.astimezone(TZ).date() == today
            and (status == "uploaded" or bool(row.get("video_id")))
        ):
            count += 1
    return count


def _checkpoint(baseline: list[str]) -> int:
    """Persist every successful upload discovered since this recovery began.

    The workflow later commits this file even when a subsequent publication
    fails, so an already uploaded Short is never lost or regenerated.
    """
    current = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = [line for line in current[len(baseline) :] if line.strip()]
    RECORDS.write_text(
        "".join(f"{line}\n" for line in new_lines),
        encoding="utf-8",
    )
    print(f"Checkpoint persistible: {len(new_lines)} nuevo(s) Short(s).", flush=True)
    return len(new_lines)


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    baseline = HISTORY.read_text(encoding="utf-8").splitlines()
    _checkpoint(baseline)

    actual = _today_uploaded_count()
    missing = max(0, DAILY_TARGET - actual)
    print(f"Shorts publicados hoy (Argentina): {actual}")
    print(f"Shorts faltantes para llegar a {DAILY_TARGET}: {missing}")
    print(
        f"Politica de recuperacion: {PUBLISH_ATTEMPTS} intento(s) por Short, "
        f"espera {RETRY_WAIT_SECONDS}s entre intentos.",
        flush=True,
    )

    for index in range(1, missing + 1):
        print(f"=== Recuperando Short {index} de {missing} ===", flush=True)
        success = False
        for attempt in range(1, PUBLISH_ATTEMPTS + 1):
            print(
                f"Intento {attempt}/{PUBLISH_ATTEMPTS}: Voz de Luz / Algenib obligatoria y Jesus realista guiado por referencia obligatorio",
                flush=True,
            )
            result = subprocess.run(
                [sys.executable, str(LOCKED_PUBLISHER)],
                cwd=ROOT,
                check=False,
            )
            _checkpoint(baseline)
            if result.returncode == 0:
                success = True
                break
            if attempt < PUBLISH_ATTEMPTS and RETRY_WAIT_SECONDS > 0:
                print(
                    f"Fallo temporal; esperando {RETRY_WAIT_SECONDS}s sin cambiar voz, sin usar Kokoro y sin sustituir la identidad visual.",
                    flush=True,
                )
                time.sleep(RETRY_WAIT_SECONDS)
        if not success:
            _checkpoint(baseline)
            print(
                f"No se pudo recuperar el Short {index} con este modelo sin violar la voz fija o la identidad visual realista; el workflow debe avanzar al siguiente modelo Algenib.",
                file=sys.stderr,
            )
            return 1

    count = _checkpoint(baseline)
    print(f"Nuevos registros preparados para persistir: {count}")
    print(f"Total publicado hoy tras catch-up: {_today_uploaded_count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
