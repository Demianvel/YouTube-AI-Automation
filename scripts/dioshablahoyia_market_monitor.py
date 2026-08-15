from __future__ import annotations

import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


TOKEN_ENV = "YOUTUBE_TOKEN_DIOSHABLAHOYIA"
STATE_PATH = Path("state/dioshablahoyia_market_signals.json")
QUERIES = (
    "Dios oración",
    "Biblia reflexión",
    "Jesús fe",
    "Salmo 91",
    "oración para dormir",
)
TRACKED_TERMS = (
    "dios",
    "jesús",
    "jesucristo",
    "biblia",
    "oración",
    "salmo 91",
    "salmos",
    "fe",
    "esperanza",
    "paz",
    "ansiedad",
    "noche",
    "dormir",
    "mañana",
    "protección",
    "amor",
)


def _youtube():
    raw = os.getenv(TOKEN_ENV, "").strip()
    if not raw:
        raise RuntimeError(f"Falta {TOKEN_ENV}")
    info = json.loads(raw)
    scopes = info.get("scopes") or None
    credentials = Credentials.from_authorized_user_info(info, scopes=scopes)
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def _hours_since(when: str, now: datetime) -> float:
    published = datetime.fromisoformat(when.replace("Z", "+00:00"))
    return max(1.0, (now - published).total_seconds() / 3600.0)


def _normalize(text: str) -> str:
    text = text.lower().replace("jesus", "jesús").replace("oracion", "oración").replace("proteccion", "protección")
    return " ".join(re.sub(r"[^a-záéíóúñ0-9 ]+", " ", text).split())


def run() -> dict:
    youtube = _youtube()
    now = datetime.now(timezone.utc)
    published_after = (now - timedelta(days=3)).isoformat().replace("+00:00", "Z")

    mine = youtube.channels().list(part="id", mine=True).execute().get("items") or []
    own_channel_id = str(mine[0].get("id") or "") if mine else ""

    discovered: dict[str, dict] = {}
    for query in QUERIES:
        response = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=8,
            order="date",
            publishedAfter=published_after,
            regionCode="AR",
            relevanceLanguage="es",
            safeSearch="strict",
        ).execute()
        for item in response.get("items") or []:
            video_id = str((item.get("id") or {}).get("videoId") or "")
            snippet = item.get("snippet") or {}
            if not video_id or str(snippet.get("channelId") or "") == own_channel_id:
                continue
            discovered.setdefault(video_id, {
                "title": str(snippet.get("title") or ""),
                "publishedAt": str(snippet.get("publishedAt") or ""),
            })

    ids = list(discovered)
    for start in range(0, len(ids), 50):
        batch = ids[start:start + 50]
        response = youtube.videos().list(part="statistics", id=",".join(batch)).execute()
        for item in response.get("items") or []:
            video_id = str(item.get("id") or "")
            if video_id in discovered:
                stats = item.get("statistics") or {}
                discovered[video_id]["views"] = int(stats.get("viewCount") or 0)
                discovered[video_id]["likes"] = int(stats.get("likeCount") or 0)
                discovered[video_id]["comments"] = int(stats.get("commentCount") or 0)

    term_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"samples": 0.0, "weighted_vph": 0.0, "weighted_engagement": 0.0})
    analyzed = 0
    for row in discovered.values():
        if not row.get("publishedAt"):
            continue
        views = int(row.get("views") or 0)
        if views <= 0:
            continue
        hours = _hours_since(row["publishedAt"], now)
        vph = views / hours
        engagement = (int(row.get("likes") or 0) + int(row.get("comments") or 0)) / max(1, views)
        title = _normalize(row.get("title") or "")
        analyzed += 1
        for term in TRACKED_TERMS:
            if _normalize(term) in title:
                stat = term_stats[term]
                stat["samples"] += 1
                stat["weighted_vph"] += math.log1p(vph)
                stat["weighted_engagement"] += engagement

    ranked = []
    for term, stat in term_stats.items():
        samples = max(1.0, stat["samples"])
        ranked.append({
            "term": term,
            "samples": int(stat["samples"]),
            "signal_score": round((stat["weighted_vph"] / samples) * (1.0 + stat["weighted_engagement"] / samples), 4),
        })
    ranked.sort(key=lambda row: (row["signal_score"], row["samples"]), reverse=True)

    result = {
        "generated_at": now.isoformat(),
        "window_hours": 72,
        "region": "AR",
        "language": "es",
        "queries": list(QUERIES),
        "videos_analyzed": analyzed,
        "top_terms": ranked[:10],
        "method": "public_youtube_recent_video_vph_and_engagement_aggregate",
        "copy_policy": "aggregate_patterns_only_no_titles_scripts_thumbnails_or_channel_copying",
        "purpose": "inform_original_packaging_not_guarantee_virality",
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
