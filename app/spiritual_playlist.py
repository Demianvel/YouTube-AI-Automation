from __future__ import annotations

import os


PLAYLIST_TITLE = os.getenv(
    "DIOS_PLAYLIST_TITLE",
    "Dios Habla Hoy | Jesús, Fe, Esperanza y Biblia",
).strip()
PLAYLIST_DESCRIPTION = os.getenv(
    "DIOS_PLAYLIST_DESCRIPTION",
    (
        "Videos y Shorts cristianos de Dios Habla Hoy IA sobre Jesús, Dios, Biblia, oración, fe, "
        "esperanza, paz y amor. Reflexiones y mensajes inspirados en pasajes bíblicos para acompañar "
        "cada día con serenidad, esperanza y confianza en Dios."
    ),
).strip()
PLAYLIST_PRIVACY = os.getenv("DIOS_PLAYLIST_PRIVACY", "public").strip() or "public"


def _mine_playlists(youtube):
    page_token = None
    while True:
        response = youtube.playlists().list(
            part="id,snippet,status",
            mine=True,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in response.get("items") or []:
            yield item
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def ensure_spiritual_playlist(youtube) -> str:
    """Return the canonical Christian playlist id, creating it when missing."""
    for item in _mine_playlists(youtube):
        title = str((item.get("snippet") or {}).get("title") or "").strip()
        if title.casefold() == PLAYLIST_TITLE.casefold():
            return str(item["id"])

    created = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": PLAYLIST_TITLE,
                "description": PLAYLIST_DESCRIPTION,
                "defaultLanguage": "es-419",
            },
            "status": {"privacyStatus": PLAYLIST_PRIVACY},
        },
    ).execute()
    playlist_id = str(created.get("id") or "")
    if not playlist_id:
        raise RuntimeError("YouTube no devolvió un ID al crear la playlist cristiana.")
    return playlist_id


def playlist_contains_video(youtube, playlist_id: str, video_id: str) -> bool:
    response = youtube.playlistItems().list(
        part="id",
        playlistId=playlist_id,
        videoId=video_id,
        maxResults=1,
    ).execute()
    return bool(response.get("items"))


def add_video_to_spiritual_playlist(youtube, video_id: str) -> tuple[str, str]:
    """Idempotently add one uploaded video/Short to the canonical playlist."""
    playlist_id = ensure_spiritual_playlist(youtube)
    if playlist_contains_video(youtube, playlist_id, video_id):
        return playlist_id, "already_present"

    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        },
    ).execute()
    return playlist_id, "added"
