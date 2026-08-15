from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from google import genai
from google.genai import types

TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")

ALLOWED_STYLES = {
    "progressive_house", "electro_house", "future_bass", "melodic_techno",
    "edm_festival", "ambient_electronic", "christian_electronic",
    "rkt", "trap_melodic", "pop_electronic", "rkt_trap", "christian_pop",
    "christian_trap", "christian_rkt",
}

_FALLBACK_STYLES = [
    "progressive_house", "future_bass", "melodic_techno", "edm_festival",
    "ambient_electronic", "pop_electronic", "trap_melodic", "rkt",
    "christian_pop", "christian_electronic",
]

_FALLBACK_TITLES = {
    "progressive_house": "Horizonte de Luz",
    "electro_house": "Pulso de Medianoche",
    "future_bass": "Pulso Infinito",
    "melodic_techno": "Despues del Cielo",
    "edm_festival": "Volver a Brillar",
    "ambient_electronic": "Luz en Silencio",
    "christian_electronic": "Camino de Luz",
    "rkt": "Hasta Que Amanezca",
    "trap_melodic": "Sin Mirar Atras",
    "pop_electronic": "Todo Puede Cambiar",
    "rkt_trap": "Noche en Movimiento",
    "christian_pop": "Aqui Sigo Creyendo",
    "christian_trap": "Fe en el Camino",
    "christian_rkt": "Con Dios Voy",
}

_FALLBACK_BPM = {
    "progressive_house": 126,
    "electro_house": 128,
    "future_bass": 150,
    "melodic_techno": 124,
    "edm_festival": 128,
    "ambient_electronic": 92,
    "christian_electronic": 122,
    "rkt": 96,
    "trap_melodic": 142,
    "pop_electronic": 118,
    "rkt_trap": 98,
    "christian_pop": 104,
    "christian_trap": 138,
    "christian_rkt": 96,
}

_FALLBACK_VISUALS = [
    "cinematic night city lights",
    "sunrise mountain landscape",
    "ocean waves cinematic",
    "night highway light trails",
    "dramatic clouds sunset",
    "modern architecture night",
    "urban street lights cinematic",
    "church architecture sunrise",
    "stars night sky landscape",
    "urban skyline blue hour",
]


def _fallback_metadata(
    minutes: int,
    manual_style: str,
    lyrics: str,
    vocal_character: str,
) -> dict[str, Any]:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or "local"
    digest = hashlib.sha256(f"demianvelo|{minutes}|{marker}|{manual_style}".encode()).digest()
    style = manual_style or _FALLBACK_STYLES[digest[0] % len(_FALLBACK_STYLES)]
    faith_style = style.startswith("christian_") or style == "christian_electronic"
    base_title = _FALLBACK_TITLES.get(style, "Nueva Musica")
    title = f"{base_title} x DemianVelo"
    description_lines = [
        f"{title} — musica original de DemianVelo.",
        "Produccion y composicion original creada para este lanzamiento, sin copiar melodias ni samples reconocibles.",
        "Videoclip cinematografico con una direccion visual propia y montaje sincronizado con la musica.",
        "Escucha con auriculares para apreciar mejor la mezcla y la dinamica.",
    ]
    if faith_style:
        description_lines[2] = "Una pieza de fe, esperanza y luz con direccion audiovisual cinematografica original."
    return {
        "topic": f"videoclip original {style} con atmosfera cinematografica",
        "music_style": style,
        "faith_theme": faith_style,
        "has_user_lyrics": bool(lyrics),
        "vocal_character": vocal_character,
        "bpm": _FALLBACK_BPM.get(style, 128),
        "title": title,
        "description": "\n".join(description_lines),
        "hashtags": ["#DemianVelo", "#Music", "#MusicaOriginal", "#NuevaMusica"],
        "tags": [
            "DemianVelo", "musica original", "original music", style.replace("_", " "),
            "music video", "videoclip", "nueva musica", "musica 2026",
            "produccion musical", "artista independiente", "cinematic music video",
            "Argentina", "Latin music", "original song",
        ],
        "visual_queries": list(_FALLBACK_VISUALS),
        "visual_direction": "Montaje cinematografico dinamico, luz natural y urbana, paisajes y arquitectura sin marcas ni personas reconocibles.",
        "thumbnail_text": base_title,
        "metadata_source": "local_resilient_fallback",
    }


