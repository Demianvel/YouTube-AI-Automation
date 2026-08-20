from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "state" / "growth" / "dioshablahoyia_internal_brain.json"
DEFAULT_HISTORY = ROOT / "state" / "history.jsonl"
INTERNAL_VERSION = "dios-internal-quality-cortex-v1"

EMOTIONAL_TERMS = {
    "esperanza", "paz", "amor", "misericordia", "consuelo", "fortaleza", "confianza",
    "alegria", "alegría", "gratitud", "proposito", "propósito", "valentia", "valentía",
    "descanso", "luz", "refugio", "acompaña", "acompanar", "acompañar", "corazon", "corazón",
}
TEACHING_TERMS = {
    "aprende", "enseña", "ensenanza", "enseñanza", "aplica", "aplicacion", "aplicación",
    "recorda", "recordá", "verdad", "sabiduria", "sabiduría", "camino", "decision", "decisión",
}
QUALITY_POLICY = {
    "biblical_grounding": 1.0,
    "emotional_resonance": 0.95,
    "clear_teaching": 0.95,
    "novelty": 0.90,
    "human_warmth": 0.90,
    "hopeful_energy": 0.88,
    "quality_over_hype": 1.0,
    "publish_consistently": 1.0,
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _history_rows(path: Path = DEFAULT_HISTORY) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict) and str(row.get("channel") or "") == "dioshablahoyia":
            rows.append(row)
    return rows


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-záéíóúüñ]+", str(text or "").lower()))


def _fingerprint(rows: list[dict[str, Any]], growth: dict[str, Any], seo: dict[str, Any]) -> str:
    compact_history = [
        {
            "id": row.get("video_id"),
            "status": row.get("status"),
            "title": row.get("title"),
            "reference": row.get("bible_reference"),
            "family": row.get("content_family"),
        }
        for row in rows[-250:]
    ]
    compact_growth = {
        "version": growth.get("version"),
        "videos": (growth.get("data_quality") or {}).get("videos_scored"),
        "outliers": [
            (row.get("video_id"), row.get("growth_score"), row.get("outlier_ratio"))
            for row in (growth.get("top_outliers") or [])[:30]
        ],
    }
    compact_seo = {
        "version": seo.get("version"),
        "keywords": [(row.get("key"), row.get("seo_score")) for row in (seo.get("keyword_weights") or [])[:50]],
    }
    raw = json.dumps([compact_history, compact_growth, compact_seo], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_internal_profile(
    history: list[dict[str, Any]],
    growth: dict[str, Any],
    seo: dict[str, Any],
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    uploaded = [row for row in history if str(row.get("status") or "") == "uploaded"]
    references = Counter(str(row.get("bible_reference") or "").strip() for row in uploaded if row.get("bible_reference"))
    families = Counter(str(row.get("content_family") or "").strip() for row in uploaded if row.get("content_family"))
    emotional_hits: Counter[str] = Counter()
    teaching_hits: Counter[str] = Counter()

    for row in uploaded[-150:]:
        text = " ".join(str(row.get(key) or "") for key in ("title", "topic", "content_family", "narration_preview"))
        tokens = _tokens(text)
        emotional_hits.update(token for token in tokens if token in EMOTIONAL_TERMS)
        teaching_hits.update(token for token in tokens if token in TEACHING_TERMS)

    data_fingerprint = _fingerprint(history, growth, seo)
    previous = previous or {}
    old_fingerprint = str(previous.get("data_fingerprint") or "")
    generation = int(previous.get("training_generation") or 0)
    if data_fingerprint != old_fingerprint:
        generation += 1

    return {
        "version": INTERNAL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "training_generation": generation,
        "data_fingerprint": data_fingerprint,
        "changed_since_previous": data_fingerprint != old_fingerprint,
        "training_mode": "local_only_zero_external_calls",
        "mission": {
            "purpose": "crear, publicar y mejorar contenido cristiano de alta calidad de forma constante",
            "editorial_tone": "emotivo, esperanzador, entusiasta, humano, claro y reverente",
            "quality_policy": QUALITY_POLICY,
            "never_fake_emotions_or_consciousness": True,
            "never_sacrifice_quality_for_clickbait": True,
            "publishing_must_continue": True,
        },
        "memory": {
            "uploaded_samples": len(uploaded),
            "unique_references": len(references),
            "unique_families": len(families),
            "recent_emotional_terms": emotional_hits.most_common(20),
            "recent_teaching_terms": teaching_hits.most_common(20),
            "most_used_references": references.most_common(15),
            "most_used_families": families.most_common(15),
        },
        "directives": {
            "hook": "captar atención en segundos con una verdad o pregunta emotiva, sin engaño",
            "body": "entregar una enseñanza bíblica concreta, comprensible y útil",
            "emotion": "transmitir esperanza, cercanía, paz, fuerza y entusiasmo sereno",
            "visual": "priorizar variedad, belleza, movimiento y coherencia con el mensaje",
            "ending": "cerrar con una enseñanza memorable y CTA natural, no agresivo",
            "learning": "crear -> publicar -> registrar -> comparar -> aprender -> variar -> mejorar",
        },
    }


def load_internal_profile(path: Path | str = DEFAULT_STATE) -> dict[str, Any]:
    return _read_json(Path(path))


def _theme_quality(theme: tuple[str, str, str, str], previous_rows: list[dict[str, Any]], state: dict[str, Any]) -> tuple[float, list[str]]:
    family, reference, truth, practice = theme
    text = " ".join(theme)
    tokens = _tokens(text)
    emotion = min(100.0, 55.0 + 7.0 * len(tokens & EMOTIONAL_TERMS))
    teaching = min(100.0, 62.0 + 7.0 * len(tokens & TEACHING_TERMS) + (12.0 if practice.strip() else 0.0))
    grounding = 96.0 if reference.strip() else 45.0
    recent = [row for row in previous_rows if row.get("status") == "uploaded"][-30:]
    same_ref = sum(1 for row in recent if str(row.get("bible_reference") or "") == reference)
    novelty = max(25.0, 100.0 - same_ref * 13.0)
    score = 0.30 * grounding + 0.25 * teaching + 0.22 * emotion + 0.23 * novelty
    reasons = [
        f"calidad_biblica={grounding:.0f}",
        f"ensenanza={teaching:.0f}",
        f"resonancia_emotiva={emotion:.0f}",
        f"novedad={novelty:.0f}",
    ]
    return round(max(0.0, min(100.0, score)), 2), reasons


def rerank_for_quality(
    themes: list[tuple[str, str, str, str]] | tuple[tuple[str, str, str, str], ...],
    previous_rows: list[dict[str, Any]],
    ranked: list[tuple[int, float, list[str]]],
    *,
    state: dict[str, Any] | None = None,
) -> list[tuple[int, float, list[str]]]:
    state = state or load_internal_profile()
    if not state:
        return ranked
    output: list[tuple[int, float, list[str]]] = []
    for index, base_score, reasons in ranked:
        quality, q_reasons = _theme_quality(themes[index], previous_rows, state)
        # Quality cortex can nudge choices, but never overpower first-party/NPU evidence.
        combined = 0.82 * float(base_score) + 0.18 * quality
        output.append((index, round(combined, 2), list(reasons[:4]) + q_reasons[:3]))
    output.sort(key=lambda row: row[1], reverse=True)
    return output
