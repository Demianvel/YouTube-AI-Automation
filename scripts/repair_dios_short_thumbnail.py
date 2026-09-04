from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from app.config import ROOT, load_channel
from app.spiritual_auto_thumbnail import build_auto_thumbnail
from app import youtube as youtube_module

HISTORY = ROOT / "state" / "history.jsonl"


def _set_verified(channel: dict, video_id: str, thumbnail: Path) -> tuple[int, dict]:
    last_exc: Exception | None = None
    for attempt in range(1, 6):
        try:
            youtube = youtube_module._youtube_for_channel(channel)
            response = youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail), mimetype="image/jpeg", resumable=False),
            ).execute()
            items = response.get("items") or []
            if not items:
                raise RuntimeError(f"YouTube thumbnails.set respondio sin items: {response}")
            return attempt, response
        except Exception as exc:
            last_exc = exc
            if attempt >= 5:
                break
            time.sleep(min(20, 2 * attempt + 1))
    raise RuntimeError(f"No se pudo confirmar la miniatura tras 5 intentos: {last_exc}")


def _patch_history(video_id: str, fields: dict) -> None:
    if not HISTORY.exists():
        return
    rows = HISTORY.read_text(encoding="utf-8").splitlines()
    changed = False
    for index, raw in enumerate(rows):
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if str(row.get("video_id") or "").strip() != video_id:
            continue
        row.update(fields)
        rows[index] = json.dumps(row, ensure_ascii=False)
        changed = True
        break
    if changed:
        HISTORY.write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()

    request_path = Path(args.request)
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    video_id = str(payload.get("video_id") or "").strip()
    if not video_id:
        raise SystemExit("Falta video_id en la solicitud de reparacion")

    metadata = {
        "title": str(payload.get("title") or "Dios Habla Hoy").strip(),
        "topic": str(payload.get("topic") or "fe, esperanza y presencia de Dios").strip(),
        "bible_reference": str(payload.get("bible_reference") or "").strip(),
    }

    workdir = ROOT / "output" / "dioshablahoyia-thumbnail-repair" / video_id
    workdir.mkdir(parents=True, exist_ok=True)

    refs = sorted((ROOT / "assets" / "dioshablahoyia" / "reference").glob("jesus_reference_*.jpg"))
    if not refs:
        raise RuntimeError("No hay referencias locales para el fallback de miniatura")
    source = refs[sum(ord(ch) for ch in video_id) % len(refs)]
    shutil.copy2(source, workdir / "repair_source.jpg")

    thumbnail = build_auto_thumbnail(
        workdir,
        metadata,
        content_type="short",
        video_path=None,
    )
    channel = load_channel("dioshablahoyia")
    attempts, response = _set_verified(channel, video_id, thumbnail)

    fields = {
        "thumbnail_status": "uploaded_to_youtube_verified_response",
        "thumbnail_upload_status": "set_verified",
        "thumbnail_upload_attempts": attempts,
        "thumbnail_youtube_response_items": len(response.get("items") or []),
        "thumbnail_repair_required": False,
        "thumbnail_repaired": True,
        "thumbnail_sha256": metadata.get("thumbnail_sha256"),
        "thumbnail_dhash": metadata.get("thumbnail_dhash"),
        "thumbnail_nearest_distance": metadata.get("thumbnail_nearest_distance"),
        "thumbnail_provider": metadata.get("thumbnail_provider"),
        "thumbnail_prompt_hash": metadata.get("thumbnail_prompt_hash"),
        "thumbnail_style_id": metadata.get("thumbnail_style_id"),
        "thumbnail_layout_id": metadata.get("thumbnail_layout_id"),
        "thumbnail_aspect": metadata.get("thumbnail_aspect"),
        "thumbnail_ai_policy": metadata.get("thumbnail_ai_policy"),
        "thumbnail_openai_fallback_reason": metadata.get("thumbnail_openai_fallback_reason"),
    }
    _patch_history(video_id, fields)

    result = {"video_id": video_id, "thumbnail": str(thumbnail), **fields}
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
