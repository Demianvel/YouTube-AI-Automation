from __future__ import annotations

import hashlib
import os
import re
import unicodedata


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
    (r"daniel\s*6", "Daniel 6"),
    (r"daniel\s*7", "Daniel 7:13-14"),
    (r"mateo\s*3", "Mateo 3:13-17"),
    (r"mateo\s*5", "Mateo 5:1-12"),
    (r"mateo\s*6", "Mateo 6:25-34"),
    (r"mateo\s*10", "Mateo 10:29-31"),
    (r"mateo\s*11", "Mateo 11:28-30"),
    (r"mateo\s*21", "Mateo 21:1-11"),
    (r"mateo\s*24", "Mateo 24"),
    (r"marcos\s*4", "Marcos 4:35-41"),
    (r"lucas\s*15", "Lucas 15"),
    (r"juan\s*3", "Juan 3:16-17"),
    (r"juan\s*10", "Juan 10:1-18"),
    (r"juan\s*14", "Juan 14:27"),
    (r"g[eé]nesis\s*(6|7|8|9)", "Génesis 6-9"),
    (r"jon[aá]s\s*(1|2)", "Jonás 1-2"),
    (r"1\s*reyes\s*17", "1 Reyes 17:1-6"),
    (r"romanos\s*8\s*[:.,-]?\s*26", "Romanos 8:26-27"),
    (r"romanos\s*8\s*[:.,-]?\s*28", "Romanos 8:28"),
    (r"filipenses\s*4", "Filipenses 4:6-7"),
    (r"apocalipsis\s*21", "Apocalipsis 21:1-5"),
)

_TOPIC_REFERENCE_PATTERNS = (
    (r"(orar cuando no .*decir|sin palabras|gemidos|intercede por nosotros)", "Romanos 8:26-27"),
    (r"(ansiedad|preocupaci[oó]n|paz frente a la ansiedad)", "Filipenses 4:6-7"),
    (r"(cansad[oa]s? y cargad[oa]s?|descanso para el alma)", "Mateo 11:28-30"),
    (r"(no temer|miedo|dios fortalece|dios acompa[nñ]a)", "Isaías 41:10"),
    (r"(buen pastor|oveja perdida|oveja)", "Juan 10:1-18"),
    (r"(p[aá]jaros|aves|gorriones)", "Mateo 6:25-34"),
    (r"(no[eé].*animales|arca.*animales)", "Génesis 6-9"),
    (r"(foso de los leones|daniel.*leones)", "Daniel 6"),
    (r"(jon[aá]s.*pez|gran pez)", "Jonás 1-2"),
    (r"(el[ií]as.*cuervos|cuervos.*el[ií]as)", "1 Reyes 17:1-6"),
    (r"(pollino|entrada.*jerusal[eé]n)", "Mateo 21:1-11"),
)

_REAL_ENVIRONMENTS = (
    "a real green alpine valley at golden sunrise with a clear river and distant snow mountains",
    "a real Nordic mountain plateau beneath a vivid aurora borealis and natural stars",
    "a real desert of warm sandstone dunes at sunrise with wind moving fine sand",
    "a real Mediterranean olive grove at golden hour with leaves moving in a light breeze",
    "a real rocky shoreline at dawn with natural waves, sea spray and moving clouds",
    "a real high mountain ridge at sunset with layered valleys and realistic atmospheric haze",
    "a real forest clearing after rain with wet leaves, soft mist and sun rays through trees",
    "a real lakeside meadow with wildflowers, moving water and warm late-afternoon light",
    "a real snowy mountain pass with cold breath and wind moving fabric",
    "a real canyon riverbank with textured rock, flowing water and warm sunset light",
    "a real ancient stone path through olive trees under soft morning light",
    "a real wheat field moving in the wind beneath a luminous evening sky",
    "a real hillside overlooking a calm sea with distant fishing boats and sunrise haze",
    "a real quiet garden at dawn with dew, lilies and natural birds",
    "a real mountain waterfall surrounded by moss, mist and changing sunlight",
    "a real moonlit desert camp with a modest fire and a clear star field",
    "a real cedar forest with soft fog and shafts of light between tall trees",
    "a real lakeshore at blue hour with gentle ripples and distant mountains",
    "a real ancient village street built of stone in warm early-morning light",
    "a real cliff above a stormy sea where dark clouds slowly open to sunlight",
    "a real spring meadow beside a small wooden bridge and flowing stream",
    "a real cave entrance at sunrise with light entering the dark interior",
    "a real hill with an empty wooden cross silhouetted against a peaceful dawn",
    "a real quiet room lit by a window, an open Bible on a wooden table and dust in the light",
)

