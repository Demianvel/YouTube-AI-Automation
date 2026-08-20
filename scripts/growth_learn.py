from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.channel_analytics import collect_channel_analytics
from app.config import load_channel
from app.youtube_growth_engine import build_growth_profile

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "state" / "history.jsonl"


def _history(channel: str) -> list[dict]:
    rows: list[dict] = []
    if not HISTORY.exists():
        return rows
    for raw in HISTORY.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") == channel:
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="dioshablahoyia")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    out = Path(args.out) if args.out else ROOT / "state" / "growth" / f"{args.channel}_growth.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    previous_profile = ""
    if out.exists():
        previous_profile = out.read_text(encoding="utf-8")

    try:
        channel = load_channel(args.channel)
        snapshot = collect_channel_analytics(channel, days=max(14, args.days))
        profile = build_growth_profile(snapshot, _history(args.channel), channel=args.channel)
        out.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Growth profile actualizado: videos={profile.get('data_quality', {}).get('videos_scored', 0)}, "
            f"analytics={profile.get('data_quality', {}).get('analytics_api_available', False)}, "
            f"outliers={len(profile.get('top_outliers') or [])}"
        )
        for row in (profile.get("top_outliers") or [])[:5]:
            print(
                f"- score={row.get('growth_score')} outlier={row.get('outlier_ratio')} "
                f"ref={row.get('bible_reference') or '-'} title={row.get('title') or row.get('video_id')}"
            )
    except Exception as exc:
        # Growth learning must never stop publishing. Preserve the last known-good
        # profile and return success so the publishing workflows remain independent.
        if previous_profile:
            out.write_text(previous_profile, encoding="utf-8")
        print(f"GROWTH_ENGINE_FAIL_OPEN: {type(exc).__name__}: {exc}")
        print("Se preserva el perfil anterior y la publicación debe continuar sin cambios.")


if __name__ == "__main__":
    main()
