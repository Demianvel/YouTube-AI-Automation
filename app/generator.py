from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

from .history import too_similar

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")


def _history_digest(previous: list[dict]) -> str:
    if not previous:
        return "Aun no hay historial."
    rows = []
    for item in previous[-50:]:
        performance = ""
        if "views" in item:
            performance = (
                f" | views={item.get('views', 0)} | vph={item.get('vph', 0)}"
                f" | like_rate={item.get('like_rate', 0)} | comment_rate={item.get('comment_rate', 0)}"
                f" | share_rate={item.get('share_rate', 0)} | sub_rate={item.get('subscriber_gain_rate', 0)}"
                f" | avg_view_pct={item.get('averageViewPercentage', 0)}"
            )
        rows.append(
            f"- formato={item.get('content_mode','')} | tema={item.get('topic','')} | titulo={item.get('title','')}{performance}"
        )
    return "\n".join(rows)


def _prompt(channel: dict, previous: list[dict], attempt: int) -> str:
    audio_mode = channel.get("audio_mode", "voice_music")
    visual_mode = channel.get("visual_mode", "")
    botanical = "botanical" in visual_mode
    kids_3d = "kids" in visual_mode
    analytics_summary = channel.get("_analytics_digest") or "No hay Analytics detallado disponible en esta ejecucion."

    if audio_mode == "music_only":
        audio_rule = (
            "FORMATO MUSICA: no generes narracion. El campo narration debe ser cadena vacia. "
            "La retencion debe venir del cambio visual real de la planta. Se agregara musica instrumental original del sistema, "
            "sin usar canciones comerciales de terceros."
        )
    elif audio_mode == "asmr":
        audio_rule = (
            "FORMATO ASMR: no generes narracion. El campo narration debe ser cadena vacia. "
            "No se usara musica: el montaje llevara un paisaje ASMR suave de tierra, agua, hojas y pequenos sonidos naturales. "
            "El visual debe sentirse cercano, macro, relajante y satisfactorio."
        )
    elif kids_3d:
        audio_rule = (
            "REGLA DE AUDIO INFANTIL/JUVENIL: cada escena debe incluir una narracion muy breve en castellano claro, alegre y natural. "
            "La voz debe sentirse amable y expresiva para niños y adolescentes, sin voz de bebe exagerada, sin gritos y sin frases adultas. "
            "Se agregara musica instrumental original muy suave; nunca canciones comerciales de terceros."
        )
    else:
        if botanical:
            audio_rule = (
                "FORMATO VOZ: cada escena debe incluir una frase breve en castellano natural, clara y serena, "
                "explicando lo que sucede en la germinacion o crecimiento. Debe sonar humana y documental, no robotica."
            )
        else:
            audio_rule = (
                "FORMATO INFLUENCER DIGITAL: cada escena debe incluir narracion en castellano natural. "
                "Habla con seguridad, excelente parla, energia controlada, ritmo agil, pausas humanas y frases faciles de recordar. "
                "Usa un gancho inmediato, una idea concreta y un cierre que deje una accion o aprendizaje. "
                "Acento argentino/rioplatense suave, comprensible para toda Hispanoamerica. No imites ni copies a ningun creador real. "
                "No prometas dinero facil ni resultados garantizados."
            )

    if botanical:
        visual_rule = (
            "FUENTE VISUAL REAL: cada escena debe incluir stock_query EN INGLES para buscar METRAJE REAL DE CAMARA "
            "en bancos de medios libres. Usa frases cortas como 'sunflower growth timelapse', 'seed germination timelapse' o "
            "'plant growing macro'. No pidas CGI, 3D, animation, illustration ni AI."
        )
    elif kids_3d:
        visual_rule = (
            "VISUAL GENERATIVO 3D: visual_prompt debe describir una escena infantil/familiar 3D completa y autocontenida, vertical 9:16, "
            "con personajes ficticios originales, expresiones claras, luz cinematografica suave, colores vivos y composicion profesional. "
            "Inspiracion general en animacion 3D familiar moderna, pero no copies personajes, diseños, vestuario, escenarios ni el estilo identificable de ninguna franquicia. "
            "No uses personas reales, logos, texto ni marcas. stock_query debe ser una frase corta en ingles que resuma la escena; "
            "se usa solo como identificador auxiliar y no como banco de metraje."
        )
    else:
        visual_rule = (
            "FUENTE VISUAL REAL: cada escena debe incluir stock_query EN INGLES, de 3 a 8 palabras, para buscar B-roll REAL DE CAMARA "
            "en bancos de medios libres. Describe algo filmable: 'small business owner calculator', 'budget planning desk' o "
            "'packing online orders'. Evita marcas, logos y terminos CGI, 3D, animation o AI."
        )

    kids_focus = ""
    if kids_3d:
        kids_focus = """
CATEGORIAS ENVIKIDSAI A ROTAR Y APRENDER:
- cocina divertida y segura;
- dinosaurios simpaticos;
- animales como patitos, gatos, perros, vacas, conejos, tortugas y animales de selva/granja;
- escuela: ciencias, arte, musica, biblioteca, recreo, amistad, numeros y colores;
- musica y baile con pista original del sistema;
- plastilina/modelado 3D satisfactorio inspirado en ASMR visual;
- naturaleza, selva amazonica fantastica/educativa, oceano, espacio, robots amistosos y aventuras positivas.
No fuerces una categoria: usa Analytics para favorecer lo que ya demostro mas vistas, retencion o suscriptores ganados, manteniendo exploracion para descubrir nuevos intereses.
""".strip()

    channel_value = (
        "transformacion visual clara y verificable" if botanical else
        "mini historia infantil segura, entretenida y visualmente distinta" if kids_3d else
        "aprendizaje concreto y aplicable explicado con personalidad"
    )

    return f"""
Eres estratega senior de YouTube Shorts, retencion, SEO natural, CTR honesto y valor autentico.
Trabajas para {channel['display_name']} ({channel['handle']}).

PROMPT MAESTRO DEL CANAL:
{channel['master_prompt']}

{audio_rule}
{visual_rule}
{kids_focus}

Genera UN concepto nuevo para un Short de {channel['scenes_per_short'] * channel['scene_seconds']} segundos.
Debe ser claramente diferente del historial reciente. El titulo debe generar curiosidad real, describir correctamente el contenido y evitar clickbait enganoso.
El primer segundo debe mostrar o decir algo que haga evidente por que vale la pena seguir viendo.
El Short debe aportar una razon real para verlo: {channel_value}.

ANALYTICS DEL CANAL PARA ADAPTAR EL CONTENIDO:
{analytics_summary}

REGLAS PARA APRENDER DE LA AUDIENCIA:
- Prioriza patrones presentes en videos que combinaron vistas, tiempo de visualizacion, porcentaje visto, compartidos, comentarios y suscriptores ganados.
- En EnViKidsAI, da peso especial a los temas de videos que ganaron mas suscriptores, no solo a los que tuvieron mas vistas.
- Si un video tiene muchas vistas pero retencion debil o casi no convierte a suscriptores, no lo copies ciegamente.
- Si ciertos paises o edades aparecen con mas fuerza, adapta vocabulario y temas sin excluir injustamente a otras audiencias.
- Usa las fuentes de trafico y dispositivos como contexto para ritmo y claridad, no como excusa para clickbait.
- Inspírate en temas y formatos que funcionaron, pero crea una idea NUEVA y original.
- No inventes datos faltantes. Si demografia o compartidos no aparecen, ignoralos.

HISTORIAL RECIENTE A EVITAR Y APRENDER:
{_history_digest(previous)}

INTENTO: {attempt}

Devuelve SOLO JSON valido:
{{
  "topic": "tema especifico y unico",
  "hook": "gancho inicial",
  "title": "titulo viral natural, maximo 90 caracteres",
  "description": "descripcion SEO natural de 2 a 4 lineas",
  "hashtags": ["#Shorts", "#..."],
  "tags": ["palabra clave", "..."],
  "cta": "CTA breve y relacionado",
  "scenes": [
    {{
      "visual_prompt": "descripcion visual precisa y autocontenida",
      "stock_query": "short English helper query",
      "narration": "frase breve o cadena vacia segun el formato"
    }}
  ]
}}

Reglas:
- scenes debe contener exactamente {channel['scenes_per_short']} elementos.
- Cada escena dura {channel['scene_seconds']} segundos.
- visual_prompt y stock_query son obligatorios.
- Hashtags: 3 a 5, solo relevantes.
- Tags: 8 a 15, relevantes y variados.
- Titulo: maximo 90 caracteres, sin mayusculas abusivas ni afirmaciones falsas.
- No agregues markdown ni comentarios fuera del JSON.
""".strip()


