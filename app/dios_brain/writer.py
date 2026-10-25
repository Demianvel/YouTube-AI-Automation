"""Writer / SEO agent: script, title, description, hashtags and tags.

* Script: hook in the first 2 seconds (<= 7 words), one biblical idea, one
  practical step, a short prayer and a closing with the spoken CTA. Sentences
  are kept whole and the total fits the Voz de Luz word budget.
* Title: <= 70 chars, primary keyword first, honest (no clickbait).
* Description: first two lines = hook + keyword, short message, rotating CTA,
  verse reference, narrator disclosure. Hashtags 5 incl. #Shorts.
"""
from __future__ import annotations

import os
import re

from .pillars import PILLARS

HOOKS: dict[str, tuple[str, ...]] = {
    "paz": (
        "Si hoy te falta paz, escuchá.",
        "¿Tu mente no para? Respirá un momento.",
        "Esta paz también es para vos.",
        "Antes de seguir, respirá conmigo.",
    ),
    "amor": (
        "Nunca dudes de esto: sos amado.",
        "¿Te sentís solo? Escuchá esto.",
        "El amor de Dios no se cansa.",
        "Hoy necesitás recordar este amor.",
    ),
    "esperanza": (
        "No te rindas todavía. Escuchá.",
        "Todavía hay esperanza para vos.",
        "La noche no dura para siempre.",
        "Si estás cansado, esto es para vos.",
    ),
    "oracion": (
        "Hagamos juntos esta breve oración.",
        "¿No sabés cómo orar? Empezá así.",
        "Un minuto de oración para hoy.",
        "Cerrá los ojos y orá conmigo.",
    ),
    "promesas": (
        "Guardá esta promesa en tu corazón.",
        "Esta promesa bíblica es para hoy.",
        "Dios cumple lo que promete.",
        "Recordá esta promesa cuando dudes.",
    ),
    "jesus": (
        "Escuchá esta enseñanza de Jesús.",
        "Jesús enseñó algo para tu día.",
        "Esto que enseñó Jesús es para vos.",
        "Mirá lo que enseñó Jesús.",
    ),
}

BRIDGES: dict[str, tuple[str, ...]] = {
    "paz": ("La paz de Dios no exige que todo esté resuelto.", "La calma también se aprende de a un paso."),
    "amor": ("Su amor no depende de que hoy te salga todo bien.", "Ese amor se vuelve concreto en gestos pequeños."),
    "esperanza": ("La esperanza bíblica no niega el dolor, lo atraviesa.", "Un día difícil no es el final de tu historia."),
    "oracion": ("Orar no necesita palabras perfectas, solo un corazón sincero.", "La oración ordena el corazón antes que las circunstancias."),
    "promesas": ("Las promesas de Dios sostienen cuando las fuerzas no alcanzan.", "Confiar no es ignorar la realidad, es mirarla con fe."),
    "jesus": ("Jesús nunca usó el miedo para invitar a confiar.", "Sus palabras siguen hablando a lo que vivís hoy."),
}

PRAYERS: dict[str, tuple[str, ...]] = {
    "paz": ("Señor, calmá mi mente y llename de tu paz.",),
    "amor": ("Señor, enseñame a recibir y a dar tu amor.",),
    "esperanza": ("Señor, renová mi esperanza para este día.",),
    "oracion": ("Señor, acá estoy; escuchá mi corazón.",),
    "promesas": ("Señor, ayudame a confiar en tus promesas.",),
    "jesus": ("Jesús, enseñame a caminar como vos.",),
}

CLOSINGS: dict[str, str] = {
    "paz": "Que la paz de Dios te acompañe hoy. Amén.",
    "amor": "Que el amor de Dios te abrace hoy. Amén.",
    "esperanza": "Que Dios sostenga tu esperanza hoy. Amén.",
    "oracion": "Que Dios escuche tu oración. Amén.",
    "promesas": "Dios sigue caminando con vos. Amén.",
    "jesus": "Que Jesús guíe tu próximo paso. Amén.",
}

