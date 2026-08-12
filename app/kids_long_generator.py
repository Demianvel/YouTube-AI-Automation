from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")
SCENE_SECONDS = 15


def generate_kids_long_metadata(channel: dict, minutes: int) -> dict[str, Any]:
    if minutes not in {5, 10}:
        raise ValueError("EnViKids long-form solo admite 5 o 10 minutos.")
    scene_count = (minutes * 60) // SCENE_SECONDS
    analytics = channel.get("_analytics_digest") or "No hay Analytics disponible; no inventar preferencias de audiencia."

    prompt = f"""
Eres guionista senior de animacion infantil y productor de YouTube familiar.
Canal: {channel['display_name']} ({channel['handle']}).
Duracion: {minutes} minutos.
Escenas: exactamente {scene_count} escenas de {SCENE_SECONDS} segundos.

UNIVERSO DEL CANAL:
{channel['master_prompt']}

ANALYTICS DISPONIBLE:
{analytics}

Crea UNA historia o programa tematico original y coherente. Elige una combinacion segura y atractiva entre cocina divertida, musica original, selva amazonica fantastica/educativa, dinosaurios simpaticos, patitos, gatos, perros, vacas, animales, naturaleza, oceano, espacio, baile, colores, numeros, amistad, robots amistosos o aventuras imaginativas.
Si Analytics muestra temas que funcionaron mejor, favorece esos patrones SIN repetir la historia o el titulo de videos anteriores.

ESTILO VISUAL:
- Animacion 3D familiar premium, personajes ficticios totalmente originales.
- Formas redondeadas, colores vivos, expresiones claras, luz cinematografica suave.
- No copiar personajes, vestuario, escenarios ni diseños de peliculas o franquicias reales.
- No personas reales, no logos, no marcas, no texto dentro de la imagen.
- Cada visual_prompt debe ser autocontenido para generar una imagen 16:9 distinta y mantener continuidad de los protagonistas.

NARRACION:
- Castellano natural, agradable y calido para niños.
- Frases simples, curiosas y positivas.
- Aproximadamente 28 a 38 palabras por escena.
- Sin gritos, amenazas, miedo intenso ni instrucciones peligrosas.
- Si aparecen bebes ficticios/cartoon en situaciones cotidianas, siempre acompañados por adultos ficticios responsables cuando exista riesgo.

Devuelve SOLO JSON valido:
{{
  "topic": "tema central",
  "title": "titulo atractivo y verdadero, maximo 95 caracteres",
  "description": "descripcion de 4 a 8 lineas para YouTube",
  "hashtags": ["#EnViKids", "#..."],
  "tags": ["..."],
  "thumbnail_text": "2 a 5 palabras",
  "scenes": [
    {{
      "visual_prompt": "escena 3D completa 16:9 con continuidad visual",
      "narration": "28 a 38 palabras en castellano"
    }}
  ]
}}

Reglas:
- scenes debe tener exactamente {scene_count} elementos.
- Hashtags: 3 a 5.
- Tags: 10 a 18.
- Nada de markdown fuera del JSON.
""".strip()

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    scenes = data.get("scenes") or []
    if len(scenes) != scene_count:
        raise RuntimeError(f"Gemini genero {len(scenes)} escenas; se requieren {scene_count}.")
    for i, scene in enumerate(scenes, start=1):
        if not str(scene.get("visual_prompt") or "").strip():
            raise RuntimeError(f"Falta visual_prompt en escena {i}.")
        if not str(scene.get("narration") or "").strip():
            raise RuntimeError(f"Falta narracion en escena {i}.")
        scene["visual_prompt"] = " ".join(str(scene["visual_prompt"]).split())[:1500]
        scene["narration"] = " ".join(str(scene["narration"]).split())

    data["title"] = str(data.get("title") or "Aventura EnViKids").strip()[:95]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["thumbnail_text"] = " ".join(str(data.get("thumbnail_text") or data["title"]).split())[:42]
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["scene_seconds"] = SCENE_SECONDS
    return data
