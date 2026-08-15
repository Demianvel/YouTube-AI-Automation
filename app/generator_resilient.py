from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone

from . import generator as base


FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")


def _service_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return any(
        token in text
        for token in (
            "503",
            "UNAVAILABLE",
            "HIGH DEMAND",
            "429",
            "RESOURCE_EXHAUSTED",
            "404 NOT_FOUND",
            "NO LONGER AVAILABLE",
            "QUOTA",
            "RATE LIMIT",
            "API KEY",
            "GEMINI_API_KEY",
        )
    )


def _marker() -> str:
    return (
        os.getenv("GITHUB_RUN_ID", "").strip()
        or os.getenv("GITHUB_RUN_NUMBER", "").strip()
        or datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    )


def _botanical_query(family: str) -> str:
    text = family.lower()
    species = [
        ("poroto", "bean seed germination timelapse"),
        ("frijol", "bean seed germination timelapse"),
        ("lenteja", "lentil seed germination timelapse"),
        ("garbanzo", "chickpea seed germination timelapse"),
        ("arveja", "pea seed germination timelapse"),
        ("guisante", "pea seed germination timelapse"),
        ("girasol", "sunflower seed germination timelapse"),
        ("tomate", "tomato seed germination timelapse"),
        ("calabaza", "pumpkin seed germination timelapse"),
        ("zapallo", "pumpkin seed germination timelapse"),
        ("rabano", "radish seed germination timelapse"),
        ("albahaca", "basil seed germination timelapse"),
        ("maiz", "corn seed germination timelapse"),
        ("trigo", "wheat seed germination timelapse"),
        ("pepino", "cucumber seed germination timelapse"),
        ("pimiento", "pepper seed germination timelapse"),
        ("lechuga", "lettuce seed germination timelapse"),
        ("cebolla", "onion seed germination timelapse"),
        ("chia", "chia seed germination timelapse"),
        ("mani", "peanut seed germination timelapse"),
        ("naranja", "orange seed germination timelapse"),
        ("limon", "lemon seed germination timelapse"),
        ("palta", "avocado seed germination timelapse"),
        ("aguacate", "avocado seed germination timelapse"),
        ("mango", "mango seed germination timelapse"),
        ("sandia", "watermelon seed germination timelapse"),
        ("kiwi", "kiwi seed germination timelapse"),
    ]
    for needle, query in species:
        if needle in text:
            return query
    if "raiz" in text or "raices" in text:
        return "roots growing macro timelapse"
    if "brote" in text:
        return "seed sprout soil timelapse"
    if "cotiled" in text or "hojas" in text:
        return "seedling first leaves timelapse"
    return "seed germination macro timelapse"


