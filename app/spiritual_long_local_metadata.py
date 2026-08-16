from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .spiritual_visual_library import enrich_visual_prompt, image_model_candidates, visual_config

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "config" / "dioshablahoyia_bible_references.json"

_BLOCKS = (
    "La fe bíblica no exige fingir que todo está bien. Podemos reconocer el cansancio, el miedo o la incertidumbre y aun así buscar una respuesta que nazca de la verdad, la paciencia y la esperanza. Orar es abrir el corazón con sinceridad, agradecer lo que todavía sostiene nuestra vida y pedir sabiduría para dar el próximo paso sin herirnos ni herir a quienes caminan a nuestro lado.",
    "Una enseñanza puede volverse práctica cuando pasa de las palabras a las decisiones. Podemos escuchar antes de juzgar, pedir perdón cuando corresponde, acompañar a quien está solo, compartir con quien necesita ayuda y cuidar la manera en que hablamos. La espiritualidad no debería alejarnos de la humanidad del otro; debería hacernos más atentos, compasivos y responsables en lo cotidiano.",
    "Hay momentos en los que no vemos una salida inmediata. En lugar de transformar esa espera en desesperación, podemos usarla para ordenar lo que sí está a nuestro alcance: descansar mejor, pedir consejo, reconocer límites, volver a conversar, buscar ayuda y sostener una oración sencilla. La esperanza no siempre cambia las circunstancias de inmediato, pero puede cambiar la forma en que las atravesamos.",
    "La Biblia reúne historias de personas con dudas, errores, pérdidas y nuevos comienzos. Su valor no está en presentarlas como seres perfectos, sino en mostrar procesos de confianza, arrepentimiento, perseverancia y misericordia. Al mirar esos relatos con contexto, podemos aprender sin convertir cada detalle en una promesa automática para nuestra propia vida ni usar la fe como una fórmula para controlar el futuro.",
    "Cuando una preocupación vuelve una y otra vez, puede ayudarnos separar lo que podemos resolver hoy de aquello que todavía debemos esperar. Podemos presentar ambas cosas en oración y después actuar sobre la primera parte con responsabilidad. La paz espiritual no significa indiferencia; puede ser la claridad suficiente para responder con menos impulsividad, más prudencia y una mirada más amplia.",
    "La gratitud también puede entrenarse sin negar el dolor. Agradecer una persona, un gesto, un alimento, una oportunidad, la naturaleza o la posibilidad de empezar de nuevo puede abrir una pequeña ventana de luz en un día difícil. Esa gratitud se vuelve más profunda cuando nos mueve a compartir, cuidar y reconocer que otras personas también están librando batallas que no siempre vemos.",
    "El amor al prójimo se vuelve concreto en gestos pequeños. Una llamada, una escucha sin interrupciones, una ayuda práctica, una palabra respetuosa o la decisión de no devolver una ofensa con otra ofensa pueden cambiar el tono de una relación. Hacer el bien no garantiza que todo salga como deseamos, pero sí nos ayuda a elegir quién queremos ser cuando las circunstancias son difíciles.",
    "La oración puede tener muchas formas. A veces será una petición; otras, una expresión de gratitud, una confesión, una intercesión por alguien o simplemente un momento de silencio interior acompañado por una frase sencilla. No necesitamos producir palabras perfectas para acercarnos a Dios. Podemos hablar desde nuestra realidad y permitir que ese momento nos prepare para vivir con mayor humildad y compasión.",
    "La esperanza cristiana mira más allá del resultado inmediato y, al mismo tiempo, nos invita a vivir responsablemente en el presente. Si deseamos un mundo con más paz, podemos empezar por nuestras conversaciones. Si deseamos más misericordia, podemos practicarla. Si deseamos que alguien se sienta acompañado, podemos acercarnos. La fe madura cuando inspira acciones coherentes con el bien que decimos creer.",
    "También la creación puede recordarnos paciencia y cuidado. Los ciclos de la naturaleza, los animales y los paisajes no necesitan convertirse en pruebas sobrenaturales para inspirarnos. Pueden invitarnos a contemplar, agradecer y asumir responsabilidad por la vida que compartimos. Una mirada de fe puede reconocer belleza sin dejar de respetar la realidad, la ciencia, el cuidado y la dignidad de cada ser vivo.",
    "Perseverar no es repetir indefinidamente algo que nos hace daño. A veces perseverar significa cambiar de estrategia, pedir ayuda profesional, establecer un límite sano o aceptar que un camino terminó. La sabiduría espiritual también incluye discernir. Podemos pedir fortaleza para continuar cuando corresponde y humildad para cambiar cuando ese sea el paso más responsable y amoroso.",
    "Cuando hablamos de promesas y profecías bíblicas, el contexto importa. Diferentes tradiciones cristianas pueden comprender algunos pasajes de maneras distintas. Por eso es más honesto estudiar el texto, reconocer lo que es claro, diferenciar interpretación de certeza y evitar usar fechas, miedo o noticias actuales para afirmar cosas que la Escritura no dice de manera explícita. La fe no necesita sensacionalismo para tener profundidad.",
    "La paz que buscamos puede comenzar con una pausa consciente antes de reaccionar. Respirar, orar, revisar nuestras palabras y pensar en las consecuencias puede evitar heridas innecesarias. Esa pequeña disciplina no resuelve todos los conflictos, pero crea espacio para una respuesta más parecida a la paciencia, la bondad y el dominio propio que tantas enseñanzas cristianas valoran.",
    "Nadie atraviesa la vida sin necesitar apoyo. La comunidad puede ser una forma concreta de cuidado cuando escucha, acompaña, comparte recursos y respeta los límites de cada persona. La fe no debería aislarnos de la ayuda disponible. Pedir acompañamiento espiritual, familiar, médico o profesional cuando hace falta también puede ser una decisión responsable y valiente.",
    "Podemos cerrar esta parte con una oración sencilla: Dios, danos claridad para reconocer lo verdadero, fortaleza para hacer el bien cuando cuesta, humildad para corregir nuestros errores y sensibilidad para notar a quien necesita compañía. Ayudanos a no usar la fe para juzgar o asustar, sino para crecer en amor, esperanza, responsabilidad y servicio hacia los demás.",
    "Ahora pensemos en una acción concreta para hoy. Tal vez sea agradecer a alguien, reparar una conversación, ayudar con algo práctico, compartir tiempo, cuidar un animal, acompañar a una persona mayor, ofrecer una disculpa o simplemente escuchar. La reflexión se vuelve más valiosa cuando deja una huella pequeña pero real en nuestra manera de tratar a otros y de cuidar lo que nos rodea.",
)


