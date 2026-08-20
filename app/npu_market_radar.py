from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build

from .channel_analytics import _credentials

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "npu_market_radar.json"
DEFAULT_OUT = ROOT / "state" / "growth" / "youtube_market_radar.json"


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _age_hours(value: str) -> float:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 24.0 * 30
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(1.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600.0)


def _chunks(values: list[str], size: int = 50) -> list[list[str]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


def _median(values: list[float], fallback: float = 1.0) -> float:
    clean = sorted(float(v) for v in values if float(v) >= 0)
    if not clean:
        return fallback
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2.0


def _score_video(row: dict[str, Any], subscribers: int, median_vph: float) -> dict[str, float]:
    views = max(0.0, _safe_float(row.get("views")))
    likes = max(0.0, _safe_float(row.get("likes")))
    comments = max(0.0, _safe_float(row.get("comments")))
    age_h = _age_hours(str(row.get("published_at") or ""))
    vph = views / age_h
    velocity_ratio = vph / max(0.1, median_vph)
    audience_ratio = views / max(100.0, float(subscribers or 0))
    like_rate = likes / max(1.0, views)
    comment_rate = comments / max(1.0, views)

    velocity_score = min(100.0, 100.0 * (1.0 - math.exp(-velocity_ratio / 1.8)))
    creator_outlier = min(100.0, math.log1p(max(0.0, audience_ratio)) * 32.0)
    interaction = min(100.0, like_rate * 900.0 + comment_rate * 3200.0)
    freshness = min(100.0, 100.0 * math.exp(-age_h / (24.0 * 10.0)))
    demand_score = min(100.0, 0.48 * velocity_score + 0.22 * creator_outlier + 0.20 * interaction + 0.10 * freshness)

    return {
        "views_per_hour": round(vph, 3),
        "velocity_ratio": round(velocity_ratio, 3),
        "views_to_subscribers": round(audience_ratio, 4),
        "like_rate": round(like_rate, 5),
        "comment_rate": round(comment_rate, 5),
        "demand_score": round(demand_score, 2),
    }


def collect_market_radar(channel: dict, config_path: Path = CONFIG) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    creds = _credentials(channel)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    now = datetime.now(timezone.utc)
    year = now.year
    published_after = (now - timedelta(days=int(config.get("lookback_days") or 7))).isoformat().replace("+00:00", "Z")
    max_calls = max(1, min(12, int((config.get("policy") or {}).get("max_daily_search_calls") or 12)))
    query_rows = list(config.get("queries") or [])[:max_calls]

    found: dict[str, dict[str, Any]] = {}
    calls = 0
    for item in query_rows:
        niche = str(item.get("niche") or "general")
        base_query = str(item.get("query") or "").strip()
        if not base_query:
            continue
        # Current year is added at runtime so the radar ages naturally instead of
        # hard-coding 2026 forever.
        query = f"{base_query} {year}"
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="date",
            publishedAfter=published_after,
            maxResults=max(1, min(20, int(config.get("max_results_per_query") or 12))),
            regionCode=str(config.get("region_code") or "AR"),
            relevanceLanguage=str(config.get("relevance_language") or "es"),
            safeSearch="strict",
        ).execute()
        calls += 1
        for result in response.get("items") or []:
            video_id = str((result.get("id") or {}).get("videoId") or "")
            snippet = result.get("snippet") or {}
            if not video_id:
                continue
            found.setdefault(video_id, {
                "video_id": video_id,
                "niches": [],
                "queries": [],
                "channel_id": str(snippet.get("channelId") or ""),
            })
            found[video_id]["niches"].append(niche)
            found[video_id]["queries"].append(query)

    for batch in _chunks(list(found)):
        response = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(batch)).execute()
        for item in response.get("items") or []:
            video_id = str(item.get("id") or "")
            if video_id not in found:
                continue
            snippet = item.get("snippet") or {}
            stats = item.get("statistics") or {}
            found[video_id].update({
                "title": str(snippet.get("title") or ""),
                "channel_id": str(snippet.get("channelId") or found[video_id].get("channel_id") or ""),
                "channel_title": str(snippet.get("channelTitle") or ""),
                "published_at": str(snippet.get("publishedAt") or ""),
                "views": int(stats.get("viewCount") or 0),
                "likes": int(stats.get("likeCount") or 0),
                "comments": int(stats.get("commentCount") or 0),
                "duration": str((item.get("contentDetails") or {}).get("duration") or ""),
            })

    channel_ids = sorted({str(row.get("channel_id") or "") for row in found.values() if row.get("channel_id")})
    channel_stats: dict[str, dict[str, int]] = {}
    for batch in _chunks(channel_ids):
        response = youtube.channels().list(part="statistics", id=",".join(batch)).execute()
        for item in response.get("items") or []:
            stats = item.get("statistics") or {}
            channel_stats[str(item.get("id") or "")] = {
                "subscribers": int(stats.get("subscriberCount") or 0),
                "channel_views": int(stats.get("viewCount") or 0),
                "video_count": int(stats.get("videoCount") or 0),
            }

    all_vph = [
        max(0.0, _safe_float(row.get("views"))) / _age_hours(str(row.get("published_at") or ""))
        for row in found.values() if row.get("title")
    ]
    median_vph = _median(all_vph, 0.1)

    config_by_niche = {str(row.get("niche") or ""): row for row in query_rows}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_rows: list[dict[str, Any]] = []
    for row in found.values():
        if not row.get("title"):
            continue
        ch = channel_stats.get(str(row.get("channel_id") or ""), {})
        features = _score_video(row, int(ch.get("subscribers") or 0), median_vph)
        enriched = dict(row)
        enriched.update(ch)
        enriched.update(features)
        all_rows.append(enriched)
        for niche in set(row.get("niches") or []):
            grouped[str(niche)].append(enriched)

    niche_results: list[dict[str, Any]] = []
    for niche, rows in grouped.items():
        demand = _mean([_safe_float(row.get("demand_score")) for row in rows], 0.0)
        top_demand = max([_safe_float(row.get("demand_score")) for row in rows] or [0.0])
        median_subs = _median([_safe_float(row.get("subscribers")) for row in rows], 0.0)
        # Lower median creator size for a given demand can indicate more accessible
        # competition. This is only an opportunity proxy, not a guarantee.
        competition_access = max(0.0, min(100.0, 100.0 - math.log10(max(10.0, median_subs)) * 18.0))
        prior = _safe_float((config_by_niche.get(niche) or {}).get("commercial_intent_prior"), 0.5)
        commercial_proxy = max(0.0, min(100.0, prior * 100.0))
        opportunity = max(0.0, min(100.0,
            0.48 * demand
            + 0.18 * top_demand
            + 0.16 * competition_access
            + 0.18 * commercial_proxy
        ))
        best = sorted(rows, key=lambda x: _safe_float(x.get("demand_score")), reverse=True)[:8]
        keywords: list[str] = []
        for best_row in best:
            for token in str(best_row.get("title") or "").lower().replace("|", " ").split():
                token = "".join(ch for ch in token if ch.isalnum() or ch in "áéíóúüñ")
                if len(token) >= 4 and token not in keywords:
                    keywords.append(token)
        niche_results.append({
            "niche": niche,
            "query": str((config_by_niche.get(niche) or {}).get("query") or ""),
            "videos_scanned": len(rows),
            "demand_score": round(demand, 2),
            "peak_demand_score": round(top_demand, 2),
            "competition_accessibility": round(competition_access, 2),
            "commercial_intent_proxy": round(commercial_proxy, 2),
            "opportunity_score": round(opportunity, 2),
            "keywords": keywords[:16],
            "top_videos": best,
        })

    niche_results.sort(key=lambda row: _safe_float(row.get("opportunity_score")), reverse=True)
    all_rows.sort(key=lambda row: _safe_float(row.get("demand_score")), reverse=True)
    return {
        "version": "youtube-market-radar-v1",
        "generated_at": now.isoformat(),
        "year_context": year,
        "region_code": config.get("region_code") or "AR",
        "relevance_language": config.get("relevance_language") or "es",
        "search_calls_used": calls,
        "videos_scanned": len(all_rows),
        "median_market_views_per_hour": round(median_vph, 3),
        "policy": dict(config.get("policy") or {}),
        "niches": niche_results,
        "top_market_videos": all_rows[:30],
        "disclaimer": "Opportunity/commercial scores are heuristic proxies, not actual RPM, revenue or guaranteed virality.",
    }


def _mean(values: list[float], fallback: float = 0.0) -> float:
    return sum(values) / len(values) if values else fallback
