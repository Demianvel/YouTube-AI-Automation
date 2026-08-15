from __future__ import annotations

import argparse
import json
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.spiritual_engagement import engagement_comment

TOKEN_ENV = "YOUTUBE_TOKEN_DIOSHABLAHOYIA"
EXPECTED_HANDLE = "@dioshablahoyia"
COMMENT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Publica un comentario superior CTA en un video de Dios Habla Hoy IA.")
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--comment", default="")
    args = parser.parse_args()

    token_json = os.getenv(TOKEN_ENV, "").strip()
    if not token_json:
        raise RuntimeError(f"Falta {TOKEN_ENV}")

    info = json.loads(token_json)
    scopes = set(info.get("scopes") or [])
    if COMMENT_SCOPE not in scopes:
        raise RuntimeError("El token OAuth no incluye youtube.force-ssl. Reautoriza el canal antes de publicar comentarios.")

    creds = Credentials.from_authorized_user_info(info, scopes=list(scopes))
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    mine = youtube.channels().list(part="id,snippet", mine=True).execute().get("items", [])
    if not mine:
        raise RuntimeError("No se pudo identificar el canal autorizado.")
    channel = mine[0]
    custom_url = str(channel.get("snippet", {}).get("customUrl") or "").lower().lstrip("/")
    if custom_url != EXPECTED_HANDLE.lower().lstrip("/"):
        raise RuntimeError(f"Token del canal incorrecto: {custom_url or '(sin handle)'}")

    video = youtube.videos().list(part="id,snippet,status", id=args.video_id).execute().get("items", [])
    if not video:
        raise RuntimeError(f"No se encontro el video {args.video_id}")

    text = " ".join(args.comment.split()).strip() or engagement_comment(f"repair|{args.video_id}")
    response = youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "channelId": channel["id"],
                "videoId": args.video_id,
                "topLevelComment": {"snippet": {"textOriginal": text}},
            }
        },
    ).execute()

    print(json.dumps({
        "video_id": args.video_id,
        "comment_thread_id": response.get("id"),
        "status": "posted_top_level",
        "comment": text,
        "pin_status": "manual_only_official_api_has_no_pin_method",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