def _local_metadata(channel: dict, previous: list[dict]) -> dict:
    """Create safe, deterministic metadata when every text API is unavailable."""
    slug = base._channel_slug(channel)
    family = base._choose_family(channel, previous, salt=f"local-{_marker()}")
    count = int(channel.get("scenes_per_short", 1))
    audio_mode = str(channel.get("audio_mode") or "voice_music")

    digest = hashlib.sha256(f"{slug}|{family}|{_marker()}".encode()).hexdigest()[:6]

    if slug == "brotavida":
        query = _botanical_query(family)
        topic = family.replace("germinacion real de ", "germinacion de ").replace("ciclo real ", "ciclo ")
        hook = "Mirá cómo una semilla empieza a transformarse"
        title = f"De semilla a brote: {topic[:58]}"
        narration = "" if audio_mode in {"music_only", "asmr"} else "La semilla se abre y comienza una nueva etapa de crecimiento."
        scenes = [
            {
                "visual_prompt": (
                    f"Macro botanical germination visualization of {topic}; one seed, coherent root emergence, "
                    "shoot rising through moist soil, same species throughout, realistic anatomy, vertical 9:16, no text"
                ),
                "stock_query": query,
                "narration": narration,
            }
        ]
        description = "Una mirada cercana al inicio del crecimiento de una planta. 🌱\nCada ejecución usa una especie o etapa diferente."
        hashtags = ["#BrotaVida", "#Plantas", "#Germinacion", "#Shorts"]
        tags = ["plantas", "germinacion", "semillas", "timelapse", "naturaleza", "brote", "raices", "macro"]
        cta = "¿Qué semilla querés ver después?"

    elif slug == "envikids":
        topic = family
        hook = f"¡Hoy empieza una aventura de {family}!"
        title = f"Una aventura 3D de {family} ✨"
        scenes = []
        beats = [
            "presenta un personaje original y un objetivo divertido",
            "muestra una pequeña sorpresa segura y una acción clara",
            "resuelve la aventura con cooperación y un final alegre",
        ]
        for i in range(count):
            beat = beats[i % len(beats)]
            scenes.append(
                {
                    "visual_prompt": (
                        f"Original premium 3D family animation about {family}; {beat}; cute fictional characters, "
                        "rounded design, cinematic lighting, colorful environment, expressive motion, no text, no logos"
                    ),
                    "stock_query": f"original 3D kids animation {family}",
                    "narration": f"{('Mirá' if i == 0 else 'Y ahora')}, descubrimos algo nuevo en esta aventura.",
                }
            )
        description = "Una mini aventura 3D original, alegre y segura para disfrutar en familia."
        hashtags = ["#EnViKids", "#Animacion3D", "#Kids", "#Shorts"]
        tags = ["envikids", "animacion 3d", "niños", "aventura", "familia", "educativo", "divertido", family]
        cta = "¿Qué aventura hacemos después?"

    elif slug == "dioshablahoyia":
        topic = family
        hook = "Si hoy necesitás una palabra de esperanza, escuchá esto"
        title = f"Un mensaje de fe para hoy: {family[:52]}"
        scene_prompts = [
            "Jesus walking slowly along a mountain path at golden sunrise, cream linen robe, serene compassionate expression, cinematic clouds and soft wind",
            "Jesus beside a calm lake extending one hand toward the viewer, warm golden light, moving water, mountains in the distance, peaceful cinematic atmosphere",
            "Jesus standing on a grassy valley at sunset looking toward the sky, soft rays through clouds, beige robe and muted red mantle, reverent hopeful mood",
        ]
        narrations = [
            "Tal vez hoy estés atravesando algo que te pesa. La fe no niega la dificultad, pero te recuerda que no caminás solo.",
            "La Biblia vuelve una y otra vez a esta idea: buscar a Dios, confiar, orar y seguir dando un paso a la vez.",
            "Que esta palabra te dé paz para hoy. Si querés, hacé una oración breve y escribí Amén como señal de esperanza.",
        ]
        scenes = []
        for i in range(count):
            scenes.append(
                {
                    "visual_prompt": scene_prompts[i % len(scene_prompts)],
                    "stock_query": "cinematic Jesus hope golden light mountain lake",
                    "narration": narrations[i % len(narrations)],
                }
            )
        description = "Una reflexión cristiana breve sobre fe, esperanza y confianza en Dios.\nContenido audiovisual con representación artística generada por IA."
        hashtags = ["#Dios", "#Jesus", "#Fe", "#Oracion", "#Shorts"]
        tags = ["dios", "jesus", "cristo", "biblia", "fe", "esperanza", "oracion", "paz", "dios habla hoy", family]
        cta = "Si esta palabra habló a tu corazón, podés escribir Amén."

    else:
        topic = family
        hook = f"Hay un detalle de {family} que cambia todo"
        title = f"{family.capitalize()}: la clave que muchos pasan por alto"
        scenes = []
        narrations = [
            f"Mirá: en {family}, primero necesitás separar la idea del número real.",
            "Después compará qué entra, qué sale y qué costo estás olvidando.",
            "La clave es decidir con números simples, no con suposiciones. ¿Qué revisarías primero?",
        ]
        for i in range(count):
            scenes.append(
                {
                    "visual_prompt": (
                        f"Premium vertical creator scene about {family}; modern small business, ecommerce, calculator, "
                        "products or workspace, cinematic realistic lighting, dynamic motion, no brands, no readable text"
                    ),
                    "stock_query": f"small business {family} entrepreneur",
                    "narration": narrations[i % len(narrations)],
                }
            )
        description = "Una idea práctica para entender mejor decisiones de dinero, ventas y negocios sin promesas fáciles."
        hashtags = ["#DineroClaro", "#Finanzas", "#Emprendedores", "#Shorts"]
        tags = ["dinero claro", "finanzas", "emprendimiento", "negocios", "ventas", "costos", "ahorro", family]
        cta = "¿Qué parte de tu negocio revisarías primero?"

    return {
        "topic": topic,
        "hook": hook,
        "title": title[:90],
        "description": description,
        "hashtags": hashtags[:5],
        "tags": tags[:15],
        "cta": cta,
        "scenes": scenes[:count],
        "content_family": family,
        "metadata_provider": f"local_resilient_{digest}",
    }


def generate_metadata(channel: dict, previous: list[dict], retries: int = 5):
    if not os.getenv("GEMINI_API_KEY", "").strip():
        metadata = _local_metadata(channel, previous)
        print("GEMINI_API_KEY ausente: usando metadata local resiliente.")
        return metadata

    try:
        return base.generate_metadata(channel, previous, retries=retries)
    except Exception as primary_exc:
        if not _service_error(primary_exc):
            raise

        primary = base.TEXT_MODEL
        if FALLBACK_MODEL != primary:
            print(f"Gemini principal {primary} sin disponibilidad/cuota; probando {FALLBACK_MODEL}.")
            base.TEXT_MODEL = FALLBACK_MODEL
            try:
                return base.generate_metadata(channel, previous, retries=max(3, retries))
            except Exception as fallback_exc:
                if not _service_error(fallback_exc):
                    raise
                print(f"Gemini de respaldo tampoco disponible ({fallback_exc}); usando metadata local resiliente.")
            finally:
                base.TEXT_MODEL = primary

        metadata = _local_metadata(channel, previous)
        print("Metadata local generada: el pipeline visual continuara sin depender de Gemini.")
        return metadata
