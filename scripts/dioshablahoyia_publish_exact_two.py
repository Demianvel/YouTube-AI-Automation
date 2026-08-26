from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "history.jsonl"
RECORDS = Path("/tmp/dios-two-premium/new-short-records.jsonl")
PUBLISHER = ROOT / "scripts" / "publish_dios_two_premium.py"
TZ = ZoneInfo("America/Argentina/Buenos_Aires")
TARGET_TOTAL = int(os.getenv("DIOS_MANUAL_TARGET_TOTAL", "2"))
MODELS = (
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
)


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


def _today_ids() -> set[str]:
    return {str(row.get("video_id")) for row in _today_rows() if row.get("video_id")}


def _checkpoint(initial_ids: set[str]) -> int:
    RECORDS.parent.mkdir(parents=True, exist_ok=True)
    found: list[dict] = []
    seen: set[str] = set()
    for row in _today_rows():
        video_id = str(row.get("video_id") or "").strip()
        if not video_id or video_id in initial_ids or video_id in seen:
            continue
        seen.add(video_id)
        found.append(row)
    RECORDS.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in found),
        encoding="utf-8",
    )
    print(f"Checkpoint premium: {len(found)} video_id nuevo(s).", flush=True)
    return len(found)


def main() -> int:
    if TARGET_TOTAL < 1:
        raise SystemExit("DIOS_MANUAL_TARGET_TOTAL debe ser >= 1")

    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.touch(exist_ok=True)
    initial_ids = _today_ids()
    initial_count = len(initial_ids)
    print(f"Shorts reales al iniciar: {initial_count}", flush=True)
    print(f"Objetivo manual total del dia: {TARGET_TOTAL}", flush=True)
    _checkpoint(initial_ids)

    if initial_count >= TARGET_TOTAL:
        print("El objetivo manual ya fue alcanzado; no se publican duplicados.", flush=True)
        return 0

    while len(_today_ids()) < TARGET_TOTAL:
        slot = len(_today_ids()) + 1
        before_ids = _today_ids()
        published = False

        for model in MODELS:
            env = os.environ.copy()
            env["GEMINI_TTS_MODEL"] = model
            env["GEMINI_TTS_MAX_ATTEMPTS"] = "1"
            env["SPIRITUAL_MOTION_SALT"] = f"{env.get('GITHUB_RUN_ID', 'manual')}-premium-slot-{slot}"
            env["SPIRITUAL_PREMIUM_RENDER"] = "true"
            print(
                f"=== Premium slot {slot}/{TARGET_TOTAL}: Algenib con {model} ===",
                flush=True,
            )
            result = subprocess.run(
                [sys.executable, str(PUBLISHER)],
                cwd=ROOT,
                env=env,
                check=False,
            )
            _checkpoint(initial_ids)
            after_ids = _today_ids()
            new_ids = after_ids - before_ids
            if new_ids:
                print(
                    "UPLOAD_CONFIRMADO " + ",".join(sorted(new_ids)),
                    flush=True,
                )
                published = True
                break
            print(
                f"Sin video_id nuevo con {model}; probando el siguiente modelo Algenib sin cambiar de voz.",
                flush=True,
            )
            if result.returncode == 0:
                print("El proceso termino sin error pero sin video_id; no se cuenta como publicado.", flush=True)

        if not published:
            _checkpoint(initial_ids)
            print(
                f"No se pudo publicar el slot {slot} con Algenib Flash ni Pro.",
                file=sys.stderr,
            )
            return 1

    _checkpoint(initial_ids)
    rows = _today_rows()
    print(f"TOTAL_CONFIRMADO_HOY={len(rows)}", flush=True)
    for row in rows:
        print(f"VIDEO_ID={row.get('video_id')} TITLE={row.get('title', '')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
