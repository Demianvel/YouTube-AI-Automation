from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from .history import similarity


ENGINE_VERSION = "dhh-premium-editorial-v7"

# These themes deliberately preserve the emotional shape of older successful
# channel formats (refuge, peace, prayer, trust, rest and faith in storms) while
# using additional biblical references and original wording. This gives the
# anti-spam guard genuinely new material instead of weakening its thresholds.
THEMES: tuple[dict[str, str], ...] = (
    {
        "family": "refugio cuando el mundo se siente inestable",
        "reference": "Nahúm 1:7",
        "angle": "Dios como lugar seguro en un día difícil",
        "truth": "la fe puede recordar que la bondad y el cuidado de Dios siguen siendo un refugio cuando alrededor hay incertidumbre",
        "context": "Nahúm habla en un contexto de tensión y recuerda que confiar en Dios no equivale a ignorar la realidad",
        "practice": "separar lo que realmente podés resolver hoy de aquello que necesitás entregar en oración",
        "visual": "Jesus on a windswept hillside after rain, dark clouds opening to warm natural sunlight, realistic live-action human appearance",
    },
    {
        "family": "descansar el alma sin escapar de la realidad",
        "reference": "Salmo 62:5-8",
        "angle": "silencio interior y confianza",
        "truth": "el corazón puede buscar quietud en Dios sin fingir que los problemas dejaron de existir",
        "context": "el salmo une esperanza, confianza y la invitación a abrir el corazón delante de Dios",
        "practice": "hacer una pausa breve, nombrar con sinceridad tu preocupación principal y pedir dirección para el próximo paso",
        "visual": "Jesus beside a quiet alpine lake before sunrise, subtle mist and natural reflections, cinematic live-action photography",
    },
    {
        "family": "paz para una mente que no deja de pensar",
        "reference": "Isaías 26:3",
        "angle": "volver a enfocar la mente en Dios",
        "truth": "la paz bíblica también se cultiva cuando la mente vuelve una y otra vez a una confianza firme en Dios",
        "context": "Isaías presenta una esperanza que no depende de controlar cada circunstancia sino de dónde se apoya el corazón",
        "practice": "interrumpir por un momento el ciclo de pensamientos y recordar una verdad que te ayude a actuar con serenidad",
        "visual": "Jesus walking through a mountain valley at first light, calm face, realistic linen robe, soft physically plausible sun rays",
    },
    {
        "family": "dejar que la paz gobierne las reacciones",
        "reference": "Colosenses 3:15",
        "angle": "responder desde la paz y no desde el impulso",
        "truth": "seguir a Cristo incluye aprender a dejar que la paz oriente nuestras reacciones y relaciones",
        "context": "la enseñanza aparece junto a llamados a la compasión, la paciencia y una vida compartida con gratitud",
        "practice": "demorar una respuesta impulsiva y elegir palabras que combinen verdad, respeto y calma",
        "visual": "Jesus in a sunlit olive grove extending an open hand, natural human skin and fabric, documentary biblical cinema",
    },
    {
        "family": "confiar cuando todavía no ves resultados",
        "reference": "Jeremías 17:7-8",
        "angle": "raíces profundas en tiempos secos",
        "truth": "la confianza en Dios puede parecerse a un árbol con raíces profundas que sigue recibiendo sustento aun en una temporada difícil",
        "context": "Jeremías usa una imagen de raíces y agua para contrastar una vida sostenida por confianza con una vida dominada por el temor",
        "practice": "fortalecer hoy una raíz concreta: oración, consejo sabio, descanso responsable o una decisión íntegra",
        "visual": "Jesus near a large tree beside clear running water, realistic roots and leaves moving in wind, cinematic natural light",
    },
    {
        "family": "esperanza cuando hay presión por todos lados",
        "reference": "2 Corintios 4:8-9",
        "angle": "golpeados pero no abandonados",
        "truth": "la dificultad puede apretar sin tener la última palabra sobre nuestra identidad, nuestra fe o nuestro futuro",
        "context": "Pablo describe presión y fragilidad sin convertirlas en derrota definitiva, señalando una esperanza que persevera",
        "practice": "pedir ayuda antes de aislarte y elegir una pequeña acción fiel en medio de lo que hoy no podés cambiar",
        "visual": "Jesus on a rocky coast after a storm, powerful sea becoming calmer, realistic human profile and natural overcast light",
    },
    {
        "family": "fuerza suficiente para la debilidad de hoy",
        "reference": "2 Corintios 12:9",
        "angle": "no esconder la fragilidad",
        "truth": "la vida de fe no exige aparentar fortaleza todo el tiempo; también puede reconocer límites y recibir gracia",
        "context": "Pablo habla de una debilidad que no desaparece de inmediato y aprende a mirar de otra manera la suficiencia de la gracia",
        "practice": "dejar de exigirte perfección por un momento y pedir la ayuda concreta que necesitás para continuar con responsabilidad",
        "visual": "Jesus seated on a simple stone overlooking a valley, compassionate expression, subtle sunrise, photoreal live-action biblical scene",
    },
    {
        "family": "seguir haciendo el bien cuando llega el cansancio",
        "reference": "Gálatas 6:9",
        "angle": "perseverancia sin agotarse por demostrar nada",
        "truth": "perseverar en el bien no significa correr sin descanso, sino no abandonar el propósito cuando el fruto tarda en verse",
        "context": "la carta anima a sostener una vida de bien y servicio sin convertir la demora en una razón para rendirse",
        "practice": "elegir una acción buena y sostenible para hoy, sin intentar resolver en una tarde lo que requiere un proceso",
        "visual": "Jesus walking along a long rural path at golden hour, realistic footsteps, wind in linen clothing, cinematic depth",
    },
    {
        "family": "una mente guiada por amor y dominio propio",
        "reference": "2 Timoteo 1:7",
        "angle": "miedo, amor y sensatez",
        "truth": "el temor no necesita gobernar cada decisión; la fe también llama a cultivar amor, fortaleza interior y dominio propio",
        "context": "Pablo anima a Timoteo a no vivir paralizado, vinculando el valor con una vida sobria y orientada al bien",
        "practice": "antes de decidir, preguntarte si estás reaccionando sólo por miedo o si podés responder con amor, prudencia y claridad",
        "visual": "Jesus at blue hour holding a small oil lamp on a stone path, realistic flame, natural human features, cinematic low light",
    },
    {
        "family": "acercarse a Dios con confianza cuando cuesta orar",
        "reference": "Hebreos 4:15-16",
        "angle": "una oración honesta sin actuación",
        "truth": "podés acercarte a Dios con sinceridad incluso cuando llegás cansado, confundido o sin palabras bonitas",
        "context": "Hebreos presenta a Jesús como alguien que comprende la fragilidad humana e invita a acercarse en busca de misericordia y ayuda",
        "practice": "hacer una oración sencilla con tres cosas: lo que sentís, lo que necesitás y el paso para el que pedís sabiduría",
        "visual": "Jesus in a quiet stone room near an open doorway filled with morning light, intimate live-action cinematic realism",
    },
    {
        "family": "pedir, buscar y llamar sin convertir la fe en una fórmula",
        "reference": "Mateo 7:7-11",
        "angle": "oración perseverante con confianza",
        "truth": "Jesús anima a pedir y buscar con confianza, no como una técnica para controlar a Dios sino como una relación perseverante",
        "context": "la enseñanza compara el cuidado de un padre con la bondad de Dios y orienta la oración hacia una confianza relacional",
        "practice": "formular una petición concreta y acompañarla con una decisión responsable que esté en tus manos",
        "visual": "Jesus speaking gently on a green hillside to a small distant group, premium live-action biblical photography, natural daylight",
    },
    {
        "family": "mirar a Jesus cuando el miedo crece sobre las olas",
        "reference": "Mateo 14:28-31",
        "angle": "fe en medio del viento",
        "truth": "el miedo puede crecer cuando miramos solamente el viento, pero la historia de Pedro también muestra que es posible volver a pedir ayuda",
        "context": "el relato no idealiza a Pedro; muestra una mezcla humana de valentía, miedo y una mano extendida cuando empieza a hundirse",
        "practice": "identificar qué ruido está concentrando toda tu atención y volver a enfocar el próximo paso posible con fe y prudencia",
        "visual": "Jesus on dark moving water reaching toward a disciple, realistic Sea of Galilee storm, reverent live-action cinema, no spectacle",
    },
    {
        "family": "tener paz aun sabiendo que habrá dificultades",
        "reference": "Juan 16:33",
        "angle": "ánimo sin negar los problemas",
        "truth": "Jesús no promete una vida sin dificultades; ofrece una paz y un ánimo que pueden coexistir con ellas",
        "context": "estas palabras aparecen cerca de una despedida difícil, por eso la esperanza del pasaje no depende de un escenario cómodo",
        "practice": "dejar de exigir que todo esté resuelto para recuperar la calma y concentrarte en la respuesta fiel que sí podés elegir hoy",
        "visual": "Jesus on a shoreline as storm clouds break into warm light, realistic waves and wind, premium photoreal biblical cinema",
    },
    {
        "family": "volver a descansar después de una jornada pesada",
        "reference": "Salmo 116:7",
        "angle": "hablarle al alma con esperanza",
        "truth": "a veces necesitamos recordarnos a nosotros mismos que descansar también puede ser una respuesta de confianza y gratitud",
        "context": "el salmista mira hacia atrás, reconoce ayuda recibida y se invita a recuperar el reposo en vez de vivir permanentemente en alerta",
        "practice": "cerrar una tarea pendiente por hoy, agradecer algo concreto y permitirte un descanso que cuide tu cuerpo y tu mente",
        "visual": "Jesus beside a quiet fire at dusk under a wide sky, peaceful realistic human figure, natural warm practical light",
    },
    {
        "family": "una presencia que acompaña el camino que viene",
        "reference": "Éxodo 33:14",
        "angle": "presencia y descanso antes de avanzar",
        "truth": "antes de pensar sólo en llegar, la fe puede volver a la pregunta por quién acompaña el camino",
        "context": "Moisés enfrenta una enorme responsabilidad y el relato conecta la presencia de Dios con el descanso que necesita para seguir",
        "practice": "antes de una decisión importante, hacer silencio, revisar tus motivos y pedir sabiduría para avanzar sin desesperación",
        "visual": "Jesus-like artistic biblical figure walking through a broad desert valley at dawn, respectful live-action realism, soft light",
    },
    {
        "family": "confiar en que Dios va delante sin conocer todo el mapa",
        "reference": "Deuteronomio 31:8",
        "angle": "caminar sin sentirte abandonado",
        "truth": "no conocer todos los detalles del futuro no significa que tengas que caminar dominado por la sensación de abandono",
        "context": "la transición de liderazgo hacia Josué viene acompañada por un llamado a la valentía y a confiar en la presencia de Dios",
        "practice": "preparar bien el próximo paso y dejar de castigarte por no poder anticipar cada curva del camino",
        "visual": "Jesus walking ahead on a mountain trail with distant sunlight, realistic human proportions, documentary cinematic look",
    },
    {
        "family": "esperar el amanecer cuando la noche se hace larga",
        "reference": "Salmo 130:5-6",
        "angle": "esperanza paciente en la oscuridad",
        "truth": "esperar en Dios puede parecerse a esperar el amanecer: todavía hay oscuridad, pero el corazón no concluye que la noche será eterna",
        "context": "el salmo nace desde la profundidad y une arrepentimiento, esperanza y una espera atenta en la palabra de Dios",
        "practice": "no tomar una decisión definitiva desde una emoción pasajera y buscar apoyo si la noche interior se está haciendo demasiado pesada",
        "visual": "Jesus in silhouette before a real mountain dawn, blue hour becoming gold, natural atmosphere, premium photoreal cinema",
    },
    {
        "family": "recibir una palabra para comenzar de nuevo cada mañana",
        "reference": "Salmo 143:8",
        "angle": "dirección y amor al despertar",
        "truth": "comenzar el día también puede ser un acto de escucha: pedir recordar el amor de Dios y conocer el camino que conviene seguir",
        "context": "el salmo combina vulnerabilidad con una petición muy concreta de guía para la jornada que comienza",
        "practice": "antes de mirar todas las notificaciones, elegir una intención sencilla para vivir el día con verdad, fe y bondad",
        "visual": "Jesus overlooking a sunlit valley at dawn, realistic face in three-quarter profile, premium natural cinematic photography",
    },
    {
        "family": "recordar que el amor no alimenta el miedo",
        "reference": "1 Juan 4:18",
        "angle": "amor maduro frente al temor",
        "truth": "el amor de Dios no está diseñado para mantenernos en una relación dominada por amenaza y miedo constante",
        "context": "la carta vincula el amor maduro con una confianza que desplaza el temor relacionado con castigo y condenación",
        "practice": "revisar si una decisión espiritual nace del amor y la verdad o solamente de presión, culpa y miedo",
        "visual": "Jesus in soft window light with a calm compassionate expression, natural human skin texture, intimate photoreal cinema",
    },
    {
        "family": "ser conocido por Dios aun cuando nadie entiende del todo lo que sentís",
        "reference": "Salmo 139:1-3",
        "angle": "Dios conoce el camino y el corazón",
        "truth": "hay momentos en que cuesta explicar lo que pasa por dentro; el salmo encuentra consuelo en la idea de ser plenamente conocido por Dios",
        "context": "el poema recorre pensamientos, caminos y lugares para expresar una presencia de la que el salmista no necesita esconderse",
        "practice": "poner por escrito una emoción que te cuesta nombrar y llevarla a una oración honesta, sin tratar de sonar perfecto",
        "visual": "Jesus walking alone beneath a star-filled sky turning toward dawn, realistic live-action photography, serene and reverent",
    },
    {
        "family": "elegir una esperanza que no avergüenza en el proceso",
        "reference": "Romanos 5:3-5",
        "angle": "paciencia y carácter en la prueba",
        "truth": "la dificultad no es buena por sí misma, pero puede convertirse en un lugar donde se forman perseverancia, carácter y una esperanza más profunda",
        "context": "Pablo conecta el sufrimiento con un proceso, no con una promesa de éxito inmediato ni con la negación del dolor",
        "practice": "medir tu avance por la fidelidad de tus decisiones y no solamente por la rapidez con la que cambia la circunstancia",
        "visual": "Jesus climbing a gentle stone path after rain, realistic wet surfaces and morning light, premium live-action biblical cinema",
    },
    {
        "family": "buscar primero lo esencial cuando todo compite por atención",
        "reference": "Lucas 12:29-31",
        "angle": "prioridades frente a la preocupación",
        "truth": "Jesús invita a no convertir la búsqueda ansiosa de seguridad en el centro de toda la vida",
        "context": "la enseñanza sobre necesidades cotidianas conduce a ordenar prioridades y a confiar sin abandonar la responsabilidad",
        "practice": "elegir una prioridad de valor para hoy y organizar alrededor de ella las tareas que realmente importan",
        "visual": "Jesus walking through a field with birds crossing a real sky, natural body motion, photoreal live-action biblical setting",
    },
    {
        "family": "mantener los ojos en lo eterno sin desentenderse del presente",
        "reference": "2 Corintios 4:16-18",
        "angle": "renovación interior mientras el proceso continúa",
        "truth": "la esperanza cristiana puede ampliar la perspectiva sin minimizar el desgaste real que una persona siente hoy",
        "context": "Pablo reconoce fragilidad exterior mientras habla de una renovación interior y de una mirada que no termina en lo visible",
        "practice": "cuidar una dimensión interior hoy: descansar, orar, conversar con alguien sabio o recordar por qué vale la pena perseverar",
        "visual": "Jesus on a high overlook above moving clouds, realistic wind and fabric, physically plausible sunrise, cinematic live-action",
    },
    {
        "family": "permitir que la esperanza vuelva a levantarte",
        "reference": "Salmo 42:11",
        "angle": "hablarle con verdad al desánimo",
        "truth": "el salmista no oculta su desánimo, pero tampoco permite que esa emoción sea la única voz que interprete toda su historia",
        "context": "la repetición de la pregunta y de la esperanza muestra una conversación interior honesta, no una negación rápida de la tristeza",
        "practice": "reconocer cómo te sentís y sumar deliberadamente una razón concreta para no rendirte hoy",
        "visual": "Jesus near a mountain stream in cool morning air, thoughtful expression, realistic water, premium natural photography",
    },
    {
        "family": "entregar una carga que se volvió demasiado pesada",
        "reference": "Salmo 55:22",
        "angle": "no sostener solo lo que te supera",
        "truth": "la oración puede ser un lugar para dejar de fingir autosuficiencia y entregar a Dios una carga que ya está afectando cada parte del día",
        "context": "el salmo surge en medio de conflicto, dolor y traición, por eso su llamado a depositar la carga no es una frase desconectada de la realidad",
        "practice": "nombrar la carga con precisión y buscar también la ayuda humana apropiada cuando el problema requiere compañía o intervención",
        "visual": "Jesus setting down a simple travel bag beside a quiet road, symbolic but realistic live-action scene, soft evening light",
    },
    {
        "family": "recordar la bondad de Dios y recuperar perspectiva",
        "reference": "Salmo 103:2-5",
        "angle": "gratitud que no borra las dificultades",
        "truth": "recordar el bien recibido puede ampliar la mirada cuando la preocupación hace que todo el día parezca reducido a un solo problema",
        "context": "el salmo se habla a sí mismo y enumera motivos para bendecir a Dios, usando la memoria como disciplina espiritual",
        "practice": "anotar tres bienes concretos que no querés dar por sentados y agradecerlos antes de volver a la preocupación principal",
        "visual": "Jesus walking through a warm autumn valley with sunlight through trees, realistic live-action color and natural depth",
    },
    {
        "family": "aprender a detenerse y reconocer a Dios en medio del ruido",
        "reference": "Salmo 46:10",
        "angle": "quietud antes de reaccionar",
        "truth": "la quietud bíblica no siempre consiste en que desaparezca el ruido exterior; a veces empieza cuando dejamos de responder automáticamente a cada alarma",
        "context": "el salmo describe conmoción y conflicto antes de llamar a reconocer la soberanía de Dios",
        "practice": "regalarte sesenta segundos sin pantalla para respirar, orar y elegir conscientemente cuál es la próxima respuesta correcta",
        "visual": "Jesus standing beside still water after turbulent weather, realistic reflections, calm human pose, premium live-action cinema",
    },
    {
        "family": "caminar en misericordia después de haber fallado",
        "reference": "Tito 3:4-7",
        "angle": "recibir gracia y empezar distinto",
        "truth": "la gracia cristiana no se presenta como premio por haber sido perfectos, sino como una iniciativa de bondad y misericordia de Dios",
        "context": "la carta conecta esa misericordia con una vida renovada, evitando tanto el orgullo como la desesperanza por el pasado",
        "practice": "reconocer un error sin justificarlo y elegir una acción concreta de reparación o cambio para hoy",
        "visual": "Jesus meeting a solitary traveler on a sunlit road, compassionate realistic human interaction, cinematic live-action style",
    },
    {
        "family": "encontrar seguridad sin depender de tener todo bajo control",
        "reference": "Salmo 16:8",
        "angle": "una presencia firme delante de los cambios",
        "truth": "la estabilidad del corazón no siempre viene de controlar el escenario, sino de volver a colocar delante de nosotros aquello en lo que confiamos",
        "context": "el salmo expresa una confianza cercana en Dios que reorganiza la manera de mirar seguridad, futuro y alegría",
        "practice": "antes de intentar controlar cinco cosas a la vez, identificar la decisión que sí te corresponde y hacerla con calma",
        "visual": "Jesus standing on firm rock above a green valley, realistic human figure and natural daylight, understated cinematic scene",
    },
    {
        "family": "una alegría serena que nace de permanecer cerca de Dios",
        "reference": "Salmo 84:5-7",
        "angle": "fuerza para seguir atravesando el valle",
        "truth": "el camino puede incluir valles difíciles y aun así convertirse en un recorrido donde la persona encuentra nuevas fuerzas",
        "context": "el salmo describe peregrinos cuyo corazón está orientado hacia Dios y que siguen avanzando en medio del trayecto",
        "practice": "mirar el camino por etapas y celebrar la fuerza suficiente para el tramo de hoy en vez de exigir energía para toda la semana",
        "visual": "Jesus walking through a lush valley trail with distant mountains, realistic footsteps and sunlight, premium live-action cinema",
    },
    {
        "family": "recordar que Dios está cerca en medio de una decisión compleja",
        "reference": "Salmo 145:18",
        "angle": "orar con verdad y no con apariencia",
        "truth": "la cercanía de Dios se relaciona con una búsqueda sincera, no con encontrar palabras religiosas perfectas",
        "context": "el salmo celebra el carácter y la bondad de Dios y conecta su cercanía con quienes lo invocan con verdad",
        "practice": "decir en oración lo que realmente pensás y después buscar consejo responsable antes de una decisión importante",
        "visual": "Jesus in a quiet mountain chapel doorway without religious ornament, realistic warm human portrait, natural light",
    },
    {
        "family": "recuperar el ánimo sin negar el cansancio",
        "reference": "1 Tesalonicenses 5:16-18",
        "angle": "gratitud y oración en la vida cotidiana",
        "truth": "la gratitud cristiana no obliga a llamar bueno a todo lo que duele; puede convivir con una oración constante en medio de circunstancias imperfectas",
        "context": "las instrucciones breves de la carta apuntan a una disposición sostenida de oración y agradecimiento, no a una emoción artificial permanente",
        "practice": "agradecer algo real, pedir ayuda por algo real y hacer algo bueno que esté a tu alcance antes de terminar el día",
        "visual": "Jesus walking through an ordinary village street at warm evening light, grounded realistic live-action biblical atmosphere",
    },
    {
        "family": "seguir acercándote con confianza cuando te sentís insuficiente",
        "reference": "Efesios 3:16-19",
        "angle": "fortaleza interior y amor de Cristo",
        "truth": "la fortaleza interior no tiene que construirse solamente desde la autosuficiencia; la oración de Pablo la conecta con el amor de Cristo",
        "context": "el pasaje es una oración por raíces profundas, comprensión del amor y una vida interior fortalecida",
        "practice": "recordar que pedir apoyo y dejarte amar no te hace menos fuerte, y abrir hoy una conversación que venías evitando",
        "visual": "Jesus beneath a broad tree with roots visible beside a river, compassionate human realism, premium cinematic sunlight",
    },
    {
        "family": "vestirse de compasion antes de entrar en una conversación difícil",
        "reference": "Colosenses 3:12-14",
        "angle": "bondad, paciencia y límites con amor",
        "truth": "la compasión no significa permitir cualquier cosa; puede acompañar límites claros sin convertir al otro en un enemigo",
        "context": "Pablo enumera cualidades como bondad, humildad y paciencia y las reúne bajo el llamado al amor",
        "practice": "preparar una conversación difícil definiendo una verdad que necesitás decir y una forma respetuosa de decirla",
        "visual": "Jesus speaking calmly with another adult on a stone path, respectful realistic interaction, natural cinematic light",
    },
)

