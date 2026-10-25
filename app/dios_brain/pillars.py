"""Faith-message pillars shared by every Dios Brain agent."""
from __future__ import annotations

import re
import unicodedata

PILLARS: dict[str, dict] = {
    "paz": {
        "label": "paz",
        "keyword": "Paz de Dios",
        "hashtag": "#PazDeDios",
        "markers": ("paz", "calma", "ansiedad", "descans", "quietud", "serenidad", "refugio", "silencio", "mente", "ruido", "tormenta"),
        "tags": ("paz de Dios", "paz interior", "ansiedad y fe", "descanso en Dios"),
    },
    "amor": {
        "label": "amor",
        "keyword": "Amor de Dios",
        "hashtag": "#AmorDeDios",
        "markers": ("amor", "compasi", "misericordia", "perdon", "projimo", "gracia", "conocido"),
        "tags": ("amor de Dios", "misericordia de Dios", "perdón y gracia", "amor al prójimo"),
    },
    "esperanza": {
        "label": "esperanza",
        "keyword": "Esperanza en Dios",
        "hashtag": "#Esperanza",
        "markers": ("esperanza", "animo", "amanecer", "levant", "persever", "noche", "nuevo", "cansancio", "presion"),
        "tags": ("esperanza en Dios", "palabra de aliento", "no te rindas", "fe en tiempos difíciles"),
    },
    "oracion": {
        "label": "oración",
        "keyword": "Oración",
        "hashtag": "#Oracion",
        "markers": ("oracion", "orar", "pedir", "clamar", "buscar", "llamar", "escucha", "invoc"),
        "tags": ("oración cristiana", "oración corta", "cómo orar", "oración de hoy"),
    },
    "promesas": {
        "label": "promesas de Dios",
        "keyword": "Promesa de Dios",
        "hashtag": "#PromesasDeDios",
        "markers": ("promesa", "presencia", "fortaleza", "fuerza", "ayuda", "cuidado", "seguridad", "delante", "confia", "raices"),
        "tags": ("promesas de Dios", "versículos de promesa", "Dios cumple", "confianza en Dios"),
    },
    "jesus": {
        "label": "enseñanzas de Jesús",
        "keyword": "Enseñanza de Jesús",
        "hashtag": "#Fe",
        "markers": ("jesus", "cristo", "pastor", "pedro", "olas", "discipul", "evangelio"),
        "tags": ("enseñanzas de Jesús", "palabras de Jesús", "Jesús hoy", "seguir a Jesús"),
    },
}

PILLAR_ORDER = tuple(PILLARS)


def normalize(value: object) -> str:
    text = " ".join(str(value or "").split()).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


def classify_text(text: object) -> str:
    """Return the pillar whose markers best match the text (ties keep PILLAR_ORDER)."""
    low = normalize(text)
    best, best_score = "esperanza", 0
    for name in PILLAR_ORDER:
        score = sum(low.count(marker) for marker in PILLARS[name]["markers"])
        if score > best_score:
            best, best_score = name, score
    return best


def classify_theme(theme: dict) -> str:
    # Family + angle are the editorial intent; truth/context only break ties.
    primary = classify_text(f"{theme.get('family', '')} {theme.get('angle', '')}")
    if any(m in normalize(f"{theme.get('family', '')} {theme.get('angle', '')}") for m in PILLARS[primary]["markers"]):
        return primary
    return classify_text(" ".join(str(theme.get(k, "")) for k in ("family", "angle", "truth", "context", "practice")))


def classify_row(row: dict) -> str:
    stored = str(row.get("brain_pillar") or "").strip()
    if stored in PILLARS:
        return stored
    return classify_text(f"{row.get('topic', '')} {row.get('title', '')}")
