from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _credentials(channel: dict) -> Credentials:
    raw = os.getenv(channel["token_env"], "").strip()
    if not raw:
        raise RuntimeError(f"Falta {channel['token_env']}")
    return Credentials.from_authorized_user_info(json.loads(raw), scopes=SCOPES)


def _rows(response: dict) -> list[dict[str, Any]]:
    headers = [item.get("name") for item in response.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in response.get("rows") or []]


def _query(analytics, *, start: str, end: str, metrics: str, dimensions: str | None = None,
           filters: str | None = None, sort: str | None = None, max_results: int | None = None) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {
        "ids": "channel==MINE",
        "startDate": start,
        "endDate": end,
        "metrics": metrics,
    }
    if dimensions:
        kwargs["dimensions"] = dimensions
    if filters:
        kwargs["filters"] = filters
    if sort:
        kwargs["sort"] = sort
    if max_results:
        kwargs["maxResults"] = max_results
    return _rows(analytics.reports().query(**kwargs).execute())


def _video_titles(youtube, ids: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i in range(0, len(ids), 50):
        batch = ids[i:i + 50]
        if not batch:
            continue
        response = youtube.videos().list(part="snippet,statistics,contentDetails", id=",".join(batch)).execute()
        for item in response.get("items", []):
            stats = item.get("statistics") or {}
            snippet = item.get("snippet") or {}
            out[item["id"]] = {
                "title": snippet.get("title", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "public_views": int(stats.get("viewCount") or 0),
                "public_likes": int(stats.get("likeCount") or 0),
                "public_comments": int(stats.get("commentCount") or 0),
                "duration": (item.get("contentDetails") or {}).get("duration", ""),
            }
    return out


def collect_channel_analytics(channel: dict, days: int = 90) -> dict[str, Any]:
    creds = _credentials(channel)
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    analytics = build("youtubeAnalytics", "v2", credentials=creds, cache_discovery=False)

    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=max(7, days) - 1)
    start, end = start_date.isoformat(), end_date.isoformat()

    channel_response = youtube.channels().list(part="id,snippet,statistics", mine=True).execute()
    channels = channel_response.get("items") or []
    if not channels:
        raise RuntimeError("YouTube no devolvio el canal autenticado.")
    ch = channels[0]
    ch_stats = ch.get("statistics") or {}

    result: dict[str, Any] = {
        "channel_id": ch.get("id"),
        "channel_title": (ch.get("snippet") or {}).get("title", ""),
        "handle": channel.get("handle"),
        "period": {"start": start, "end": end, "days": days},
        "channel_totals_public": {
            "subscribers": int(ch_stats.get("subscriberCount") or 0),
            "views": int(ch_stats.get("viewCount") or 0),
            "videos": int(ch_stats.get("videoCount") or 0),
        },
        "reports": {},
        "warnings": [],
    }

    report_specs = {
        "top_videos": dict(
            dimensions="video",
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained,subscribersLost",
            sort="-views",
            max_results=50,
        ),
        "countries": dict(
            dimensions="country",
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
            sort="-estimatedMinutesWatched",
            max_results=25,
        ),
        "demographics": dict(
            dimensions="ageGroup,gender",
            metrics="viewerPercentage",
            sort="gender,ageGroup",
        ),
        "traffic_sources": dict(
            dimensions="insightTrafficSourceType",
            metrics="views,estimatedMinutesWatched",
            sort="-views",
        ),
        "devices": dict(
            dimensions="deviceType",
            metrics="views,estimatedMinutesWatched",
            sort="-views",
        ),
        "sharing_services": dict(
            dimensions="sharingService",
            metrics="shares",
            sort="-shares",
        ),
        "content_types": dict(
            dimensions="creatorContentType",
            metrics="views,likes,comments,shares,subscribersGained,estimatedMinutesWatched",
            sort="-views",
        ),
    }

    for name, spec in report_specs.items():
        try:
            result["reports"][name] = _query(analytics, start=start, end=end, **spec)
        except Exception as exc:
            result["reports"][name] = []
            result["warnings"].append(f"{name}: {type(exc).__name__}: {exc}")

    top = result["reports"].get("top_videos") or []
    ids = [str(row.get("video") or "") for row in top if row.get("video")]
    titles = _video_titles(youtube, ids)
    for row in top:
        video_id = str(row.get("video") or "")
        row.update(titles.get(video_id, {}))
        views = max(1, int(row.get("views") or 0))
        row["like_rate"] = round(float(row.get("likes") or 0) / views, 5)
        row["comment_rate"] = round(float(row.get("comments") or 0) / views, 5)
        row["share_rate"] = round(float(row.get("shares") or 0) / views, 5)
        row["subscriber_gain_rate"] = round(float(row.get("subscribersGained") or 0) / views, 5)

    return result


def analytics_digest(snapshot: dict[str, Any], max_videos: int = 12) -> str:
    reports = snapshot.get("reports") or {}
    lines = [
        f"Periodo analizado: {snapshot.get('period', {}).get('start')} a {snapshot.get('period', {}).get('end')}.",
        f"Suscriptores publicos actuales: {snapshot.get('channel_totals_public', {}).get('subscribers', 0)}.",
    ]

    top = reports.get("top_videos") or []
    if top:
        lines.append("Videos con mejor rendimiento reciente:")
        for row in top[:max_videos]:
            lines.append(
                "- "
                + f"{row.get('title') or row.get('video')}: views={row.get('views', 0)}, "
                + f"watch_min={round(float(row.get('estimatedMinutesWatched') or 0), 1)}, "
                + f"avg_pct={round(float(row.get('averageViewPercentage') or 0), 1)}, "
                + f"likes={row.get('likes', 0)}, comments={row.get('comments', 0)}, shares={row.get('shares', 0)}, "
                + f"subs+={row.get('subscribersGained', 0)}, share_rate={row.get('share_rate', 0)}, sub_rate={row.get('subscriber_gain_rate', 0)}"
            )

    countries = reports.get("countries") or []
    if countries:
        lines.append("Principales paises por tiempo de visualizacion: " + ", ".join(str(x.get("country")) for x in countries[:8]))

    demo = reports.get("demographics") or []
    if demo:
        strongest = sorted(demo, key=lambda x: float(x.get("viewerPercentage") or 0), reverse=True)[:6]
        lines.append(
            "Demografia disponible: "
            + ", ".join(f"{x.get('ageGroup')}/{x.get('gender')}={round(float(x.get('viewerPercentage') or 0),1)}%" for x in strongest)
        )

    traffic = reports.get("traffic_sources") or []
    if traffic:
        lines.append("Fuentes de trafico principales: " + ", ".join(str(x.get("insightTrafficSourceType")) for x in traffic[:6]))

    devices = reports.get("devices") or []
    if devices:
        lines.append("Dispositivos principales: " + ", ".join(str(x.get("deviceType")) for x in devices[:5]))

    shares = reports.get("sharing_services") or []
    if shares:
        lines.append("Servicios de compartido principales: " + ", ".join(str(x.get("sharingService")) for x in shares[:5]))

    if snapshot.get("warnings"):
        lines.append("Algunos reportes no estuvieron disponibles; no inventar esos datos.")
    return "\n".join(lines)
