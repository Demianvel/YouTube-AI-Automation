from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Autoriza una vez un canal de YouTube y genera el JSON para GitHub Secrets.")
    parser.add_argument("--client-secrets", default="client_secret.json")
    args = parser.parse_args()
    cfg = json.loads(Path(args.client_secrets).read_text(encoding="utf-8"))
    flow = InstalledAppFlow.from_client_config(cfg, scopes=SCOPE)
    creds = flow.run_local_server(port=0, open_browser=False, access_type="offline", prompt="consent")
    print("\nCOPIA TODO ESTE JSON COMO SECRET DEL CANAL:\n")
    print(creds.to_json())


if __name__ == "__main__":
    main()
