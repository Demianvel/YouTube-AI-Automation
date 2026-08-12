from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
RETRIABLE = {500, 502, 503, 504}


def _credentials(token_json: str) -> Credentials:
    info = json.loads(token_json)
    return Credentials.from_authorized_user_info(info, scopes=YOUTUBE_SCOPES)


def _verify_channel(youtube, channel: dict) -> None:
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise RuntimeError("No se pudo identificar el canal autorizado antes de publicar.")

    snippet = items[0].get("snippet", {})
    actual = (snippet.get("customUrl") or "").lower().lstrip("/")
    expected = channel["handle"].lower().lstrip("/")
    if actual != expected:
        title = snippet.get("title", "canal desconocido")
        raise RuntimeError(
            f"Token asociado al canal incorrecto: se esperaba {channel['handle']} y Google devolvió {actual or title}."
        )


def upload_video(channel: dict, metadata: dict, video_path: Path) -> str:
    token_json = os.getenv(channel["token_env"])
    if not token_json:
        raise RuntimeError(f"Falta el secret {channel['token_env']}")

    youtube = build("youtube", "v3", credentials=_credentials(token_json), cache_discovery=False)
    _verify_channel(youtube, channel)

    hashtags = " ".join(metadata.get("hashtags", [])[:5])
    description = (metadata.get("description", "").strip() + "\n\n" + hashtags).strip()
    body = {
        "snippet": {
            "title": metadata["title"],
            "description": description,
            "tags": metadata.get("tags", [])[:15],
            "categoryId": channel["category_id"],
            "defaultLanguage": channel.get("language", "es-419"),
        },
        "status": {
            "privacyStatus": channel.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": bool(channel.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(channel.get("contains_synthetic_media", True)),
        },
    }
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True),
    )

    response = None
    retries = 0
    while response is None:
        try:
            _, response = request.next_chunk()
        except HttpError as exc:
            if exc.resp.status not in RETRIABLE or retries >= 7:
                raise
            retries += 1
            time.sleep(random.uniform(1, 2 ** retries))

    video_id = response.get("id")
    if not video_id:
        raise RuntimeError(f"Respuesta inesperada de YouTube: {response}")
    return video_id
