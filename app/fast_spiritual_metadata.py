from __future__ import annotations

import hashlib
import os
import re
import time
from difflib import SequenceMatcher


THEMES = (
    ("Salmo 23 y el Buen Pastor", "Salmo 23:1-4", "Dios guía incluso cuando el camino atraviesa un valle", "dar el siguiente paso con calma y pedir dirección"),
    ("Juan 14 y la paz de Jesus", "Juan 14:27", "la paz de Cristo puede permanecer aun cuando no todo esté resuelto", "nombrar la preocupación y entregar a Dios lo que no podés controlar"),
    ("Isaias 43 y atravesar pruebas", "Isaías 43:2", "atravesar aguas profundas no significa caminar sin la presencia de Dios", "hacer hoy solamente el paso que corresponde"),
    ("Proverbios 3 y confiar en Dios", "Proverbios 3:5-6", "la sabiduría bíblica invita a confiar sin apagar el discernimiento", "orar, revisar opciones y decidir con integridad"),
    ("Salmo 121 y la ayuda de Dios", "Salmo 121:1-8", "la ayuda no depende únicamente de nuestras propias fuerzas", "pedir ayuda con humildad y seguir avanzando"),
    ("Mateo 6 y vivir un dia a la vez", "Mateo 6:31-34", "Jesús enseña a no cargar hoy con todos los problemas de mañana", "resolver una acción concreta del presente y soltar el resto"),
    ("Salmo 34 y el corazon herido", "Salmo 34:18", "Dios está cerca de quienes atraviesan dolor y quebranto", "buscar compañía, descanso y una oración sincera"),
    ("Romanos 12 y vencer el mal con el bien", "Romanos 12:21", "el mal no tiene que decidir en qué persona nos convertimos", "responder con límites, verdad y una acción de bien"),
    ("Filipenses 4 y entregar la ansiedad", "Filipenses 4:6-7", "la oración abre espacio para una paz que no depende de tener todas las respuestas", "convertir una preocupación concreta en una oración concreta"),
    ("Josue 1 y avanzar con valentia", "Josué 1:9", "la valentía bíblica no elimina el miedo, pero evita que el miedo gobierne", "dar un paso responsable confiando en que Dios acompaña"),
    ("Isaias 41 y no vivir dominado por el miedo", "Isaías 41:10", "Dios promete sostener y fortalecer al que se siente débil", "recordar una verdad bíblica antes de tomar una decisión desde el temor"),
    ("Mateo 11 y descansar en Jesus", "Mateo 11:28-30", "Jesús invita a los cansados a acercarse y encontrar descanso", "soltar una carga innecesaria y aceptar ayuda"),
    ("Romanos 8 y Dios obrando en medio de todo", "Romanos 8:28", "la fe puede confiar aun cuando todavía no entiende cómo encajan las circunstancias", "mirar el día con paciencia y elegir una respuesta fiel"),
    ("Romanos 8 y orar cuando faltan palabras", "Romanos 8:26-27", "la oración no deja de ser válida cuando el cansancio nos deja sin palabras", "presentarse ante Dios con sinceridad aunque solo haya silencio"),
    ("Salmo 46 y encontrar refugio", "Salmo 46:1-3", "Dios es presentado como refugio y fortaleza en momentos de inestabilidad", "detener el ruido, respirar y recordar dónde está la seguridad"),
    ("Salmo 91 y habitar bajo el cuidado de Dios", "Salmo 91:1-2", "el salmo habla de refugio y confianza en medio de la incertidumbre", "repetir una promesa bíblica y actuar con prudencia"),
    ("1 Pedro 5 y soltar preocupaciones", "1 Pedro 5:7", "la Biblia invita a depositar las preocupaciones en Dios porque Él cuida de nosotros", "identificar una carga y dejar de sostenerla en soledad"),
    ("Juan 10 y Jesus como Buen Pastor", "Juan 10:11-14", "Jesús describe un cuidado personal que conoce y acompaña", "escuchar su enseñanza y elegir un camino de paz y verdad"),
    ("Juan 8 y Jesus como luz", "Juan 8:12", "seguir a Jesús ofrece dirección cuando el camino parece confuso", "buscar claridad para el próximo paso en lugar de exigir ver todo el futuro"),
    ("Marcos 4 y Jesus calma la tormenta", "Marcos 4:39-40", "la tormenta no impide que Jesús esté presente con sus discípulos", "separar el peligro real del miedo que amplifica todo"),
    ("Lucas 10 y el Buen Samaritano", "Lucas 10:33-37", "el amor al prójimo se vuelve concreto cuando alguien decide detenerse y ayudar", "hacer hoy una obra de misericordia posible y prudente"),
    ("Lucas 15 y volver a casa", "Lucas 15:20-24", "la parábola muestra un padre que recibe con misericordia al que regresa", "dar un paso de arrepentimiento, reconciliación o nuevo comienzo"),
    ("Genesis 9 y la esperanza despues de la tormenta", "Génesis 9:12-16", "el arco después del diluvio recuerda pacto, memoria y esperanza", "mirar lo que sobrevivió a la tormenta y agradecer por un nuevo comienzo"),
    ("Exodo 14 y avanzar cuando parece no haber salida", "Éxodo 14:13-16", "Israel enfrentó un momento donde el camino parecía cerrado", "dejar de paralizarse y hacer la parte que sí corresponde"),
    ("Exodo 16 y confiar en la provision diaria", "Éxodo 16:4", "el maná enseña una dependencia diaria en vez de vivir atrapados por el mañana", "agradecer lo suficiente para hoy y administrar con responsabilidad"),
    ("1 Reyes 17 y la provision inesperada", "1 Reyes 17:4-6", "Elías recibió sustento de una manera que no habría podido planificar", "mantenerse atento a soluciones humildes e inesperadas"),
    ("Jonas 2 y clamar desde la profundidad", "Jonás 2:1-2", "Jonás oró desde un lugar de oscuridad y reconoció que todavía podía dirigirse a Dios", "dejar de huir y comenzar una oración honesta"),
    ("Daniel 6 y permanecer fiel", "Daniel 6:10", "Daniel mantuvo su práctica de oración incluso bajo presión", "sostener una convicción sin responder con violencia ni arrogancia"),
    ("Salmo 27 y esperar con confianza", "Salmo 27:13-14", "esperar en Dios no es resignarse sino fortalecer el corazón mientras llega claridad", "usar la espera para prepararse, orar y actuar con paciencia"),
    ("Salmo 30 y recordar que la noche no dura para siempre", "Salmo 30:5", "el salmo contrasta el llanto de la noche con una mañana que puede traer alegría", "permitirse sentir sin convertir el dolor presente en una sentencia permanente"),
    ("Lamentaciones 3 y misericordias nuevas", "Lamentaciones 3:22-23", "en medio del dolor aparece la memoria de una misericordia que se renueva", "empezar el día agradeciendo una oportunidad concreta de volver a intentar"),
    ("Efesios 4 y practicar el perdon", "Efesios 4:31-32", "la vida cristiana llama a abandonar amargura y cultivar compasión", "perdonar con sabiduría sin negar límites ni verdad"),
    ("Santiago 1 y pedir sabiduria", "Santiago 1:5", "cuando falta claridad la Biblia invita a pedir sabiduría a Dios", "hacer preguntas mejores antes de apresurarse a decidir"),
    ("Miqueas 6 y caminar con humildad", "Miqueas 6:8", "la fe se expresa haciendo justicia, amando misericordia y caminando humildemente", "elegir una acción pequeña que combine verdad y compasión"),
    ("Mateo 5 y ser luz con buenas obras", "Mateo 5:14-16", "Jesús relaciona la luz con obras que ayudan a otros y apuntan a Dios", "hacer algo bueno sin buscar reconocimiento personal"),
)

