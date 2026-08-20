from __future__ import annotations

import json
import math
import re
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRAIN = ROOT / "state" / "growth" / "dioshablahoyia_npu_brain.json"
DEFAULT_NICHE_RADAR = ROOT / "state" / "growth" / "dioshablahoyia_niche_radar.json"
DEFAULT_MARKET_RADAR = ROOT / "state" / "growth" / "youtube_market_radar.json"

# This is deliberately "quantum-inspired", not quantum hardware. The engine uses
# softmax amplitudes + entropy/confidence to balance exploitation and exploration.
BRAIN_VERSION = "alien-npu-brain-v1"

_STOPWORDS = {
    "a", "al", "algo", "ante", "como", "con", "cuando", "de", "del", "dios", "el", "en",
    "es", "esta", "fe", "hoy", "la", "las", "lo", "los", "más", "mi", "para", "por", "que",
    "se", "si", "sin", "su", "te", "tu", "un", "una", "y", "ya", "jesus", "jesús", "short",
    "shorts", "video", "vídeo", "biblia", "biblico", "bíblico",
}

DEFAULT_LOBE_WEIGHTS = {
    "audience_resonance": 0.25,
    "retention_satisfaction": 0.20,
    "trend_momentum": 0.16,
    "outlier_similarity": 0.14,
    "novelty": 0.11,
    "channel_fit": 0.09,
    "market_opportunity": 0.05,
}


@dataclass(frozen=True)
class NPUDecision:
    score: float
    confidence: float
    probability_mass: float
    lobes: dict[str, float]
    reasons: list[str]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-záéíóúüñ0-9]+", str(text or "").lower())
    return {token for token in raw if len(token) >= 3 and token not in _STOPWORDS}


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    left, right = set(a), set(b)
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_brain_state(path: Path | str = DEFAULT_BRAIN) -> dict[str, Any]:
    return _read_json(Path(path))


def _softmax(values: list[float], temperature: float = 10.0) -> list[float]:
    if not values:
        return []
    temp = max(0.5, float(temperature))
    peak = max(values)
    exps = [math.exp((value - peak) / temp) for value in values]
    total = sum(exps) or 1.0
    return [value / total for value in exps]


def _entropy_confidence(probabilities: list[float]) -> float:
    if len(probabilities) <= 1:
        return 100.0
    entropy = -sum(p * math.log(max(p, 1e-12)) for p in probabilities)
    max_entropy = math.log(len(probabilities))
    return _clamp((1.0 - entropy / max_entropy) * 100.0)


def _mean(rows: Iterable[float], fallback: float = 50.0) -> float:
    values = [float(x) for x in rows]
    return sum(values) / len(values) if values else fallback


def _growth_keyword_map(profile: dict[str, Any]) -> dict[str, float]:
    return {
        str(row.get("key") or "").lower(): _safe_float(row.get("mean_score"), 50.0)
        for row in profile.get("keyword_weights") or []
        if row.get("key")
    }


def _niche_keyword_map(radar: dict[str, Any]) -> dict[str, float]:
    return {
        str(row.get("key") or "").lower(): _safe_float(row.get("mean_score"), 50.0)
        for row in radar.get("keyword_weights") or []
        if row.get("key")
    }


def _market_keyword_map(radar: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, list[float]] = {}
    for niche in radar.get("niches") or []:
        score = _safe_float(niche.get("opportunity_score"), 50.0)
        text = f"{niche.get('niche', '')} {niche.get('query', '')} {' '.join(niche.get('keywords') or [])}"
        for token in _tokens(text):
            weights.setdefault(token, []).append(score)
    return {key: _mean(values) for key, values in weights.items()}


