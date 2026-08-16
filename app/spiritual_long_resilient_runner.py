from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

from . import spiritual_long_pipeline as base
from . import spiritual_long_runner as enhanced
from .spiritual_long_local_metadata import generate_local_long_metadata
from .spiritual_source_growth_engine import ground_and_optimize_spiritual_metadata
from .spiritual_tts import make_spiritual_spanish_voice
from .workers.celestial_cinema_engine import mark_render_metadata, render_directive
from .workers.divine_publisher_4x10 import mark_publish_metadata
from .workers.peace_motion_director import apply_director_requirements, performance_directive


_LONG_ENVIRONMENTS = (
    "a real olive grove at dawn with moving leaves and warm natural light",
    "a real mountain lake at sunrise with mist and gentle water movement",
    "a real desert path under a vast golden sky with wind moving the robe",
    "a real Nordic valley beneath an aurora borealis and natural stars",
    "a real rocky coast where storm clouds slowly open to sunlight",
    "a real ancient stone village street in soft morning light",
    "a real cedar forest with mist and shafts of sunlight",
    "a real field of wheat moving beneath an evening sky",
    "a real quiet garden with lilies, dew and natural birds",
    "a real mountain ridge above layered valleys at sunset",
    "a real riverbank with textured stone and clear flowing water",
    "a real snowy pass with visible breath and fabric moving in the wind",
    "a real cave entrance receiving the first light of sunrise",
    "a real hillside overlooking a calm Mediterranean sea",
    "a real spring meadow beside a wooden bridge and stream",
    "a real moonlit desert camp with a modest fire and clear stars",
)

_LONG_VISUAL_MODES = (
    "intimate medium close-up with natural speech, breathing, blinking and compassionate eye contact",
    "full-body tracking shot of Jesus walking while the camera moves beside him",
    "wide landscape composition with Jesus small in frame, emphasizing creation and scale",
    "over-the-shoulder shot as Jesus looks across the landscape and then turns gently",
    "seated medium shot beside an olive tree with relaxed hands and natural posture",
    "side-profile prayer shot with changing natural light across the face",
    "waist-up teaching shot with one restrained open-hand gesture",
    "low-angle respectful full-body shot on a ridge with moving clouds",
    "slow orbit around Jesus as he walks near water and looks toward the viewer",
    "close detail of hands opening Scripture followed by a calm facial reaction",
    "three-quarter shot of Jesus helping or accompanying another non-identifiable synthetic person respectfully",
    "long-lens walking shot through a real biblical landscape with foreground depth",
)

_LONG_SYMBOLIC_CUTAWAYS = (
    "an open Bible on a wooden table illuminated by moving natural window light",
    "a simple wooden cross on a real hill at peaceful dawn",
    "an empty tomb entrance receiving warm sunrise light, reverent and non-graphic",
    "a white dove flying naturally through a shaft of sunlight",
    "a shepherd staff beside a calm sheep near living water",
    "an oil lamp among olive branches and an open Scripture",
    "sunlight opening through storm clouds and reflecting on water",
    "a narrow stone path becoming illuminated ahead as a symbol of hope",
    "hands holding an open Bible while pages move gently in the breeze",
    "a quiet church interior receiving soft natural colored light",
)