_VISUAL_BEATS = (
    "intimate medium close-up, the recurring synthetic Jesus character speaks calmly toward camera with soft blinks and subtle head motion",
    "full-body tracking shot, Jesus walks slowly along a path while one hand makes a natural reassuring gesture",
    "waist-up moving camera shot, Jesus extends an open hand toward the viewer with compassionate eye contact",
    "three-quarter shot, Jesus turns toward warm light and then looks back with a peaceful expression",
    "close-up live-action style shot focused on natural eyes, breathing, lips and a small reassuring nod",
    "wide cinematic shot, Jesus walks beside moving water while the robe and surrounding vegetation respond to wind",
    "medium shot, Jesus gently raises one hand while teaching and then lowers it naturally",
    "full-body dolly shot, Jesus approaches the camera through a realistic biblical landscape",
    "over-the-shoulder shot of Jesus looking across a valley before turning with calm attention",
    "side-profile shot of Jesus praying quietly while dawn light changes across the face",
    "medium two-plane composition with Jesus in focus and an open Bible visible in the foreground",
    "low-angle respectful shot of Jesus standing on a ridge as clouds move and sunlight breaks through",
    "seated medium shot, Jesus speaks beside an olive tree with relaxed hands and natural breathing",
    "walking side-tracking shot, Jesus carries a shepherd staff while a sheep follows naturally",
    "close-up of Jesus placing one hand over the heart with a calm compassionate expression",
    "wide shot of Jesus near a small boat on a peaceful lake with natural water movement",
    "gentle orbit shot around Jesus as he looks upward and then returns his gaze toward the viewer",
    "medium shot of Jesus opening an ancient scroll or Bible respectfully before continuing the reflection",
)

_DIVINE_MOTIFS = (
    "soft rays of natural light symbolize the presence and love of God without depicting God as a literal human figure",
    "an open Bible catches warm window light as pages move gently in a breeze",
    "a simple wooden cross appears in the distance under a peaceful dawn sky",
    "a white dove crosses the frame naturally as a respectful biblical symbol",
    "water reflects a bright opening in the clouds, suggesting hope and divine guidance",
    "a narrow stone path becomes illuminated ahead, symbolizing faith and direction",
    "an empty tomb entrance receives the first light of sunrise in a reverent non-graphic scene",
    "olive branches move softly around a small oil lamp and an open Scripture",
    "a shepherd staff and a calm sheep support the biblical message of care and guidance",
    "a quiet church interior receives natural colored light through simple windows",
    "hands hold an open Bible while sunlight forms a gentle glow across the page",
    "a distant gate of warm light appears beyond a real mountain path as a symbolic visual of hope",
)

_ANIMAL_VISUALS = (
    (r"buen pastor|oveja", "a photoreal living sheep calmly walks beside him with natural anatomy and gentle interaction"),
    (r"p[aá]jaros|aves|gorriones", "small photoreal wild birds fly and perch naturally nearby"),
    (r"no[eé]|arca", "a respectful group of photoreal animals appears in the background as a reference to Noah"),
    (r"leones", "photoreal lions remain calm at a safe distance as a symbolic reference to Daniel 6"),
    (r"jon[aá]s|gran pez", "a photoreal large fish appears in open water as a respectful biblical-story visualization"),
    (r"cuervos", "photoreal ravens fly through the scene with natural feather detail"),
    (r"pollino|jerusal[eé]n", "a photoreal gentle young donkey appears naturally as a reference to Matthew 21"),
    (r"paloma|bautismo", "a photoreal white dove flies through warm sunlight as a biblical symbol"),
    (r"animales|creaci[oó]n", "one or two photoreal animals appear peacefully with natural behavior"),
)

