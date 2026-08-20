from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import load_channel
from app.youtube_niche_radar import collect_niche_radar

ROOT = Path(__file__).resolve().parents[1]
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
    parser.add_argument("--out", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out = Path(args.out) if args.out else ROOT / "state" / "growth" / f"{args.channel}_niche_radar.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not args.force and _same_local_day(out):
        print("Niche radar ya actualizado hoy en Argentina; se omite para cuidar cuota de YouTube Data API.")
        return

    previous = out.read_text(encoding="utf-8") if out.exists() else ""
    try:
        radar = collect_niche_radar(load_channel(args.channel))
        out.write_text(json.dumps(radar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Niche radar actualizado: {radar.get('videos_scanned', 0)} videos analizados")
        for row in (radar.get("top_niche_outliers") or [])[:5]:
            print(
                f"- score={row.get('niche_outlier_score')} vph={row.get('views_per_hour')} "
                f"canal={row.get('channel_title')} titulo={row.get('title')}"
            )
    except Exception as exc:
        if previous:
            out.write_text(previous, encoding="utf-8")
        print(f"NICHE_RADAR_FAIL_OPEN: {type(exc).__name__}: {exc}")
        print("La publicación no depende de este radar y debe continuar normalmente.")


if __name__ == "__main__":
    main()
