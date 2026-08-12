from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")
CHAPTERS = 10
CHAPTER_SECONDS = 30


def _prompt(channel: dict) -> str:
    botanical = "botanical" in channel.get("visual_mode", "")
    if botanical:
        brief = """
Crea un video educativo de 5 minutos sobre germinacion y crecimiento de plantas usando EXCLUSIVAMENTE B-roll REAL DE CAMARA.
Elige un enfoque amplio y verdadero que pueda sostenerse con metraje real: por ejemplo, que necesita una semilla para germinar, etapas visibles de germinacion, raices, brotes, primeras hojas, luz, agua y crecimiento temprano.
No inventes especies concretas si el metraje no puede verificarlas. No uses dibujos, CGI, renders ni plantas generadas por IA.
La narracion debe ser en castellano natural, clara, serena, interesante y educativa, como un documental breve y accesible.
Cada capitulo debe tener una narracion de aproximadamente 55 a 70 palabras para ocupar cerca de 30 segundos a ritmo conversacional.
Las consultas stock_query deben estar en ingles y buscar VIDEO REAL, por ejemplo: seed germination timelapse, roots growing timelapse, plant sprout timelapse, seedlings growing sunlight.
"""
    else:
        brief = """
Crea un video educativo original de 5 minutos sobre finanzas personales, emprendimiento o negocios, explicado de forma simple y profesional.
Debe sentirse como un creador experto que hace las finanzas faciles de entender, SIN copiar titulos, guiones, frases ni estructura exacta de otros canales.
Elige UN tema central util, por ejemplo: ordenar las finanzas de un pequeno negocio, calcular ganancia real, separar dinero personal y del negocio, margen, flujo de caja, presupuesto, capital de trabajo, inventario o errores financieros de emprendedores.
Usa EXCLUSIVAMENTE B-roll REAL DE CAMARA de comercios, emprendedores, calculadoras, productos, cajas, inventario, escritorios, pagos genericos y trabajo real. No uses CGI ni dibujos.
Narracion en castellano profesional, natural y conversacional, tono argentino/rioplatense suave y comprensible para toda Hispanoamerica. No sonar robotico ni vendedor de humo.
Cada capitulo debe tener aproximadamente 55 a 70 palabras. Usa ejemplos con numeros redondos si ayudan, sin inventar tasas o datos actuales. No prometas dinero facil ni resultados garantizados.
Las stock_query deben estar en ingles y describir B-roll filmable real.
"""

    return f"""
Eres productor senior de YouTube, guionista educativo y editor de retencion.
Canal: {channel['display_name']} ({channel['handle']}).

{brief}

Genera exactamente {CHAPTERS} capitulos consecutivos de {CHAPTER_SECONDS} segundos, total aproximado 5 minutos.
Debe existir continuidad narrativa: introduccion fuerte, desarrollo ordenado y cierre claro.
No repitas la misma idea entre capitulos.
El titulo debe ser atractivo pero verdadero. La descripcion debe explicar lo que aprendera o vera el espectador.

Devuelve SOLO JSON valido con esta estructura:
{{
  "topic": "tema central",
  "title": "titulo natural de YouTube, maximo 95 caracteres",
  "description": "descripcion original de 4 a 8 lineas",
  "hashtags": ["#..."],
  "tags": ["..."],
  "chapters": [
    {{
      "heading": "nombre breve del capitulo",
      "visual_prompt": "que debe verse en B-roll real",
      "stock_query": "English query for real camera video",
      "narration": "55 a 70 palabras aproximadamente"
    }}
  ]
}}

Reglas estrictas:
- chapters debe tener exactamente {CHAPTERS} elementos.
- Cada narration debe ser autocontenida pero conectada con la siguiente.
- stock_query obligatorio, concreto y en ingles.
- Hashtags: 3 a 5.
- Tags: 10 a 18.
- Nada de markdown fuera del JSON.
""".strip()


def generate_long_metadata(channel: dict) -> dict[str, Any]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=_prompt(channel),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    chapters = data.get("chapters") or []
    if len(chapters) != CHAPTERS:
        raise RuntimeError(f"Gemini genero {len(chapters)} capitulos; se requieren {CHAPTERS}.")
    for index, chapter in enumerate(chapters, start=1):
        if not str(chapter.get("stock_query") or "").strip():
            raise RuntimeError(f"Falta stock_query en capitulo {index}.")
        if not str(chapter.get("narration") or "").strip():
            raise RuntimeError(f"Falta narracion en capitulo {index}.")
        chapter["stock_query"] = " ".join(str(chapter["stock_query"]).split())[:120]
    data["title"] = str(data.get("title") or "Video educativo").strip()[:95]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["long_form"] = True
    data["duration_seconds"] = CHAPTERS * CHAPTER_SECONDS
    return data
