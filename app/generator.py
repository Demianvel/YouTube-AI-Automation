from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from .history import too_similar

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")
FAMILIES_FILE = Path(__file__).resolve().parents[1] / "config" / "topic_families.json"


def _channel_slug(channel: dict) -> str:
    text = f"{channel.get('handle','')} {channel.get('display_name','')}".lower()
    if "brotavida" in text:
        return "brotavida"
    if "dineroclaro" in text or "dinero claro" in text:
        return "dineroclaro"
    if "envikids" in text:
        return "envikids"
    raise ValueError("Canal no reconocido para rotacion tematica")


def _load_families(channel: dict) -> list[str]:
    data = json.loads(FAMILIES_FILE.read_text(encoding="utf-8"))
    return [str(x).strip() for x in data[_channel_slug(channel)] if str(x).strip()]


def _choose_family(channel: dict, previous: list[dict], salt: str = "short") -> str:
    families = _load_families(channel)
    recent = [str(x.get("content_family") or "").strip() for x in previous[-8:]]
    recent = [x for x in recent if x]

    marker = os.getenv("GITHUB_RUN_NUMBER", "").strip()
    if marker.isdigit():
        base = int(marker)
    else:
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        base = int(hashlib.sha256(f"{now}|{salt}".encode()).hexdigest()[:10], 16)

    slug = _channel_slug(channel)
    offset = int(hashlib.sha256(f"{slug}|{salt}".encode()).hexdigest()[:8], 16)
    start = (base + offset) % len(families)

    for step in range(len(families)):
        family = families[(start + step) % len(families)]
        if family not in recent:
            return family
    return families[start]


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
            f"- familia={item.get('content_family','')} | formato={item.get('content_mode','')} | tema={item.get('topic','')} | titulo={item.get('title','')}{performance}"
        )
    return "\n".join(rows)


def _prompt(channel: dict, previous: list[dict], attempt: int, family: str) -> str:
    audio_mode = channel.get("audio_mode", "voice_music")
    visual_mode = channel.get("visual_mode", "")
    botanical = "botanical" in visual_mode
    kids_3d = "kids" in visual_mode
    analytics_summary = channel.get("_analytics_digest") or "No hay Analytics detallado disponible en esta ejecucion."

    if audio_mode == "music_only":
        audio_rule = (
            "FORMATO MUSICA: no generes narracion. El campo narration debe ser cadena vacia. "
            "La retencion debe venir del cambio visual real de la planta. Se agregara musica instrumental original del sistema."
        )
    elif audio_mode == "asmr":
        audio_rule = (
            "FORMATO ASMR: no generes narracion. El campo narration debe ser cadena vacia. "
            "No se usara musica: el montaje llevara sonidos naturales originales y suaves."
        )
    elif kids_3d:
        audio_rule = (
            "REGLA DE AUDIO INFANTIL/JUVENIL: narracion muy breve en castellano claro, alegre y natural. "
            "Voz amable y expresiva, sin voz de bebe exagerada ni imitacion de voces conocidas."
        )
    elif botanical:
        audio_rule = (
            "FORMATO VOZ: narracion breve en castellano natural, clara y serena, explicando lo que realmente se observa. "
            "Debe sonar humana y documental, no robotica."
        )
    else:
        audio_rule = (
            "FORMATO INFLUENCER DIGITAL: narracion en castellano natural, energia controlada, ritmo agil y pausas humanas. "
            "Acento argentino/rioplatense suave y comprensible. No imites a ningun creador real ni prometas dinero facil."
        )

    if botanical:
        visual_rule = (
            "FUENTE VISUAL REAL: stock_query EN INGLES para METRAJE REAL DE CAMARA. "
            "No CGI, 3D, animation, illustration ni AI. No afirmes una especie o etapa que el video no permita verificar."
        )
    elif kids_3d:
        visual_rule = (
            "VISUAL 3D ORIGINAL: escena infantil/familiar vertical 9:16 con personajes ficticios originales, colores vivos y luz cinematografica suave. "
            "No copiar franquicias, personas reales, logos, texto ni marcas."
        )
    else:
        visual_rule = (
            "DINERO CLARO PUEDE SER REAL O ANIMADO: elige el tratamiento que mejor cuente esta idea. "
            "Si es real, usa B-roll filmable de comercios, emprendedores, productos, calculadoras, pedidos o trabajo cotidiano. "
            "Si es animado, describe una animacion original tipo doodle, infografia, monedas, barras, decisiones A/B o mini historia visual. "
            "Nunca politica, gobierno, elecciones, funcionarios ni propaganda."
        )

    channel_value = (
        "transformacion botanica visual clara y verificable" if botanical else
        "mini historia infantil segura y visualmente distinta" if kids_3d else
        "entretenimiento financiero con un aprendizaje concreto"
    )

    return f"""
Eres estratega senior de YouTube Shorts, retencion y variedad editorial.
Trabajas para {channel['display_name']} ({channel['handle']}).

FAMILIA TEMATICA OBLIGATORIA PARA ESTA EJECUCION:
{family}

No cambies a otra familia aunque Analytics muestre buen rendimiento de un tema reciente. Analytics sirve para mejorar gancho, ritmo y presentacion, NO para repetir el concepto. La historia, ejemplo, escenas, titulo, hook y estructura deben ser nuevos.

PROMPT MAESTRO DEL CANAL:
{channel['master_prompt']}

{audio_rule}
{visual_rule}

Genera UN concepto nuevo para un Short de {channel['scenes_per_short'] * channel['scene_seconds']} segundos.
Debe ser claramente diferente del historial reciente y aportar: {channel_value}.
El primer segundo debe justificar visual o verbalmente por que seguir mirando.

ANALYTICS DEL CANAL:
{analytics_summary}

HISTORIAL RECIENTE A EVITAR:
{_history_digest(previous)}

INTENTO: {attempt}

Devuelve SOLO JSON valido:
{{
  "topic": "tema especifico y unico dentro de la familia obligatoria",
  "hook": "gancho inicial",
  "title": "titulo natural, maximo 90 caracteres",
  "description": "descripcion SEO natural de 2 a 4 lineas",
  "hashtags": ["#Shorts", "#..."],
  "tags": ["palabra clave", "..."],
  "cta": "CTA breve y relacionado",
  "scenes": [
    {{
      "visual_prompt": "descripcion visual precisa y autocontenida",
      "stock_query": "short English helper query",
      "narration": "frase breve o cadena vacia segun formato"
    }}
  ]
}}

Reglas:
- scenes debe contener exactamente {channel['scenes_per_short']} elementos.
- Cada escena dura {channel['scene_seconds']} segundos.
- visual_prompt y stock_query son obligatorios.
- Hashtags: 3 a 5 relevantes.
- Tags: 8 a 15 relevantes.
- Nada de clickbait falso, afirmaciones inventadas o contenido repetido.
- No agregues markdown fuera del JSON.
""".strip()


def generate_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict[str, Any]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    last_reason = ""
    family = _choose_family(channel, previous, salt="short")

    for attempt in range(1, retries + 1):
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=_prompt(channel, previous, attempt, family),
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

        data["content_family"] = family
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
