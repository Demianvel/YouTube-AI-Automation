from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

REPO = "Demianvel/YouTube-AI-Automation"
SECRET_NAME = "YOUTUBE_TOKEN_ENVIKIDS"
EXPECTED_HANDLE = "@envikidsai"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _find_client_secret() -> Path:
    candidates = []
    env_path = os.getenv("GOOGLE_OAUTH_CLIENT_FILE", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend([
        Path.home() / "client_secret.json",
        Path.home() / "YouTube-AI-Automation" / "client_secret.json",
        Path("/storage/emulated/0/Download/client_secret.json"),
    ])
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    raise FileNotFoundError(
        "No encontre client_secret.json. Descarga una credencial OAuth tipo Desktop app de tu proyecto Google Cloud "
        "y guardala como ~/client_secret.json o /storage/emulated/0/Download/client_secret.json."
    )


def _verify_channel(credentials: Credentials) -> tuple[str, str]:
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items") or []
    if not items:
        raise RuntimeError("Google autorizo la cuenta, pero no devolvio ningun canal de YouTube.")
    snippet = items[0].get("snippet") or {}
    handle = (snippet.get("customUrl") or "").strip()
    title = str(snippet.get("title") or "")
    if handle.lower().lstrip("/") != EXPECTED_HANDLE:
        raise RuntimeError(
            f"Canal incorrecto. Se esperaba @EnViKidsAI y Google devolvio {handle or title}. "
            "No se guardo ningun token. Volve a ejecutar y elegi la cuenta/canal EnViKidsAI."
        )
    return handle, title


def _save_github_secret(token_json: str) -> None:
    if not shutil_which("gh"):
        raise RuntimeError("No encontre gh. Instala GitHub CLI en Termux con: pkg install gh")
    result = subprocess.run(
        ["gh", "secret", "set", SECRET_NAME, "--repo", REPO, "--body", token_json],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GitHub CLI no pudo guardar el secret: {result.stderr.strip()}")


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def main() -> None:
    client_file = _find_client_secret()
    print(f"Usando cliente OAuth: {client_file}")
    print("Se abrira un enlace de Google. Elegi la cuenta que administra @EnViKidsAI y acepta los permisos.")
    print("El token NO se imprimira ni se guardara en el repositorio.")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
    credentials = flow.run_local_server(
        host="127.0.0.1",
        port=8765,
        open_browser=False,
        authorization_prompt_message="\nAbri esta URL en el navegador del mismo telefono:\n{url}\n",
        success_message="Autorizacion recibida. Podes volver a Termux.",
        access_type="offline",
        prompt="consent",
    )

    handle, title = _verify_channel(credentials)
    token_json = credentials.to_json()
    _save_github_secret(token_json)

    with tempfile.NamedTemporaryFile("w", delete=False, prefix="envikidsai-token-check-", suffix=".json") as fh:
        fh.write(json.dumps({"channel": handle, "title": title, "secret": SECRET_NAME}, ensure_ascii=False))
        temp_name = fh.name
    Path(temp_name).unlink(missing_ok=True)

    print(f"OK: {title} ({handle}) fue verificado.")
    print(f"OK: GitHub secret {SECRET_NAME} actualizado en {REPO}.")
    print("No copies ni pegues el token en el chat.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
