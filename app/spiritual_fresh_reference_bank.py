from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
VISUAL_REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "visual_reference"
HISTORY_FILES = (
    ROOT / "state" / "history.jsonl",
    ROOT / "state" / "dioshablahoyia_long_history.jsonl",
)
_STYLE_MARKER = ", premium live-action photoreal cinematic spiritual scene"


def _rows() -> list[dict]:
    rows: list[dict] = []
    for path in HISTORY_FILES:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(raw)
            except Exception:
                continue
            if row.get("channel") == "dioshablahoyia":
                rows.append(row)
    return rows


def subject_prompt(prompt: str) -> str:
    text = str(prompt or "")
    lower = text.lower()
    marker_index = lower.find(_STYLE_MARKER.strip().lower())
    if marker_index >= 0:
        text = text[:marker_index]
    return " ".join(text.split()).strip()


def _recent_reference_names(limit: int = 120) -> set[str]:
    result: set[str] = set()
    for row in _rows()[-limit:]:
        providers = row.get("generated_visual_provider") or []
        if isinstance(providers, str):
            providers = [providers]
        for provider in providers:
            text = str(provider)
            for marker in ("reference:", "style-reference:", "fresh-bank-style:"):
                if marker not in text:
                    continue
                tail = text.split(marker, 1)[1]
                result.add(tail.split(" ", 1)[0].split("/", 1)[0].strip())
    return result


def new_jesus_references() -> list[Path]:
    refs = sorted(REFERENCE_DIR.glob("jesus_reference_user_new_*.jpg"))
    if not refs:
        raise RuntimeError("No existe el banco renovado de referencias de Jesus.")
    return refs


def noah_references() -> list[Path]:
    refs = sorted(VISUAL_REFERENCE_DIR.glob("noah_ark_user_new_*.jpg"))
    if not refs:
        raise RuntimeError("No existe el banco renovado del Arca de Noe.")
    return refs


def _pick(refs: list[Path], seed: int) -> Path:
    recent = _recent_reference_names()
    preferred = [ref for ref in refs if ref.name not in recent]
    pool = preferred or refs
    digest = hashlib.sha256(f"fresh-reference-v3|{seed}".encode()).hexdigest()
    return pool[int(digest[:12], 16) % len(pool)]


def choose_new_jesus_reference(seed: int) -> Path:
    return _pick(new_jesus_references(), seed)


def is_noah_prompt(prompt: str) -> bool:
    lower = subject_prompt(prompt).lower()
    if any(phrase in lower for phrase in ("flood waters", "animals approaching in pairs", "animals approach in pairs")):
        return True
    return bool(re.search(r"\b(noah|noe|noé|ark|arca)\b", lower, flags=re.IGNORECASE))


def is_jesus_prompt(prompt: str) -> bool:
    lower = subject_prompt(prompt).lower()
    return bool(re.search(r"\b(jesus|jesús|jesucristo|cristo|christ|messiah|mesias|mesías)\b", lower, flags=re.IGNORECASE))


def choose_reference_for_prompt(prompt: str, seed: int) -> Path:
    if is_noah_prompt(prompt):
        try:
            return _pick(noah_references(), seed)
        except Exception:
            pass
    return choose_new_jesus_reference(seed)