INTRO_STYLES = (
    "Si hoy necesitás volver a encontrar el eje, guardá esta idea:",
    "Hay días en que el corazón necesita una verdad más fuerte que el ruido:",
    "Antes de responder a todo lo que te preocupa, considerá esto:",
    "Quizás no puedas cambiar todo hoy, pero sí podés cambiar desde dónde lo enfrentás:",
    "Una pausa de un minuto puede cambiar la forma en que atravesás este momento:",
    "Si venís sosteniendo demasiado, esta reflexión puede ayudarte a ordenar el próximo paso:",
    "La Biblia no evita las preguntas difíciles; muchas veces las atraviesa con nosotros:",
    "Hoy no necesitás una promesa exagerada, sino una verdad que puedas llevar a la vida:",
)

BRIDGES = (
    "Eso no convierte la fe en una fórmula mágica; la convierte en una manera distinta de caminar la realidad.",
    "Confiar no es cerrar los ojos. Es mirar lo que pasa sin entregar al miedo toda la autoridad sobre tus decisiones.",
    "La esperanza bíblica puede ser muy concreta: respirar, pedir ayuda, actuar con integridad y volver a intentarlo.",
    "A veces el cambio más importante no ocurre primero afuera, sino en la forma en que respondemos por dentro.",
    "No todo se resuelve rápido. Pero incluso un proceso lento puede vivirse con verdad, compañía y dirección.",
    "La oración no reemplaza las decisiones responsables; puede ayudarnos a tomarlas con un corazón menos dominado por la ansiedad.",
    "Jesús nunca necesitó manipular el miedo para invitar a confiar; por eso esta reflexión tampoco lo hará.",
    "La fe madura puede sostener dos cosas a la vez: reconocer lo difícil y seguir creyendo que todavía existe un próximo paso.",
)

