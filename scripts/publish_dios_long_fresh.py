from __future__ import annotations

import argparse
import json

from app import spiritual_long_pipeline as base
from app.spiritual_long_fresh_visual import download_fresh_long_visual
from app.spiritual_long_resilient_runner import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[10, 15, 20, 30])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    original_download = base._download_image
    base._download_image = download_fresh_long_visual
    try:
        result = run(args.minutes, publish=args.publish)
    finally:
        base._download_image = original_download
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
