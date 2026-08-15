from __future__ import annotations

import json
import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.spiritual_playlist import (
    PLAYLIST_DESCRIPTION,
    PLAYLIST_TITLE,
    add_video_to_spiritual_playlist,
    ensure_spiritual_playlist,
)


TOKEN_ENV = "YOUTUBE_TOKEN_DIOSHABLAHOYIA"
WRITE_SCOPES = {
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
}
MAX_ADDS_PER_RUN = max(1, min(150, int(os.getenv("PLAYLIST_SYNC_MAX_ADDS", "120"))))


def _youtube():
    raw = os.getenv(TOKEN_ENV, "").strip()
    if not raw:
        raise RuntimeError(f"Falta el secret {TOKEN_ENV}.")
    info = json.loads(raw)
    scopes = set(info.get("scopes") or [])
    if scopes and not (scopes & WRITE_SCOPES):
        raise RuntimeError(
            "El token OAuth necesita youtube.force-ssl o youtube para crear y administrar playlists."
        )
    credentials = Credentials.from_authorized_user_info(info, scopes=list(scopes) or None)
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def _channel_uploads_playlist(youtube) -> tuple[str, str]:
    response = youtube.channels().list(part="id,contentDetails,snippet", mine=True).execute()
    items = response.get("items") or []
    if not items:
        raise RuntimeError("No se pudo identificar el canal autenticado.")
    item = items[0]
    channel_id = str(item.get("id") or "")
    uploads = str(
        ((item.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads") or ""
    )
    if not channel_id or not uploads:
        raise RuntimeError("YouTube no devolvió la playlist de subidas del canal.")
    return channel_id, uploads


def _playlist_page(youtube, playlist_id: str, page_token: str | None):
    last_error: Exception | None = None
    for attempt in range(1, 7):
        try:
            return youtube.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=page_token,
            ).execute()
        except HttpError as exc:
            last_error = exc
            status = int(getattr(exc.resp, "status", 0) or 0)
            body = str(exc)
            if status == 404 and "playlistNotFound" in body and attempt < 6:
                time.sleep(attempt * 2)
                continue
            raise
    raise RuntimeError(f"La playlist no quedó disponible después de varios reintentos: {last_error}")


def _video_ids_from_playlist(youtube, playlist_id: str):
    page_token = None
    while True:
        response = _playlist_page(youtube, playlist_id, page_token)
        for item in response.get("items") or []:
            video_id = str((item.get("contentDetails") or {}).get("videoId") or "")
            if video_id:
                yield video_id
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def _existing_destination_ids(youtube, playlist_id: str) -> set[str]:
    return set(_video_ids_from_playlist(youtube, playlist_id))


def run() -> dict:
    youtube = _youtube()
    channel_id, uploads_playlist_id = _channel_uploads_playlist(youtube)
    destination_id = ensure_spiritual_playlist(youtube)
    existing = _existing_destination_ids(youtube, destination_id)

    scanned = 0
    added = 0
    already_present = 0
    stopped_at_quota_guard = False

    for video_id in _video_ids_from_playlist(youtube, uploads_playlist_id):
        scanned += 1
        if video_id in existing:
            already_present += 1
            continue
        if added >= MAX_ADDS_PER_RUN:
            stopped_at_quota_guard = True
            break
        playlist_id, status = add_video_to_spiritual_playlist(youtube, video_id)
        if playlist_id != destination_id:
            raise RuntimeError("La playlist destino cambió durante la sincronización.")
        if status == "added":
            added += 1
            existing.add(video_id)
        else:
            already_present += 1

    result = {
        "channel_id": channel_id,
        "playlist_id": destination_id,
        "playlist_title": PLAYLIST_TITLE,
        "playlist_description": PLAYLIST_DESCRIPTION,
        "uploads_playlist_id": uploads_playlist_id,
        "scanned": scanned,
        "added": added,
        "already_present": already_present,
        "max_adds_per_run": MAX_ADDS_PER_RUN,
        "stopped_at_quota_guard": stopped_at_quota_guard,
        "includes_shorts_and_long_videos": True,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