CLOSINGS = (
    "Llevá esta enseñanza a una oración sencilla y elegí un paso posible para hoy. Que Dios te dé paz y sabiduría. Amén.",
    "No necesitás tener resuelta toda la semana para caminar bien este día. Que Dios acompañe tu próximo paso. Amén.",
    "Guardá esta reflexión para volver cuando el ruido crezca y compartila sólo si puede hacerle bien a alguien. Amén.",
    "Que la presencia de Dios te recuerde que pedir ayuda, descansar y volver a empezar también pueden ser actos de fe. Amén.",
    "Que esta palabra se transforme en una decisión más serena, más verdadera y más compasiva durante el día de hoy. Amén.",
    "Que Dios te conceda una mente clara, un corazón firme y la humildad de caminar un paso a la vez. Amén.",
)

TITLE_PATTERNS = (
    "{angle} | {reference}",
    "Para cuando necesitás {need} | {reference}",
    "Una verdad para este momento | {reference}",
    "Cuando el corazón pide {need} | {reference}",
    "{reference}: una reflexión para volver a {need}",
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9áéíóúüñ]+", " ", _clean(value).lower()).strip()


def _uploaded(previous: list[dict]) -> list[dict]:
    return [row for row in previous if str(row.get("status") or "").lower() == "uploaded"]


