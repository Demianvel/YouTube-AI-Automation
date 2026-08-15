from __future__ import annotations

import re


def validate_spiritual_visual_diversity(provider_labels: list[str] | None) -> dict:
    """Block uploads that would mostly recycle the tiny emergency image set."""
    labels = [str(x or "").strip() for x in (provider_labels or []) if str(x or "").strip()]
    if not labels:
        raise RuntimeError("BLOQUEADO ANTI-SPAM VISUAL: no hay trazabilidad de las fuentes visuales.")

    local = [x for x in labels if "local_proven_photoreal_reference/" in x]
    local_names: set[str] = set()
    for label in local:
        match = re.search(r"local_proven_photoreal_reference/([^ +]+)", label)
        if match:
            local_names.add(match.group(1))

    ratio = len(local) / len(labels)
    # One or two emergency shots are acceptable inside a genuinely varied
    # production. A video dominated by the same tiny local reference library is
    # intentionally rejected rather than mass-published with minimal changes.
    if len(labels) >= 4 and ratio > 0.60 and len(local_names) < 4:
        raise RuntimeError(
            "BLOQUEADO ANTI-SPAM VISUAL: demasiadas escenas dependen de las mismas referencias locales "
            f"({len(local)}/{len(labels)}, {len(local_names)} imagenes base unicas). "
            "Se reintentara cuando haya generacion visual suficientemente diversa."
        )

    return {
        "visual_diversity_gate_passed": True,
        "visual_provider_count": len(labels),
        "local_reference_scene_count": len(local),
        "local_reference_ratio": round(ratio, 4),
        "unique_local_reference_count": len(local_names),
    }
