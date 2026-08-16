from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "dioshablahoyia_visual_engine.json"
MARKET = ROOT / "state" / "dioshablahoyia_market_signals.json"
OUTPUT = ROOT / "state" / "dioshablahoyia_visual_plan.json"


def _load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def build_plan() -> dict:
    config = _load(CONFIG)
    signals = _load(MARKET)
    families = list((config.get("families") or {}).keys())
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signal_text = json.dumps(signals.get("top_terms") or [], ensure_ascii=False, sort_keys=True)
    seed = int(hashlib.sha256(f"{day}|{signal_text}".encode("utf-8")).hexdigest()[:12], 16)

    scored = []
    for index, family in enumerate(families):
        row = (config.get("families") or {}).get(family) or {}
        weight = max(1, int(row.get("weight", 1)))
        score = (seed // (index + 3)) % 1000 + weight * 100
        scored.append((score, family))
    scored.sort(reverse=True)
    order = [family for _, family in scored]

    # Creation is always present; Norway appears every day but changes its exact scene.
    for required in ("creation_and_nature", "norway"):
        if required in order:
            order.remove(required)
        order.insert(0 if required == "norway" else 1, required)

    weekday = datetime.now(timezone.utc).weekday()
    featured_story = "Noah's Ark" if weekday in {1, 4} else "rotating biblical story"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": day,
        "family_order": order,
        "featured_location": "Norway",
        "featured_norway_regions": ["Lofoten", "Geirangerfjord", "Tromso", "Senja"],
        "featured_biblical_story": featured_story,
        "policy": "daily deterministic rotation informed by aggregate channel signals; no autonomous model retraining",
        "models": config.get("image_models") or [],
        "optional_video_models": config.get("optional_video_models") or [],
    }


def main() -> None:
    plan = build_plan()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False))


if __name__ == "__main__":
    main()
