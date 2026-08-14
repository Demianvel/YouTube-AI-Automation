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

_REAL_ENVIRONMENTS = (
    "a real green alpine valley at golden sunrise with a clear river and distant snow mountains",
    "a real Nordic mountain plateau beneath a vivid aurora borealis, cold night air and natural stars",
    "a real desert of warm sandstone dunes at sunrise with wind moving fine sand",
    "a real Mediterranean olive grove at golden hour with leaves moving in a light breeze",
    "a real rocky shoreline at dawn with natural waves, sea spray and moving clouds",
    "a real high mountain ridge at sunset with layered valleys and realistic atmospheric haze",
    "a real forest clearing after rain with wet leaves, soft mist and sun rays through trees",
    "a real lakeside meadow with wildflowers, moving water and warm late-afternoon light",
    "a real snowy mountain pass with cold breath, wind moving fabric and cinematic natural light",
    "a real canyon riverbank with textured rock, flowing water and warm sunset light",
)

_VISUAL_BEATS = (
    "medium close-up, the recurring photoreal synthetic Jesus character looks directly toward camera and speaks continuously with natural phoneme-like mouth and jaw articulation, soft blinks and subtle head motion",
    "full-body tracking shot, the recurring photoreal synthetic Jesus character walks slowly while speaking continuously, natural heel-to-toe steps, robe reacting to leg movement and wind, one calm hand gesture",
    "waist-up moving camera shot, the recurring photoreal synthetic Jesus character speaks continuously and extends one open hand toward the viewer, fingers and wrist moving naturally",
    "three-quarter full-body shot, the recurring photoreal synthetic Jesus character turns slightly, keeps speaking, moves both hands naturally and shifts body weight realistically",
    "close-up live-action style shot, the recurring photoreal synthetic Jesus character speaks continuously with realistic lips, cheeks, jaw, breathing and eye focus, then makes a small nod",
    "wide live-action shot, the recurring photoreal synthetic Jesus character walks through the landscape while speaking, arms and shoulders moving naturally with each step",
    "medium shot, the recurring photoreal synthetic Jesus character raises one hand gently while speaking, then lowers it naturally without breaking eye contact",
    "full-body cinematic dolly shot, the recurring photoreal synthetic Jesus character approaches the camera while speaking continuously, realistic legs, hands, robe folds and body balance",
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
        base += "\n\nLa figura de Jesús es una representación humana digital fotorrealista generada con IA para acompañar la reflexión; no es una grabación de una persona real."
    return base[:4600].strip()


def enforce_spiritual_metadata(metadata: dict, previous: list[dict] | None = None) -> dict:
    """Apply channel-specific quality, truthfulness and live-action visual rules."""
    previous = previous or []
    seed = _marker(metadata)
    reference = _reference(metadata)

    metadata["title"] = _truthful_title(metadata, seed)
    metadata["bible_reference"] = reference
    metadata["description"] = _description(metadata, reference)
    metadata["synthetic_character_disclosure"] = True
    metadata["character_is_fictional_artistic_representation"] = True
    metadata["spiritual_quality_profile"] = "premium_live_action_photoreal_v4"
    metadata["photoreal_human_required"] = True
    metadata["no_cartoon_no_3d_animation"] = True
    metadata["continuous_speech_requested"] = True
    metadata["lip_sync_requested"] = True
    metadata["full_body_motion_requested"] = True

    hashtags = [str(x).strip() for x in (metadata.get("hashtags") or []) if str(x).strip()]
    for tag in ("#Dios", "#Jesus", "#Biblia", "#Fe", "#Shorts"):
        if tag.lower() not in {x.lower() for x in hashtags}:
            hashtags.append(tag)
    metadata["hashtags"] = hashtags[:5]

    scenes = list(metadata.get("scenes") or [])
    offset = seed % len(_VISUAL_BEATS)
    env_offset = (seed // 7) % len(_REAL_ENVIRONMENTS)
    for index, scene in enumerate(scenes):
        beat = _VISUAL_BEATS[(offset + index * 3) % len(_VISUAL_BEATS)]
        environment = _REAL_ENVIRONMENTS[(env_offset + index * 2) % len(_REAL_ENVIRONMENTS)]
        original = _clean(scene.get("visual_prompt", ""))
        scene["visual_prompt"] = (
            f"{beat}, filmed in {environment}. {original}. SAME recurring face and body identity in every scene: adult Middle Eastern/Mediterranean-looking man, shoulder-length wavy dark-brown hair, full groomed brown beard, warm hazel-brown eyes, natural skin pores and fine facial hair, ivory or cream linen robe and beige mantle. "
            "The result must look like premium live-action cinema filmed with a real camera and a real human performer even though the person is fully synthetic AI. Realistic anatomy, five fingers on each hand, natural shoulders, elbows, wrists, hips, knees and walking balance. "
            "Continuous believable speech performance, realistic lip/jaw/cheek motion suitable for later audio lip-sync, natural breathing, blinking, head turns, hand gestures and full-body movement. "
            "Photoreal skin, photoreal hair strands, photoreal fabric weave, physically plausible sunlight, real landscape depth, natural depth of field and cinematic camera movement. "
            "ABSOLUTELY NO cartoon, no illustration, no painting, no anime, no stylized 3D, no game character, no plastic CGI skin, no doll face, no frozen pose, no duplicated fingers, no text, no subtitles, no logo, no watermark, no celebrity likeness."
        )[:1900]
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
