from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MASTER_PROMPT = ROOT / "presets" / "dioshablahoyia_master_prompts.txt"
PACKAGING_VERSION = "dhh-sovereign-packaging-v2"

EMOTIONAL_TERMS = (
    "paz", "esperanza", "fortaleza", "confianza", "consuelo", "amor", "descanso", "luz", "refugio",
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-záéíóúüñ0-9]+", _clean(value).lower()))


def _prompt_hash() -> str:
    try:
        raw = MASTER_PROMPT.read_bytes()
    except Exception:
        raw = b""
    return hashlib.sha256(raw).hexdigest()


def _safe_number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _performance_signal(row: dict) -> float:
    views = max(0.0, _safe_number(row.get("views") or row.get("view_count")))
    likes = max(0.0, _safe_number(row.get("likes") or row.get("like_count")))
    comments = max(0.0, _safe_number(row.get("comments") or row.get("comment_count")))
    shares = max(0.0, _safe_number(row.get("shares")))
    subs = max(0.0, _safe_number(row.get("subscribersGained")))
    avp = max(0.0, min(100.0, _safe_number(row.get("averageViewPercentage"))))
    return (
        math.log1p(views) * 1.8
        + math.log1p(likes) * 1.1
        + math.log1p(comments) * 1.2
        + math.log1p(shares) * 1.5
        + math.log1p(subs) * 1.6
        + avp * 0.055
    )


def _historical_affinity(title: str, previous: list[dict]) -> tuple[float, int]:
    scored = [(row, _performance_signal(row)) for row in previous if str(row.get("status") or "") == "uploaded"]
    scored = [(row, score) for row, score in scored if score > 0]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    title_tokens = _tokens(title)
    if not scored or not title_tokens:
        return 0.0, 0
    boosts: list[float] = []
    for row, score in scored[:16]:
        old_tokens = _tokens(row.get("title"))
        union = title_tokens | old_tokens
        overlap = (len(title_tokens & old_tokens) / len(union)) if union else 0.0
        boosts.append(overlap * min(10.0, score / 3.0))
    return (max(boosts) if boosts else 0.0), len(scored)


def _title_score(title: str, reference: str, previous: list[dict]) -> tuple[float, int]:
    clean = _clean(title)
    low = clean.lower()
    score = 58.0
    length = len(clean)
    if 42 <= length <= 78:
        score += 16.0
    elif 32 <= length <= 92:
        score += 9.0
    else:
        score -= 7.0
    if "dios" in low or "jesús" in low or "jesus" in low:
        score += 9.0
    if reference and reference.lower() in low:
        score += 8.0
    if any(term in low for term in EMOTIONAL_TERMS):
        score += 5.0
    if any(term in low for term in ("urgente", "secreto", "nadie te lo dice", "antes de que sea tarde")):
        score -= 18.0
    affinity, samples = _historical_affinity(clean, previous)
    score += min(8.0, affinity)
    return max(0.0, min(100.0, score)), samples


def _candidate_titles(metadata: dict) -> list[str]:
    reference = _clean(metadata.get("bible_reference"))
    topic = _clean(metadata.get("topic") or metadata.get("content_family"))
    base = _clean(metadata.get("title"))
    low = topic.lower()
    emotion = next((term for term in EMOTIONAL_TERMS if term in low), "esperanza")
    candidates = [
        base,
        f"Dios te recuerda esto hoy | {reference}",
        f"Una palabra de Dios para tu {emotion} | {reference}",
        f"Jesús te invita a confiar hoy | {reference}",
        f"Si hoy necesitás {emotion}, recordá esto | {reference}",
    ]
    unique: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        value = _clean(raw).strip(" |")
        key = value.lower()
        if value and key not in seen:
            unique.append(value[:100].rstrip())
            seen.add(key)
    return unique


