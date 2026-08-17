from __future__ import annotations

import hashlib
import os
import time


THEMES = (
    {
        "family": "Salmo 23 y caminar acompañado por Dios",
        "reference": "Salmo 23:1-4",
        "title": "Cuando el camino pesa, recordá quién camina con vos | Salmo 23",
        "hook": "Si hoy sentís que estás caminando solo, este Salmo puede cambiar tu mirada.",
        "lines": (
            "Hay días en que el camino parece demasiado largo y el corazón se cansa antes que los pies, pero el Salmo 23 recuerda que Dios guía con paciencia.",
            "El buen Pastor no promete una vida sin valles; promete su presencia dentro de ellos, una compañía firme cuando la oscuridad intenta ocupar toda la atención.",
            "Tal vez hoy no puedas resolver cada problema, pero sí podés dar el siguiente paso con calma, confiando en que no estás abandonado a tu propia fuerza.",
            "Pedile a Dios discernimiento para reconocer el camino correcto, serenidad para no decidir desde el miedo y humildad para aceptar ayuda cuando la necesites.",
            "La fe también se practica en gestos pequeños: respirar antes de reaccionar, hablar con verdad, cuidar a alguien y descansar sin sentir culpa por detenerte.",
            "Que esta palabra te acompañe hoy: aun en el valle, hay una presencia que sostiene, orienta y devuelve esperanza. Caminá un paso a la vez. Amén.",
        ),
    },
    {
        "family": "Juan 14 y la paz que Jesus ofrece",
        "reference": "Juan 14:27",
        "title": "La paz que Jesús ofrece no depende de un día perfecto | Juan 14:27",
        "hook": "No necesitás que todo esté resuelto para empezar a recuperar la paz.",
        "lines": (
            "Jesús habló de una paz distinta a la tranquilidad momentánea: una paz que puede permanecer incluso cuando alrededor todavía existen preguntas, cambios y preocupaciones.",
            "En Juan 14:27, su invitación no es ignorar lo que duele, sino evitar que el temor se convierta en la única voz que dirige tus decisiones.",
            "Hoy podés reconocer aquello que te inquieta sin dejar que te domine; nombrarlo delante de Dios puede ser el comienzo de una respuesta más serena y sabia.",
            "Hacé una pausa, soltá la necesidad de controlar cada resultado y pedí claridad para ocuparte de lo que sí está en tus manos durante este día.",
            "La paz bíblica no es pasividad: puede impulsarte a pedir perdón, poner un límite sano, trabajar con paciencia o buscar ayuda en el momento adecuado.",
            "Que la paz de Cristo ordene tus pensamientos y te permita avanzar sin apresurarte. Guardá esta verdad para cuando el ruido vuelva a crecer. Amén.",
        ),
    },
    {
        "family": "Isaias 43 y atravesar tiempos dificiles",
        "reference": "Isaías 43:2",
        "title": "Si atravesás una etapa difícil, Isaías 43 tiene una palabra para vos",
        "hook": "Atravesar una dificultad no significa que Dios te haya dejado atrás.",
        "lines": (
            "Isaías 43 presenta aguas profundas y fuego, imágenes de etapas donde parece que todo exige más de lo que podemos dar y la salida todavía no se ve.",
            "La promesa no dice que nunca habrá momentos difíciles; afirma que la presencia de Dios puede acompañarte mientras los atravesás y el miedo pierde autoridad.",
            "Si hoy estás en una transición, una pérdida o una decisión incierta, no necesitás fingir fortaleza; podés llevar tu cansancio a Dios con sinceridad.",
            "Pedí sabiduría para diferenciar lo urgente de lo importante y fuerza para hacer solamente el paso que corresponde hoy, sin cargar también con todo el mañana.",
            "Recordá las veces en que ya atravesaste algo que parecía imposible. La memoria agradecida puede devolverte perspectiva cuando el presente se siente demasiado grande.",
            "Que Isaías 43 te recuerde esto: estás atravesando, no viviendo para siempre en ese lugar. Seguí caminando con fe, paciencia y esperanza. Amén.",
        ),
    },
    {
        "family": "Proverbios 3 y confiar cuando no entendemos",
        "reference": "Proverbios 3:5-6",
        "title": "Cuando no ves el camino completo, hacé esto | Proverbios 3:5-6",
        "hook": "No ver todo el camino no significa que no puedas dar un buen próximo paso.",
        "lines": (
            "Proverbios 3 invita a confiar en Dios de todo corazón y a no depender únicamente de nuestra propia comprensión, especialmente cuando faltan datos o certezas.",
            "Confiar no significa dejar de pensar; significa reconocer que nuestra mirada es limitada y abrir espacio para la oración, el consejo sabio y una decisión humilde.",
            "Si tenés que elegir algo importante, evitá decidir desde la ansiedad. Revisá las opciones, sus consecuencias y pedí a Dios una conciencia clara para discernir.",
            "A veces la dirección correcta no llega como una señal espectacular, sino como coherencia: una puerta honesta, una conversación necesaria o una acción que trae paz.",
            "También puede ser sabio esperar. No toda demora es pérdida de tiempo; algunas pausas evitan decisiones impulsivas y permiten ver detalles que antes estaban ocultos.",
            "Que hoy puedas confiar sin apagar tu inteligencia y pensar sin apagar tu fe. Pedí dirección, actuá con integridad y avanzá con serenidad. Amén.",
        ),
    },
    {
        "family": "Salmo 121 y ayuda en el camino",
        "reference": "Salmo 121:1-8",
        "title": "¿De dónde viene mi ayuda? Una reflexión para hoy | Salmo 121",
        "hook": "Cuando sentís que todo depende de vos, recordá la pregunta del Salmo 121.",
        "lines": (
            "El Salmo 121 comienza levantando la mirada hacia los montes y preguntando de dónde vendrá la ayuda cuando nuestras fuerzas personales parecen insuficientes.",
            "La respuesta dirige la atención al Creador, no para negar nuestras responsabilidades, sino para recordar que nuestra vida no descansa solamente sobre nuestra capacidad.",
            "Hoy quizás necesites ayuda práctica, emocional o espiritual. Pedirla no disminuye tu fe; muchas veces Dios acompaña mediante personas, oportunidades y decisiones prudentes.",
            "Pensá en una carga que estás sosteniendo solo por orgullo o costumbre. Tal vez hoy sea buen momento para iniciar una conversación o aceptar una mano cercana.",
            "El Salmo habla de un Dios atento al camino diario. Esa imagen puede ayudarte a trabajar, viajar, descansar y tomar decisiones con menos temor y más conciencia.",
            "Levantá la mirada sin dejar de mover los pies. Que hoy encuentres la ayuda necesaria y también puedas convertirte en ayuda para otra persona. Amén.",
        ),
    },
    {
        "family": "Mateo 6 y vivir un dia a la vez",
        "reference": "Mateo 6:31-34",
        "title": "Jesús enseñó a no cargar hoy con todo el mañana | Mateo 6",
        "hook": "Tal vez parte de tu cansancio viene de intentar vivir mañana antes de que llegue.",
        "lines": (
            "En Mateo 6, Jesús habla a personas preocupadas por necesidades reales y les enseña a no convertir el futuro en una carga permanente sobre el presente.",
            "La preocupación puede hacernos repetir escenarios que todavía no ocurrieron. La fe propone otra práctica: atender con responsabilidad lo de hoy y confiar el resto a Dios.",
            "Elegí una preocupación concreta y preguntate qué acción útil podés realizar ahora. Si existe una llamada, una conversación o una tarea pendiente, empezá por ahí.",
            "Después soltá aquello que no podés controlar. Orar también es reconocer límites y dejar de exigirle a la mente una respuesta para cada posibilidad futura.",
            "Mirar la creación, como propone Jesús, es recuperar atención sobre la vida presente: respirar, agradecer, trabajar y observar lo que sí está sucediendo hoy.",
            "Que hoy tenga su propio espacio y mañana llegue cuando corresponda. Caminá con responsabilidad, gratitud y confianza en la fidelidad de Dios. Amén.",
        ),
    },
    {
        "family": "Salmo 34 y Dios cerca del corazon herido",
        "reference": "Salmo 34:18",
        "title": "Para el corazón herido: una promesa breve del Salmo 34",
        "hook": "Hay dolores que nadie ve, pero eso no significa que tengas que atravesarlos en silencio.",
        "lines": (
            "El Salmo 34 dice que Dios está cerca de quienes tienen el corazón quebrantado, una frase valiosa cuando el dolor no se puede explicar con facilidad.",
            "La fe no exige sonreír todo el tiempo. Podés reconocer tristeza, decepción o cansancio sin sentir que eso te aleja de Dios; la sinceridad también puede ser oración.",
            "Si algo te hirió, tratá de no convertir esa herida en aislamiento permanente. Elegí una persona confiable y hablá con la claridad que hoy te sea posible.",
            "Cuidar el corazón también incluye descansar, alimentarse bien, pedir ayuda cuando hace falta y alejarse de dinámicas que siguen causando daño innecesario.",
            "Dios puede acompañar procesos que llevan tiempo. No midas tu avance solamente por cómo te sentís hoy; observá también las decisiones saludables que estás aprendiendo.",
            "Que esta promesa te recuerde que tu dolor no es invisible. Buscá compañía, cuidate con paciencia y permití que la esperanza vuelva poco a poco. Amén.",
        ),
    },
    {
        "family": "Romanos 12 y vencer el mal con el bien",
        "reference": "Romanos 12:21",
        "title": "No dejes que el mal decida quién vas a ser | Romanos 12:21",
        "hook": "Responder bien a una herida no es debilidad; a veces es la forma más difícil de ser fuerte.",
        "lines": (
            "Romanos 12:21 resume una decisión exigente: no ser vencidos por el mal, sino vencer el mal haciendo el bien, sin convertirnos en aquello que nos dañó.",
            "Eso no significa permitir abusos ni ignorar límites. Hacer el bien puede incluir decir no, tomar distancia, pedir justicia y negarse a responder desde el odio.",
            "Antes de reaccionar a una ofensa, preguntate qué respuesta protege tu dignidad sin alimentar el conflicto. A veces una pausa evita palabras que después pesan mucho.",
            "También existe un bien silencioso: no difundir rumores, no celebrar la caída de otro y elegir hablar con verdad incluso cuando sería fácil devolver la misma moneda.",
            "Jesús enseñó un amor que no depende de que el otro lo merezca, pero ese amor también camina con sabiduría, límites y respeto por la verdad.",
            "Que hoy el dolor no escriba tu carácter. Elegí una acción concreta de bien compatible con la justicia, la prudencia y la paz. Amén.",
        ),
    },
)