def _marker(minutes: int) -> int:
    raw = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or datetime.now(timezone.utc).isoformat()
    return int(hashlib.sha256(f"local-long|{minutes}|{raw}".encode()).hexdigest()[:8], 16)


def _words(text: str) -> int:
    return len(text.split())


def _narration(target_words: int, section_index: int, seed: int, reference: str, theme: str) -> str:
    intro = (
        f"En esta parte tomamos como referencia {reference}. La idea central que vamos a considerar es {theme}. "
        "No vamos a convertir esta reflexión en una cita textual ni en una promesa automática; vamos a mirar el tema con respeto por su contexto y pensar cómo puede orientarnos hoy."
    )
    pieces = [intro]
    cursor = 0
    while sum(_words(x) for x in pieces) < target_words and cursor < len(_BLOCKS) * 2:
        block = _BLOCKS[(seed + section_index * 3 + cursor * 5) % len(_BLOCKS)]
        if block not in pieces:
            pieces.append(block)
        cursor += 1
    return " ".join(pieces)


def generate_local_long_metadata(channel: dict, minutes: int) -> dict:
    refs = json.loads(REFS.read_text(encoding="utf-8"))
    sections_count = max(5, minutes // 2)
    seed = _marker(minutes)
    start = seed % len(refs)
    chosen = [refs[(start + i * 7) % len(refs)] for i in range(sections_count)]
    target_words = max(120, round((minutes * 128) / sections_count))

    sections = []
    visual_manifest = []
    for index, item in enumerate(chosen):
        reference = str(item["reference"])
        theme = str(item["theme"])
        visual_meta = {
            "topic": theme,
            "title": f"{theme} | Oración, Biblia, fe y esperanza",
            "bible_reference": reference,
        }
        base_prompt = (
            "Recurring synthetic photoreal human representation of Jesus speaking calmly with natural human body language, "
            "premium cinematic live-action look, realistic environment and movement, no text and no logos"
        )
        visual_prompt, selected = enrich_visual_prompt(
            base_prompt,
            visual_meta,
            index,
            aspect="horizontal 16:9",
        )
        sections.append({
            "heading": f"Reflexión {index + 1}: {reference}",
            "bible_reference": reference,
            "visual_prompt": visual_prompt,
            "visual_theme": selected,
            "narration": _narration(target_words, index, seed, reference, theme),
        })
        visual_manifest.append(selected)

    topic = str(chosen[0]["theme"]).split(";")[0].strip().capitalize()
    return {
        "topic": topic,
        "title": f"{topic} | Oración, Biblia, fe y esperanza"[:95],
        "description": (
            "Reflexión cristiana original sobre Biblia, oración, fe, esperanza y acciones de bien. "
            "Las referencias se explican de forma contextual y se prefieren paráfrasis antes que citas extensas."
        ),
        "hashtags": ["#Dios", "#Jesus", "#Biblia", "#Fe", "#Oracion"],
        "tags": ["dios", "jesus", "biblia", "fe", "esperanza", "oracion", "reflexion cristiana", "dios habla hoy", "paz", "amor al projimo"],
        "sections": sections,
        "duration_seconds": minutes * 60,
        "target_minutes": minutes,
        "contains_synthetic_media": True,
        "metadata_provider": "local_resilient_bible_library_with_daily_visual_rotation",
        "reference_seed": chosen,
        "visual_rotation_manifest": visual_manifest,
        "visual_engine_version": str(visual_config().get("version") or "visual-library-v1"),
        "visual_image_models": image_model_candidates(),
        "visual_norway_enabled": True,
        "visual_noahs_ark_enabled": True,
    }
