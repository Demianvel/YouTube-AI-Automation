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
        rows.append(f"- tema={item.get('topic','')} | titulo={item.get('title','')}")
    return "\n".join(rows)


def _prompt(channel: dict, previous: list[dict], attempt: int) -> str:
    audio_mode = channel.get("audio_mode", "voice_music")
    if audio_mode == "music_only":
        audio_rule = (
            "REGLA ABSOLUTA DE AUDIO: NO escribas narracion. El campo narration de TODAS las escenas "
            "debe ser una cadena vacia. El gancho debe ser 100% visual."
        )
    else:
        audio_rule = (
            "REGLA DE AUDIO: cada escena debe incluir una narracion breve, natural y clara en castellano argentino. "
            "No uses frases grandilocuentes ni promesas."
        )

    return f"""
Eres estratega senior de YouTube Shorts especializado en retencion, busqueda, SEO natural, CTR honesto y engagement autentico.
Trabajas para el canal {channel['display_name']} ({channel['handle']}).

PROMPT MAESTRO UNICO DEL CANAL:
{channel['master_prompt']}

{audio_rule}

OBJETIVO:
Genera UN concepto nuevo para un Short de {channel['scenes_per_short'] * channel['scene_seconds']} segundos.
Debe ser claramente distinto del historial reciente y aportar valor visual o educativo real.
Optimiza el primer segundo para detener el scroll, el titulo para curiosidad verdadera y claridad, y el cierre para una accion natural.
No uses clickbait enganoso, no prometas resultados inexistentes, no inventes datos y no copies frases completas del historial.

HISTORIAL RECIENTE QUE DEBES EVITAR:
{_history_digest(previous)}

INTENTO: {attempt}

Devuelve SOLO JSON valido con esta estructura exacta:
{{
  "topic": "tema especifico y unico",
  "hook": "gancho de los primeros 2 segundos",
  "title": "titulo para YouTube, maximo 90 caracteres",
  "description": "descripcion SEO natural de 2 a 4 lineas que explique realmente el contenido",
  "hashtags": ["#Shorts", "#..."],
  "tags": ["palabra clave", "..."],
  "cta": "CTA breve y natural, sin manipulacion",
  "pinned_comment": "comentario breve para fijar manualmente y generar conversacion autentica",
  "scenes": [
    {{"visual_prompt": "descripcion visual autocontenida y concreta de la escena", "narration": "frase breve o cadena vacia segun la regla de audio"}}
  ]
}}

Reglas tecnicas:
- scenes debe tener exactamente {channel['scenes_per_short']} elementos.
- Cada escena dura {channel['scene_seconds']} segundos.
- visual_prompt debe describir sujeto, accion, entorno, encuadre, iluminacion y continuidad con la escena anterior.
- Hashtags: 3 a 5, relevantes; no rellenar con tendencias no relacionadas.
- Tags: 8 a 15, relevantes y variados.
- Titulo: maximo 90 caracteres, sin MAYUSCULAS abusivas ni afirmaciones falsas.
- pinned_comment: una sola pregunta o invitacion relevante, no spam.
- No menciones marcas registradas ni agregues markdown.
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

        if channel.get("audio_mode") == "music_only":
            for scene in scenes:
                scene["narration"] = ""
        else:
            if any(not (scene.get("narration") or "").strip() for scene in scenes):
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
        data["pinned_comment"] = (data.get("pinned_comment") or "").strip()[:400]
        return data

    raise RuntimeError(f"No se pudo generar un concepto suficientemente distinto: {last_reason}")