def generate_music_metadata(
    channel: dict,
    minutes: int,
    manual_style: str = "",
    lyrics: str = "",
    vocal_character: str = "",
) -> dict[str, Any]:
    if minutes not in {1, 5, 10, 30}:
        raise ValueError("DemianVelo admite 1, 5, 10 o 30 minutos.")
    analytics = channel.get("_analytics_digest") or "No hay Analytics disponible; no inventar preferencias de audiencia."
    is_short = minutes == 1
    manual_style = manual_style.strip().lower().replace(" ", "_")
    if manual_style and manual_style not in ALLOWED_STYLES:
        raise ValueError(f"Estilo no soportado: {manual_style}")
    lyrics = lyrics.strip()
    vocal_character = vocal_character.strip() or (
        "voz original calida, magnetica, juvenil-adulta, clara, emocional, con presencia y gancho inmediato; "
        "intima en versos y mas abierta en estribillos, sin imitar a ningun cantante real"
    )

    user_control = ""
    if manual_style:
        user_control += f"\nESTILO ELEGIDO POR EL ARTISTA: {manual_style}. Debes respetarlo."
    if lyrics:
        user_control += (
            "\nLETRA PROPORCIONADA POR EL ARTISTA:\n---\n"
            + lyrics
            + "\n---\nLa letra es material del usuario: NO la reescribas, no cambies palabras y no inventes versos nuevos. "
              "Solo organiza la direccion musical y visual alrededor de ella."
        )
    user_control += f"\nCARACTER VOCAL DESEADO: {vocal_character}"

    prompt = f"""
Eres productor musical, director creativo y estratega de YouTube para el canal de artista DemianVelo.
Duracion objetivo: {minutes} minuto(s). Formato: {'Short vertical 9:16' if is_short else 'video musical horizontal 16:9'}.

IDENTIDAD DEL CANAL:
{channel['master_prompt']}

ANALYTICS DISPONIBLE:
{analytics}
{user_control}

Crea una direccion creativa ORIGINAL para una nueva pieza. Si el artista fijo un estilo, respeta ese estilo. Si no, elige entre progressive_house, electro_house, future_bass, melodic_techno, edm_festival, ambient_electronic, christian_electronic, rkt, trap_melodic, pop_electronic, rkt_trap, christian_pop, christian_trap o christian_rkt.

DIRECCION MUSICAL Y VOCAL:
- RKT: energia urbana bailable, percusion marcada, bajo contundente y sintesis moderna; evitar copiar beats o melodias reconocibles.
- trap_melodic: atmosfera emocional, 808/sintesis original, ritmo moderno y melodias propias.
- pop_electronic: estribillo claro, armonia luminosa, produccion moderna y memorable sin copiar canciones existentes.
- fusiones cristianas: conservar energia moderna pero con clima de fe, esperanza, luz, Jesucristo, gratitud o superacion.
- La voz, cuando el motor vocal premium este disponible, debe sentirse calida, magnetica, expresiva y con personalidad propia. Nada de imitaciones de artistas reales.
- Si hay letra proporcionada, debe cantarse exactamente como fue entregada; no inventar ni sustituir versos.
- Si Analytics muestra estilos/temas con mejor retencion o suscriptores, favorecelos sin repetir titulos, melodias o conceptos.

VISUALES:
Genera 10 consultas de B-roll REAL DE CAMARA en ingles para montaje cinematografico. Evita gobiernos, politica, marcas, conciertos de artistas reconocibles y videoclips ajenos. Para RKT/trap/pop puedes usar ciudad nocturna, calles con luces, autos genericos sin marcas, siluetas, estudio musical generico, moda urbana sin logos, arquitectura, luces, humo escenico, rutas, playas, amaneceres y paisajes. Para contenido cristiano mezcla naturaleza, amaneceres, cielo, arquitectura religiosa generica y luz cinematografica. Cada consulta debe ser distinta.

Devuelve SOLO JSON valido:
{{
  "topic": "concepto audiovisual",
  "music_style": "uno de los estilos permitidos",
  "faith_theme": true,
  "has_user_lyrics": true,
  "vocal_character": "descripcion de voz original",
  "bpm": 128,
  "title": "titulo original, maximo 90 caracteres",
  "description": "descripcion original de 4 a 8 lineas",
  "hashtags": ["#DemianVelo", "#Music", "#..."],
  "tags": ["..."],
  "visual_queries": ["night city cinematic", "... exactly 10"],
  "visual_direction": "direccion de montaje y atmosfera",
  "thumbnail_text": "2 a 5 palabras"
}}

Reglas:
- visual_queries: exactamente 10, ingles, sin marcas.
- bpm entre 85 y 145. Para RKT/trap puedes usar half-time/double-time conceptual si ayuda.
- hashtags 3 a 5; tags 10 a 18.
- title verdadero y no engañoso.
""".strip()

    data: dict[str, Any]
    try:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        data = json.loads(response.text)
        data["metadata_source"] = "gemini"
    except Exception as exc:
        print(f"Gemini metadata no disponible ({exc}); usando metadata original local resiliente.")
        data = _fallback_metadata(minutes, manual_style, lyrics, vocal_character)

    style = manual_style or str(data.get("music_style") or "progressive_house").strip().lower().replace(" ", "_")
    if style not in ALLOWED_STYLES:
        style = "progressive_house"
    queries = [" ".join(str(x).split())[:100] for x in (data.get("visual_queries") or []) if str(x).strip()]
    if len(queries) < 10:
        for item in _FALLBACK_VISUALS:
            if len(queries) >= 10:
                break
            if item not in queries:
                queries.append(item)

    faith_style = style.startswith("christian_") or style == "christian_electronic"
    data["music_style"] = style
    data["faith_theme"] = bool(data.get("faith_theme")) or faith_style
    data["has_user_lyrics"] = bool(lyrics)
    data["user_lyrics"] = lyrics
    data["vocal_character"] = vocal_character
    data["bpm"] = max(85, min(145, int(data.get("bpm") or (95 if "rkt" in style else 128))))
    data["title"] = str(data.get("title") or "DemianVelo - Nueva Musica").strip()[:90]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["visual_queries"] = queries[:10]
    data["thumbnail_text"] = " ".join(str(data.get("thumbnail_text") or data["title"]).split())[:42]
    data["duration_minutes"] = minutes
    data["duration_seconds"] = minutes * 60
    data["is_short"] = is_short
    return data