def build_fast_metadata(base_metadata: dict, channel: dict, previous: list[dict]) -> dict:
    recent = {
        str(row.get("content_family") or row.get("topic") or "").lower().strip()
        for row in previous[-20:]
    }
    available = [theme for theme in THEMES if theme["family"].lower() not in recent]
    pool = available or list(THEMES)
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "") or str(time.time_ns())
    index = int(hashlib.sha256(marker.encode("utf-8")).hexdigest()[:12], 16) % len(pool)
    theme = pool[index]

    count = int(channel.get("scenes_per_short") or 6)
    rows = list(base_metadata.get("scenes") or [])
    while len(rows) < count:
        rows.append({})
    for idx in range(count):
        rows[idx]["narration"] = theme["lines"][idx % len(theme["lines"])]

    base_metadata["scenes"] = rows[:count]
    base_metadata["content_family"] = theme["family"]
    base_metadata["topic"] = theme["family"]
    base_metadata["title"] = theme["title"]
    base_metadata["hook"] = theme["hook"]
    base_metadata["bible_reference"] = theme["reference"]
    base_metadata["description"] = f"Reflexión cristiana inspirada en {theme['reference']} para vivir la fe en lo cotidiano."
    base_metadata["cta"] = "Si esta reflexión te ayudó, guardala para volver a escucharla cuando la necesites."
    base_metadata["metadata_provider"] = "local_unique_biblical:fast_voice_quota_reserved:v2"
    return base_metadata