_TITLE_TEMPLATES = (
    "{topic} | Una verdad bíblica para hoy",
    "Cuando el corazón necesita descanso | {reference}",
    "La esperanza que permanece en medio de la prueba",
    "Dios no se ha olvidado de vos | {reference}",
    "Una luz para el momento que estás atravesando",
    "Lo que la Biblia enseña cuando todo parece detenido",
    "Jesús trae paz al corazón cansado | {reference}",
    "Una reflexión para volver a confiar en Dios",
    "Esta promesa bíblica puede sostener tu día | {reference}",
    "Fe para seguir caminando aun sin ver el resultado",
    "El silencio no significa ausencia | Reflexión cristiana",
    "Cuando necesitás fuerzas, recordá esta palabra | {reference}",
    "Dios obra también en los procesos que no entendemos",
    "Una oración breve para recuperar la serenidad",
    "Jesús conoce la carga que hoy llevás",
    "La paz de Dios en medio de la incertidumbre | {reference}",
    "No estás solo en esta etapa | Mensaje de fe",
    "Volver a empezar con esperanza y misericordia",
    "Una enseñanza de Jesús para transformar este día",
    "La Biblia y el valor de confiar paso a paso | {reference}",
)

_DESCRIPTION_OPENERS = (
    "Esta reflexión cristiana acompaña un momento de fe, calma y esperanza.",
    "Un mensaje bíblico original para respirar, ordenar el corazón y volver a confiar.",
    "Hoy meditamos en una enseñanza de la Biblia que invita a caminar con serenidad.",
    "Una pausa para escuchar la Palabra, renovar la fe y recordar el amor de Dios.",
    "Este mensaje une Biblia, oración y una aplicación práctica para la vida cotidiana.",
    "Una reflexión serena sobre Jesús, la esperanza y el cuidado de Dios.",
    "Cuando la mente se llena de preocupaciones, la Biblia puede ayudarnos a mirar de nuevo.",
    "Un espacio de paz para acercarnos a Dios con un corazón sincero.",
)

_HASHTAG_POOLS = {
    "prayer": ("#Oracion", "#OracionDeLaNoche", "#OracionDeLaMañana", "#DiosEscucha", "#PazInterior"),
    "hope": ("#Esperanza", "#ConfiaEnDios", "#DiosEsFiel", "#Fortaleza", "#NoEstasSolo"),
    "jesus": ("#Jesus", "#Jesucristo", "#PalabraDeJesus", "#CaminoVerdadYVida", "#Cristo"),
    "bible": ("#Biblia", "#PalabraDeDios", "#ReflexionBiblica", "#VersiculoDelDia", "#Evangelio"),
    "peace": ("#PazDeDios", "#Serenidad", "#DescansoEnDios", "#Fe", "#AmorDeDios"),
}


def _marker(metadata: dict) -> int:
    raw = "|".join([
        str(metadata.get("topic") or ""),
        str(metadata.get("content_family") or ""),
        os.getenv("GITHUB_RUN_ID", ""),
        os.getenv("GITHUB_RUN_NUMBER", ""),
    ])
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _reference(metadata: dict) -> str:
    topic_haystack = " ".join([
        _clean(metadata.get("topic", "")),
        _clean(metadata.get("content_family", "")),
    ]).lower()
    for pattern, reference in _TOPIC_REFERENCE_PATTERNS:
        if re.search(pattern, topic_haystack, flags=re.IGNORECASE):
            return reference

    full_haystack = " ".join([
        topic_haystack,
        _clean(metadata.get("description", "")),
        " ".join(_clean(scene.get("narration", "")) for scene in (metadata.get("scenes") or [])),
    ]).lower()
    for pattern, reference in _REFERENCE_PATTERNS:
        if re.search(pattern, full_haystack, flags=re.IGNORECASE):
            return reference
    return ""


def _animal_visual(metadata: dict) -> str:
    topic = " ".join([
        _clean(metadata.get("topic", "")),
        _clean(metadata.get("content_family", "")),
        _clean(metadata.get("description", "")),
    ]).lower()
    for pattern, visual in _ANIMAL_VISUALS:
        if re.search(pattern, topic, flags=re.IGNORECASE):
            return visual
    return ""


def _compact_topic(metadata: dict) -> str:
    topic = _clean(metadata.get("topic", "")) or _clean(metadata.get("content_family", ""))
    topic = re.sub(r"\([^)]{25,}\)", "", topic).strip(" -:,.!")
    return topic[:52].rstrip(" -:,.!") or "Fe, paz y esperanza"


def _truthful_title(metadata: dict, seed: int, previous: list[dict]) -> str:
    topic = _compact_topic(metadata)
    reference = _reference(metadata) or "la Biblia"
    recent = {_slug(item.get("title", "")) for item in previous[-30:] if item.get("title")}
    risky = ("dios te dice", "jesus te dice", "dios me revelo", "profecia para hoy", "mensaje urgente")

    candidates: list[str] = []
    for step in range(len(_TITLE_TEMPLATES)):
        template = _TITLE_TEMPLATES[(seed + step * 7) % len(_TITLE_TEMPLATES)]
        candidate = template.format(topic=topic, reference=reference)
        candidate = _clean(candidate)[:94].rstrip(" -:,.!")
        if any(term in _slug(candidate) for term in risky):
            continue
        candidates.append(candidate)
        if _slug(candidate) not in recent:
            return candidate

    # Deterministic final fallback keeps the topic and reference specific.
    return f"{topic} | {reference}"[:94].rstrip(" -:,.!")


