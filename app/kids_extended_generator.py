from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")
SCENE_SECONDS = 12


def generate_extended_short_metadata(channel: dict, minutes: int) -> dict[str, Any]:
    if minutes not in {1, 2, 3}:
        raise ValueError("EnViKids extended Shorts solo admite 1, 2 o 3 minutos.")
    scene_count = minutes * 5
    analytics = channel.get("_analytics_digest") or "No hay Analytics disponible; no inventar preferencias de audiencia."

    prompt = f"""
Eres guionista senior de YouTube Shorts infantiles y productor de animacion 3D familiar.
Canal: {channel['display_name']} ({channel['handle']}).
Duracion exacta objetivo: {minutes} minuto(s), vertical 9:16.
Escenas: exactamente {scene_count} escenas de {SCENE_SECONDS} segundos.

UNIVERSO DEL CANAL:
{channel['master_prompt']}

ANALYTICS DISPONIBLE:
{analytics}

Crea UNA mini-historia original, coherente, segura y entretenida. Si Analytics muestra temas con mas vistas, likes, comentarios, retencion, compartidos o suscriptores ganados, favorece esos patrones SIN repetir titulos ni historias anteriores.

TEMAS POSIBLES A ROTAR:
- cocina divertida y segura;
- dinosaurios simpaticos;
- patitos, gatos, perros, vacas y otros animales;
- selva amazonica fantastica y educativa;
- oceano, espacio, robots amistosos;
- musica y baile con pista instrumental original;
- amistad, colores, numeros, naturaleza y pequeños misterios sin miedo;
- bebes ficticios/cartoon siempre en situaciones seguras y acompañados por adultos ficticios cuando corresponda.

ESTILO VISUAL:
- pelicula familiar 3D premium, personajes completamente originales;
- formas redondeadas, expresiones claras, luz cinematografica suave, colores vivos;
- continuidad de protagonistas entre escenas;
- no copiar personajes, vestuario, escenarios ni diseños de ninguna franquicia real;
- no personas reales, no logos, no marcas, no texto dentro de la imagen;
- cada visual_prompt debe ser autocontenido, vertical 9:16, con accion visible y encuadre distinto.

NARRACION:
- castellano natural, calido y agradable para niños;
- 18 a 26 palabras por escena;
- ritmo agil pero no gritado;
- vocabulario simple, positivo y curioso;
- sin violencia, miedo intenso, humillacion ni conductas peligrosas imitables.

Devuelve SOLO JSON valido:
{{
  "topic": "tema central",
  "hook": "gancho de los primeros 2 segundos",
  "title": "titulo atractivo y verdadero, maximo 90 caracteres",
  "description": "descripcion de 3 a 6 lineas para YouTube",
  "hashtags": ["#Shorts", "#EnViKids", "#..."],
  "tags": ["..."],
  "scenes": [
    {{
      "visual_prompt": "escena 3D completa vertical 9:16 con continuidad",
      "narration": "18 a 26 palabras en castellano"
    }}
  ]
}}

Reglas estrictas:
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

    for index, scene in enumerate(scenes, start=1):
        visual = " ".join(str(scene.get("visual_prompt") or "").split())
        narration = " ".join(str(scene.get("narration") or "").split())
        if not visual:
            raise RuntimeError(f"Falta visual_prompt en escena {index}.")
        if not narration:
            raise RuntimeError(f"Falta narracion en escena {index}.")
        scene["visual_prompt"] = visual[:1500]
        scene["narration"] = narration

    data["title"] = str(data.get("title") or "Nueva aventura EnViKids").strip()[:90]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["scene_seconds"] = SCENE_SECONDS
    data["extended_short"] = True
    return data
