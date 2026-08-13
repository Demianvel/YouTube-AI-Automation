from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")


def generate_music_metadata(channel: dict, minutes: int) -> dict[str, Any]:
    if minutes not in {1, 5, 10, 30}:
        raise ValueError("DemianVelo admite 1, 5, 10 o 30 minutos.")
    analytics = channel.get("_analytics_digest") or "No hay Analytics disponible; no inventar preferencias de audiencia."
    is_short = minutes == 1

    prompt = f"""
Eres productor musical electronico, director creativo y estratega de YouTube para el canal de artista DemianVelo.
Duracion objetivo: {minutes} minuto(s). Formato: {'Short vertical 9:16' if is_short else 'video musical horizontal 16:9'}.

IDENTIDAD DEL CANAL:
{channel['master_prompt']}

ANALYTICS DISPONIBLE:
{analytics}

Crea una direccion creativa ORIGINAL para una nueva pieza musical instrumental. Elige entre progressive_house, electro_house, future_bass, melodic_techno, edm_festival, ambient_electronic o christian_electronic.
- Si Analytics muestra que ciertos estilos/temas generan mas vistas, retencion o suscriptores, favorecelos sin repetir titulos ni conceptos.
- Aproximadamente 30-45% de las ideas pueden ser christian_electronic cuando no haya datos suficientes; el resto electronica general.
- No copies melodias, letras, nombres ni conceptos distintivos de artistas reales.
- La musica se sintetizara localmente sin samples comerciales.
- Para christian_electronic, el mensaje visual puede sugerir fe, luz, esperanza, Jesucristo y gratitud de forma respetuosa, sin fingir citas biblicas.

VISUALES:
Genera 10 consultas de B-roll REAL DE CAMARA en ingles para montaje cinematografico. Evita gobiernos, politica, marcas, conciertos de artistas reconocibles y videoclips ajenos. Prioriza ciudad nocturna, carreteras, luces urbanas, naturaleza, mar, montañas, amaneceres, cielos, arquitectura, iglesias/templos como arquitectura, manos no identificables, siluetas lejanas y paisajes. Cada consulta debe ser distinta y filmable.

Devuelve SOLO JSON valido:
{{
  "topic": "concepto audiovisual",
  "music_style": "progressive_house|electro_house|future_bass|melodic_techno|edm_festival|ambient_electronic|christian_electronic",
  "faith_theme": true,
  "bpm": 128,
  "title": "titulo original, maximo 90 caracteres",
  "description": "descripcion original de 4 a 8 lineas",
  "hashtags": ["#DemianVelo", "#ElectronicMusic", "#..."],
  "tags": ["..."],
  "visual_queries": ["night city cinematic", "... exactly 10"],
  "visual_direction": "direccion de montaje y atmosfera",
  "thumbnail_text": "2 a 5 palabras"
}}

Reglas:
- visual_queries: exactamente 10, ingles, sin marcas.
- bpm entre 105 y 140.
- hashtags 3 a 5; tags 10 a 18.
- title verdadero y no engañoso.
""".strip()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    style = str(data.get("music_style") or "progressive_house").strip().lower()
    allowed = {
        "progressive_house", "electro_house", "future_bass", "melodic_techno",
        "edm_festival", "ambient_electronic", "christian_electronic",
    }
    if style not in allowed:
        style = "progressive_house"
    queries = [" ".join(str(x).split())[:100] for x in (data.get("visual_queries") or []) if str(x).strip()]
    if len(queries) < 10:
        fallback = [
            "cinematic night city lights", "sunrise mountain landscape", "ocean waves cinematic",
            "night highway light trails", "dramatic clouds sunset", "modern architecture night",
            "forest sunlight cinematic", "church architecture sunrise", "stars night sky landscape",
            "urban skyline blue hour",
        ]
        for item in fallback:
            if len(queries) >= 10:
                break
            if item not in queries:
                queries.append(item)
    data["music_style"] = style
    data["faith_theme"] = bool(data.get("faith_theme")) or style == "christian_electronic"
    data["bpm"] = max(105, min(140, int(data.get("bpm") or 128)))
    data["title"] = str(data.get("title") or "DemianVelo - Nueva Electronica").strip()[:90]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["visual_queries"] = queries[:10]
    data["thumbnail_text"] = " ".join(str(data.get("thumbnail_text") or data["title"]).split())[:42]
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["is_short"] = is_short
    return data