def generate_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict[str, Any]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    last_reason = ""

    for attempt in range(1, retries + 1):
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=_prompt(channel, previous, attempt),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(response.text)
        scenes = data.get("scenes") or []

        if len(scenes) != channel["scenes_per_short"]:
            last_reason = "cantidad incorrecta de escenas"
            continue
        if any(not (scene.get("visual_prompt") or "").strip() for scene in scenes):
            last_reason = "falta visual_prompt para una escena"
            continue
        if any(not (scene.get("stock_query") or "").strip() for scene in scenes):
            last_reason = "falta stock_query para una escena"
            continue

        if channel.get("audio_mode") in {"music_only", "asmr"}:
            for scene in scenes:
                scene["narration"] = ""
        elif any(not (scene.get("narration") or "").strip() for scene in scenes):
            last_reason = "falta narracion en una escena"
            continue

        is_similar, reason = too_similar(data, previous)
        if is_similar:
            last_reason = reason
            continue

        data["title"] = (data.get("title") or "")[:90].strip()
        if not data["title"]:
            last_reason = "titulo vacio"
            continue

        data["description"] = (data.get("description") or "").strip()
        data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
        data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:15]
        data["cta"] = (data.get("cta") or "").strip()
        for scene in scenes:
            scene["stock_query"] = " ".join(str(scene["stock_query"]).strip().split())[:100]
            scene["visual_prompt"] = " ".join(str(scene["visual_prompt"]).strip().split())[:1200]
        return data

    raise RuntimeError(f"No se pudo generar un concepto suficientemente distinto: {last_reason}")