INTRO_STYLES = (
    "Tal vez hoy necesitás escuchar una verdad sencilla:",
    "Antes de seguir con el día, considerá esta enseñanza bíblica:",
    "Cuando la mente se llena de preguntas, la Biblia ofrece una perspectiva diferente:",
    "Hay momentos en que una sola verdad puede ordenar el corazón:",
    "Si hoy sentís que llevás demasiado peso, recordá esto:",
    "Una enseñanza antigua puede hablar con mucha claridad a lo que vivís hoy:",
)

BRIDGE_STYLES = (
    "Eso no significa negar la realidad; significa mirarla sin entregarle todo el control al miedo.",
    "La fe bíblica no reemplaza la responsabilidad: la acompaña con esperanza, prudencia y oración.",
    "Dios no nos invita a fingir que nada duele, sino a atravesarlo sin perder dirección.",
    "La confianza no exige entender cada detalle antes de avanzar; sí invita a caminar con integridad.",
    "Muchas veces la respuesta comienza cuando dejamos de intentar resolverlo todo al mismo tiempo.",
    "Esta enseñanza no promete una vida sin problemas, pero sí cambia la manera de enfrentarlos.",
)

CLOSINGS = (
    "Que esta palabra te acompañe durante el resto del día y te ayude a caminar con fe, serenidad y esperanza. Amén.",
    "Llevá esta verdad a tu oración de hoy y permití que produzca una decisión más tranquila y fiel. Amén.",
    "No necesitás resolver toda tu historia ahora; caminá con Dios en el próximo paso que sí podés dar. Amén.",
    "Que Dios te conceda claridad para decidir, paciencia para esperar y fuerza para perseverar en el bien. Amén.",
    "Guardá esta enseñanza para cuando vuelva el ruido y recordá que la fe también se construye un día a la vez. Amén.",
    "Que la Palabra de Dios vuelva a ordenar tu mirada y te recuerde que la esperanza todavía tiene lugar. Amén.",
)


