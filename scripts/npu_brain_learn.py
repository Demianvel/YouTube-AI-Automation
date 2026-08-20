from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.alien_npu_brain import DEFAULT_BRAIN, build_brain_state

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROWTH = ROOT / "state" / "growth" / "dioshablahoyia_growth.json"
DEFAULT_NICHE = ROOT / "state" / "growth" / "dioshablahoyia_niche_radar.json"
DEFAULT_MARKET = ROOT / "state" / "growth" / "youtube_market_radar.json"


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
    parser.add_argument("--out", default=str(DEFAULT_BRAIN))
    args = parser.parse_args()

    growth = _read(Path(args.growth))
    niche = _read(Path(args.niche))
    market = _read(Path(args.market))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    previous = out.read_text(encoding="utf-8") if out.exists() else ""

    try:
        if not growth:
            raise RuntimeError("No existe perfil Growth Engine válido todavía")
        brain = build_brain_state(growth, niche_radar=niche, market_radar=market)
        out.write_text(json.dumps(brain, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Alien NPU aprendido: confidence={brain.get('brain_confidence')} "
            f"videos={brain.get('data_quality', {}).get('videos_scored')} "
            f"market={brain.get('data_quality', {}).get('market_radar_available')}"
        )
        for niche_row in (brain.get("memory", {}).get("market_niches") or [])[:5]:
            print(
                f"- mercado {niche_row.get('niche')}: opportunity={niche_row.get('opportunity_score')}"
            )
    except Exception as exc:
        if previous:
            out.write_text(previous, encoding="utf-8")
        print(f"ALIEN_NPU_FAIL_OPEN: {type(exc).__name__}: {exc}")
        print("Se preserva la memoria anterior; publicar contenido sigue siendo prioritario.")


if __name__ == "__main__":
    main()
