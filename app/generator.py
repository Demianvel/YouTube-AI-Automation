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
            "REGLA ABSOLUTA: no generes narracion. El campo narration debe ser una cadena vacia. "
            "Todo el gancho y la retencion deben ser visuales."
        )
    else:
        audio_rule = (
            "REGLA DE AUDIO: cada escena debe incluir narracion breve, natural y clara en castellano argentino. "
            "No uses promesas ni frases exageradas."
        )

    return f"""
Eres estratega senior de YouTube Shorts, retencion y SEO natural.
Trabajas para {channel['display_name']} ({channel['handle']}).

PROMPT MAESTRO DEL CANAL:
{channel['master_prompt']}

{audio_rule}

Genera UN concepto nuevo para un Short de {channel['scenes_per_short'] * channel['scene_seconds']} segundos.
Debe ser claramente diferente del historial reciente. El titulo debe generar curiosidad real, describir correctamente el contenido y evitar clickbait enganoso.

HISTORIAL RECIENTE A EVITAR:
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
    {{"visual_prompt": "descripcion visual precisa y autocontenida", "narration": "frase breve o cadena vacia segun el canal"}}
  ]
}}

Reglas:
- scenes debe contener exactamente {channel['scenes_per_short']} elementos.
- Cada escena dura {channel['scene_seconds']} segundos.
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

        if channel.get("audio_mode") == "music_only":
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
        return data

    raise RuntimeError(f"No se pudo generar un concepto suficientemente distinto: {last_reason}")
