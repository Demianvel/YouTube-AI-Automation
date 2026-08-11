from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNELS_FILE = ROOT / "config" / "channels.json"
HISTORY_FILE = ROOT / "state" / "history.jsonl"
OUTPUT_DIR = ROOT / "output"


def load_channels() -> dict:
    return json.loads(CHANNELS_FILE.read_text(encoding="utf-8"))


def load_channel(slug: str) -> dict:
    channels = load_channels()
    if slug not in channels:
        raise KeyError(f"Canal desconocido: {slug}. Opciones: {', '.join(channels)}")
    data = dict(channels[slug])
    data["slug"] = slug
    return data


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Falta la variable/secret requerido: {name}")
    return value
