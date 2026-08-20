from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.npu_internal_cortex import DEFAULT_HISTORY, DEFAULT_STATE, build_internal_profile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROWTH = ROOT / "state" / "growth" / "dioshablahoyia_growth.json"
DEFAULT_SEO = ROOT / "state" / "growth" / "dioshablahoyia_seo_brain.json"


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _read_history(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict) and str(row.get("channel") or "") == "dioshablahoyia":
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--growth", default=str(DEFAULT_GROWTH))
    parser.add_argument("--seo", default=str(DEFAULT_SEO))
    parser.add_argument("--out", default=str(DEFAULT_STATE))
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = _read_json(out)
    history = _read_history(Path(args.history))
    growth = _read_json(Path(args.growth))
    seo = _read_json(Path(args.seo))

    profile = build_internal_profile(history, growth, seo, previous)
    if previous and not profile.get("changed_since_previous"):
        print(
            "INTERNAL_NPU_NO_NEW_DATA: ciclo ejecutado sin llamadas externas; "
            f"generation={previous.get('training_generation', 0)}"
        )
        return

    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    memory = profile.get("memory") or {}
    print(
        "INTERNAL_NPU_TRAINED: zero external calls; "
        f"generation={profile.get('training_generation')} "
        f"uploads={memory.get('uploaded_samples')} refs={memory.get('unique_references')} "
        f"families={memory.get('unique_families')}"
    )


if __name__ == "__main__":
    main()