def build_brain_state(
    growth_profile: dict[str, Any],
    *,
    niche_radar: dict[str, Any] | None = None,
    market_radar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    niche_radar = niche_radar or _read_json(DEFAULT_NICHE_RADAR)
    market_radar = market_radar or _read_json(DEFAULT_MARKET_RADAR)

    quality = growth_profile.get("data_quality") or {}
    videos_scored = int(quality.get("videos_scored") or 0)
    analytics_ok = bool(quality.get("analytics_api_available"))
    warnings = list(quality.get("warnings") or [])
    outliers = list(growth_profile.get("top_outliers") or [])

    # Dynamic weights: if first-party analytics are healthy, audience/retention
    # dominate. When data are sparse, the engine explores more but never lets
    # external trends dominate channel fit.
    weights = dict(DEFAULT_LOBE_WEIGHTS)
    if analytics_ok and videos_scored >= 20:
        weights["audience_resonance"] += 0.03
        weights["retention_satisfaction"] += 0.03
        weights["market_opportunity"] -= 0.02
        weights["trend_momentum"] -= 0.02
        weights["novelty"] -= 0.02
    elif videos_scored < 10:
        weights["novelty"] += 0.04
        weights["trend_momentum"] += 0.03
        weights["audience_resonance"] -= 0.04
        weights["retention_satisfaction"] -= 0.03

    total = sum(max(0.0, value) for value in weights.values()) or 1.0
    weights = {key: round(max(0.0, value) / total, 4) for key, value in weights.items()}

    top_market = sorted(
        list(market_radar.get("niches") or []),
        key=lambda row: _safe_float(row.get("opportunity_score")),
        reverse=True,
    )[:12]

    confidence = 25.0
    confidence += min(35.0, videos_scored * 1.2)
    confidence += 15.0 if analytics_ok else 0.0
    confidence += min(12.0, len(outliers) * 0.8)
    confidence -= min(20.0, len(warnings) * 3.0)
    confidence = _clamp(confidence)

    return {
        "version": BRAIN_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "architecture": {
            "type": "multi-cortex ensemble with quantum-inspired softmax exploration",
            "literal_consciousness": False,
            "literal_quantum_hardware": False,
            "fail_open": True,
            "publishing_must_continue": True,
            "no_viral_guarantee": True,
        },
        "weights": weights,
        "brain_confidence": round(confidence, 2),
        "data_quality": {
            "videos_scored": videos_scored,
            "analytics_api_available": analytics_ok,
            "warnings": warnings[-8:],
            "niche_radar_available": bool(niche_radar),
            "market_radar_available": bool(market_radar),
        },
        "memory": {
            "top_outliers": outliers[:20],
            "reference_weights": list(growth_profile.get("reference_weights") or [])[:30],
            "family_weights": list(growth_profile.get("family_weights") or [])[:30],
            "keyword_weights": list(growth_profile.get("keyword_weights") or [])[:50],
            "niche_keyword_weights": list(niche_radar.get("keyword_weights") or [])[:50],
            "market_niches": top_market,
        },
        "decision_policy": {
            "first_party_data_priority": True,
            "external_market_max_weight": 0.05,
            "channel_fit_guard": True,
            "novelty_guard": True,
            "exploration_rate": 0.20,
            "truthful_probability_language": True,
        },
    }


def _reference_score(reference: str, state: dict[str, Any]) -> float:
    rows = state.get("memory", {}).get("reference_weights") or []
    mapping = {str(row.get("key") or ""): _safe_float(row.get("mean_score"), 50.0) for row in rows}
    return _clamp(mapping.get(reference, 50.0))


def _keyword_affinity(tokens: set[str], mapping: dict[str, float], neutral: float = 50.0) -> float:
    hits = [mapping[token] for token in tokens if token in mapping]
    return _clamp(_mean(hits, neutral))


def _outlier_similarity(theme_text: str, state: dict[str, Any]) -> tuple[float, str]:
    theme_tokens = _tokens(theme_text)
    best = 0.0
    best_title = ""
    for row in state.get("memory", {}).get("top_outliers") or []:
        row_tokens = _tokens(
            f"{row.get('title', '')} {row.get('content_family', '')} {row.get('bible_reference', '')}"
        )
        similarity = _jaccard(theme_tokens, row_tokens)
        strength = _safe_float(row.get("growth_score"), 50.0)
        outlier = min(3.0, max(0.0, _safe_float(row.get("outlier_ratio"), 1.0))) / 3.0
        score = similarity * (0.75 * strength + 25.0 * outlier)
        if score > best:
            best = score
            best_title = str(row.get("title") or "")
    return _clamp(best), best_title


def _novelty_score(reference: str, family: str, previous: list[dict[str, Any]]) -> float:
    recent = [row for row in previous if row.get("status") == "uploaded"][-25:]
    family_tokens = _tokens(family)
    same_ref = sum(1 for row in recent if str(row.get("bible_reference") or "") == reference)
    similarity = 0.0
    for row in recent:
        old_tokens = _tokens(str(row.get("content_family") or row.get("topic") or ""))
        similarity = max(similarity, _jaccard(family_tokens, old_tokens))
    return _clamp(100.0 - same_ref * 14.0 - similarity * 45.0)


def _channel_fit(reference: str, family: str, truth: str, practice: str) -> float:
    text = f"{reference} {family} {truth} {practice}".lower()
    biblical = bool(reference.strip())
    faith_terms = sum(term in text for term in ("dios", "jes", "salmo", "oraci", "bib", "fe", "esper", "miseric"))
    return _clamp((65.0 if biblical else 30.0) + min(35.0, faith_terms * 7.0))


def score_theme(
    theme: tuple[str, str, str, str],
    previous: list[dict[str, Any]],
    *,
    state: dict[str, Any] | None = None,
) -> NPUDecision:
    state = state or load_brain_state()
    if not state:
        return NPUDecision(
            score=50.0,
            confidence=10.0,
            probability_mass=0.0,
            lobes={"neutral_fallback": 50.0},
            reasons=["NPU sin memoria todavía: selector base debe continuar"],
        )

    family, reference, truth, practice = theme
    theme_text = " ".join(theme)
    tokens = _tokens(theme_text)
    memory = state.get("memory") or {}

    growth_keywords = {
        str(row.get("key") or "").lower(): _safe_float(row.get("mean_score"), 50.0)
        for row in memory.get("keyword_weights") or [] if row.get("key")
    }
    niche_keywords = {
        str(row.get("key") or "").lower(): _safe_float(row.get("mean_score"), 50.0)
        for row in memory.get("niche_keyword_weights") or [] if row.get("key")
    }
    market_mapping = _market_keyword_map({"niches": memory.get("market_niches") or []})

    ref_score = _reference_score(reference, state)
    keyword_score = _keyword_affinity(tokens, growth_keywords)
    audience = _clamp(0.58 * ref_score + 0.42 * keyword_score)

    outlier, nearest = _outlier_similarity(theme_text, state)
    trend = _keyword_affinity(tokens, niche_keywords)
    market = _keyword_affinity(tokens, market_mapping)
    novelty = _novelty_score(reference, family, previous)
    fit = _channel_fit(reference, family, truth, practice)

    # Retention/satisfaction is inferred only from first-party winners and never
    # fabricated as a raw metric for a new idea.
    top = memory.get("top_outliers") or []
    retention_proxy = _mean(
        [
            0.55 * _safe_float(row.get("engagement"), 50.0)
            + 0.45 * _safe_float(row.get("satisfaction"), 50.0)
            for row in top[:12]
        ],
        50.0,
    )
    retention_satisfaction = _clamp(0.55 * audience + 0.45 * retention_proxy)

    lobes = {
        "audience_resonance": round(audience, 2),
        "retention_satisfaction": round(retention_satisfaction, 2),
        "trend_momentum": round(trend, 2),
        "outlier_similarity": round(outlier, 2),
        "novelty": round(novelty, 2),
        "channel_fit": round(fit, 2),
        "market_opportunity": round(market, 2),
    }
    weights = dict(DEFAULT_LOBE_WEIGHTS)
    weights.update({k: _safe_float(v) for k, v in (state.get("weights") or {}).items()})
    total_weight = sum(max(0.0, weights.get(key, 0.0)) for key in lobes) or 1.0
    score = sum(lobes[key] * max(0.0, weights.get(key, 0.0)) for key in lobes) / total_weight

    lobe_values = list(lobes.values())
    disagreement = statistics.pstdev(lobe_values) if len(lobe_values) > 1 else 0.0
    base_confidence = _safe_float(state.get("brain_confidence"), 25.0)
    confidence = _clamp(base_confidence - disagreement * 0.45 + (8.0 if fit >= 80 else 0.0))

    reasons = [
        f"audiencia={audience:.1f}",
        f"tendencia={trend:.1f}",
        f"novedad={novelty:.1f}",
        f"encaje_canal={fit:.1f}",
    ]
    if nearest:
        reasons.append(f"outlier parecido: {nearest[:70]}")

    return NPUDecision(
        score=round(_clamp(score), 2),
        confidence=round(confidence, 2),
        probability_mass=0.0,
        lobes=lobes,
        reasons=reasons[:6],
    )


def rerank_themes(
    themes: list[tuple[str, str, str, str]] | tuple[tuple[str, str, str, str], ...],
    previous: list[dict[str, Any]],
    seed: int,
    baseline_ranked: list[tuple[int, float, list[str]]],
    *,
    state: dict[str, Any] | None = None,
) -> list[tuple[int, float, list[str]]]:
    state = state or load_brain_state()
    if not state:
        return baseline_ranked

    baseline_map = {index: (float(score), list(reasons)) for index, score, reasons in baseline_ranked}
    rows: list[tuple[int, float, list[str], NPUDecision]] = []
    for index, theme in enumerate(themes):
        decision = score_theme(theme, previous, state=state)
        base_score, base_reasons = baseline_map.get(index, (50.0, []))
        # First-party Growth Engine remains the anchor; the NPU is a meta-model,
        # not an override. Channel-fit below 60 is strongly suppressed.
        combined = 0.55 * base_score + 0.45 * decision.score
        if decision.lobes.get("channel_fit", 0.0) < 60.0:
            combined -= 20.0
        tiny_tie = ((seed ^ (index * 2246822519)) & 0xFFFF) / 65535.0 * 0.01
        rows.append((index, _clamp(combined + tiny_tie), base_reasons, decision))

    # Quantum-inspired probability amplitudes. This is classical softmax math,
    # used only as an exploration heuristic and never described as quantum hardware.
    probabilities = _softmax([row[1] for row in rows], temperature=8.0)
    entropy_conf = _entropy_confidence(probabilities)
    output: list[tuple[int, float, list[str]]] = []
    for row, probability in zip(rows, probabilities):
        index, combined, base_reasons, decision = row
        effective_conf = 0.75 * decision.confidence + 0.25 * entropy_conf
        reasons = list(base_reasons[:2]) + decision.reasons[:3] + [
            f"NPU={decision.score:.1f}",
            f"confianza={effective_conf:.1f}%",
            f"amplitud={probability:.3f}",
        ]
        output.append((index, round(combined, 2), reasons[:7]))
    output.sort(key=lambda item: item[1], reverse=True)
    return output
