from __future__ import annotations

import json
import os
from pathlib import Path

from .topic_rotation import choose_topic_family

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

    # EnViKids long-form reads master_prompt directly. Inject a deterministic
    # family based on the GitHub workflow run so consecutive long videos do not
    # keep choosing the same category. Shorts have their own history-aware
    # rotation in app/generator.py and are intentionally left untouched here.
    workflow = os.getenv("GITHUB_WORKFLOW", "").lower()
    if slug == "envikids" and "envikids" in workflow and "minute" in workflow:
        family = choose_topic_family("envikids", [], salt="envikids-long")
        data["forced_content_family"] = family
        data["master_prompt"] = (
            str(data.get("master_prompt") or "")
            + "\n\nREGLA DE VARIEDAD PARA ESTA EJECUCION: "
            + f"la historia debe pertenecer a '{family}'. "
            + "No cambies de familia por Analytics y no reutilices una historia, mision, titulo, protagonista o secuencia reciente."
        )
    return data


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Falta la variable/secret requerido: {name}")
    return value
