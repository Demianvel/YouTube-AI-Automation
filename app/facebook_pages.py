from __future__ import annotations

import os
from pathlib import Path

import requests


GRAPH_API_VERSION = os.getenv("FACEBOOK_GRAPH_API_VERSION", "v25.0").strip() or "v25.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def facebook_page_configured() -> bool:
    return bool(os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip())


def _clean_hashtag(value: str) -> str:
    text = "".join(str(value or "").strip().split())
    if not text:
        return ""
    return text if text.startswith("#") else f"#{text}"


def build_facebook_reel_copy(metadata: dict) -> tuple[str, str]:
    """Create concise Facebook-native packaging from the already approved spiritual metadata."""
    title = " ".join(str(metadata.get("title") or "Una palabra de fe para hoy").split()).strip()
    title = title.replace(" IA", "").replace(" AI", "")[:255]

    topic = " ".join(str(metadata.get("topic") or "").split()).strip()
    reference = " ".join(str(metadata.get("bible_reference") or "").split()).strip()
    description = " ".join(str(metadata.get("description") or "").split()).strip()

    body_parts: list[str] = []
    if description:
        body_parts.append(description[:1100])
    elif topic:
        body_parts.append(topic[:700])
    if reference and reference.lower() not in " ".join(body_parts).lower():
        body_parts.append(f"📖 {reference}")

    body_parts.append(
        "🙏 Si este mensaje te ayudó, seguí la página y compartilo con alguien que hoy necesite fe, paz y esperanza."
    )

    requested = metadata.get("hashtags") or []
    if isinstance(requested, str):
        requested = requested.split()
    hashtags: list[str] = []
    for raw in list(requested) + ["Dios", "Jesus", "Fe", "Biblia", "Oracion", "Esperanza"]:
        tag = _clean_hashtag(str(raw))
        if tag and tag.lower() not in {h.lower() for h in hashtags}:
            hashtags.append(tag)
        if len(hashtags) >= 8:
            break

    body_parts.append(" ".join(hashtags))
    return title, "\n\n".join(part for part in body_parts if part).strip()[:2200]


def _raise_for_meta(response: requests.Response, step: str) -> dict:
    try:
        payload = response.json()
    except Exception:
        payload = {"raw": response.text[:1000]}
    if not response.ok:
        raise RuntimeError(f"Facebook {step} falló HTTP {response.status_code}: {payload}")
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"Facebook {step} devolvió error: {payload['error']}")
    return payload if isinstance(payload, dict) else {"result": payload}


def publish_facebook_reel(video_path: Path, metadata: dict) -> dict:
    """Publish a local vertical MP4 to a Facebook Page using Meta's Reels upload flow."""
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    page_id = os.getenv("FACEBOOK_PAGE_ID", "").strip()
    if not token:
        return {"status": "not_configured", "reason": "missing_page_access_token"}

    video_path = Path(video_path)
    if not video_path.exists() or video_path.stat().st_size < 10_000:
        raise RuntimeError(f"Facebook Reel inválido o inexistente: {video_path}")

    title, description = build_facebook_reel_copy(metadata)
    page_target = page_id or "me"
    endpoint = f"{GRAPH_BASE}/{page_target}/video_reels"

    with requests.Session() as session:
        start_response = session.post(
            endpoint,
            params={"access_token": token, "upload_phase": "start"},
            timeout=(20, 90),
        )
        start = _raise_for_meta(start_response, "inicio de Reel")
        video_id = str(start.get("video_id") or "").strip()
        upload_url = str(start.get("upload_url") or "").strip()
        if not video_id:
            raise RuntimeError(f"Facebook no devolvió video_id al iniciar el Reel: {start}")
        if not upload_url:
            upload_url = f"https://rupload.facebook.com/video-upload/{GRAPH_API_VERSION}/{video_id}"

        size = video_path.stat().st_size
        headers = {
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(size),
            "Content-Type": "application/octet-stream",
        }
        with video_path.open("rb") as handle:
            upload_response = session.post(
                upload_url,
                headers=headers,
                data=handle,
                timeout=(30, 600),
            )
        upload = _raise_for_meta(upload_response, "carga de Reel")

        finish_response = session.post(
            endpoint,
            params={
                "access_token": token,
                "video_id": video_id,
                "upload_phase": "finish",
                "video_state": "PUBLISHED",
                "title": title,
                "description": description,
            },
            timeout=(20, 120),
        )
        finish = _raise_for_meta(finish_response, "publicación de Reel")

    return {
        "status": "published",
        "facebook_video_id": video_id,
        "facebook_page_target": page_target,
        "facebook_title": title,
        "facebook_description": description,
        "upload_result": upload,
        "publish_result": finish,
        "graph_api_version": GRAPH_API_VERSION,
    }
