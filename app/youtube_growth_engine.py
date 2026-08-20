from __future__ import annotations

import json
import math
import re
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "state" / "growth" / "dioshablahoyia_growth.json"

_STOPWORDS = {
    "a", "al", "algo", "ante", "como", "con", "cuando", "de", "del", "dios", "el", "en",
    "es", "esta", "fe", "hoy", "la", "las", "lo", "los", "más", "mi", "para", "por", "que",
    "se", "si", "sin", "su", "te", "tu", "un", "una", "y", "ya", "jesus", "jesús",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-záéíóúüñ0-9]+", str(text or "").lower())
    return {token for token in raw if len(token) >= 3 and token not in _STOPWORDS}


def _median(values: Iterable[float], fallback: float = 1.0) -> float:
    clean = [float(v) for v in values if float(v) > 0]
    return statistics.median(clean) if clean else fallback


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _history_by_video(history: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in history:
        video_id = str(row.get("video_id") or row.get("video") or "").strip()
        if video_id:
            out[video_id] = row
    return out


def _public_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    reports = snapshot.get("reports") or {}
    rows = reports.get("top_videos") or reports.get("public_recent_videos") or []
    return [dict(row) for row in rows if row.get("video")]


def _age_hours(row: dict[str, Any], now: datetime) -> float:
    published = _parse_dt(str(row.get("publishedAt") or ""))
    if not published:
        return 24.0 * 30
    return max(1.0, (now - published).total_seconds() / 3600.0)


def _row_features(row: dict[str, Any], median_vph: float, now: datetime) -> dict[str, float]:
    views = max(0.0, _safe_float(row.get("views") or row.get("public_views")))
    age_h = _age_hours(row, now)
    vph = views / age_h
    outlier_ratio = vph / max(0.01, median_vph)

    engaged = _safe_float(row.get("engagedViews"))
    engaged_ratio = engaged / max(1.0, views) if engaged > 0 else 0.0
    avg_pct = _safe_float(row.get("averageViewPercentage")) / 100.0
    like_rate = _safe_float(row.get("like_rate"))
    comment_rate = _safe_float(row.get("comment_rate"))
    share_rate = _safe_float(row.get("share_rate"))
    sub_rate = _safe_float(row.get("subscriber_gain_rate"))

    # Appeal: how strongly the video earns views relative to the channel's recent baseline.
    appeal = 100.0 * (1.0 - math.exp(-max(0.0, outlier_ratio) / 1.5))
    if engaged_ratio > 0:
        appeal = 0.72 * appeal + 28.0 * _clamp(engaged_ratio * 100.0) / 100.0

    # Engagement: retention when available; otherwise public interaction proxies.
    if avg_pct > 0:
        engagement = _clamp(avg_pct * 100.0)
    else:
        engagement = _clamp((like_rate * 900.0) + (comment_rate * 3500.0))

    # Satisfaction proxy from explicit positive interactions and subscriber conversion.
    satisfaction = _clamp(
        like_rate * 850.0
        + comment_rate * 2200.0
        + share_rate * 4000.0
        + sub_rate * 6500.0
    )

    freshness = _clamp(100.0 * math.exp(-age_h / (24.0 * 21.0)))
    score = _clamp(0.35 * appeal + 0.30 * engagement + 0.25 * satisfaction + 0.10 * freshness)

    return {
        "views_per_hour": round(vph, 4),
        "outlier_ratio": round(outlier_ratio, 4),
        "appeal": round(appeal, 2),
        "engagement": round(engagement, 2),
        "satisfaction": round(satisfaction, 2),
        "freshness": round(freshness, 2),
        "growth_score": round(score, 2),
    }


def build_growth_profile(
    snapshot: dict[str, Any],
    history: list[dict[str, Any]],
    *,
    channel: str = "dioshablahoyia",
) -> dict[str, Any]:
    now = _now()
    rows = _public_rows(snapshot)
    history_map = _history_by_video(history)
    vph_values = []
    for row in rows:
        views = max(0.0, _safe_float(row.get("views") or row.get("public_views")))
        vph_values.append(views / _age_hours(row, now))
    median_vph = _median(vph_values, fallback=0.1)

    scored: list[dict[str, Any]] = []
    reference_totals: dict[str, list[float]] = defaultdict(list)
    family_totals: dict[str, list[float]] = defaultdict(list)
    keyword_totals: dict[str, list[float]] = defaultdict(list)

    for row in rows:
        video_id = str(row.get("video") or "")
        linked = history_map.get(video_id, {})
        features = _row_features(row, median_vph, now)
        reference = str(linked.get("bible_reference") or row.get("bible_reference") or "").strip()
        family = str(linked.get("content_family") or linked.get("topic") or "").strip()
        title = str(row.get("title") or linked.get("title") or "")
        topic = str(linked.get("topic") or "")
        entry = {
            "video_id": video_id,
            "title": title,
            "published_at": row.get("publishedAt") or linked.get("created_at") or "",
            "bible_reference": reference,
            "content_family": family,
            "views": int(_safe_float(row.get("views") or row.get("public_views"))),
            **features,
        }
        scored.append(entry)
        score = float(features["growth_score"])
        if reference:
            reference_totals[reference].append(score)
        if family:
            family_totals[family].append(score)
        for token in _tokens(f"{title} {topic} {family}"):
            keyword_totals[token].append(score)

    scored.sort(key=lambda x: (float(x["growth_score"]), float(x["outlier_ratio"])), reverse=True)

    def aggregate(source: dict[str, list[float]], limit: int) -> list[dict[str, Any]]:
        items = []
        for key, values in source.items():
            if not key or not values:
                continue
            items.append({
                "key": key,
                "samples": len(values),
                "mean_score": round(sum(values) / len(values), 2),
                "best_score": round(max(values), 2),
            })
        items.sort(key=lambda x: (float(x["mean_score"]), int(x["samples"]), float(x["best_score"])), reverse=True)
        return items[:limit]

    analytics_available = bool(snapshot.get("analytics_api_available", False))
    return {
        "version": "dios-growth-engine-v1",
        "generated_at": now.isoformat(),
        "channel": channel,
        "fail_open": True,
        "publishing_must_continue": True,
        "algorithm_policy": {
            "objective": "optimize for audience appeal, engagement and satisfaction without claiming guaranteed virality",
            "signals": [
                "views_per_hour_vs_recent_channel_baseline",
                "engaged_views_when_available",
                "average_view_percentage_when_available",
                "likes_comments_shares",
                "subscribers_gained_when_available",
                "recency_and_topic_novelty",
            ],
            "exploration_rate": 0.25,
            "tags_are_low_priority": True,
        },
        "data_quality": {
            "analytics_api_available": analytics_available,
            "videos_scored": len(scored),
            "median_recent_views_per_hour": round(median_vph, 4),
            "warnings": list(snapshot.get("warnings") or [])[-8:],
        },
        "top_outliers": scored[:15],
        "reference_weights": aggregate(reference_totals, 20),
        "family_weights": aggregate(family_totals, 20),
        "keyword_weights": aggregate(keyword_totals, 30),
    }


def load_growth_profile(path: Path | str = DEFAULT_PROFILE) -> dict[str, Any]:
    target = Path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def candidate_growth_score(
    *,
    family: str,
    reference: str,
    truth: str,
    practice: str,
    previous: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
    profile = profile or load_growth_profile()
    if not profile:
        return 50.0, ["sin perfil de crecimiento: selección neutral"]

    score = 50.0
    reasons: list[str] = []

    ref_map = {str(x.get("key")): float(x.get("mean_score") or 0) for x in profile.get("reference_weights") or []}
    family_rows = profile.get("family_weights") or []
    keyword_map = {str(x.get("key")): float(x.get("mean_score") or 0) for x in profile.get("keyword_weights") or []}

    if reference in ref_map:
        bonus = (ref_map[reference] - 50.0) * 0.22
        score += bonus
        reasons.append(f"referencia histórica {reference}: {bonus:+.1f}")

    candidate_tokens = _tokens(f"{family} {truth} {practice}")
    keyword_hits = [keyword_map[token] for token in candidate_tokens if token in keyword_map]
    if keyword_hits:
        mean_keyword = sum(keyword_hits) / len(keyword_hits)
        bonus = (mean_keyword - 50.0) * 0.16
        score += bonus
        reasons.append(f"afinidad temática con audiencia: {bonus:+.1f}")

    family_tokens = _tokens(family)
    best_family = 0.0
    for row in family_rows:
        known = _tokens(str(row.get("key") or ""))
        union = family_tokens | known
        if not union:
            continue
        similarity = len(family_tokens & known) / len(union)
        best_family = max(best_family, similarity * float(row.get("mean_score") or 0))
    if best_family > 0:
        bonus = (best_family - 25.0) * 0.08
        score += bonus
        reasons.append(f"familia relacionada con ganadores: {bonus:+.1f}")

    recent = [row for row in previous if row.get("status") == "uploaded"][-20:]
    same_ref = sum(1 for row in recent if str(row.get("bible_reference") or "") == reference)
    similar_family = sum(
        1 for row in recent
        if len(_tokens(str(row.get("content_family") or row.get("topic") or "")) & family_tokens) >= 2
    )
    repetition_penalty = min(18.0, same_ref * 5.0 + similar_family * 2.0)
    if repetition_penalty:
        score -= repetition_penalty
        reasons.append(f"penalización por repetición reciente: -{repetition_penalty:.1f}")
    else:
        score += 5.0
        reasons.append("novedad reciente: +5.0")

    return round(_clamp(score), 2), reasons[:5]


def ranked_theme_indices(
    themes: list[tuple[str, str, str, str]] | tuple[tuple[str, str, str, str], ...],
    previous: list[dict[str, Any]],
    seed: int,
    *,
    profile: dict[str, Any] | None = None,
) -> list[tuple[int, float, list[str]]]:
    profile = profile or load_growth_profile()
    ranked = []
    for index, theme in enumerate(themes):
        family, reference, truth, practice = theme
        score, reasons = candidate_growth_score(
            family=family,
            reference=reference,
            truth=truth,
            practice=practice,
            previous=previous,
            profile=profile,
        )
        # Deterministic tiny tie-breaker; never materially changes the learned score.
        tie = ((seed ^ (index * 2654435761)) & 0xFFFF) / 65535.0
        ranked.append((index, score + tie * 0.01, reasons))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked
