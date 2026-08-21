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
LOCKED_PUBLISHER = "publish_dios_locked.py"


def _rows() -> list[dict]:
    if not HISTORY.exists():
        return []
    rows: list[dict] = []
    for raw in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") != "dioshablahoyia":
            continue
        status = str(row.get("status") or "").lower()
        if status != "uploaded" and not row.get("video_id"):
            continue
        rows.append(row)
    return rows


def _uploaded_ids() -> set[str]:
    return {str(row.get("video_id")) for row in _rows() if str(row.get("video_id") or "").strip()}


def today_uploaded_count() -> int:
    today = datetime.now(TZ).date()
    count = 0
    for row in _rows():
        stamp = str(row.get("created_at") or "").strip()
        if not stamp:
            continue
        try:
            moment = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=ZoneInfo("UTC"))
            if moment.astimezone(TZ).date() == today:
                count += 1
        except Exception:
            continue
    return count


def _publisher_script() -> str:
    """Always use the permanent identity-locked publisher.

    DIOS_GUARD_LOCAL_ONLY is intentionally ignored for media identity. Older
    workflows may still export it, but it can no longer switch the narrator or
    visual engine away from Voz de Luz / Algenib + the approved reference bank.
    """
    return LOCKED_PUBLISHER


def _recovery_limit(initial_today: int) -> int:
    raw = os.getenv("DIOS_GUARD_RECOVERY_LIMIT", "").strip()
    if raw:
        try:
            return max(0, int(raw))
        except ValueError as exc:
            raise RuntimeError(f"DIOS_GUARD_RECOVERY_LIMIT invalido: {raw}") from exc
    return max(0, DAILY_TARGET - initial_today)


def main() -> int:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    NEW_RECORDS.parent.mkdir(parents=True, exist_ok=True)

    baseline_lines = HISTORY.read_text(encoding="utf-8").splitlines()
    initial_ids = _uploaded_ids()
    initial_today = today_uploaded_count()
    initial_missing = _recovery_limit(initial_today)
    publisher = _publisher_script()

    print(f"GUARDIA DIARIA: {initial_today}/{DAILY_TARGET} Shorts subidos al iniciar en Argentina.")
    print(f"Objetivo congelado para esta recuperacion: {initial_missing} nuevas subidas maximas.")
    print(f"Publicador permanente de esta pasada: {publisher}")

    if initial_missing <= 0:
        NEW_RECORDS.write_text("", encoding="utf-8")
        print("No hay subidas pendientes para esta recuperacion.")
        return 0

    successful_new = 0
    while successful_new < initial_missing:
        before_ids = _uploaded_ids()
        remaining = initial_missing - successful_new
        print(
            f"Faltan {remaining} de esta recuperacion. Se intenta uno con Voz de Luz / Algenib obligatoria "
            "y referencias realistas bloqueadas; nunca se permite otra voz ni visual procedural.",
            flush=True,
        )

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / publisher)],
            cwd=ROOT,
            check=False,
        )
        after_ids = _uploaded_ids()
        newly_recorded = after_ids - before_ids

        if newly_recorded:
            accepted = min(len(newly_recorded), remaining)
            successful_new += accepted
            ids_text = ", ".join(sorted(newly_recorded))
            print(
                f"Short confirmado por nuevo video_id ({ids_text}). "
                f"Recuperados: {successful_new}/{initial_missing}",
                flush=True,
            )
            if successful_new < initial_missing:
                time.sleep(75)
            continue

        if result.returncode != 0:
            print(
                "La publicacion fallo antes de quedar registrada. Se detiene esta pasada antes de cambiar la voz, "
                "perder la identidad visual o arriesgar un duplicado.",
                file=sys.stderr,
            )
            break

        print(
            "El publicador termino sin error pero no aparecio un nuevo video_id. Se detiene por seguridad "
            "para evitar una subida duplicada.",
            file=sys.stderr,
        )
        break

    all_lines = HISTORY.read_text(encoding="utf-8").splitlines()
    new_lines = all_lines[len(baseline_lines) :]
    NEW_RECORDS.write_text(
        "".join(f"{line}\n" for line in new_lines if line.strip()),
        encoding="utf-8",
    )

    final_ids = _uploaded_ids()
    confirmed_new = len(final_ids - initial_ids)
    final_today = today_uploaded_count()
    print(
        f"GUARDIA FINAL: nuevos confirmados={confirmed_new}/{initial_missing}; "
        f"conteo fecha local actual={final_today}/{DAILY_TARGET}"
    )
    return 0 if confirmed_new >= initial_missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
