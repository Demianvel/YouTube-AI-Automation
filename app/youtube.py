from __future__ import annotations

import json
import os
import random
import subprocess
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
MAX_SHORT_SECONDS = 180.0
LONG_MIN_SECONDS = 240.0
LONG_MAX_SECONDS = 360.0


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
            f"Token asociado al canal incorrecto: se esperaba {channel['handle']} y Google devolvio {actual or title}."
        )


def _probe_video(path: Path) -> tuple[float, int, int]:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise RuntimeError("El archivo no contiene un stream de video valido.")
    stream = streams[0]
    duration = float((data.get("format") or {}).get("duration") or 0)
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    return duration, width, height


def _enforce_short_only(video_path: Path) -> None:
    duration, width, height = _probe_video(video_path)
    if duration <= 0:
        raise RuntimeError("No se pudo validar la duracion del Short.")
    if duration > MAX_SHORT_SECONDS + 0.25:
        raise RuntimeError(
            f"BLOQUEADO: este workflow solo publica Shorts. Duracion detectada: {duration:.2f}s; maximo permitido: {MAX_SHORT_SECONDS:.0f}s."
        )
    if width <= 0 or height <= 0:
        raise RuntimeError("No se pudo validar la relacion de aspecto del Short.")
    if height < width:
        raise RuntimeError(
            f"BLOQUEADO: este workflow solo publica video vertical o cuadrado. Resolucion detectada: {width}x{height}."
        )
    print(f"Short validation OK: {duration:.2f}s, {width}x{height}")


def _enforce_five_minute_long(video_path: Path) -> None:
    duration, width, height = _probe_video(video_path)
    if not (LONG_MIN_SECONDS <= duration <= LONG_MAX_SECONDS):
        raise RuntimeError(
            f"BLOQUEADO: el uploader long-form espera aproximadamente 5 minutos. Duracion detectada: {duration:.2f}s."
        )
    if width <= height:
        raise RuntimeError(
            f"BLOQUEADO: el video largo debe ser horizontal 16:9. Resolucion detectada: {width}x{height}."
        )
    print(f"Long-form validation OK: {duration:.2f}s, {width}x{height}")


def _description(metadata: dict) -> str:
    parts: list[str] = []
    base = (metadata.get("description") or "").strip()
    if base:
        parts.append(base)

    hashtags = " ".join(metadata.get("hashtags", [])[:5]).strip()
    if hashtags:
        parts.append(hashtags)

    credits = metadata.get("source_credits") or []
    if credits:
        lines = ["Fuentes visuales reales utilizadas y editadas para este video:"]
        for item in credits[:20]:
            provider = (item.get("provider") or "Fuente visual").strip()
            creator = (item.get("creator") or "colaborador").strip()
            license_name = (item.get("license") or "").strip()
            source_url = (item.get("source_url") or item.get("creator_url") or "").strip()
            label = f"- {provider} — {creator}"
            if license_name:
                label += f" — {license_name}"
            if source_url:
                label += f": {source_url}"
            lines.append(label)
        parts.append("\n".join(lines))

    return "\n\n".join(parts)[:4900].strip()


def _upload(channel: dict, metadata: dict, video_path: Path) -> str:
    token_json = os.getenv(channel["token_env"])
    if not token_json:
        raise RuntimeError(f"Falta el secret {channel['token_env']}")

    youtube = build("youtube", "v3", credentials=_credentials(token_json), cache_discovery=False)
    _verify_channel(youtube, channel)

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": _description(metadata),
            "tags": metadata.get("tags", [])[:18],
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


def upload_video(channel: dict, metadata: dict, video_path: Path) -> str:
    _enforce_short_only(video_path)
    return _upload(channel, metadata, video_path)


def upload_long_video(channel: dict, metadata: dict, video_path: Path) -> str:
    _enforce_five_minute_long(video_path)
    return _upload(channel, metadata, video_path)
