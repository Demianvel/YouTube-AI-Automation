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
        raise ValueError("EnViKidsAI long-form solo admite 5 o 10 minutos.")
    scene_count = (minutes * 60) // SCENE_SECONDS
    analytics = channel.get("_analytics_digest") or "No hay Analytics disponible; no inventar preferencias de audiencia."

    prompt = f"""
Eres guionista senior de animacion infantil/familiar y productor de YouTube para niños y adolescentes.
Canal: {channel['display_name']} ({channel['handle']}).
Duracion: {minutes} minutos.
Escenas: exactamente {scene_count} escenas de {SCENE_SECONDS} segundos.

UNIVERSO DEL CANAL:
{channel['master_prompt']}

ANALYTICS DISPONIBLE:
{analytics}

OBJETIVO DE APRENDIZAJE CONTINUO:
- Antes de elegir tema, revisa los videos listados en Analytics.
- Da prioridad a patrones de los videos con mas vistas Y a los que mas suscriptores ganaron.
- Tambien considera porcentaje visto, tiempo de visualizacion, compartidos y likes cuando existan.
- Este canal esta marcado como Made for Kids: los comentarios pueden estar deshabilitados; no dependas de comentarios como senal principal.
- Si un video tuvo muchas vistas pero mala retencion o pocos suscriptores, no lo copies ciegamente.
- Si un tema convierte muy bien a suscriptores aunque tenga menos vistas, dale peso adicional.
- Repite el INTERES o la CATEGORIA que funciono, nunca la misma historia, titulo, escenas o personajes exactos.
- Si los datos todavia son escasos, rota categorias para seguir explorando y aprender.

TEMAS Y FORMATOS A ROTAR:
- cocina divertida, recetas ficticias simples y seguras;
- dinosaurios simpaticos y aventuras prehistoricas educativas;
- animales: patitos, gatos, perros, vacas, conejos, tortugas, peces, ositos y animales de selva/granja;
- escuela: primer dia, ciencias, arte, musica, biblioteca, recreo, amistad, numeros, colores y curiosidades;
- selva amazonica fantastica y educativa, naturaleza, oceano y espacio;
- musica y baile con pista instrumental ORIGINAL generada por el sistema;
- plastilina/modelado 3D satisfactorio tipo ASMR, siempre ficticio y seguro;
- robots amistosos, juegos de imaginacion, pequenos misterios sin miedo y aventuras positivas.

AUDIO:
Elige exactamente uno:
1) "voice_music": narracion en castellano + musica instrumental original muy suave.
2) "clay_asmr": para plastilina/modelado: narracion castellana suave + sonidos originales de amasado/modelado; SIN musica comercial.
La narracion siempre debe estar presente y ser adecuada para niños y adolescentes: natural, clara, amable, expresiva, sin voz de bebe exagerada y sin gritos.
La voz debe sentirse CONTINUA a lo largo del video. No reinicies la historia ni hagas una presentacion nueva en cada escena. La ultima frase de una escena puede dejar la idea abierta para que la siguiente la complete. Evita silencios largos: escribe suficiente texto para ocupar casi toda cada escena a ritmo conversacional.
Puedes incluir dialogos cortos de personajes ficticios. Para cada escena usa speaker_style con uno de estos valores: narrator, bright_character, calm_character, comic_character. Son perfiles sinteticos originales; NUNCA imites una voz conocida, actor, personaje protegido o creador real. Usa narrator en la mayoria de escenas y perfiles de personaje solo cuando el dialogo lo justifique.

ESTILO VISUAL:
- Animacion 3D familiar premium y cinematografica, personajes ficticios totalmente originales.
- Formas redondeadas, colores vivos, expresiones claras, materiales limpios, iluminacion suave.
- Inspiracion general en largometrajes familiares 3D modernos, pero SIN copiar el estilo identificable, personajes, vestuario, escenarios ni diseños de ninguna pelicula o franquicia existente.
- No personas reales, no logos, no marcas, no texto dentro de la imagen.
- Cada visual_prompt debe ser autocontenido para una imagen 16:9 distinta y mantener continuidad de protagonistas.

NARRACION:
- Castellano natural y neutro/latino, facil de entender en Argentina y otros paises hispanohablantes.
- Aproximadamente 34 a 42 palabras por escena para mantener voz casi continua durante 15 segundos.
- Evita puntos innecesarios y pausas dramaticas largas; usa frases enlazadas y fluidas.
- Para niños: vocabulario simple y curioso. Para adolescentes: no sonar infantilizado.
- Sin amenazas, miedo intenso, humillacion, sexualizacion ni instrucciones peligrosas.
- Si aparecen bebes ficticios/cartoon en situaciones cotidianas, siempre acompañados por adultos ficticios responsables cuando exista riesgo.

Devuelve SOLO JSON valido:
{{
  "topic": "tema central",
  "content_category": "cocina|dinosaurios|animales|escuela|musica|naturaleza|plastilina_asmr|aventura",
  "audio_style": "voice_music|clay_asmr",
  "title": "titulo atractivo y verdadero, maximo 95 caracteres",
  "description": "descripcion de 4 a 8 lineas para YouTube",
  "hashtags": ["#EnViKidsAI", "#..."],
  "tags": ["..."],
  "thumbnail_text": "2 a 5 palabras",
  "scenes": [
    {{
      "visual_prompt": "escena 3D completa 16:9 con continuidad visual",
      "speaker_style": "narrator|bright_character|calm_character|comic_character",
      "narration": "34 a 42 palabras en castellano, conectadas con la escena anterior y siguiente"
    }}
  ]
}}

Reglas:
- scenes debe tener exactamente {scene_count} elementos.
- Si content_category es plastilina_asmr, audio_style debe ser clay_asmr; en los demas puede ser voice_music.
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
    for i, scene in enumerate(scenes, start=1):
        if not str(scene.get("visual_prompt") or "").strip():
            raise RuntimeError(f"Falta visual_prompt en escena {i}.")
        if not str(scene.get("narration") or "").strip():
            raise RuntimeError(f"Falta narracion en escena {i}.")
        scene["visual_prompt"] = " ".join(str(scene["visual_prompt"]).split())[:1500]
        scene["narration"] = " ".join(str(scene["narration"]).split())
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
    data["title"] = str(data.get("title") or "Aventura EnViKids AI").strip()[:95]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["thumbnail_text"] = " ".join(str(data.get("thumbnail_text") or data["title"]).split())[:42]
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["scene_seconds"] = SCENE_SECONDS
    return data