EXTRAS: tuple[str, ...] = (
    "Respirá despacio y dejá que esta verdad te acompañe.",
    "No estás solo en este camino.",
    "Dios conoce lo que llevás en el corazón.",
)

TITLE_TEMPLATES: dict[str, str] = {
    "kw_angle_ref": "{kw}: {angle} | {ref}",
    "kw_hoy_angle": "{kw} para hoy: {angle}",
    "kw_en_ref": "{kw} en {ref}: {angle}",
}
# Fallback template ids (used only when the angle does not fit the main ones):
# kw_angle, kw_ref, kw_ref_short.
TITLE_ORDER = tuple(TITLE_TEMPLATES)
MAX_TITLE = 70


def _clean(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _cap(text: str) -> str:
    text = _clean(text)
    return text[:1].upper() + text[1:] if text else text


_PROPER_START = ("Dios", "Jesús", "Jesus", "Cristo", "Señor", "Él", "Espíritu", "Pedro", "Pablo", "Moisés", "Israel", "Zaqueo")


def _low_first(text: str) -> str:
    text = _clean(text)
    if any(text == name or text.startswith(name + " ") or text.startswith(name + ",") for name in _PROPER_START):
        return text
    if len(text) > 1 and text[1:2].islower():
        return text[:1].lower() + text[1:]
    return text


def _sentence(text: str) -> str:
    text = _clean(text).rstrip(" ,;:")
    return text if not text or text[-1] in ".!?" else text + "."


def _words(text: str) -> int:
    return len(_clean(text).split())


def word_budget(target_seconds: float) -> tuple[int, int]:
    try:
        from app.spiritual_audio import narration_word_budget

        return narration_word_budget(target_seconds)
    except Exception:
        try:
            wpm = float(os.getenv("DIOS_NARRATION_WPM", "126"))
        except ValueError:
            wpm = 126.0
        max_words = max(36, int(max(8.0, float(target_seconds)) * wpm / 60.0))
        return max_words, max(32, int(round(max_words * 0.93)))


def choose_hook(pillar: str, previous: list[dict], seed: int, offset: int = 0) -> tuple[str, str]:
    hooks = HOOKS[pillar]
    used = [str(row.get("brain_hook_id") or "") for row in (previous or [])[-8:]]
    for step in range(len(hooks)):
        index = (seed + offset + step) % len(hooks)
        hook_id = f"{pillar}:{index}"
        if hook_id not in used:
            return hook_id, hooks[index]
    index = (seed + offset) % len(hooks)
    return f"{pillar}:{index}", hooks[index]


def build_script(theme: dict, pillar: str, hook: str, cta_spoken: str, seed: int, count: int, budget: tuple[int, int]) -> list[str]:
    max_words, min_words = budget
    ref = _clean(theme.get("reference"))
    angle = _clean(theme.get("angle"))
    truth_long = _sentence(_cap(theme.get("truth")))
    context_long = _sentence(f"En {ref}, {_low_first(theme.get('context'))}")
    practice_long = _sentence(f"Un paso concreto: {_low_first(theme.get('practice'))}")
    slots = {
        "open": [f"{hook} {truth_long}", f"{hook} {_sentence(_cap(angle))}"],
        "context": [context_long, _sentence(f"{ref} nos recuerda {_low_first(angle)}")],
        "bridge": [BRIDGES[pillar][seed % len(BRIDGES[pillar])], BRIDGES[pillar][(seed + 1) % len(BRIDGES[pillar])]],
        "practice": [practice_long, "Hoy podés dar un paso pequeño y fiel."],
        "prayer": [PRAYERS[pillar][seed % len(PRAYERS[pillar])]],
        "close": [f"{CLOSINGS[pillar]} {cta_spoken}".strip()],
    }
    choice = {key: 0 for key in slots}

    def render() -> list[str]:
        return [slots[key][choice[key]] for key in ("open", "context", "bridge", "practice", "prayer", "close")]

    # Shorten the longest shortenable slot until the budget fits (sentences stay whole).
    for _ in range(12):
        lines = render()
        if sum(_words(line) for line in lines) <= max_words:
            break
        options = [
            key for key in ("context", "open", "practice", "bridge")
            if choice[key] + 1 < len(slots[key]) and _words(slots[key][choice[key] + 1]) < _words(slots[key][choice[key]])
        ]
        if not options:
            break
        key = max(options, key=lambda k: _words(slots[k][choice[k]]))
        choice[key] += 1
    lines = render()

    extra_index = seed % len(EXTRAS)
    added = 0
    while sum(_words(line) for line in lines) < min_words and added < len(EXTRAS):
        lines[4] = f"{EXTRAS[(extra_index + added) % len(EXTRAS)]} {lines[4]}"
        added += 1

    # Map the six beats onto the configured number of scenes.
    if count == len(lines):
        return lines
    if count < len(lines):
        merged = lines[: count - 1] + [" ".join(lines[count - 1:])]
        return merged
    while len(lines) < count:
        lines.insert(-1, EXTRAS[(extra_index + len(lines)) % len(EXTRAS)])
    return lines


def _fit_title(text: str) -> str:
    return _clean(text).rstrip(" -|:,.!")


def title_candidates(theme: dict, pillar: str, seed: int) -> list[tuple[str, str]]:
    """Titles that fit 70 chars WITHOUT truncating the angle (no half sentences)."""
    kw = PILLARS[pillar]["keyword"]
    ref = _clean(theme.get("reference"))
    angle = _low_first(theme.get("angle"))
    result: list[tuple[str, str]] = []
    for step in range(len(TITLE_ORDER)):
        template_id = TITLE_ORDER[(seed + step) % len(TITLE_ORDER)]
        title = _fit_title(TITLE_TEMPLATES[template_id].format(kw=kw, angle=angle, ref=ref))
        if title and len(title) <= MAX_TITLE and title not in [t for _, t in result]:
            result.append((template_id, title))
    for template_id, raw in (("kw_angle", f"{kw}: {angle}"), ("kw_ref", f"{kw}: una reflexión sobre {ref}"), ("kw_ref_short", f"{kw} | {ref}")):
        title = _fit_title(raw)
        if len(result) >= 2:
            break
        if title and len(title) <= MAX_TITLE and title not in [t for _, t in result]:
            result.append((template_id, title))
    return result


def build_description(theme: dict, pillar: str, hook: str, cta_description: str) -> str:
    kw = PILLARS[pillar]["keyword"]
    ref = _clean(theme.get("reference"))
    angle = _low_first(theme.get("angle"))
    hook_line = _low_first(_clean(hook).rstrip("."))
    truth = _sentence(_cap(theme.get("truth")))
    practice = _sentence(f"Para hoy: {_low_first(theme.get('practice'))}")
    lines = [
        f"{kw}: {hook_line}.",
        f"Una reflexión breve sobre {ref}: {angle}.",
        "",
        truth,
        practice,
        "",
        cta_description,
        "",
        f"Versículo para leer: {ref}.",
        "Narración: «Voz de Luz», voz sintética del canal. No es la voz literal de Dios.",
    ]
    return "\n".join(lines).strip()[:4500]


def build_hashtags(pillar: str) -> list[str]:
    tags = [PILLARS[pillar]["hashtag"], "#Shorts", "#Dios", "#Jesus", "#Biblia"]
    result: list[str] = []
    for tag in tags:
        if tag.lower() not in {t.lower() for t in result}:
            result.append(tag)
    return result[:5]


def build_tags(theme: dict, pillar: str) -> list[str]:
    kw = PILLARS[pillar]["keyword"]
    ref = _clean(theme.get("reference"))
    raw = [kw, ref, f"{kw} para hoy", *PILLARS[pillar]["tags"], "reflexión cristiana", "mensaje cristiano para hoy"]
    result: list[str] = []
    for tag in raw:
        tag = _clean(tag)[:60]
        if tag and tag.lower() not in {t.lower() for t in result}:
            result.append(tag)
    return result[:9]
