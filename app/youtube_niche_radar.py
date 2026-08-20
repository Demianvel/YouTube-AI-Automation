from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build

from .channel_analytics import _credentials

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "dioshablahoyia_growth_radar.json"
DEFAULT_RADAR = ROOT / "state" / "growth" / "dioshablahoyia_niche_radar.json"

_STOPWORDS = {
    "a", "al", "ante", "como", "con", "cuando", "de", "del", "dios", "el", "en", "es", "esta",
    "fe", "hoy", "la", "las", "lo", "los", "para", "por", "que", "se", "si", "sin", "su", "te",
    "tu", "un", "una", "y", "ya", "jesus", "jesús", "video", "short", "shorts",
}


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-záéíóúüñ0-9]+", str(text or "").lower())
    return [token for token in raw if len(token) >= 3 and token not in _STOPWORDS]


def _age_hours(published_at: str) -> float:
    try:
        dt = datetime.fromisoformat(str(published_at).replace("Z", "+00:00"))
    except ValueError:
        return 24.0 * 30
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(1.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600.0)


def _chunks(values: list[str], size: int = 50) -> list[list[str]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


def _score(views: int, likes: int, comments: int, subscribers: int, age_h: float) -> dict[str, float]:
    vph = views / max(1.0, age_h)
    like_rate = likes / max(1, views)
    comment_rate = comments / max(1, views)
    audience_ratio = views / max(100.0, float(subscribers or 0))
    velocity = min(100.0, math.log1p(vph) * 12.0)
    interaction = min(100.0, like_rate * 900.0 + comment_rate * 3200.0)
    channel_outlier = min(100.0, math.log1p(audience_ratio) * 28.0)
    total = min(100.0, velocity * 0.50 + interaction * 0.30 + channel_outlier * 0.20)
    return {
        "views_per_hour": round(vph, 3),
        "like_rate": round(like_rate, 5),
        "comment_rate": round(comment_rate, 5),
        "views_to_subscribers": round(audience_ratio, 4),
        "niche_outlier_score": round(total, 2),
    }


def collect_niche_radar(channel: dict, config_path: Path = CONFIG) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    creds = _credentials(channel)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    mine = youtube.channels().list(part="id", mine=True).execute().get("items") or []
    own_channel_id = str(mine[0].get("id") or "") if mine else ""
    published_after = (datetime.now(timezone.utc) - timedelta(days=int(config.get("lookback_days") or 7))).isoformat().replace("+00:00", "Z")

    found: dict[str, dict[str, Any]] = {}
    for query in config.get("queries") or []:
        response = youtube.search().list(
            part="snippet",
            q=str(query),
            type="video",
            order="date",
            publishedAfter=published_after,
            maxResults=max(1, min(25, int(config.get("max_results_per_query") or 10))),
            regionCode=str(config.get("region_code") or "AR"),
            relevanceLanguage=str(config.get("relevance_language") or "es"),
            safeSearch="strict",
        ).execute()
        for item in response.get("items") or []:
            video_id = str((item.get("id") or {}).get("videoId") or "")
            snippet = item.get("snippet") or {}
            if not video_id or str(snippet.get("channelId") or "") == own_channel_id:
                continue
            found[video_id] = {
                "video_id": video_id,
                "query": str(query),
                "channel_id": str(snippet.get("channelId") or ""),
            }

    video_ids = list(found)
    for batch in _chunks(video_ids):
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
                "duration": str((item.get("contentDetails") or {}).get("duration") or ""),
                "views": int(stats.get("viewCount") or 0),
                "likes": int(stats.get("likeCount") or 0),
                "comments": int(stats.get("commentCount") or 0),
            })

    channel_ids = sorted({str(row.get("channel_id") or "") for row in found.values() if row.get("channel_id")})
    channel_stats: dict[str, dict[str, Any]] = {}
    for batch in _chunks(channel_ids):
        response = youtube.channels().list(part="snippet,statistics", id=",".join(batch)).execute()
        for item in response.get("items") or []:
            stats = item.get("statistics") or {}
            channel_stats[str(item.get("id") or "")] = {
                "subscribers": int(stats.get("subscriberCount") or 0),
                "channel_views": int(stats.get("viewCount") or 0),
                "video_count": int(stats.get("videoCount") or 0),
            }

    rows: list[dict[str, Any]] = []
    keyword_scores: dict[str, list[float]] = {}
    for row in found.values():
        if not row.get("title"):
            continue
        ch = channel_stats.get(str(row.get("channel_id") or ""), {})
        features = _score(
            int(row.get("views") or 0),
            int(row.get("likes") or 0),
            int(row.get("comments") or 0),
            int(ch.get("subscribers") or 0),
            _age_hours(str(row.get("published_at") or "")),
        )
        row.update(ch)
        row.update(features)
        rows.append(row)
        for token in set(_tokens(str(row.get("title") or ""))):
            keyword_scores.setdefault(token, []).append(float(features["niche_outlier_score"]))

    rows.sort(key=lambda x: (float(x.get("niche_outlier_score") or 0), float(x.get("views_per_hour") or 0)), reverse=True)
    keywords = [
        {
            "key": token,
            "samples": len(values),
            "mean_score": round(sum(values) / len(values), 2),
            "best_score": round(max(values), 2),
        }
        for token, values in keyword_scores.items()
        if values
    ]
    keywords.sort(key=lambda x: (float(x["mean_score"]), int(x["samples"])), reverse=True)

    return {
        "version": "dios-niche-radar-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "channel": str(channel.get("slug") or "dioshablahoyia"),
        "policy": dict(config.get("policy") or {}),
        "queries": list(config.get("queries") or []),
        "videos_scanned": len(rows),
        "top_niche_outliers": rows[:40],
        "keyword_weights": keywords[:40],
    }


def load_niche_radar(path: Path | str = DEFAULT_RADAR) -> dict[str, Any]:
    target = Path(path)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def candidate_niche_bonus(theme: tuple[str, str, str, str], radar: dict[str, Any] | None = None) -> tuple[float, list[str]]:
    radar = radar or load_niche_radar()
    if not radar:
        return 0.0, []
    weights = {str(x.get("key")): float(x.get("mean_score") or 0) for x in radar.get("keyword_weights") or []}
    tokens = set(_tokens(" ".join(theme)))
    hits = [weights[token] for token in tokens if token in weights]
    if not hits:
        return 0.0, []
    mean_score = sum(hits) / len(hits)
    bonus = max(-6.0, min(10.0, (mean_score - 45.0) * 0.14))
    return round(bonus, 2), [f"radar de nicho: {bonus:+.1f}"]