def _clean(text: str) -> str:
    text = " ".join(str(text or "").split()).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ\s]", " ", text)
    return " ".join(text.split())


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()


def _candidate(theme: tuple[str, str, str, str], style: int, count: int) -> dict:
    family, reference, truth, practice = theme
    intro = INTRO_STYLES[style % len(INTRO_STYLES)]
    bridge = BRIDGE_STYLES[(style * 3 + 1) % len(BRIDGE_STYLES)]
    close = CLOSINGS[(style * 5 + 2) % len(CLOSINGS)]
    lines = [
        f"{intro} {truth}.",
        f"En {reference}, la atención vuelve a Dios y a una forma de vivir que no queda gobernada solamente por las circunstancias.",
        bridge,
        f"Una aplicación concreta para hoy puede ser {practice}.",
        "Hacé una pausa y preguntate qué parte de esta enseñanza necesitás convertir en una decisión, una conversación, una oración o un acto de amor.",
        close,
    ]
    while len(lines) < count:
        lines.append(lines[len(lines) % 6])
    title_prefixes = ("Una palabra para hoy", "Cuando necesitás dirección", "Una verdad bíblica para recordar", "Fe para este momento")
    title = f"{title_prefixes[style % len(title_prefixes)]} | {reference}"
    topic = f"{family} — enfoque {style + 1}"
    script = _clean(" ".join(lines[:count]))
    return {
        "family": topic,
        "topic": topic,
        "reference": reference,
        "title": title,
        "hook": intro,
        "lines": lines[:count],
        "script": script,
        "script_hash": hashlib.sha256(script.encode("utf-8")).hexdigest(),
    }


def _passes_recent(candidate: dict, previous: list[dict]) -> bool:
    recent = [row for row in previous if str(row.get("status") or "") == "uploaded"][-30:]
    for old in recent:
        old_hash = str(old.get("script_hash") or "").strip()
        if old_hash and old_hash == candidate["script_hash"]:
            return False
        old_preview = _clean(str(old.get("narration_preview") or ""))
        if old_preview and _sim(candidate["script"][:1200], old_preview) >= 0.75:
            return False
        old_title = str(old.get("title") or "")
        old_topic = str(old.get("topic") or "")
        if old_title and old_topic:
            if _sim(candidate["title"], old_title) >= 0.80 and _sim(candidate["topic"], old_topic) >= 0.84:
                return False
    return True


def build_fast_metadata(base_metadata: dict, channel: dict, previous: list[dict]) -> dict:
    count = int(channel.get("scenes_per_short") or 6)
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or str(time.time_ns())
    seed = int(hashlib.sha256(marker.encode("utf-8")).hexdigest()[:16], 16)

    chosen = None
    for offset in range(len(THEMES)):
        theme = THEMES[(seed + offset) % len(THEMES)]
        for style_offset in range(len(INTRO_STYLES)):
            style = (seed + offset + style_offset) % len(INTRO_STYLES)
            candidate = _candidate(theme, style, count)
            if _passes_recent(candidate, previous):
                chosen = candidate
                break
        if chosen is not None:
            break

    if chosen is None:
        theme = THEMES[seed % len(THEMES)]
        chosen = _candidate(theme, (seed // len(THEMES)) % len(INTRO_STYLES), count)

    rows = list(base_metadata.get("scenes") or [])
    while len(rows) < count:
        rows.append({})
    for idx in range(count):
        rows[idx]["narration"] = chosen["lines"][idx]

    base_metadata["scenes"] = rows[:count]
    base_metadata["content_family"] = chosen["family"]
    base_metadata["topic"] = chosen["topic"]
    base_metadata["title"] = chosen["title"]
    base_metadata["hook"] = chosen["hook"]
    base_metadata["bible_reference"] = chosen["reference"]
    base_metadata["description"] = (
        f"Reflexión cristiana inspirada en {chosen['reference']} para fortalecer la fe, "
        "la esperanza y la confianza en Dios en la vida cotidiana."
    )
    base_metadata["cta"] = "Si esta palabra te ayudó, guardala para volver a escucharla cuando la necesites."
    base_metadata["metadata_provider"] = "local_unique_biblical:prechecked_against_history:v3"
    return base_metadata
