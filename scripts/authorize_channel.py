from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autoriza un canal de YouTube, verifica su identidad y genera el JSON para GitHub Secrets."
    )
    parser.add_argument("--client-secrets", default="client_secret.json")
    parser.add_argument("--output", help="Guarda el token OAuth en un archivo en vez de imprimirlo.")
    parser.add_argument("--expected-handle", help="Handle esperado, por ejemplo @BrotaVidaAI.")
    args = parser.parse_args()

    cfg = json.loads(Path(args.client_secrets).read_text(encoding="utf-8"))
    flow = InstalledAppFlow.from_client_config(cfg, scopes=SCOPES)
    creds = flow.run_local_server(
        port=0,
        open_browser=False,
        access_type="offline",
        prompt="consent",
    )

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise RuntimeError("No se pudo identificar un canal de YouTube para esta autorización.")

    channel = items[0]
    snippet = channel.get("snippet", {})
    title = snippet.get("title", "(sin nombre)")
    custom_url = snippet.get("customUrl", "")
    channel_id = channel.get("id", "")

    print("\nCANAL AUTORIZADO:")
    print(f"Nombre: {title}")
    if custom_url:
        print(f"Handle/URL: {custom_url}")
    print(f"Channel ID: {channel_id}")

    if args.expected_handle:
        actual = custom_url.lower().lstrip("/")
        expected = args.expected_handle.lower().lstrip("/")
        if actual != expected:
            raise RuntimeError(
                f"Canal incorrecto. Se esperaba {args.expected_handle} pero Google autorizó {custom_url or title}."
            )

    token_json = creds.to_json()
    if args.output:
        output = Path(args.output)
        output.write_text(token_json, encoding="utf-8")
        os.chmod(output, 0o600)
        print(f"Token guardado de forma privada en: {output}")
    else:
        print("\nVerifica que sea el canal correcto antes de guardar el token.")
        print("\nCOPIA TODO ESTE JSON COMO SECRET DEL CANAL:\n")
        print(token_json)


if __name__ == "__main__":
    main()
