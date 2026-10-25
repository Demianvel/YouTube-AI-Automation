"""Dios Habla Hoy IA - Orquestador 10 Shorts 24/7.

Decides how many Shorts to publish *now* and delegates the publishing to the
proven path: scripts/dioshablahoyia_catchup_shorts_hybrid.py ->
scripts/publish_dios_hybrid.py (Dios Brain + Voz de Luz + upload + history).

Rule: confirmed Shorts today (Argentina, real video_id) are compared with the
slots already elapsed (app.workers.divine_publisher_4x10.SHORT_TIMES). The
difference is published, at most DIOS_ORCHESTRATOR_MAX_PER_RUN (default 2) per
run and never above 10 per day. A manual ``count`` (DIOS_ORCHESTRATOR_COUNT > 0)
asks for that many extra Shorts now, with the same caps.

Usage:
  python scripts/dios_orchestrator.py plan   # stdlib only; prints/exports the plan
  python scripts/dios_orchestrator.py run    # plan + publish what is missing
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.workers.divine_publisher_4x10 import DAILY_SHORT_TARGET, SHORT_TIMES  # noqa: E402
from scripts.dioshablahoyia_catchup_shorts_hybrid import _today_uploaded_count  # noqa: E402

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
CATCHUP = ROOT / "scripts" / "dioshablahoyia_catchup_shorts_hybrid.py"
PLAN_FILE = Path("/tmp/dios-catchup/orchestrator-plan.json")


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(str(os.getenv(name, str(default))).strip() or default)
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def slots_due(now: datetime | None = None, slots: list[time] | None = None) -> int:
    now = (now or datetime.now(TZ)).astimezone(TZ)
    return sum(1 for slot in (slots or SHORT_TIMES) if slot <= now.time())


def build_plan(confirmed: int, due: int, manual_count: int = 0, max_per_run: int = 2, daily_target: int = DAILY_SHORT_TARGET) -> dict:
    confirmed = max(0, int(confirmed))
    if manual_count > 0:
        target = min(daily_target, confirmed + manual_count)
        mode = "manual"
    else:
        target = min(daily_target, max(0, int(due)))
        mode = "slots"
    to_publish = max(0, min(target - confirmed, max_per_run, daily_target - confirmed))
    return {
        "mode": mode,
        "confirmed_today": confirmed,
        "slots_due": int(due),
        "daily_target": daily_target,
        "run_target": min(daily_target, confirmed + to_publish),
        "max_per_run": max_per_run,
        "to_publish": to_publish,
    }


def current_plan() -> dict:
    now = datetime.now(TZ)
    plan = build_plan(
        confirmed=_today_uploaded_count(),
        due=slots_due(now),
        manual_count=_env_int("DIOS_ORCHESTRATOR_COUNT", 0, 0, DAILY_SHORT_TARGET),
        max_per_run=_env_int("DIOS_ORCHESTRATOR_MAX_PER_RUN", 2, 1, 3),
    )
    plan["now_argentina"] = now.strftime("%Y-%m-%d %H:%M ART")
    plan["slots_argentina"] = [slot.strftime("%H:%M") for slot in SHORT_TIMES]
    return plan


def _export(plan: dict) -> None:
    PLAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLAN_FILE.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    output = os.getenv("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as fh:
            for key in ("to_publish", "confirmed_today", "slots_due", "run_target"):
                fh.write(f"{key}={plan[key]}\n")
    print(json.dumps(plan, ensure_ascii=False), flush=True)


def main(argv: list[str]) -> int:
    action = (argv[1] if len(argv) > 1 else "plan").strip().lower()
    plan = current_plan()
    _export(plan)
    if action == "plan":
        return 0
    if action != "run":
        print(f"Accion desconocida: {action}", file=sys.stderr)
        return 2
    if plan["to_publish"] <= 0:
        print("Al dia con los slots: no hay Shorts para publicar en esta ejecucion.")
        return 0
    env = dict(os.environ)
    env["DIOS_CATCHUP_TARGET"] = str(plan["run_target"])
    env["DIOS_CATCHUP_MAX_NEW"] = str(plan["to_publish"])
    print(f"Publicando {plan['to_publish']} Short(s): objetivo {plan['run_target']}/{plan['daily_target']}.", flush=True)
    return subprocess.run([sys.executable, str(CATCHUP)], cwd=ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
