from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
channels = json.loads((ROOT / "config" / "channels.json").read_text(encoding="utf-8"))

parser = argparse.ArgumentParser()
parser.add_argument(
    "--generation-only",
    action="store_true",
    help="Require only the credentials needed to generate content, not to upload it.",
)
args = parser.parse_args()

channel = os.environ.get("CHANNEL", "")
if channel not in channels:
    print(f"ready=false: canal invalido {channel}")
    sys.exit(2)

required: list[str] = []
# Dios Habla Hoy has a local Bible-based script fallback and persistent
# photoreal reference assets, so text generation can proceed without Gemini.
if channel != "dioshablahoyia":
    required.append("GEMINI_API_KEY")

if not args.generation_only:
    required.append(channels[channel]["token_env"])

missing = [name for name in required if not os.getenv(name)]
if missing:
    print("ready=false")
    print("missing=" + ",".join(missing))
    sys.exit(3)

print("ready=true")