def _seed(previous: list[dict]) -> int:
    marker = os.getenv("DIOS_SOVEREIGN_VARIATION_NONCE", "").strip()
    run = os.getenv("GITHUB_RUN_ID", "").strip() or os.getenv("GITHUB_RUN_NUMBER", "").strip()
    raw = f"{ENGINE_VERSION}|{run}|{marker}|history={len(previous)}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _recent_references(previous: list[dict], limit: int = 36) -> set[str]:
    refs: set[str] = set()
    for row in _uploaded(previous)[-limit:]:
        ref = _norm(row.get("bible_reference"))
        if ref:
            refs.add(ref)
    return refs


def _recent_topics(previous: list[dict], limit: int = 30) -> list[str]:
    return [_clean(row.get("topic")) for row in _uploaded(previous)[-limit:] if _clean(row.get("topic"))]


def _choose_theme(previous: list[dict]) -> tuple[dict[str, str], int]:
    seed = _seed(previous)
    recent_refs = _recent_references(previous)
    recent_topics = _recent_topics(previous)
    start = seed % len(THEMES)
    ordered = [THEMES[(start + step * 7) % len(THEMES)] for step in range(len(THEMES))]

    for theme in ordered:
        if _norm(theme["reference"]) in recent_refs:
            continue
        proposed_topic = f"{theme['family']} | {theme['reference']}"
        if any(similarity(proposed_topic, old) >= 0.82 for old in recent_topics):
            continue
        return theme, seed

    # The library is intentionally larger than the anti-spam window; reaching this
    # branch means unusually dense history. Pick the least-similar topic rather than
    # disabling the gate.
    scored: list[tuple[float, dict[str, str]]] = []
    for theme in THEMES:
        proposed = f"{theme['family']} | {theme['reference']}"
        worst = max((similarity(proposed, old) for old in recent_topics), default=0.0)
        scored.append((worst, theme))
    scored.sort(key=lambda pair: pair[0])
    return scored[0][1], seed


