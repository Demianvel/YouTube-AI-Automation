from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import urljoin

import requests


def _base_url() -> str:
    url = os.getenv("ACESTEP_API_URL", "").strip()
    if not url:
        raise RuntimeError("Falta ACESTEP_API_URL. Usa un servidor ACE-Step 1.5 propio o self-hosted GPU.")
    return url.rstrip("/") + "/"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = os.getenv("ACESTEP_API_KEY", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def generate_song(
    out: Path,
    *,
    prompt: str,
    lyrics: str,
    duration_seconds: int,
    bpm: int,
    vocal_language: str = "es",
    model: str = "acestep-v15-turbo",
    thinking: bool = True,
) -> None:
    """Generate a song through the official ACE-Step 1.5 async REST API.

    The server may run locally on a self-hosted GPU runner or on another machine controlled by
    the user. User-provided lyrics are passed verbatim. No third-party singing voice is cloned.
    """
    base = _base_url()
    payload = {
        "prompt": prompt,
        "lyrics": lyrics,
        "thinking": thinking,
        "vocal_language": vocal_language,
        "audio_format": "wav",
        "audio_duration": max(10, min(600, int(duration_seconds))),
        "bpm": max(30, min(300, int(bpm))),
        "model": model,
        "use_random_seed": True,
        "batch_size": 1,
        "use_cot_caption": True,
        "use_cot_language": False,
    }
    response = requests.post(urljoin(base, "release_task"), json=payload, headers=_headers(), timeout=(15, 120))
    response.raise_for_status()
    wrapped = response.json()
    if int(wrapped.get("code", 200)) != 200:
        raise RuntimeError(f"ACE-Step rechazo la tarea: {wrapped.get('error')}")
    data = wrapped.get("data") or {}
    task_id = data.get("task_id") or data.get("taskId") or data.get("id")
    if not task_id:
        raise RuntimeError(f"ACE-Step no devolvio task_id: {wrapped}")

    deadline = time.monotonic() + int(os.getenv("ACESTEP_TIMEOUT_SECONDS", "1800"))
    result_data = None
    while time.monotonic() < deadline:
        query = requests.post(
            urljoin(base, "query_result"),
            json={"task_id_list": [task_id]},
            headers=_headers(),
            timeout=(15, 120),
        )
        query.raise_for_status()
        body = query.json()
        if int(body.get("code", 200)) != 200:
            raise RuntimeError(f"ACE-Step query_result fallo: {body.get('error')}")
        rows = body.get("data") or []
        if isinstance(rows, dict):
            rows = rows.get("results") or rows.get("tasks") or [rows]
        row = next((x for x in rows if str(x.get("task_id") or x.get("taskId") or x.get("id")) == str(task_id)), rows[0] if rows else None)
        if row:
            status = int(row.get("status", 0))
            if status == 2:
                raise RuntimeError(f"ACE-Step marco la generacion como fallida: {row}")
            if status == 1:
                result_data = row
                break
        time.sleep(5)
    if result_data is None:
        raise TimeoutError("ACE-Step no termino dentro del tiempo configurado.")

    # Result shapes differ slightly between versions; search common fields without guessing a local path.
    candidates = []
    for key in ("result", "results", "audio_files", "files", "outputs"):
        value = result_data.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif value:
            candidates.append(value)
    candidates.append(result_data)

    audio_url = ""
    for item in candidates:
        if isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
            audio_url = item
            break
        if isinstance(item, dict):
            for key in ("audio_url", "audioUrl", "url", "download_url"):
                value = str(item.get(key) or "").strip()
                if value:
                    audio_url = value
                    break
            if audio_url:
                break
            path = str(item.get("path") or item.get("audio_path") or "").strip()
            if path:
                audio_url = urljoin(base, f"v1/audio?path={requests.utils.quote(path, safe='')}")
                break
    if not audio_url:
        raise RuntimeError(f"ACE-Step termino pero no expuso una URL de audio reconocible: {result_data}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(audio_url, headers={k: v for k, v in _headers().items() if k != "Content-Type"}, stream=True, timeout=(20, 300)) as audio:
        audio.raise_for_status()
        with out.open("wb") as fh:
            for chunk in audio.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    if not out.exists() or out.stat().st_size < 100_000:
        raise RuntimeError("ACE-Step devolvio un archivo de audio invalido.")
