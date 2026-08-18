from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from app import spiritual_long_pipeline as base
from app.spiritual_long_fresh_visual import download_fresh_long_visual
from app.spiritual_long_resilient_runner import run

ROOT = Path(__file__).resolve().parents[1]
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"


def _extract_visual_fingerprints(providers: list[str]) -> tuple[list[str], list[str]]:
    sha_values: list[str] = []
    dhash_values: list[str] = []
    for provider in providers:
        text = str(provider or "")
        sha_match = re.search(r"image_sha256=([0-9a-f]{64})", text, flags=re.IGNORECASE)
        dhash_match = re.search(r"image_dhash=([0-9a-f]{64})", text, flags=re.IGNORECASE)
        if sha_match and sha_match.group(1).lower() not in sha_values:
            sha_values.append(sha_match.group(1).lower())
        if dhash_match and dhash_match.group(1).lower() not in dhash_values:
            dhash_values.append(dhash_match.group(1).lower())
    return sha_values, dhash_values


def _enrich_last_history(result: dict) -> None:
    if not LONG_HISTORY.exists():
        return
    raw_lines = LONG_HISTORY.read_text(encoding="utf-8").splitlines()
    if not raw_lines:
        return
    try:
        last = json.loads(raw_lines[-1])
    except Exception:
        return

    providers = [str(item) for item in (result.get("visual_providers") or [])]
    sha_values, dhash_values = _extract_visual_fingerprints(providers)
    last["visual_providers"] = providers
    last["visual_asset_sha256"] = sha_values
    last["visual_asset_dhash"] = dhash_values
    last["visual_freshness_verified"] = bool(sha_values or providers)
    last["visual_fingerprint_mode"] = "sha256_plus_256bit_dhash"
    last["voice_identity_locked"] = True
    last["voice_profile"] = "voz_de_luz_serena_original_v1"
    last["voice_expected_provider"] = "Gemini TTS/Algenib"
    last["voice_lock_version"] = "voz-de-luz-algenib-v2"
    raw_lines[-1] = json.dumps(last, ensure_ascii=False)
    LONG_HISTORY.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[10, 15, 20, 30])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    original_download = base._download_image
    base._download_image = download_fresh_long_visual
    try:
        result = run(args.minutes, publish=args.publish)
        _enrich_last_history(result)
    finally:
        base._download_image = original_download
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
