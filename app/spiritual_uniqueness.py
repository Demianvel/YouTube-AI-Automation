from __future__ import annotations

import hashlib
import re

from .history import similarity


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalized_script(metadata: dict) -> str:
    text = " ".join(
        _clean(scene.get("narration", ""))
        for scene in (metadata.get("scenes") or [])
        if _clean(scene.get("narration", ""))
    ).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", text)
    return " ".join(text.split())


def _minimum_script_words(metadata: dict) -> int:
    """Scale substance threshold to the intended Short duration.

    The previous fixed 80-word gate was appropriate for long 1-3 minute Shorts,
    but incorrectly rejected the new 8-10 second native cinematic clips.
    """
    try:
        seconds = int(metadata.get("target_short_seconds") or 60)
    except Exception:
        seconds = 60
    # About 1.7 spoken words/second, with a floor that still blocks empty/template
    # clips and the original 80-word ceiling for longer content.
    return max(12, min(80, round(seconds * 1.7)))


def validate_spiritual_uniqueness(metadata: dict, previous: list[dict] | None = None) -> dict:
    """Reject template-like or duplicate Shorts before expensive rendering/upload."""
    previous = [row for row in (previous or []) if str(row.get("status") or "") == "uploaded"][-30:]
    title = _clean(metadata.get("title"))
    topic = _clean(metadata.get("topic"))
    script = _normalized_script(metadata)
    min_words = _minimum_script_words(metadata)
    if not script or len(script.split()) < min_words:
        raise RuntimeError(
            f"BLOQUEADO ANTI-SPAM: la narracion espiritual tiene {len(script.split())} palabras; "
            f"se requieren al menos {min_words} para este formato."
        )

    script_hash = hashlib.sha256(script.encode("utf-8")).hexdigest()
    preview = script[:1200]
    highest_title = 0.0
    highest_topic = 0.0
    highest_script = 0.0

    for old in previous:
        old_title = _clean(old.get("title"))
        old_topic = _clean(old.get("topic"))
        old_preview = _clean(old.get("narration_preview"))
        old_hash = _clean(old.get("script_hash"))

        if old_hash and old_hash == script_hash:
            raise RuntimeError("BLOQUEADO ANTI-SPAM: el guion coincide exactamente con un Short ya publicado.")

        if title and old_title:
            highest_title = max(highest_title, similarity(title, old_title))
        if topic and old_topic:
            highest_topic = max(highest_topic, similarity(topic, old_topic))
        if preview and old_preview:
            highest_script = max(highest_script, similarity(preview, old_preview))

    if highest_script >= 0.78:
        raise RuntimeError(
            f"BLOQUEADO ANTI-SPAM: narracion demasiado parecida a contenido reciente ({highest_script:.1%})."
        )
    if highest_title >= 0.82 and highest_topic >= 0.86:
        raise RuntimeError(
            f"BLOQUEADO ANTI-SPAM: titulo/tema demasiado parecidos a una publicacion reciente "
            f"(titulo {highest_title:.1%}, tema {highest_topic:.1%})."
        )

    metadata["script_hash"] = script_hash
    metadata["narration_preview"] = preview
    metadata["uniqueness_gate_passed"] = True
    metadata["uniqueness_min_words"] = min_words
    metadata["uniqueness_scores"] = {
        "highest_recent_title_similarity": round(highest_title, 4),
        "highest_recent_topic_similarity": round(highest_topic, 4),
        "highest_recent_script_similarity": round(highest_script, 4),
    }
    return metadata