_LONG_TITLE_TEMPLATES = {
    "prayer": (
        "Oración para entregar tus cargas y volver a confiar | {topic}",
        "Hablemos con Dios: una oración de paz y fortaleza | {topic}",
        "Oración serena para renovar la fe | {topic}",
        "Un momento de oración para el corazón cansado | {topic}",
        "Oración para caminar con esperanza y sabiduría | {topic}",
    ),
    "night_prayer": (
        "Oración de la noche para descansar en la paz de Dios | {topic}",
        "Antes de dormir: entregá tus preocupaciones a Dios | {topic}",
        "Una oración nocturna de gratitud, descanso y esperanza | {topic}",
        "Descansá tu corazón en Dios esta noche | {topic}",
        "Oración para cerrar el día con serenidad | {topic}",
    ),
    "biblical_story": (
        "La historia bíblica de {topic}: contexto, enseñanza y esperanza",
        "{topic} | Una historia de la Biblia para comprender y aplicar",
        "Lo que enseña la historia de {topic}",
        "Una historia bíblica que todavía habla a nuestra vida | {topic}",
        "{topic}: relato bíblico, significado y reflexión",
    ),
    "biblical_reflection": (
        "{topic} | Reflexión bíblica profunda para la vida cotidiana",
        "Una enseñanza de la Biblia para volver a mirar el camino | {topic}",
        "Fe, paz y esperanza: lo que aprendemos de {topic}",
        "Cómo llevar esta enseñanza bíblica a la vida | {topic}",
        "{topic}: una reflexión para crecer en confianza y amor",
    ),
    "auto": (
        "{topic} | Biblia, reflexión y oración",
        "Una palabra de fe y esperanza para hoy | {topic}",
        "{topic}: enseñanza bíblica y aplicación para la vida",
        "Volver a confiar en Dios | Una reflexión sobre {topic}",
        "Un camino de fe, paz y amor | {topic}",
    ),
}

_LONG_DESCRIPTION_OPENERS = (
    "Este video cristiano original combina Biblia, reflexión y una aplicación serena para la vida cotidiana.",
    "Una experiencia de fe narrada con calma para escuchar, comprender y llevar la enseñanza a acciones concretas.",
    "Este recorrido bíblico busca ofrecer contexto, esperanza y un espacio respetuoso de oración.",
    "Un video para hacer una pausa, acercarnos a la Palabra y volver a confiar paso a paso.",
    "Una reflexión cristiana profunda, sin miedo ni promesas automáticas, centrada en Dios, Jesús y la Biblia.",
    "Acompañamos este tema con una narración serena, referencias bíblicas y escenas originales de gran variedad.",
)


def _service_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return any(token in text for token in (
        "429", "RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT", "503", "UNAVAILABLE", "HIGH DEMAND", "404 NOT_FOUND",
    ))


