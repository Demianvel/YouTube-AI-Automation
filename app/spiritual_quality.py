from __future__ import annotations

import hashlib
import os
import re


_REFERENCE_PATTERNS = (
    (r"salmo\s*23", "Salmo 23"),
    (r"salmo\s*27", "Salmo 27"),
    (r"salmo\s*46", "Salmo 46"),
    (r"salmo\s*91", "Salmo 91"),
    (r"isa[ií]as\s*9", "Isaías 9"),
    (r"isa[ií]as\s*40", "Isaías 40:28-31"),
    (r"isa[ií]as\s*41", "Isaías 41:10"),
    (r"miqueas\s*5", "Miqueas 5:2"),
    (r"zacar[ií]as\s*9", "Zacarías 9:9"),
    (r"daniel\s*7", "Daniel 7:13-14"),
    (r"mateo\s*5", "Mateo 5:1-12"),
    (r"mateo\s*6", "Mateo 6:25-34"),
    (r"mateo\s*11", "Mateo 11:28-30"),
    (r"mateo\s*24", "Mateo 24"),
    (r"juan\s*3", "Juan 3:16-17"),
    (r"juan\s*14", "Juan 14"),
    (r"romanos\s*8\s*[:.,-]?\s*26", "Romanos 8:26-27"),
    (r"romanos\s*8\s*[:.,-]?\s*28", "Romanos 8:28"),
    (r"filipenses\s*4", "Filipenses 4:6-7"),
    (r"apocalipsis\s*21", "Apocalipsis 21:1-5"),
)

_TOPIC_REFERENCE_PATTERNS = (
    (
        r"(orar cuando no (sabes|sab[eé]s) qu[eé] decir|sin palabras|silencio en la oraci[oó]n|coraz[oó]n abrumado|gemidos|intercede por nosotros)",
        "Romanos 8:26-27",
    ),
    (r"(ansiedad|preocupaci[oó]n|orar en vez de preocuparse|paz frente a la ansiedad)", "Filipenses 4:6-7"),
    (r"(cansad[oa]s? y cargad[oa]s?|descanso para el alma|venir a jes[uú]s con las cargas)", "Mateo 11:28-30"),
    (r"(no temer|miedo|dios fortalece|dios acompa[nñ]a)", "Isaías 41:10"),
)

_VISUAL_BEATS = (
    "medium close-up, the recurring fictional Jesus character looks gently toward camera and speaks with subtle natural mouth and jaw movement, calm eye contact and one restrained hand gesture",
    "wide cinematic shot, the recurring fictional Jesus character walks slowly along a stone mountain path while speaking softly, robe moving in a light breeze, then turns toward camera",
    "lakeside medium shot, the recurring fictional Jesus character speaks calmly toward camera with small natural mouth movement and an open-palm gesture, water rippling behind him",
    "olive grove at golden hour, the recurring fictional Jesus character pauses, speaks with serene facial movement and gentle hand gestures, leaves moving naturally in the wind",
    "sunrise valley tracking shot, the recurring fictional Jesus character walks toward camera while speaking in a peaceful manner, soft rays changing through moving clouds",
    "quiet riverbank close-up, the recurring fictional Jesus character speaks with compassionate eye contact, subtle head movement and relaxed hand gesture, flowing water in background",
    "mountain overlook at sunset, the recurring fictional Jesus character speaks reflectively, briefly looks toward the horizon and returns his gaze to camera, mantle moving softly",
    "simple ancient-inspired courtyard, the recurring fictional Jesus character speaks naturally to camera with restrained gestures, warm sunlight and realistic fabric movement",
)

_TITLE_TEMPLATES = (
    "{topic}: una reflexión de fe para hoy",
    "Cuando el corazón necesita paz: {topic}",
    "Una palabra de esperanza basada en la Biblia: {topic}",
    "Fe para este momento: {topic}",
    "Una oración y reflexión sobre {topic}",
    "Biblia y esperanza: {topic}",
)


