"""Dios Brain orchestration: strategist -> writer/SEO + CTA -> quality editor -> analyst.

Entry points used by scripts/publish_dios_hybrid.py:

* ``brain_choose_theme`` wraps the v7 editorial theme selector.
* ``apply_brain_packaging`` rewrites script + packaging after the existing SEO
  stack and before the anti-spam uniqueness gate. On any brain error, or when
  the editor rejects every brain variant, it returns the original metadata
  untouched (fallback to existing behavior), unless the original itself breaks
  a hard YouTube policy, in which case it raises a "BLOQUEADO ANTI-SPAM" error
  so the pipeline picks another candidate.
"""
from __future__ import annotations

import copy
import os

from . import analyst, cta, editor, strategist, writer
from .pillars import PILLARS, classify_theme
from .themes import EXTRA_THEMES

BRAIN_VERSION = "dios-brain-v1"


def enabled() -> bool:
    return os.getenv("DIOS_BRAIN_ENABLED", "true").strip().lower() == "true"


def brain_choose_theme(v7_module, previous: list[dict]):
    """Return (theme, seed) or None to let v7 keep its own selector."""
    seed = v7_module._seed(previous)
    return strategist.choose_theme(
        tuple(v7_module.THEMES) + EXTRA_THEMES,
        previous,
        seed,
        recent_references=v7_module._recent_references(previous),
        recent_topics=v7_module._recent_topics(previous),
        similarity=lambda a, b: editor._similarity(a, b),
        norm=v7_module._norm,
    )


def _find_theme(metadata: dict, themes) -> dict | None:
    stored = metadata.get("_brain_theme")
    if isinstance(stored, dict) and stored.get("reference"):
        return stored
    ref = str(metadata.get("_premium_editorial_reference") or metadata.get("bible_reference") or "").strip()
    for theme in tuple(themes or ()) + EXTRA_THEMES:
        if str(theme.get("reference")) == ref:
            return dict(theme)
    return None


def _seed(metadata: dict, previous: list[dict]) -> int:
    import hashlib

    raw = "|".join([
        BRAIN_VERSION,
        os.getenv("GITHUB_RUN_ID", ""), os.getenv("GITHUB_RUN_NUMBER", ""),
        os.getenv("DIOS_SOVEREIGN_VARIATION_NONCE", ""),
        str(metadata.get("bible_reference")), str(len(previous or [])),
    ])
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16)


def _package(base: dict, theme: dict, pillar: str, previous: list[dict], seed: int, variant: int, growth: dict) -> dict:
    meta = copy.deepcopy(base)
    count = max(1, len(meta.get("scenes") or []) or 6)
    target_seconds = float(meta.get("target_short_seconds") or 60)
    budget = writer.word_budget(target_seconds)

    hook_id, hook = writer.choose_hook(pillar, previous, seed, offset=variant)
    cta_id, cta_variant, cta_mode = cta.choose_cta(previous, seed + variant, growth)
    lines = writer.build_script(theme, pillar, hook, cta_variant["spoken"], seed + variant, count, budget)

    scenes = list(meta.get("scenes") or [{} for _ in range(count)])
    while len(scenes) < len(lines):
        scenes.append(dict(scenes[-1]) if scenes else {})
    for index, line in enumerate(lines):
        scenes[index]["narration"] = line
    meta["scenes"] = scenes[: len(lines)]

    titles = writer.title_candidates(theme, pillar, seed + variant)
    recent_titles = [str(r.get("title") or "") for r in previous[-30:] if r.get("title")]
    template_id, title = min(
        titles,
        key=lambda item: max((editor._similarity(item[1], old) for old in recent_titles), default=0.0),
    )

    meta.update({
        "title": title,
        "hook": lines[0],
        "description": writer.build_description(theme, pillar, hook, cta_variant["description"]),
        "hashtags": writer.build_hashtags(pillar),
        "brain_tags": writer.build_tags(theme, pillar),
        "cta": cta_variant["description"],
        "cta_spoken": cta_variant["spoken"],
        "cta_packaging": cta_variant["description"],
        "cta_mode": "spoken_closing_and_description",
        "seo_primary_keyword": PILLARS[pillar]["keyword"],
        "contains_synthetic_media": True,
        "synthetic_media_disclosure": "ai_generated_visuals_and_synthetic_narrator_voz_de_luz",
        "voice_is_literal_voice_of_god": False,
        "brain_version": BRAIN_VERSION,
        "brain_pillar": pillar,
        "brain_hook_id": hook_id,
        "brain_title_template": template_id,
        "brain_cta_id": cta_id,
        "brain_cta_mode": cta_mode,
        "brain_word_count": sum(len(line.split()) for line in lines),
        "brain_word_budget": list(budget),
    })
    # Keep downstream SEO/history fields consistent with the new title.
    meta["title_variants"] = [t for _, t in titles][:3]
    meta["seo_title_candidates"] = [t for _, t in titles][:3]
    return meta


def apply_brain_packaging(metadata: dict, previous: list[dict], themes=None) -> dict:
    previous = list(previous or [])
    if not enabled():
        metadata["brain_status"] = "disabled"
        return metadata
    original = copy.deepcopy(metadata)
    reasons_seen: list[str] = []
    try:
        theme = _find_theme(metadata, themes)
        if not theme:
            raise RuntimeError("tema editorial no encontrado para el cerebro")
        pillar = str(metadata.get("brain_pillar") or "")
        if pillar not in PILLARS:
            pillar = classify_theme(theme)
        growth = analyst.load_growth_state()
        seed = _seed(metadata, previous)
        budget = writer.word_budget(float(metadata.get("target_short_seconds") or 60))
        for variant in range(4):
            candidate = _package(metadata, theme, pillar, previous, seed, variant, growth)
            ok, reasons = editor.review(candidate, previous, budget)
            if ok:
                candidate["brain_status"] = "applied"
                candidate["brain_editor_passed"] = True
                candidate["brain_editor_reasons"] = []
                return candidate
            reasons_seen.extend(reasons)
        status = "fallback_editor_rejected"
    except Exception as exc:  # brain must never break publishing
        reasons_seen.append(f"{type(exc).__name__}: {exc}"[:300])
        status = "fallback_error"

    original["brain_status"] = status
    original["brain_version"] = BRAIN_VERSION
    original["brain_editor_passed"] = False
    original["brain_editor_reasons"] = reasons_seen[:8]
    hard = editor.policy_violations(original)
    if hard:
        raise RuntimeError(f"BLOQUEADO ANTI-SPAM: dios_brain editor detecto riesgo de politica: {hard[:3]}")
    print(f"Dios Brain sin cambios ({status}): {reasons_seen[:4]}", flush=True)
    return original


def record_fields(metadata: dict) -> dict:
    return analyst.record_fields(metadata)
