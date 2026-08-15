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

from .spiritual_visual_uniqueness import validate_spiritual_visual_diversity

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]
COMMENT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
RETRIABLE = {500, 502, 503, 504}
MAX_SHORT_SECONDS = 180.0


def _token_info(token_json: str) -> dict:
    return json.loads(token_json)


def _credentials(token_json: str) -> Credentials:
    info = _token_info(token_json)
    scopes = info.get("scopes") or YOUTUBE_SCOPES
    return Credentials.from_authorized_user_info(info, scopes=scopes)


def _token_has_scope(channel: dict, scope: str) -> bool:
    token_json = os.getenv(channel["token_env"], "")
    if not token_json:
        return False
    try:
        scopes = set(_token_info(token_json).get("scopes") or [])
    except Exception:
        return False
    return scope in scopes


def _youtube_for_channel(channel: dict):
    token_json = os.getenv(channel["token_env"])
    if not token_json:
        raise RuntimeError(f"Falta el secret {channel['token_env']}")
    youtube = build("youtube", "v3", credentials=_credentials(token_json), cache_discovery=False)
    _verify_channel(youtube, channel)
    return youtube


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
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise RuntimeError("El archivo no contiene un stream de video valido.")
    stream = streams[0]
    duration = float((data.get("format") or {}).get("duration") or 0)
    return duration, int(stream.get("width") or 0), int(stream.get("height") or 0)


def _has_audio_stream(path: Path) -> bool:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_type", "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return bool(data.get("streams"))


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


def _enforce_long(video_path: Path, expected_minutes: int) -> None:
    duration, width, height = _probe_video(video_path)
    target = expected_minutes * 60.0
    tolerance = max(30.0, target * 0.12)
    if not (target - tolerance <= duration <= target + tolerance):
        raise RuntimeError(
            f"BLOQUEADO: se esperaban ~{expected_minutes} minutos. Duracion detectada: {duration:.2f}s."
        )
    if width <= height:
        raise RuntimeError(
            f"BLOQUEADO: el video largo debe ser horizontal 16:9. Resolucion detectada: {width}x{height}."
        )
    print(f"Long-form validation OK: {duration:.2f}s, {width}x{height}, target={expected_minutes}min")


def _is_spiritual_channel(channel: dict) -> bool:
    return str(channel.get("handle") or "").lower().lstrip("/") == "@dioshablahoyia"


def _is_native_gemini_clip(metadata: dict) -> bool:
    return (
        metadata.get("gemini_omni_primary") is True
        and metadata.get("native_generated_audio") is True
        and metadata.get("photoreal_live_action_look") is True
    )


def _enforce_spiritual_voice_guard(channel: dict, metadata: dict, video_path: Path) -> None:
    if not _is_spiritual_channel(channel):
        return

    # Gemini Omni generates the spoken performance inside the same audiovisual
    # clip. The legacy coverage/silence fields belong to the external TTS mixer
    # and therefore do not exist for this native path. We still require a real
    # audio stream before upload instead of blindly bypassing validation.
    if _is_native_gemini_clip(metadata):
        if not _has_audio_stream(video_path):
            raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: Gemini devolvio un video sin stream de audio.")
        metadata["voice_continuity_guard_mode"] = "native_audiovisual_clip_audio_stream_verified"
        return

    passed = metadata.get("voice_continuity_passed")
    coverage_raw = metadata.get("voice_coverage_ratio")
    longest_raw = metadata.get("longest_voice_silence_seconds")
    coverage = float(coverage_raw if coverage_raw is not None else 0.0)
    longest = float(longest_raw if longest_raw is not None else 999.0)
    if passed is not True or coverage < 0.96 or longest > 2.2:
        raise RuntimeError(
            "BLOQUEADO ANTES DE YOUTUBE: la narracion espiritual no supero el control de continuidad "
            f"(passed={passed}, coverage={coverage:.1%}, longest_silence={longest:.2f}s)."
        )