def _description(metadata: dict, reference: str, seed: int) -> str:
    topic = _compact_topic(metadata)
    opener = _DESCRIPTION_OPENERS[seed % len(_DESCRIPTION_OPENERS)]
    application = (
        f"Tema: {topic}."
        if topic.lower() not in opener.lower()
        else ""
    )
    reference_line = f"Referencia bíblica para profundizar: {reference}." if reference else ""
    closing_variants = (
        "Escuchalo con calma y guardá la enseñanza que pueda ayudarte hoy.",
        "Que esta reflexión te ayude a caminar con más fe, amor y paciencia.",
        "Podés compartir tu intención de oración con respeto en los comentarios.",
        "Volvé a este mensaje cuando necesites recordar que la esperanza también se construye paso a paso.",
        "La fe no niega lo difícil: nos ayuda a atravesarlo acompañados por Dios.",
    )
    closing = closing_variants[(seed // 11) % len(closing_variants)]
    disclosure = (
        "La representación visual de Jesús es artística y generada digitalmente; "
        "no es una grabación literal de una persona o de un hecho divino."
    )
    parts = [x for x in (opener, application, reference_line, closing, disclosure) if x]
    return "\n\n".join(parts)[:4600].strip()


def _dynamic_hashtags(metadata: dict, seed: int) -> list[str]:
    haystack = _slug(" ".join([
        metadata.get("topic", ""), metadata.get("content_family", ""), metadata.get("bible_reference", "")
    ]))
    keys = ["bible", "peace"]
    if any(x in haystack for x in ("oracion", "orar", "noche", "manana")):
        keys.insert(0, "prayer")
    if any(x in haystack for x in ("esperanza", "miedo", "cansado", "prueba", "fortaleza")):
        keys.insert(0, "hope")
    if any(x in haystack for x in ("jesus", "cristo", "mesias", "evangelio")):
        keys.insert(0, "jesus")

    result = ["#Dios"]
    for offset, key in enumerate(keys):
        pool = _HASHTAG_POOLS[key]
        tag = pool[(seed + offset * 5) % len(pool)]
        if tag.lower() not in {x.lower() for x in result}:
            result.append(tag)
        if len(result) >= 5:
            break
    if "#Shorts" not in result:
        result.append("#Shorts")
    return result[:5]


def enforce_spiritual_metadata(metadata: dict, previous: list[dict] | None = None) -> dict:
    """Apply permanent Voz de Luz, anti-repeat editorial rules and broad visual rotation."""
    previous = previous or []
    seed = _marker(metadata)
    reference = _reference(metadata)
    animal_visual = _animal_visual(metadata)

    metadata["title"] = _truthful_title(metadata, seed, previous)
    metadata["bible_reference"] = reference
    metadata["description"] = _description(metadata, reference, seed)
    metadata["hashtags"] = _dynamic_hashtags(metadata, seed)
    metadata["synthetic_character_disclosure"] = True
    metadata["character_is_fictional_artistic_representation"] = True
    metadata["spiritual_quality_profile"] = "voz_de_luz_premium_visual_variety_v7"
    metadata["voice_profile"] = "voz_de_luz_serena_original_v1"
    metadata["voice_brand"] = "Voz de Luz"
    metadata["photoreal_human_required"] = True
    metadata["no_cartoon_no_3d_animation"] = True
    metadata["continuous_speech_requested"] = True
    metadata["lip_sync_requested"] = True
    metadata["full_body_motion_requested"] = True
    metadata["biblical_animal_visual_requested"] = bool(animal_visual)
    metadata["editorial_variety_seed"] = seed

    scenes = list(metadata.get("scenes") or [])
    beat_offset = seed % len(_VISUAL_BEATS)
    env_offset = (seed // 7) % len(_REAL_ENVIRONMENTS)
    motif_offset = (seed // 13) % len(_DIVINE_MOTIFS)
    used_combinations: set[tuple[int, int, int]] = set()

    for index, scene in enumerate(scenes):
        beat_i = (beat_offset + index * 5) % len(_VISUAL_BEATS)
        env_i = (env_offset + index * 7) % len(_REAL_ENVIRONMENTS)
        motif_i = (motif_offset + index * 3) % len(_DIVINE_MOTIFS)
        combo = (beat_i, env_i, motif_i)
        while combo in used_combinations:
            motif_i = (motif_i + 1) % len(_DIVINE_MOTIFS)
            combo = (beat_i, env_i, motif_i)
        used_combinations.add(combo)

        beat = _VISUAL_BEATS[beat_i]
        environment = _REAL_ENVIRONMENTS[env_i]
        motif = _DIVINE_MOTIFS[motif_i]
        original = _clean(scene.get("visual_prompt", ""))
        animal_part = f" {animal_visual}." if animal_visual and index % 2 == 0 else ""
        symbolic_cutaway = index % 3 == 2
        subject_rule = (
            "Use a reverent cinematic cutaway centered on God through biblical symbols, Scripture, light, creation or the cross; Jesus may appear in the middle or background but avoid another identical talking-head composition."
            if symbolic_cutaway else
            "Keep Jesus clearly visible as the principal subject with a different body position, camera distance and action from adjacent scenes."
        )
        scene["visual_prompt"] = (
            f"{beat}, filmed in {environment}. {motif}. {subject_rule}{animal_part} {original}. "
            "Recurring original synthetic Jesus identity when shown: adult Middle Eastern/Mediterranean-looking man, shoulder-length wavy dark-brown hair, full groomed brown beard, warm hazel-brown eyes, natural skin pores, ivory or cream linen robe and beige or muted-red mantle. "
            "Premium live-action cinema, realistic anatomy, five fingers, natural breathing, blinking, head turns, hand gestures, walking balance and fabric movement. "
            "Use a visibly different composition from every other scene in this video: vary close-up, medium, full-body, over-the-shoulder, side profile, wide landscape, Bible detail and symbolic divine-light cutaway. "
            "Photoreal skin, hair, fabric, animals and landscape; physically plausible light, water, clouds and depth of field. "
            "ABSOLUTELY NO cartoon, illustration, painting, anime, stylized 3D, game character, plastic CGI skin, frozen pose, malformed hands, text, subtitles, logo, watermark or celebrity likeness."
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
        scene["visual_variety_signature"] = f"b{beat_i}-e{env_i}-m{motif_i}"

    metadata["scenes"] = scenes
    metadata["visual_variety_signatures"] = [scene.get("visual_variety_signature") for scene in scenes]
    metadata["recent_titles_avoided"] = [
        _clean(item.get("title", "")) for item in previous[-12:] if _clean(item.get("title", ""))
    ][-8:]
    return metadata
