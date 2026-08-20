from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.npu_seo_cortex import build_seo_profile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROWTH = ROOT / "state" / "growth" / "dioshablahoyia_growth.json"
DEFAULT_NICHE = ROOT / "state" / "growth" / "dioshablahoyia_niche_radar.json"
DEFAULT_MARKET = ROOT / "state" / "growth" / "youtube_market_radar.json"
DEFAULT_OUT = ROOT / "state" / "growth" / "dioshablahoyia_seo_brain.json"


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--growth", default=str(DEFAULT_GROWTH))
    parser.add_argument("--niche", default=str(DEFAULT_NICHE))
    parser.add_argument("--market", default=str(DEFAULT_MARKET))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = out.read_text(encoding="utf-8") if out.exists() else ""

    try:
        growth = _read(Path(args.growth))
        if not growth:
            raise RuntimeError("No existe Growth Engine válido todavía")
        seo = build_seo_profile(
            growth,
            niche_radar=_read(Path(args.niche)),
            market_radar=_read(Path(args.market)),
        )
        out.write_text(json.dumps(seo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"SEO Cortex entrenado: confidence={seo.get('confidence')} "
            f"videos={seo.get('videos_learned')} keywords={len(seo.get('keyword_weights') or [])}"
        )
        for row in (seo.get("keyword_weights") or [])[:8]:
            print(f"- SEO {row.get('key')}: {row.get('seo_score')} ({row.get('evidence_points')} señales)")
    except Exception as exc:
        if previous:
            out.write_text(previous, encoding="utf-8")
        print(f"NPU_SEO_FAIL_OPEN: {type(exc).__name__}: {exc}")
        print("Se conserva la memoria SEO anterior; la publicación sigue siendo prioritaria.")


if __name__ == "__main__":
    main()
