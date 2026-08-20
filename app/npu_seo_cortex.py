from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

SEO_VERSION = "npu-seo-cortex-v1"

_STOPWORDS = {
    "a", "al", "algo", "ante", "como", "con", "cuando", "de", "del", "dios", "el", "en",
    "es", "esta", "este", "fe", "hoy", "la", "las", "lo", "los", "más", "mi", "para", "por",
    "que", "se", "si", "sin", "su", "te", "tu", "un", "una", "y", "ya", "jesus", "jesús",
    "short", "shorts", "video", "vídeo",
}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-záéíóúüñ0-9]+", str(text or "").lower())
    return [token for token in raw if len(token) >= 3 and token not in _STOPWORDS]


def _ngrams(tokens: list[str]) -> set[str]:
    out = set(tokens)
    for i in range(len(tokens) - 1):
        out.add(tokens[i] + " " + tokens[i + 1])
    return out


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _bucket_title_length(title: str) -> str:
    n = len(str(title or "").strip())
    if n < 35:
        return "short_lt35"
    if n <= 60:
        return "compact_35_60"
    if n <= 80:
        return "medium_61_80"
    return "long_gt80"


def _weighted_mean(rows: list[tuple[float, float]], fallback: float = 50.0) -> float:
    if not rows:
        return fallback
    total_weight = sum(max(0.01, w) for _, w in rows)
    return sum(value * max(0.01, weight) for value, weight in rows) / total_weight


def build_seo_profile(
    growth_profile: dict[str, Any],
    *,
    niche_radar: dict[str, Any] | None = None,
    market_radar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Learn discoverability patterns without pretending tags/SEO guarantee recommendation.

    First-party performance remains the dominant evidence. External trend terms are
    shrunk aggressively and only the faith-Christian market slice is allowed to
    influence this channel's SEO memory.
    """
    niche_radar = niche_radar or {}
    market_radar = market_radar or {}
    outliers = list(growth_profile.get("top_outliers") or [])

    keyword_rows: dict[str, list[tuple[float, float]]] = defaultdict(list)
    title_buckets: dict[str, list[float]] = defaultdict(list)
    structure_rows: dict[str, list[float]] = defaultdict(list)

    for row in outliers[:40]:
        title = str(row.get("title") or "").strip()
        family = str(row.get("content_family") or "")
        reference = str(row.get("bible_reference") or "")
        score = _clamp(_safe_float(row.get("growth_score"), 50.0))
        outlier_ratio = max(0.1, _safe_float(row.get("outlier_ratio"), 1.0))
        evidence_weight = min(3.0, 0.6 + outlier_ratio)

        for token in _ngrams(_tokens(f"{title} {family} {reference}")):
            keyword_rows[token].append((score, evidence_weight))

        title_buckets[_bucket_title_length(title)].append(score)
        structure_rows["question" if "?" in title or "¿" in title else "statement"].append(score)
        structure_rows["has_reference" if reference and reference.lower() in title.lower() else "reference_not_in_title"].append(score)
        structure_rows["has_separator" if "|" in title or ":" in title or "—" in title else "no_separator"].append(score)

    # Existing niche radar is allowed to nudge keyword discovery, but at a much
    # lower evidence weight than first-party channel performance.
    for row in (niche_radar.get("keyword_weights") or [])[:40]:
        key = str(row.get("key") or "").strip().lower()
        if not key:
            continue
        external_score = _clamp(_safe_float(row.get("mean_score"), 50.0))
        keyword_rows[key].append((50.0 + (external_score - 50.0) * 0.20, 0.20))

    # Broad market data must not make a Christian channel chase unrelated niches.
    for niche in market_radar.get("niches") or []:
        if str(niche.get("niche") or "") != "fe_cristiana":
            continue
        opportunity = _clamp(_safe_float(niche.get("opportunity_score"), 50.0))
        shrunk = 50.0 + (opportunity - 50.0) * 0.10
        text = f"{niche.get('query', '')} {' '.join(niche.get('keywords') or [])}"
        for token in _ngrams(_tokens(text)):
            keyword_rows[token].append((shrunk, 0.10))

    keywords = []
    for key, evidence in keyword_rows.items():
        score = _clamp(_weighted_mean(evidence))
        keywords.append({
            "key": key,
            "seo_score": round(score, 2),
            "evidence_points": len(evidence),
        })
    keywords.sort(key=lambda row: (float(row["seo_score"]), int(row["evidence_points"])), reverse=True)

    title_lengths = [
        {"bucket": key, "mean_growth_score": round(sum(values) / len(values), 2), "samples": len(values)}
        for key, values in title_buckets.items() if values
    ]
    title_lengths.sort(key=lambda row: (float(row["mean_growth_score"]), int(row["samples"])), reverse=True)

    structures = [
        {"pattern": key, "mean_growth_score": round(sum(values) / len(values), 2), "samples": len(values)}
        for key, values in structure_rows.items() if values
    ]
    structures.sort(key=lambda row: (float(row["mean_growth_score"]), int(row["samples"])), reverse=True)

    sample_count = len(outliers)
    confidence = _clamp(20.0 + min(65.0, sample_count * 2.0) + (10.0 if growth_profile.get("data_quality", {}).get("analytics_api_available") else 0.0))

    return {
        "version": SEO_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "first_party_priority": True,
            "external_signal_max_weight": 0.20,
            "faith_channel_guard": True,
            "tags_are_not_a_viral_guarantee": True,
            "optimize_for_relevance_and_audience_response": True,
        },
        "confidence": round(confidence, 2),
        "videos_learned": sample_count,
        "keyword_weights": keywords[:80],
        "title_length_patterns": title_lengths,
        "title_structure_patterns": structures,
    }


def blend_growth_with_seo(growth_profile: dict[str, Any], seo_profile: dict[str, Any]) -> dict[str, Any]:
    """Blend SEO learned terms into Growth keywords, capped so SEO cannot dominate."""
    if not seo_profile:
        return growth_profile
    out = dict(growth_profile)
    existing = {
        str(row.get("key") or "").lower(): dict(row)
        for row in growth_profile.get("keyword_weights") or []
        if row.get("key")
    }
    for seo in seo_profile.get("keyword_weights") or []:
        key = str(seo.get("key") or "").strip().lower()
        if not key:
            continue
        seo_score = _clamp(_safe_float(seo.get("seo_score"), 50.0))
        if key in existing:
            old = _clamp(_safe_float(existing[key].get("mean_score"), 50.0))
            existing[key]["mean_score"] = round(0.85 * old + 0.15 * seo_score, 2)
            existing[key]["seo_supported"] = True
        else:
            existing[key] = {
                "key": key,
                "samples": 0,
                "mean_score": round(50.0 + (seo_score - 50.0) * 0.12, 2),
                "best_score": round(seo_score, 2),
                "seo_only": True,
            }
    merged = list(existing.values())
    merged.sort(key=lambda row: (float(row.get("mean_score") or 0), int(row.get("samples") or 0)), reverse=True)
    out["keyword_weights"] = merged[:80]
    out["seo_cortex"] = {
        "version": seo_profile.get("version"),
        "generated_at": seo_profile.get("generated_at"),
        "confidence": seo_profile.get("confidence"),
        "weight_in_growth_keywords": 0.15,
    }
    return out
