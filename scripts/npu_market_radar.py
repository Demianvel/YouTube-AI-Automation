from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import load_channel
from app.npu_market_radar import DEFAULT_OUT, collect_market_radar

ZONE = ZoneInfo("America/Argentina/Buenos_Aires")


def _same_local_day(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        stamp = datetime.fromisoformat(str(data.get("generated_at") or "").replace("Z", "+00:00"))
    except Exception:
        return False
    if stamp.tzinfo is None:
        return False
    return stamp.astimezone(ZONE).date() == datetime.now(ZONE).date()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="dioshablahoyia")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not args.force and _same_local_day(out):
        print("NPU market radar ya actualizado hoy en Argentina; se omite para cuidar cuota.")
        return

    previous = out.read_text(encoding="utf-8") if out.exists() else ""
    try:
        result = collect_market_radar(load_channel(args.channel))
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Market radar: niches={len(result.get('niches') or [])} "
            f"videos={result.get('videos_scanned', 0)} search_calls={result.get('search_calls_used', 0)}"
        )
        for niche in (result.get("niches") or [])[:5]:
            print(
                f"- {niche.get('niche')}: opportunity={niche.get('opportunity_score')} "
                f"demand={niche.get('demand_score')} competition={niche.get('competition_accessibility')}"
            )
    except Exception as exc:
        if previous:
            out.write_text(previous, encoding="utf-8")
        print(f"NPU_MARKET_RADAR_FAIL_OPEN: {type(exc).__name__}: {exc}")
        print("El publicador no depende del radar y debe continuar normalmente.")


if __name__ == "__main__":
    main()
