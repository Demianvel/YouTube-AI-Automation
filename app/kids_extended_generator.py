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
        raise ValueError("EnViKidsAI extended Shorts solo admite 1, 2 o 3 minutos.")
    scene_count = minutes * 5
    analytics = channel.get("_analytics_digest") or "No hay Analytics disponible; no inventar preferencias de audiencia."

    prompt = f"""
Eres guionista senior de YouTube Shorts infantiles/familiares y productor de animacion 3D para niños y adolescentes.
Canal: {channel['display_name']} ({channel['handle']}).
Duracion exacta objetivo: {minutes} minuto(s), vertical 9:16.
Escenas: exactamente {scene_count} escenas de {SCENE_SECONDS} segundos.

UNIVERSO DEL CANAL:
{channel['master_prompt']}

ANALYTICS DISPONIBLE:
{analytics}

APRENDIZAJE DE AUDIENCIA:
- Prioriza categorias presentes en videos con mas vistas y, especialmente, videos que ganaron mas suscriptores.
- Tambien considera retencion, porcentaje visto, compartidos y likes cuando existan.
- Como el canal es Made for Kids, los comentarios pueden estar deshabilitados; no los uses como senal principal.
- No copies el video ganador: conserva el INTERES principal y crea otra historia, gancho y escenas.
- Si Analytics aun tiene pocos datos, explora distintas categorias de manera equilibrada.

TEMAS POSIBLES A ROTAR:
- cocina divertida y segura;
- dinosaurios simpaticos;
- patitos, gatos, perros, vacas, conejos, tortugas y otros animales;
- escuela: ciencias, arte, musica, biblioteca, recreo, amistad, numeros y colores;
- selva amazonica fantastica/educativa, naturaleza, oceano y espacio;
- musica y baile con pista instrumental original;
- plastilina/modelado 3D satisfactorio tipo ASMR;
- robots amistosos, pequenos misterios sin miedo y juegos de imaginacion;
- bebes ficticios/cartoon siempre en situaciones seguras y acompañados por adultos ficticios cuando corresponda.

AUDIO:
Elige exactamente uno:
1) "voice_music": voz castellana agradable + musica instrumental ORIGINAL muy suave.
2) "clay_asmr": solo para plastilina/modelado: voz castellana suave + foley original de amasado/modelado, sin musica comercial.
Siempre debe haber narracion. La voz debe servir para niños y adolescentes: calida, clara, expresiva, sin gritos y sin infantilizar en exceso.
La narracion debe fluir de una escena a la siguiente como una sola historia continua, sin presentaciones repetidas ni silencios largos. Escribe suficiente texto para ocupar casi toda cada escena a ritmo natural.
Puedes usar dialogos cortos de personajes ficticios. En cada escena indica speaker_style: narrator, bright_character, calm_character o comic_character. Son perfiles sinteticos originales; nunca imites una voz reconocible, actor, personaje protegido o creador real.

ESTILO VISUAL:
- pelicula familiar 3D premium, personajes completamente originales;
- formas redondeadas, expresiones claras, luz cinematografica suave, colores vivos;
- inspiracion general en animacion 3D familiar moderna, sin copiar el estilo identificable ni personajes de ninguna franquicia;
- continuidad de protagonistas entre escenas;
- no personas reales, no logos, no marcas, no texto dentro de la imagen;
- cada visual_prompt debe ser autocontenido, vertical 9:16, con accion visible y encuadre distinto.

NARRACION:
- castellano natural y facil de entender para audiencia hispanohablante;
- 27 a 33 palabras por escena para mantener voz casi continua durante 12 segundos;
- frases enlazadas, pocas pausas, ritmo agil pero no gritado;
- vocabulario positivo, curioso y apropiado para niños/adolescentes;
- sin violencia, miedo intenso, humillacion, sexualizacion ni conductas peligrosas imitables.

Devuelve SOLO JSON valido:
{{
  "topic": "tema central",
  "content_category": "cocina|dinosaurios|animales|escuela|musica|naturaleza|plastilina_asmr|aventura",
  "audio_style": "voice_music|clay_asmr",
  "hook": "gancho de los primeros 2 segundos",
  "title": "titulo atractivo y verdadero, maximo 90 caracteres",
  "description": "descripcion de 3 a 6 lineas para YouTube",
  "hashtags": ["#Shorts", "#EnViKidsAI", "#..."],
  "tags": ["..."],
  "scenes": [
    {{
      "visual_prompt": "escena 3D completa vertical 9:16 con continuidad",
      "speaker_style": "narrator|bright_character|calm_character|comic_character",
      "narration": "27 a 33 palabras en castellano conectadas con las escenas vecinas"
    }}
  ]
}}

Reglas estrictas:
- scenes debe tener exactamente {scene_count} elementos.
- Si content_category es plastilina_asmr, audio_style debe ser clay_asmr.
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

    allowed_styles = {"narrator", "bright_character", "calm_character", "comic_character"}
    for index, scene in enumerate(scenes, start=1):
        visual = " ".join(str(scene.get("visual_prompt") or "").split())
        narration = " ".join(str(scene.get("narration") or "").split())
        if not visual:
            raise RuntimeError(f"Falta visual_prompt en escena {index}.")
        if not narration:
            raise RuntimeError(f"Falta narracion en escena {index}.")
        scene["visual_prompt"] = visual[:1500]
        scene["narration"] = narration
        style = str(scene.get("speaker_style") or "narrator").strip().lower()
        scene["speaker_style"] = style if style in allowed_styles else "narrator"

    category = str(data.get("content_category") or "aventura").strip().lower()
    audio_style = str(data.get("audio_style") or "voice_music").strip().lower()
    if category == "plastilina_asmr":
        audio_style = "clay_asmr"
    if audio_style not in {"voice_music", "clay_asmr"}:
        audio_style = "voice_music"

    data["content_category"] = category
    data["audio_style"] = audio_style
    data["title"] = str(data.get("title") or "Nueva aventura EnViKids AI").strip()[:90]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["scene_seconds"] = SCENE_SECONDS
    data["extended_short"] = True
    return data
