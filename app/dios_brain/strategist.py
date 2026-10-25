"""Strategist agent: picks the faith pillar and biblical theme for the next Short.

Rotates paz, amor, esperanza, oración, promesas and enseñanzas de Jesús. It
penalizes pillars used in the most recent uploads, prefers winners when the
analyst has enough data (UCB1), adds a small bonus from growth keyword weights,
and then picks a theme of the chosen pillar whose Bible reference and topic
were not used recently. Returns None when nothing qualifies so the caller keeps
the original editorial selector.
"""
from __future__ import annotations

from typing import Callable

from . import analyst
from .pillars import PILLAR_ORDER, PILLARS, classify_row, classify_theme, normalize

LAST_DECISION: dict = {}


def _uploaded(previous: list[dict]) -> list[dict]:
    return [row for row in previous or [] if str(row.get("status") or "").lower() == "uploaded"]


def pillar_ranking(previous: list[dict], seed: int, available: set[str], growth: dict | None = None) -> tuple[list[str], str]:
    recent = [classify_row(row) for row in _uploaded(previous)[-6:]]
    scores: dict[str, float] = {}
    for index, name in enumerate(PILLAR_ORDER):
        if name not in available:
            continue
        score = 1.0
        if recent and recent[-1] == name:
            score -= 2.0          # never the same pillar twice in a row when avoidable
        score -= 0.35 * recent.count(name)
        score += 0.3 * analyst.pillar_bonus(PILLARS[name]["markers"], growth)
        score += ((seed >> (index * 3)) % 97) / 1000.0   # deterministic tie-break per run
        scores[name] = score
    ranked = sorted(scores, key=lambda name: scores[name], reverse=True)
    mode = "rotation"
    exclude = set(recent[-2:])
    winner = analyst.choose_arm(ranked, previous, "brain_pillar", exclude=exclude, growth=growth)
    if winner and winner in ranked:
        ranked.remove(winner)
        ranked.insert(0, winner)
        mode = "bandit_ucb1"
    return ranked, mode


def choose_theme(
    themes: tuple[dict, ...] | list[dict],
    previous: list[dict],
    seed: int,
    *,
    recent_references: set[str],
    recent_topics: list[str],
    similarity: Callable[[str, str], float],
    norm: Callable[[object], str],
) -> tuple[dict, int] | None:
    """Return (theme, seed) like dios_premium_editorial_v7._choose_theme, or None."""
    global LAST_DECISION
    themes = list(themes or [])
    if not themes:
        return None
    by_pillar: dict[str, list[dict]] = {}
    for theme in themes:
        by_pillar.setdefault(classify_theme(theme), []).append(theme)

    growth = analyst.load_growth_state()
    ranked, mode = pillar_ranking(previous, seed, set(by_pillar), growth)
    for pillar in ranked:
        pool = by_pillar[pillar]
        start = seed % len(pool)
        for step in range(len(pool)):
            theme = pool[(start + step * 7) % len(pool)]
            if norm(theme.get("reference")) in recent_references:
                continue
            proposed = f"{theme.get('family')} | {theme.get('reference')}"
            if any(similarity(proposed, old) >= 0.82 for old in recent_topics):
                continue
            LAST_DECISION = {
                "brain_pillar": pillar,
                "brain_selection_mode": mode,
                "brain_pillar_ranking": ranked,
                "brain_theme_reference": theme.get("reference"),
                "brain_theme_family": theme.get("family"),
            }
            return theme, seed
    LAST_DECISION = {"brain_selection_mode": "no_fresh_theme_fallback_original"}
    return None


def pillar_for(metadata: dict) -> str:
    stored = str(metadata.get("brain_pillar") or "")
    if stored in PILLARS:
        return stored
    return classify_row({"topic": metadata.get("topic"), "title": metadata.get("title")}) or normalize("esperanza")
