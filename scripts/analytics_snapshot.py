from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.channel_analytics import analytics_digest, collect_channel_analytics
from app.config import load_channel


def main() -> None:
    parser = argparse.ArgumentParser()
    # Do not hard-code channel choices here. load_channel() is the source of
    # truth, so newly configured channels can be monitored without changing
    # this CLI again.
    parser.add_argument("--channel", required=True)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    channel = load_channel(args.channel)
    snapshot = collect_channel_analytics(channel, days=args.days)
    digest = analytics_digest(snapshot)
    print(digest)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Snapshot guardado: {out}")


if __name__ == "__main__":
    main()