def _quality_score(metadata: dict) -> float:
    title = _clean(metadata.get("title"))
    description = _clean(metadata.get("description"))
    reference = _clean(metadata.get("bible_reference"))
    hook = _clean(metadata.get("hook"))
    scenes = list(metadata.get("scenes") or [])
    narrated = sum(1 for scene in scenes if _clean(scene.get("narration")))
    score = 0.0
    score += 19.0 if 32 <= len(title) <= 100 else 10.0
    score += 15.0 if reference else 0.0
    score += 14.0 if len(hook.split()) >= 5 else 7.0
    score += 22.0 * (narrated / max(1, len(scenes))) if scenes else 0.0
    score += 11.0 if len(description) >= 110 else 6.0
    score += 10.0 if len(metadata.get("tags") or []) >= 8 else 5.0
    score += 5.0 if len(metadata.get("hashtags") or []) >= 3 else 2.0
    score += 4.0 if _clean(metadata.get("pinned_comment_candidate")) else 0.0
    return round(max(0.0, min(100.0, score)), 2)


def apply_premium_packaging(metadata: dict, previous: list[dict] | None = None) -> dict:
    previous = list(previous or [])
    reference = _clean(metadata.get("bible_reference"))
    topic = _clean(metadata.get("topic") or metadata.get("content_family") or "fe y esperanza")

    ranked = []
    samples = 0
    for title in _candidate_titles(metadata):
        score, used = _title_score(title, reference, previous)
        samples = max(samples, used)
        ranked.append((score, title))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    if ranked:
        metadata["title"] = ranked[0][1]
        metadata["seo_title_score"] = round(ranked[0][0], 2)
        metadata["seo_title_candidates"] = [title for _, title in ranked[:3]]

    metadata["description"] = (
        f"Reflexión cristiana inspirada en {reference or 'la Biblia'} sobre {topic}. "
        "Una palabra breve para volver a Dios con fe, esperanza y una decisión concreta para hoy.\n\n"
        "Escuchá hasta el final, guardá esta reflexión para volver a verla y compartila con alguien que necesite ánimo. "
        "Si esta palabra habló a tu corazón, podés escribir Amén en los comentarios."
    )
    tags = [
        "Dios Habla Hoy", "Dios", "Jesucristo", "Jesús", "Biblia", "Fe", "Oración", "Esperanza",
        "Reflexión Cristiana", "Palabra de Dios", "Mensaje de Dios", "Cristiano", "Shorts Cristianos",
        "Jesus", "Cristo", reference, topic,
    ]
    metadata["tags"] = list(dict.fromkeys(_clean(tag) for tag in tags if _clean(tag)))[:18]
    metadata["hashtags"] = ["#Dios", "#Jesús", "#Fe", "#Biblia", "#DiosHablaHoy"]
    metadata["pinned_comment_candidate"] = (
        f"🙏 Si esta palabra basada en {reference or 'la Biblia'} habló a tu corazón, escribí “Amén”. "
        "¿Por quién te gustaría que oremos hoy? Guardá el Short y compartilo con alguien que necesite esperanza."
    )
    metadata["cta"] = "Comentá Amén, guardá esta palabra y compartila con alguien que hoy necesite esperanza."
    metadata["seo_primary_keyword"] = f"Dios Habla Hoy {reference}".strip()
    metadata["packaging_provider"] = PACKAGING_VERSION
    metadata["master_prompt_version"] = "dioshablahoyia-master-v2"
    metadata["master_prompt_sha256"] = _prompt_hash()
    metadata["adaptive_history_samples"] = samples
    metadata["adaptive_learning_mode"] = "first_party_history_rerank_no_viral_guarantee"
    metadata["quality_policy"] = "biblical_grounding_human_warmth_retention_clarity_no_clickbait"

    quality = _quality_score(metadata)
    metadata["packaging_quality_score"] = quality
    metadata["packaging_quality_gate_passed"] = quality >= 72.0
    if quality < 64.0:
        raise RuntimeError(f"QUALITY_GATE: paquete editorial soberano insuficiente ({quality}/100).")
    return metadata
