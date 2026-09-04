from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2").strip() or "gpt-image-2"
KEY = os.getenv("OPENAI_API_KEY", "").strip()


def _emit(status: str, detail: str, *, ok: bool) -> None:
    payload = {
        "provider": "openai",
        "model": MODEL,
        "status": status,
        "detail": detail,
        "key_present": bool(KEY),
        "ready": ok,
    }
    print(json.dumps(payload, ensure_ascii=False))
    output = os.getenv("GITHUB_OUTPUT", "").strip()
    if output:
        with Path(output).open("a", encoding="utf-8") as fh:
            fh.write(f"ready={'true' if ok else 'false'}\n")
            fh.write(f"status={status}\n")
    env = os.getenv("GITHUB_ENV", "").strip()
    if env:
        with Path(env).open("a", encoding="utf-8") as fh:
            fh.write(f"OPENAI_IMAGE_API_READY={'true' if ok else 'false'}\n")
            fh.write(f"OPENAI_IMAGE_API_STATUS={status}\n")


def main() -> int:
    required = "--required" in sys.argv
    if not KEY:
        _emit(
            "missing_actions_secret",
            "GitHub Actions no entrego ninguna clave OpenAI al job. Revisar repository/environment secret o alias configurado.",
            ok=False,
        )
        return 2 if required else 0

    try:
        response = requests.get(
            f"https://api.openai.com/v1/models/{MODEL}",
            headers={"Authorization": f"Bearer {KEY}"},
            timeout=(10, 30),
        )
    except requests.RequestException as exc:
        _emit("network_error", f"{type(exc).__name__}: {exc}"[:240], ok=False)
        return 3 if required else 0

    if response.status_code == 200:
        _emit("ready", f"OpenAI autentico la clave y el proyecto puede consultar {MODEL}.", ok=True)
        return 0

    detail = ""
    try:
        body = response.json()
        error = body.get("error") or {}
        detail = str(error.get("message") or error.get("type") or "")[:240]
    except Exception:
        detail = response.text[:240]

    status_map = {
        401: "invalid_or_revoked_key",
        403: "project_or_model_forbidden",
        404: "model_not_available_to_project",
        429: "rate_or_billing_limit",
    }
    status = status_map.get(response.status_code, f"http_{response.status_code}")
    _emit(status, detail or f"OpenAI respondio HTTP {response.status_code}", ok=False)
    return 4 if required else 0


if __name__ == "__main__":
    raise SystemExit(main())
