"""Analyst agent: learns which pillar / hook / title template / CTA variants win.

Rewards come from what already exists in the history rows passed to the
publisher (views, vph, like/comment rates added by app.performance and the
channel-analytics enrichment) plus optional state/growth/*.json snapshots.
Real CTR/impressions are not available per video in this repo, so the reward is
an engagement proxy: views-per-hour relative to the channel median, lightly
boosted by like/comment/share rates. When there is not enough data the analyst
returns None and callers fall back to plain rotation (graceful no-op).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from .pillars import classify_row

ROOT = Path(__file__).resolve().parents[2]
GROWTH_DIR = ROOT / "state" / "growth"
MIN_REWARDED_SAMPLES = 5
MIN_AGE_HOURS = 6.0


def _parse_time(value: object) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except Exception:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_growth_state() -> dict:
    """Merge optional growth snapshots; never raises."""
    merged: dict = {"keyword_weights": {}, "video_scores": {}}
    try:
        files = sorted(GROWTH_DIR.glob("*.json")) if GROWTH_DIR.exists() else []
    except Exception:
        files = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for item in data.get("keyword_weights") or []:
            if isinstance(item, dict) and item.get("key"):
                try:
                    merged["keyword_weights"][str(item["key"]).lower()] = float(item.get("mean_score") or 0.0)
                except (TypeError, ValueError):
                    pass
        for item in data.get("top_outliers") or []:
            if isinstance(item, dict) and item.get("video_id"):
                try:
                    merged["video_scores"][str(item["video_id"])] = float(item.get("growth_score") or 0.0)
                except (TypeError, ValueError):
                    pass
    return merged


def _raw_reward(row: dict, now: datetime) -> float | None:
    if not str(row.get("video_id") or "").strip():
        return None
    created = _parse_time(row.get("created_at"))
    if created and (now - created).total_seconds() / 3600.0 < MIN_AGE_HOURS:
        return None
    vph = row.get("vph")
    try:
        if vph is not None:
            return max(0.0, float(vph))
        if row.get("views") is not None and created:
            hours = max(1.0, (now - created).total_seconds() / 3600.0)
            return max(0.0, float(row["views"]) / hours)
    except (TypeError, ValueError):
        return None
    return None


def rewards(previous: list[dict], growth: dict | None = None) -> dict[str, float]:
    """video_id -> normalized reward (1.0 == channel median)."""
    now = datetime.now(timezone.utc)
    raw: dict[str, float] = {}
    rows: dict[str, dict] = {}
    for row in previous or []:
        value = _raw_reward(row, now)
        if value is None:
            continue
        vid = str(row["video_id"])
        raw[vid] = value
        rows[vid] = row
    result: dict[str, float] = {}
    if raw:
        base = median(raw.values()) or 1.0
        for vid, value in raw.items():
            row = rows[vid]
            bonus = 0.0
            for key, weight in (("like_rate", 4.0), ("comment_rate", 8.0), ("share_rate", 10.0)):
                try:
                    bonus += weight * float(row.get(key) or 0.0)
                except (TypeError, ValueError):
                    pass
            result[vid] = value / base + min(0.5, bonus)
    scores = (growth or {}).get("video_scores") or {}
    for vid, score in scores.items():
        # growth_score is 0-100; fold it in only where history has no stats.
        result.setdefault(vid, max(0.0, score) / 50.0)
    return result


def arm_stats(previous: list[dict], field: str, growth: dict | None = None) -> dict[str, tuple[int, float]]:
    reward_by_id = rewards(previous, growth)
    stats: dict[str, list[float]] = {}
    for row in previous or []:
        arm = classify_row(row) if field == "brain_pillar" else str(row.get(field) or "").strip()
        vid = str(row.get("video_id") or "").strip()
        if not arm or vid not in reward_by_id:
            continue
        stats.setdefault(arm, []).append(reward_by_id[vid])
    return {arm: (len(vals), sum(vals) / len(vals)) for arm, vals in stats.items()}


def choose_arm(
    arms: list[str],
    previous: list[dict],
    field: str,
    *,
    exclude: set[str] | None = None,
    growth: dict | None = None,
    c: float = 0.6,
) -> str | None:
    """UCB1 over recorded variants. Returns None when data is insufficient."""
    candidates = [arm for arm in arms if arm not in (exclude or set())] or list(arms)
    stats = arm_stats(previous, field, growth)
    total = sum(n for n, _ in stats.values())
    if total < MIN_REWARDED_SAMPLES:
        return None
    best, best_score = None, -1.0
    for arm in candidates:
        n, mean = stats.get(arm, (0, 0.0))
        score = 10.0 if n == 0 else mean + c * math.sqrt(math.log(max(2, total)) / n)
        if score > best_score:
            best, best_score = arm, score
    return best


def pillar_bonus(pillar_markers: tuple[str, ...], growth: dict | None) -> float:
    weights = (growth or {}).get("keyword_weights") or {}
    hits = [score for key, score in weights.items() if any(marker in key for marker in pillar_markers)]
    if not hits:
        return 0.0
    return min(1.0, (sum(hits) / len(hits)) / 100.0)


def record_fields(metadata: dict) -> dict:
    """Fields persisted with each confirmed upload so future runs can learn."""
    keys = (
        "brain_version", "brain_status", "brain_pillar", "brain_hook_id", "brain_title_template",
        "brain_cta_id", "brain_selection_mode", "brain_editor_passed", "brain_editor_reasons",
        "brain_word_count",
    )
    return {key: metadata.get(key) for key in keys if metadata.get(key) is not None}


def summarize(previous: list[dict]) -> dict:
    growth = load_growth_state()
    return {
        field: arm_stats(previous, field, growth)
        for field in ("brain_pillar", "brain_hook_id", "brain_title_template", "brain_cta_id")
    }