def _enforce_spiritual_visual_guard(channel: dict, metadata: dict) -> None:
    if not _is_spiritual_channel(channel):
        return

    # The legacy diversity guard detects repeated still/reference frames across
    # stitched multi-scene videos. A single natively generated moving clip is a
    # different format, so requiring several source labels would falsely block
    # it. Keep a strict provenance/profile check instead.
    if _is_native_gemini_clip(metadata):
        refs = metadata.get("character_reference_images") or []
        if not refs:
            raise RuntimeError("BLOQUEADO ANTES DE YOUTUBE: falta la referencia del personaje para el clip Gemini.")
        metadata["visual_diversity_guard_mode"] = "single_native_generated_motion_clip"
        metadata["native_reference_count"] = len(refs)
        return

    labels = metadata.get("generated_visual_provider") or metadata.get("visual_providers") or []
    stats = validate_spiritual_visual_diversity(list(labels) if isinstance(labels, (list, tuple)) else [str(labels)])
    metadata.update(stats)


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
    youtube = _youtube_for_channel(channel)
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


def _post_engagement_comment(channel: dict, metadata: dict, video_id: str) -> None:
    text = " ".join(str(metadata.get("pinned_comment_candidate") or "").split()).strip()
    if not text:
        metadata["comment_publish_status"] = "no_comment_candidate"
        return
    if not _token_has_scope(channel, COMMENT_SCOPE):
        metadata["comment_publish_status"] = "oauth_refresh_required_for_youtube.force-ssl"
        print("Comentario CTA preparado pero no publicado: el token OAuth actual no incluye youtube.force-ssl.")
        return
    try:
        youtube = _youtube_for_channel(channel)
        channel_response = youtube.channels().list(part="id", mine=True).execute()
        items = channel_response.get("items") or []
        if not items:
            raise RuntimeError("No se pudo obtener channelId para publicar el comentario.")
        channel_id = items[0]["id"]
        response = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "channelId": channel_id,
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": text[:9500]}
                    },
                }
            },
        ).execute()
        metadata["comment_publish_status"] = "posted_top_level"
        metadata["comment_thread_id"] = response.get("id")
        metadata["comment_pin_status"] = "manual_only_api_has_no_pin_method"
    except Exception as exc:
        metadata["comment_publish_status"] = f"failed_nonfatal: {type(exc).__name__}"
        print(f"El video {video_id} ya fue publicado; el comentario CTA fallo sin duplicar la subida: {exc}")


def set_custom_thumbnail(channel: dict, video_id: str, thumbnail_path: Path) -> None:
    if not thumbnail_path.exists() or thumbnail_path.stat().st_size <= 0:
        raise RuntimeError("La miniatura personalizada no existe o esta vacia.")
    youtube = _youtube_for_channel(channel)
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg", resumable=False),
    ).execute()


def upload_video(channel: dict, metadata: dict, video_path: Path) -> str:
    _enforce_short_only(video_path)
    _enforce_spiritual_voice_guard(channel, metadata, video_path)
    _enforce_spiritual_visual_guard(channel, metadata)
    video_id = _upload(channel, metadata, video_path)
    _post_engagement_comment(channel, metadata, video_id)
    return video_id


def upload_long_video(channel: dict, metadata: dict, video_path: Path, thumbnail_path: Path | None = None, expected_minutes: int = 10) -> str:
    _enforce_long(video_path, expected_minutes=expected_minutes)
    _enforce_spiritual_voice_guard(channel, metadata, video_path)
    _enforce_spiritual_visual_guard(channel, metadata)
    video_id = _upload(channel, metadata, video_path)
    metadata["thumbnail_upload_status"] = "not_requested"
    if thumbnail_path is not None:
        try:
            time.sleep(2)
            set_custom_thumbnail(channel, video_id, thumbnail_path)
            metadata["thumbnail_upload_status"] = "set"
        except Exception as exc:
            metadata["thumbnail_upload_status"] = f"failed_nonfatal: {type(exc).__name__}"
            print(f"Video {video_id} ya fue subido. La miniatura personalizada fallo sin reintentar el video: {exc}")
    _post_engagement_comment(channel, metadata, video_id)
    return video_id
