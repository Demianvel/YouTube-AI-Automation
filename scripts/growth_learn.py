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


def _blend_niche_radar(profile: dict, channel: str) -> dict:
    radar_path = ROOT / "state" / "growth" / f"{channel}_niche_radar.json"
    if not radar_path.exists():
        profile["niche_radar"] = {"available": False}
        return profile
    try:
        radar = json.loads(radar_path.read_text(encoding="utf-8"))
    except Exception:
        profile["niche_radar"] = {"available": False, "warning": "radar JSON invalido"}
        return profile

    own_rows = {str(row.get("key")): dict(row) for row in profile.get("keyword_weights") or [] if row.get("key")}
    for external in radar.get("keyword_weights") or []:
        key = str(external.get("key") or "").strip()
        if not key:
            continue
        ext_score = float(external.get("mean_score") or 50.0)
        if key in own_rows:
            # Own-channel evidence has 80% weight. External niche signal can
            # nudge but never dominate what the user's audience actually does.
            own_score = float(own_rows[key].get("mean_score") or 50.0)
            own_rows[key]["mean_score"] = round(0.80 * own_score + 0.20 * ext_score, 2)
            own_rows[key]["niche_supported"] = True
        else:
            # External-only terms are deliberately shrunk toward neutral.
            own_rows[key] = {
                "key": key,
                "samples": 0,
                "mean_score": round(50.0 + (ext_score - 50.0) * 0.20, 2),
                "best_score": round(ext_score, 2),
                "niche_only": True,
            }

    merged = list(own_rows.values())
    merged.sort(key=lambda row: (float(row.get("mean_score") or 0), int(row.get("samples") or 0)), reverse=True)
    profile["keyword_weights"] = merged[:40]
    profile["niche_radar"] = {
        "available": True,
        "version": radar.get("version"),
        "generated_at": radar.get("generated_at"),
        "videos_scanned": radar.get("videos_scanned", 0),
        "queries": radar.get("queries") or [],
        "top_outliers": (radar.get("top_niche_outliers") or [])[:10],
        "policy": radar.get("policy") or {},
        "weight_in_decisions": 0.20,
    }
    return profile


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
        profile = _blend_niche_radar(profile, args.channel)
        out.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Growth profile actualizado: videos={profile.get('data_quality', {}).get('videos_scored', 0)}, "
            f"analytics={profile.get('data_quality', {}).get('analytics_api_available', False)}, "
            f"outliers={len(profile.get('top_outliers') or [])}, "
            f"niche_radar={profile.get('niche_radar', {}).get('available', False)}"
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