def _marker(metadata: dict) -> int:
    raw = "|".join(
        [
            str(metadata.get("topic") or ""),
            str(metadata.get("content_family") or ""),
            os.getenv("GITHUB_RUN_ID", ""),
            os.getenv("GITHUB_RUN_NUMBER", ""),
        ]
    )
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _reference(metadata: dict) -> str:
    topic_haystack = " ".join(
        [
            _clean(metadata.get("topic", "")),
            _clean(metadata.get("content_family", "")),
        ]
    ).lower()
    for pattern, reference in _TOPIC_REFERENCE_PATTERNS:
        if re.search(pattern, topic_haystack, flags=re.IGNORECASE):
            return reference

    full_haystack = " ".join(
        [
            topic_haystack,
            _clean(metadata.get("description", "")),
            " ".join(_clean(scene.get("narration", "")) for scene in (metadata.get("scenes") or [])),
        ]
    ).lower()
    for pattern, reference in _REFERENCE_PATTERNS:
        if re.search(pattern, full_haystack, flags=re.IGNORECASE):
            return reference
    return ""


def _truthful_title(metadata: dict, seed: int) -> str:
    title = _clean(metadata.get("title", ""))
    topic = _clean(metadata.get("topic", "")) or _clean(metadata.get("content_family", "")) or "fe y esperanza"

    risky = (
        "dios te dice",
        "jesus te dice",
        "dios me revelo",
        "profecia para hoy",
        "esto pasara hoy",
        "mensaje urgente de dios",
        "si ignoras esto",
    )
    generic = (
        not title
        or title.lower().startswith("un mensaje de fe para hoy")
        or any(term in title.lower() for term in risky)
    )
    if generic:
        template = _TITLE_TEMPLATES[seed % len(_TITLE_TEMPLATES)]
        title = template.format(topic=topic)
    return title[:90].rstrip(" -:,.!")


def _description(metadata: dict, reference: str) -> str:
    base = str(metadata.get("description") or "").strip()
    if not base:
        base = "Reflexión cristiana original sobre Biblia, fe, esperanza y oración."
    if reference and reference.lower() not in base.lower():
        base += f"\n\nReferencia bíblica para profundizar: {reference}."
    if "representación artística" not in base.lower() and "representacion artistica" not in base.lower():
        base += "\n\nLa imagen de Jesús es una representación artística ficticia generada para acompañar la reflexión."
    return base[:4600].strip()


def enforce_spiritual_metadata(metadata: dict, previous: list[dict] | None = None) -> dict:
    """Apply channel-specific quality, truthfulness and visual-variety rules."""
    previous = previous or []
    seed = _marker(metadata)
    reference = _reference(metadata)

    metadata["title"] = _truthful_title(metadata, seed)
    metadata["bible_reference"] = reference
    metadata["description"] = _description(metadata, reference)
    metadata["synthetic_character_disclosure"] = True
    metadata["character_is_fictional_artistic_representation"] = True
    metadata["spiritual_quality_profile"] = "premium_varied_truthful_v3"

    hashtags = [str(x).strip() for x in (metadata.get("hashtags") or []) if str(x).strip()]
    for tag in ("#Dios", "#Jesus", "#Biblia", "#Fe", "#Shorts"):
        if tag.lower() not in {x.lower() for x in hashtags}:
            hashtags.append(tag)
    metadata["hashtags"] = hashtags[:5]

    scenes = list(metadata.get("scenes") or [])
    offset = seed % len(_VISUAL_BEATS)
    for index, scene in enumerate(scenes):
        beat = _VISUAL_BEATS[(offset + index * 3) % len(_VISUAL_BEATS)]
        original = _clean(scene.get("visual_prompt", ""))
        scene["visual_prompt"] = (
            f"{beat}. {original}. Keep the same recurring fictional character identity, but make this camera angle, setting, gesture and physical action clearly different from the other scenes. "
            "Premium photoreal cinematic lighting, natural facial micro-expressions, no exaggerated lip motion, no text, no subtitles, no logo, no watermark, no celebrity likeness."
        )[:1500]
        narration = _clean(scene.get("narration", ""))
        replacements = {
            "Jesús te dice:": "El mensaje de Jesús en la Biblia nos recuerda:",
            "Jesus te dice:": "El mensaje de Jesús en la Biblia nos recuerda:",
            "Dios te dice:": "La Biblia nos recuerda sobre Dios:",
            "Dios me reveló": "Esta reflexión considera",
            "Dios me revelo": "Esta reflexión considera",
        }
        for old, new in replacements.items():
            narration = narration.replace(old, new)
        scene["narration"] = narration

    metadata["scenes"] = scenes
    recent_titles = [_clean(x.get("title", "")) for x in previous[-12:] if _clean(x.get("title", ""))]
    metadata["recent_titles_avoided"] = recent_titles[-6:]
    return metadata
