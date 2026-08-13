from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

FAMILIES_FILE = Path(__file__).resolve().parents[1] / "config" / "topic_families.json"


def choose_topic_family(channel_slug: str, previous: list[dict] | None = None, salt: str = "default") -> str:
    data = json.loads(FAMILIES_FILE.read_text(encoding="utf-8"))
    families = [str(x).strip() for x in data[channel_slug] if str(x).strip()]
    previous = previous or []

    # BrotaVida has many species. Keep a much longer cooldown so a plant does
    # not come back after only a handful of uploads. Other channels retain a
    # shorter window so their formats can learn/adapt faster.
    cooldown = 24 if channel_slug == "brotavida" else 8
    recent = [str(x.get("content_family") or "").strip() for x in previous[-cooldown:]]
    recent = [x for x in recent if x]

    marker = os.getenv("GITHUB_RUN_NUMBER", "").strip()
    if marker.isdigit():
        base = int(marker)
    else:
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        base = int(hashlib.sha256(f"{now}|{salt}".encode()).hexdigest()[:10], 16)

    offset = int(hashlib.sha256(f"{channel_slug}|{salt}".encode()).hexdigest()[:8], 16)
    start = (base + offset) % len(families)

    for step in range(len(families)):
        family = families[(start + step) % len(families)]
        if family not in recent:
            return family
    return families[start]