def _need(theme: dict[str, str]) -> str:
    family = theme["family"].lower()
    for word in ("paz", "refugio", "descanso", "esperanza", "confianza", "ánimo", "animo", "fortaleza", "claridad"):
        if word in family:
            return word.replace("ánimo", "ánimo")
    return "esperanza"


def _title_candidates(theme: dict[str, str], seed: int) -> list[str]:
    need = _need(theme)
    values: list[str] = []
    for offset in range(len(TITLE_PATTERNS)):
        pattern = TITLE_PATTERNS[(seed + offset * 3) % len(TITLE_PATTERNS)]
        value = pattern.format(
            angle=theme["angle"].capitalize(),
            reference=theme["reference"],
            need=need,
        )
        value = _clean(value)[:90].rstrip(" -|:,.!")
        if value and value not in values:
            values.append(value)
    return values


def _scene_lines(theme: dict[str, str], seed: int, count: int) -> list[str]:
    intro = INTRO_STYLES[seed % len(INTRO_STYLES)]
    bridge = BRIDGES[(seed // 5) % len(BRIDGES)]
    close = CLOSINGS[(seed // 11) % len(CLOSINGS)]
    reference = theme["reference"]
    lines = [
        f"{intro} {theme['truth']}.",
        f"En {reference}, {theme['context']}. No hace falta convertir el pasaje en una consigna rápida para que pueda hablarnos hoy.",
        bridge,
        f"Una práctica concreta puede ser {theme['practice']}. Hacelo de una forma pequeña, realista y sostenible.",
        f"Preguntate qué cambiaría en este día si vivieras desde esta idea: {theme['angle'].lower()}. No busques una emoción perfecta; buscá una respuesta fiel.",
        close,
    ]
    while len(lines) < count:
        lines.append(lines[len(lines) % len(lines)])
    return lines[:count]


def _visual_prompts(theme: dict[str, str], count: int) -> list[str]:
    base = theme["visual"]
    supporting = (
        "symbolic divine presence through physically plausible sunlight breaking through real clouds, no human face for God, premium live-action photography",
        "open Bible on natural wood beside a window, realistic paper texture and soft morning light, shallow depth of field, no readable text",
        "wide Norwegian-style mountain valley with moving clouds and natural water, cinematic real-world photography, no CGI or illustration",
        "simple wooden cross seen at a distance in a real landscape during golden hour, subtle and reverent, no text or logos",
        "Jesus walking on a natural path in a cream linen robe, realistic adult human anatomy and skin, documentary cinematic lens",
    )
    prompts = [base]
    prompts.extend(supporting)
    while len(prompts) < count:
        prompts.extend(supporting)
    return prompts[:count]


def generate_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    theme, seed = _choose_theme(previous)
    count = int(channel.get("scenes_per_short") or 6)
    lines = _scene_lines(theme, seed, count)
    visuals = _visual_prompts(theme, count)
    titles = _title_candidates(theme, seed)
    topic = f"{theme['family']} | {theme['reference']} | {theme['angle']}"

    scenes = [
        {
            "visual_prompt": visuals[index],
            "stock_query": f"biblical cinematic {theme['reference']} hope nature",
            "narration": lines[index],
        }
        for index in range(count)
    ]

    return {
        "topic": topic,
        "content_family": f"premium_v7:{theme['family']}",
        "bible_reference": theme["reference"],
        "hook": lines[0],
        "title": titles[0],
        "description": (
            f"Reflexión cristiana original inspirada en {theme['reference']} sobre {theme['angle'].lower()}. "
            "Una pausa para volver a Dios con fe, serenidad y una decisión concreta."
        ),
        "hashtags": ["#Dios", "#Jesús", "#Fe", "#Biblia", "#DiosHablaHoy"],
        "tags": [
            "Dios Habla Hoy", "Dios", "Jesús", "Jesucristo", "Biblia", "fe", "esperanza",
            "reflexión cristiana", theme["reference"], theme["family"], theme["angle"],
        ],
        "cta": "Guardá esta reflexión y compartila con alguien a quien pueda acompañar hoy.",
        "scenes": scenes,
        "metadata_provider": ENGINE_VERSION,
        "premium_editorial_version": ENGINE_VERSION,
        "legacy_style_inspiration": "refugio_paz_oracion_confianza_descanso_tormenta_reinterpretado_sin_reupload",
        "_premium_editorial_title_candidates": titles,
        "_premium_editorial_topic": topic,
        "_premium_editorial_reference": theme["reference"],
        "_premium_editorial_angle": theme["angle"],
    }


def restore_unique_packaging(metadata: dict, previous: list[dict] | None = None) -> dict:
    """Restore theme-specific packaging after generic SEO reranking.

    The generic packager is still used for descriptions, tags and quality scoring,
    but it historically converged on a small set of high-scoring title templates.
    Here we select the least-repetitive theme-specific title without weakening the
    final anti-spam validator.
    """
    previous = list(previous or [])
    recent = _uploaded(previous)[-30:]
    candidates = list(metadata.get("_premium_editorial_title_candidates") or [])
    reference = _clean(metadata.get("_premium_editorial_reference") or metadata.get("bible_reference"))
    angle = _clean(metadata.get("_premium_editorial_angle") or "una esperanza para este momento")
    topic = _clean(metadata.get("_premium_editorial_topic") or metadata.get("topic"))

    if not candidates:
        candidates = [
            f"{angle.capitalize()} | {reference}",
            f"{reference}: {angle}",
        ]

    best_title = ""
    best_similarity = 2.0
    for candidate in candidates:
        candidate = _clean(candidate)[:90].rstrip(" -|:,.!")
        if not candidate:
            continue
        worst = max(
            (similarity(candidate, _clean(row.get("title"))) for row in recent if _clean(row.get("title"))),
            default=0.0,
        )
        if worst < best_similarity:
            best_title = candidate
            best_similarity = worst
        if worst < 0.76:
            break

    if not best_title:
        best_title = f"{reference}: {angle}"[:90].rstrip(" -|:,.!")

    metadata["title"] = best_title
    metadata["topic"] = topic
    metadata["content_family"] = _clean(metadata.get("content_family") or topic)
    metadata["bible_reference"] = reference
    metadata["seo_title_candidates"] = candidates[:3]
    metadata["premium_editorial_title_max_recent_similarity"] = round(best_similarity if best_similarity <= 1 else 0.0, 4)
    metadata["premium_editorial_version"] = ENGINE_VERSION
    metadata["final_packaging_variety_guard"] = "theme_specific_title_plus_existing_spiritual_uniqueness_gate"
    return metadata
