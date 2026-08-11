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
    for item in previous[-40:]:
        rows.append(f"- tema={item.get('topic','')} | titulo={item.get('title','')}")
    return "\n".join(rows)


def _prompt(channel: dict, previous: list[dict], attempt: int) -> str:
    return f"""
Eres estratega senior de YouTube Shorts, SEO y retencion. Trabajas para el canal {channel['display_name']} ({channel['handle']}).

PROMPT MAESTRO DEL CANAL:
{channel['master_prompt']}

OBJETIVO:
Genera UN concepto nuevo para un Short de {channel['scenes_per_short'] * channel['scene_seconds']} segundos. Debe ser claramente distinto del historial. No uses clickbait enganoso. El titulo debe crear curiosidad sin afirmar algo falso. No copies frases completas del historial.

HISTORIAL RECIENTE QUE DEBES EVITAR:
{_history_digest(previous)}

INTENTO: {attempt}

Devuelve SOLO JSON valido con esta estructura exacta:
{{
  "topic": "tema especifico y unico",
  "hook": "gancho de los primeros 2 segundos",
  "title": "titulo para YouTube, maximo 90 caracteres",
  "description": "descripcion SEO natural, 2 a 4 lineas, sin spam",
  "hashtags": ["#Shorts", "#..."],
  "tags": ["palabra clave", "..."],
  "scenes": [
    {{"visual_prompt": "prompt cinematografico autocontenido para Veo, sin texto incrustado", "narration": "frase muy breve en castellano argentino"}}
  ]
}}

Reglas: scenes debe tener exactamente {channel['scenes_per_short']} elementos. Cada escena dura {channel['scene_seconds']} segundos. Los visual_prompt deben estar en ingles descriptivo para maximizar consistencia visual; la narration debe estar en castellano argentino y caber comodamente en 8 segundos. Hashtags: 3 a 5. Tags: 6 a 12. No menciones marcas registradas. No agregues markdown.
""".strip()


def generate_metadata(channel: dict, previous: list[dict], retries: int = 4) -> dict[str, Any]:
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
        is_similar, reason = too_similar(data, previous)
        if is_similar:
            last_reason = reason
            continue
        data["title"] = data.get("title", "")[:90].strip()
        if not data["title"]:
            last_reason = "titulo vacio"
            continue
        return data
    raise RuntimeError(f"No se pudo generar un concepto suficientemente distinto: {last_reason}")
