"""Extra 'enseñanzas de Jesús' themes (same shape as dios_premium_editorial_v7.THEMES).

The v7 library has a single Jesus-teaching theme, which would block that pillar
for weeks once used. These original paraphrase-based themes keep the rotation
balanced. Script text is original; no protected translation is quoted.
"""
from __future__ import annotations

_JESUS_VISUAL = "Jesus {scene}, realistic adult human appearance, natural linen clothing, premium live-action biblical cinema, soft natural light"

EXTRA_THEMES: tuple[dict[str, str], ...] = (
    {
        "family": "las bienaventuranzas como enseñanza de Jesús",
        "reference": "Mateo 5:3-9",
        "angle": "dichosos los humildes y los que buscan la paz",
        "truth": "Jesús llamó dichosos a los humildes, a los que lloran y a los que trabajan por la paz, mostrando que el Reino empieza por un corazón sencillo",
        "context": "Jesús enseña en un monte a una multitud común, y sus palabras invierten la idea de quién es realmente bendecido",
        "practice": "elegir una actitud de mansedumbre o de paz en una situación concreta que hoy te toque vivir",
        "visual": _JESUS_VISUAL.format(scene="teaching gently on a green hillside above the Sea of Galilee, small listening crowd out of focus"),
    },
    {
        "family": "el mandamiento nuevo de Jesús",
        "reference": "Juan 13:34-35",
        "angle": "amarnos unos a otros como fuimos amados",
        "truth": "Jesús pidió a sus discípulos que se amaran unos a otros como Él los había amado, y dijo que así serían reconocidos",
        "context": "estas palabras aparecen en la última cena, cuando Jesús se despide y deja el amor como señal de sus seguidores",
        "practice": "tener un gesto concreto de amor paciente con alguien cercano, sin esperar nada a cambio",
        "visual": _JESUS_VISUAL.format(scene="sharing bread at a simple wooden table at dusk, warm oil lamps"),
    },
    {
        "family": "Jesús enseña a orar con el Padre Nuestro",
        "reference": "Mateo 6:9-13",
        "angle": "el Padre Nuestro, frase por frase",
        "truth": "Jesús enseñó una oración sencilla que empieza llamando Padre a Dios y pide el pan, el perdón y la guía de cada día",
        "context": "Jesús la presenta como contraste con las oraciones largas hechas para aparentar, invitando a una confianza simple",
        "practice": "rezar despacio el Padre Nuestro y detenerte en la frase que hoy más necesitás",
        "visual": _JESUS_VISUAL.format(scene="kneeling in quiet prayer among olive trees at dawn, side profile"),
    },
    {
        "family": "Jesús y la vid verdadera",
        "reference": "Juan 15:4-5",
        "angle": "permanecer unidos como ramas a la vid",
        "truth": "Jesús se comparó con una vid y a sus discípulos con las ramas, enseñando que la vida verdadera nace de permanecer unidos a Él",
        "context": "es una imagen tomada del campo, que habla de cercanía diaria más que de esfuerzo aislado",
        "practice": "reservar un momento tranquilo para orar antes de llenar el día de tareas",
        "visual": _JESUS_VISUAL.format(scene="walking slowly between vineyard rows at golden hour, hand touching a grapevine"),
    },
    {
        "family": "Jesús enseña a perdonar sin llevar la cuenta",
        "reference": "Mateo 18:21-22",
        "angle": "perdonar sin llevar la cuenta",
        "truth": "cuando Pedro preguntó cuántas veces perdonar, Jesús respondió con una medida que deja de contar, invitando a un corazón libre",
        "context": "la respuesta de Jesús no niega el daño, pero rompe la lógica de llevar un registro de ofensas",
        "practice": "dar un paso pequeño hacia el perdón, aunque todavía duela, cuidando también límites sanos",
        "visual": _JESUS_VISUAL.format(scene="talking calmly with a disciple on a stone path by the lake, compassionate expression"),
    },
    {
        "family": "Jesús y el agua viva",
        "reference": "Juan 4:13-14",
        "angle": "agua viva para el corazón cansado",
        "truth": "junto a un pozo, Jesús habló de un agua viva que calma una sed más profunda que la del cuerpo",
        "context": "Jesús conversa con una mujer samaritana que no esperaba ser escuchada, y le ofrece dignidad y esperanza",
        "practice": "presentarle a Dios con honestidad aquello que ninguna otra cosa logró llenar",
        "visual": _JESUS_VISUAL.format(scene="seated beside an ancient stone well at midday, clear water in a clay jar"),
    },
    {
        "family": "Jesús busca a Zaqueo",
        "reference": "Lucas 19:1-10",
        "angle": "nadie está demasiado lejos para volver",
        "truth": "Jesús se detuvo frente a Zaqueo y quiso entrar en su casa, mostrando que nadie está demasiado lejos para volver",
        "context": "Zaqueo era despreciado por la multitud, pero el encuentro con Jesús transformó su manera de vivir",
        "practice": "dejar de definirte por tu peor error y dar hoy un paso concreto de cambio",
        "visual": _JESUS_VISUAL.format(scene="looking up warmly toward a sycamore tree on a village street"),
    },
    {
        "family": "Jesús en el más pequeño",
        "reference": "Mateo 25:35-40",
        "angle": "servir con amor al que necesita",
        "truth": "Jesús enseñó que dar de comer, visitar o recibir al que sufre es una forma de servirlo a Él",
        "context": "la enseñanza muestra que la fe se vuelve visible en gestos concretos hacia los más vulnerables",
        "practice": "hacer hoy un acto sencillo de servicio por alguien que lo necesite",
        "visual": _JESUS_VISUAL.format(scene="offering bread to a traveler at a village doorway, faces softly lit"),
    },
)
