from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from . import spiritual_long_pipeline as base
from . import spiritual_long_runner as enhanced
from .spiritual_long_local_metadata import generate_local_long_metadata
from .spiritual_source_growth_engine import ground_and_optimize_spiritual_metadata
from .spiritual_tts import make_spiritual_spanish_voice
from .workers.celestial_cinema_engine import mark_render_metadata, render_directive
from .workers.divine_publisher_4x10 import mark_publish_metadata
from .workers.peace_motion_director import apply_director_requirements, performance_directive


def _service_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return any(token in text for token in (
        "429", "RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT", "503", "UNAVAILABLE", "HIGH DEMAND", "404 NOT_FOUND",
    ))


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
    return f"{prompt}\n\n{directive.strip()}"


def _apply_style_metadata(meta: dict, minutes: int) -> dict:
    style = _narration_style()
    meta["narration_style"] = style
    meta["fixed_voice_identity"] = "Algenib deep biblical narrator"
    meta["voice_style_reference_video_id"] = "bm6LxLsrMbE"
    meta["voice_reference_mode"] = "style_only_no_speaker_clone"
    if style in {"prayer", "night_prayer"}:
        night = style == "night_prayer"
        topic = " ".join(str(meta.get("topic") or "Paz, fe y esperanza").split())
        meta["title"] = (
            f"Oración de la noche: {topic}" if night else f"Oración para fortalecer tu fe: {topic}"
        )[:95]
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


def _robust_image_motion(source: Path, out: Path, duration: int, index: int) -> None:
    """Animate a still on Ubuntu FFmpeg without the unsupported image2 -loop option."""
    frames = max(1, duration * base.FPS)
    if index % 3 == 0:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif index % 3 == 1:
        x_expr = f"min(iw-iw/zoom,(iw-iw/zoom)*on/{frames})"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = f"min(ih-ih/zoom,(ih-ih/zoom)*on/{frames})"
    vf = (
        f"scale={base.W * 2}:{base.H * 2}:force_original_aspect_ratio=increase,crop={base.W * 2}:{base.H * 2},"
        f"zoompan=z='min(zoom+0.00035,1.07)':x='{x_expr}':y='{y_expr}':d={frames}:s={base.W}x{base.H}:fps={base.FPS},"
        "setsar=1,eq=contrast=1.025:saturation=1.04:brightness=0.003"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def _direct_long_metadata(meta: dict, minutes: int) -> dict:
    mark_render_metadata(meta, format_name=f"long_horizontal_16x9_{minutes}min")
    apply_director_requirements(meta)
    mark_publish_metadata(meta, content_type="long_video")

    render_block = render_directive(meta, vertical=False)
    for section in meta.get("sections") or []:
        narration = " ".join(str(section.get("narration") or "").split()).strip()
        existing = " ".join(str(section.get("visual_prompt") or "").split()).strip()
        performance = performance_directive(narration[:1000])
        section["visual_prompt"] = (
            f"{render_block}\n\n{existing}\n\n{performance}\n\n"
            "Long-form continuity rule: preserve exactly the same recurring synthetic character identity, "
            "wardrobe family and facial proportions across all generated sections. Prefer genuine moving video "
            "with continuous human body performance over animated still images whenever a video model is available."
        )[:4800]

    meta["worker_chain"] = [
        "Motor Celestial Cinema",
        "Director Paz Viva",
        "Publicador Reino 4x10",
    ]
    meta["worker_chain_separated"] = True
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
        return _direct_long_metadata(enhanced_meta, requested_minutes)

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
