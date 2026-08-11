from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


def read_history(path: Path, channel: str | None = None, limit: int = 80) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if channel is None or item.get("channel") == channel:
            rows.append(item)
    return rows[-limit:]


def append_history(path: Path, item: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()


def too_similar(candidate: dict, previous: Iterable[dict], threshold: float = 0.72) -> tuple[bool, str]:
    title = candidate.get("title", "")
    topic = candidate.get("topic", "")
    for old in previous:
        if similarity(title, old.get("title", "")) >= threshold:
            return True, f"titulo similar a: {old.get('title', '')}"
        if topic and similarity(topic, old.get("topic", "")) >= 0.80:
            return True, f"tema similar a: {old.get('topic', '')}"
    return False, ""