def _normalize(value: object) -> str:
    text = " ".join(str(value or "").split()).lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _seed(meta: dict, minutes: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"long-voz-de-luz|{meta.get('topic','')}|{minutes}|{marker}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16)


def _narration_style() -> str:
    value = os.getenv("SPIRITUAL_NARRATION_STYLE", "auto").strip().lower()
    return value if value in {"prayer", "night_prayer", "biblical_story", "biblical_reflection"} else "auto"


def _styled_metadata_prompt(channel: dict, minutes: int, sections: int, references: list[dict]) -> str:
    prompt = _ORIGINAL_METADATA_PROMPT(channel, minutes, sections, references)
    style = _narration_style()
    if style == "prayer":
        directive = """
FORMATO EDITORIAL OBLIGATORIO: ORACION GUIADA.
El video completo debe sentirse como una oracion cristiana continua, reverente y cercana, dirigida a Dios. Usa las referencias biblicas como fundamento y contexto, preferentemente parafraseadas. Alterna gratitud, entrega de cargas, peticion de sabiduria, fortaleza, paz, esperanza, perdon e intercesion. No conviertas la fe en promesas automaticas de salud, dinero o milagros. No reinicies la oracion en cada seccion: todas deben enlazarse como una sola plegaria. Reserva "Amen" para el cierre natural del contenido, antes del CTA final si lo hubiera.
"""
    elif style == "night_prayer":
        directive = """
FORMATO EDITORIAL OBLIGATORIO: ORACION NOCTURNA.
Crea una oracion continua para terminar el dia: descanso, gratitud, entrega de preocupaciones, perdon, proteccion entendida con prudencia biblica, paz interior y esperanza para el nuevo dia. Habla directamente a Dios de forma serena y humana. Las referencias biblicas deben sostener la oracion sin citas extensas ni promesas garantizadas. No reinicies la oracion en cada seccion y reserva "Amen" para el cierre natural del contenido, antes del CTA final si lo hubiera.
"""
    elif style == "biblical_story":
        directive = """
FORMATO EDITORIAL OBLIGATORIO: HISTORIA BIBLICA NARRADA.
Construye un relato biblico con contexto, personajes, conflicto, aprendizaje y significado espiritual. Diferencia claramente el texto biblico de la reflexion, no inventes hechos ni dialogos presentados como Escritura y termina con una breve aplicacion practica y una oracion natural. El interes debe nacer de la historia y su significado, nunca de miedo o sensacionalismo.
"""
    elif style == "biblical_reflection":
        directive = """
FORMATO EDITORIAL OBLIGATORIO: REFLEXION BIBLICA PROFUNDA.
Desarrolla una enseñanza biblica clara, contextual, esperanzadora y practica. Conecta cada seccion con la vida cotidiana y termina con un momento de oracion. Evita repeticiones, falsas promesas y afirmaciones profeticas sobre hechos actuales.
"""
    else:
        directive = """
FORMATO EDITORIAL: alterna de manera natural entre historia biblica, reflexion y oracion, siempre con referencias verificables y un cierre esperanzador.
"""
    diversity = """
DIVERSIDAD VISUAL Y EDITORIAL OBLIGATORIA:
- Ninguna seccion puede repetir el mismo encuadre, ambiente, gesto o accion de la anterior.
- Alterna Jesus hablando, caminando, enseñando, orando y acompañando, con planos abiertos de creacion y cortes simbolicos de Dios mediante Biblia, cruz, luz natural, paloma, agua, tumba vacia o camino iluminado.
- No representes a Dios Padre como un humano gigante ni como una cara en el cielo.
- Evita repetir formulas de titulo, aperturas de descripcion, frases de introduccion o llamados a comentar usados en videos recientes.
- Mantiene una narracion continua con la identidad original Voz de Luz: baritono masculino calido, sereno, claro, cercano y con autoridad suave.
"""
    return f"{prompt}\n\n{directive.strip()}\n\n{diversity.strip()}"


def _apply_style_metadata(meta: dict, minutes: int) -> dict:
    style = _narration_style()
    meta["narration_style"] = style
    meta["fixed_voice_identity"] = "Voz de Luz"
    meta["voice_profile"] = "voz_de_luz_serena_original_v1"
    meta["voice_reference_mode"] = "two_reference_style_blend_no_speaker_clone"
    if style in {"prayer", "night_prayer"}:
        night = style == "night_prayer"
        prefix = (
            "Señor, al terminar este día venimos ante ti con un corazón sincero, entregando nuestras cargas y buscando descanso en tu Palabra. "
            if night else
            "Señor, nos acercamos a ti con un corazón sincero, agradeciendo tu amor y poniendo delante de ti nuestras cargas, necesidades y esperanzas. "
        )
        sections = list(meta.get("sections") or [])
        if sections:
            first = " ".join(str(sections[0].get("narration") or "").split())
            if not first.lower().startswith(("señor", "senor", "padre", "dios")):
                sections[0]["narration"] = f"{prefix}{first}".strip()
            meta["sections"] = sections
        meta["description"] = (
            "Oración cristiana original basada en referencias bíblicas, con un mensaje de fe, paz, esperanza y confianza en Dios.\n\n"
            + str(meta.get("description") or "").strip()
        )[:4700]
    elif style == "biblical_story":
        meta["format_focus"] = "biblical_story_context_then_reflection_and_prayer"
    elif style == "biblical_reflection":
        meta["format_focus"] = "biblical_teaching_reflection_then_prayer"
    meta["target_minutes"] = minutes
    return meta


def _compact_topic(meta: dict) -> str:
    topic = " ".join(str(meta.get("topic") or "Fe, paz y esperanza").split())
    topic = re.sub(r"\([^)]{25,}\)", "", topic).strip(" -:,.!")
    return topic[:58].rstrip(" -:,.!") or "Fe, paz y esperanza"


def _unique_long_title(meta: dict, previous: list[dict], minutes: int) -> str:
    style = _narration_style()
    templates = _LONG_TITLE_TEMPLATES[style]
    seed = _seed(meta, minutes)
    topic = _compact_topic(meta)
    recent = {_normalize(item.get("title", "")) for item in previous[-40:] if item.get("title")}
    for offset in range(len(templates)):
        template = templates[(seed + offset * 3) % len(templates)]
        candidate = " ".join(template.format(topic=topic).split())[:95].rstrip(" -:,.!")
        if _normalize(candidate) not in recent:
            return candidate
    return f"{topic} | Reflexión bíblica de {minutes} minutos"[:95].rstrip(" -:,.!")


def _robust_image_motion(source: Path, out: Path, duration: int, index: int) -> None:
    """Animate long-form stills through six visibly different camera paths."""
    frames = max(1, duration * base.FPS)
    motion = index % 6
    if motion == 0:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == 1:
        x_expr, y_expr = f"min(iw-iw/zoom,(iw-iw/zoom)*on/{frames})", "ih/2-(ih/zoom/2)"
    elif motion == 2:
        x_expr, y_expr = f"max(0,(iw-iw/zoom)*(1-on/{frames}))", "ih/2-(ih/zoom/2)"
    elif motion == 3:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", f"min(ih-ih/zoom,(ih-ih/zoom)*on/{frames})"
    elif motion == 4:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", f"max(0,(ih-ih/zoom)*(1-on/{frames}))"
    else:
        x_expr = f"min(iw-iw/zoom,(iw-iw/zoom)*on/{frames})"
        y_expr = f"min(ih-ih/zoom,(ih-ih/zoom)*on/{frames})"
    zoom_rate = 0.00024 + motion * 0.000025
    vf = (
        f"scale={base.W * 2}:{base.H * 2}:force_original_aspect_ratio=increase,crop={base.W * 2}:{base.H * 2},"
        f"zoompan=z='min(zoom+{zoom_rate:.6f},1.085)':x='{x_expr}':y='{y_expr}':d={frames}:s={base.W}x{base.H}:fps={base.FPS},"
        "setsar=1,eq=contrast=1.025:saturation=1.04:brightness=0.003"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def _direct_long_metadata(meta: dict, minutes: int, previous: list[dict]) -> dict:
    mark_render_metadata(meta, format_name=f"long_horizontal_16x9_{minutes}min")
    apply_director_requirements(meta)
    mark_publish_metadata(meta, content_type="long_video")

    seed = _seed(meta, minutes)
    meta["title"] = _unique_long_title(meta, previous, minutes)
    opener = _LONG_DESCRIPTION_OPENERS[seed % len(_LONG_DESCRIPTION_OPENERS)]
    existing_description = str(meta.get("description") or "").strip()
    disclosure = (
        "Las representaciones de Jesús y las escenas bíblicas son creaciones artísticas digitales originales; "
        "no son grabaciones literales de hechos divinos."
    )
    meta["description"] = "\n\n".join(
        part for part in (opener, existing_description, disclosure) if part
    )[:4700]

    hashtag_pools = (
        ("#Dios", "#Jesus", "#Biblia", "#ReflexionCristiana", "#Fe"),
        ("#Dios", "#Oracion", "#Esperanza", "#PazDeDios", "#Jesus"),
        ("#Dios", "#PalabraDeDios", "#Jesucristo", "#AmorDeDios", "#Biblia"),
        ("#Dios", "#ConfiaEnDios", "#Fortaleza", "#ReflexionBiblica", "#Jesus"),
    )
    meta["hashtags"] = list(hashtag_pools[(seed // 17) % len(hashtag_pools)])

    render_block = render_directive(meta, vertical=False)
    signatures: list[str] = []
    for index, section in enumerate(meta.get("sections") or []):
        narration = " ".join(str(section.get("narration") or "").split()).strip()
        existing = " ".join(str(section.get("visual_prompt") or "").split()).strip()
        performance = performance_directive(narration[:1000])
        env_i = (seed + index * 5) % len(_LONG_ENVIRONMENTS)
        mode_i = (seed // 7 + index * 7) % len(_LONG_VISUAL_MODES)
        symbolic = index % 4 == 2
        signature = f"long-e{env_i}-m{mode_i}-s{int(symbolic)}"
        signatures.append(signature)

        if symbolic:
            symbol_i = (seed // 13 + index * 3) % len(_LONG_SYMBOLIC_CUTAWAYS)
            subject = (
                f"Symbolic God-centered cutaway: {_LONG_SYMBOLIC_CUTAWAYS[symbol_i]}. "
                "Do not depict God as a giant human, a face in the sky or a fantasy deity. "
                "Jesus may be absent or appear only as a secondary distant figure."
            )
        else:
            subject = (
                f"Jesus-centered performance: {_LONG_VISUAL_MODES[mode_i]}. "
                "Preserve the recurring original synthetic Jesus identity while changing pose, action, camera distance and wardrobe mantle variation from adjacent sections."
            )

        section["visual_prompt"] = (
            f"{render_block}\n\nEnvironment: {_LONG_ENVIRONMENTS[env_i]}.\n\n{subject}\n\n"
            f"Original section intent: {existing}\n\n{performance}\n\n"
            "Long-form diversity rule: this section must look visibly different from both adjacent sections. "
            "Prefer genuine moving video with continuous natural body, fabric, water, cloud, vegetation or page motion. "
            "Premium live-action photoreal cinema only; no cartoon, illustration, painting, anime, stylized 3D, plastic CGI, text, logo or watermark."
        )[:4800]
        section["visual_variety_signature"] = signature

    meta["visual_variety_signatures"] = signatures
    meta["worker_chain"] = [
        "Motor Celestial Cinema",
        "Director Paz Viva",
        "Publicador Reino 4x10",
    ]
    meta["worker_chain_separated"] = True
    meta["fixed_voice_identity"] = "Voz de Luz"
    meta["voice_profile"] = "voz_de_luz_serena_original_v1"
    meta["voice_reference_mode"] = "two_reference_style_blend_no_speaker_clone"
    meta["visual_variety_profile"] = "long_form_jesus_and_god_symbolic_rotation_v3"
    meta["recent_titles_avoided"] = [
        str(item.get("title") or "") for item in previous[-10:] if item.get("title")
    ]
    return meta


_ORIGINAL_METADATA_PROMPT = base._metadata_prompt


def run(minutes: int, publish: bool = False) -> dict:
    original_metadata = base._generate_metadata
    original_voice = base.make_natural_spanish_voice
    original_enhance = enhanced._enhance_metadata
    original_prompt = base._metadata_prompt
    original_image_motion = base._image_motion

    def resilient(channel: dict, requested_minutes: int) -> dict:
        if not os.getenv("GEMINI_API_KEY", "").strip():
            print("GEMINI_API_KEY no disponible; usando guionista biblico local resiliente.")
            return _apply_style_metadata(generate_local_long_metadata(channel, requested_minutes), requested_minutes)
        try:
            return _apply_style_metadata(original_metadata(channel, requested_minutes), requested_minutes)
        except Exception as exc:
            if not _service_error(exc):
                raise
            print(f"Gemini long-form no disponible ({exc}); usando guionista biblico local resiliente.")
            return _apply_style_metadata(generate_local_long_metadata(channel, requested_minutes), requested_minutes)

    def directed_enhance(meta: dict, previous: list[dict], requested_minutes: int) -> dict:
        enhanced_meta = original_enhance(meta, previous, requested_minutes)
        enhanced_meta = ground_and_optimize_spiritual_metadata(
            enhanced_meta,
            previous,
            content_type="long",
        )
        return _direct_long_metadata(enhanced_meta, requested_minutes, previous)

    base._generate_metadata = resilient
    base.make_natural_spanish_voice = make_spiritual_spanish_voice
    base._metadata_prompt = _styled_metadata_prompt
    base._image_motion = _robust_image_motion
    enhanced._enhance_metadata = directed_enhance
    try:
        return enhanced.run(minutes, publish=publish)
    finally:
        base._generate_metadata = original_metadata
        base.make_natural_spanish_voice = original_voice
        base._metadata_prompt = original_prompt
        base._image_motion = original_image_motion
        enhanced._enhance_metadata = original_enhance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[5, 10, 15, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.minutes, publish=args.publish), ensure_ascii=False))


if __name__ == "__main__":
    main()
