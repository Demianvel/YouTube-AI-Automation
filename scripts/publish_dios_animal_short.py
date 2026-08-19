from __future__ import annotations

import os
from copy import deepcopy

# Importing the fast publisher installs the hardened HF visual route and
# permanent Voz de Luz / Algenib TTS guardrails, but does not publish by itself.
from scripts import publish_dios_fast as fast
from app import pipeline


PRESETS = {
    "1": {
        "title": "Mirá las aves: Dios no olvida su creación | Mateo 6:26",
        "topic": "Las aves del cielo y la confianza en el cuidado de Dios",
        "reference": "Mateo 6:26",
        "description": (
            "Jesús invita a mirar las aves del cielo para aprender a confiar en el cuidado del Padre. "
            "Una reflexión bíblica sobre la creación, la ansiedad, la fe y el valor de cada vida."
        ),
        "lines": [
            "Mirá por un momento a las aves del cielo. Jesús usó algo tan sencillo como un pájaro para enseñarnos una verdad profunda sobre Dios.",
            "En Mateo 6:26, Jesús señala que las aves no siembran ni almacenan y, sin embargo, el Padre celestial las alimenta.",
            "La enseñanza no es abandonar la responsabilidad. Es recordar que la preocupación no debe gobernar el corazón ni hacernos olvidar quién sostiene la vida.",
            "Cada ave que cruza el cielo puede recordarnos que la creación tiene valor ante Dios y que nosotros también somos vistos, conocidos y llamados a confiar.",
            "Hoy cuidá la vida que tenés cerca: un animal, una persona, la tierra que pisás. La fe también se demuestra con gratitud, respeto y compasión.",
            "Cuando aparezca el miedo por el mañana, mirá nuevamente la creación y recordá las palabras de Jesús. Confiá, actuá con responsabilidad y caminá con fe. Amén.",
        ],
        "visuals": [
            "premium photorealistic cinematic flock of small sparrows flying over a golden Galilee-like hillside at sunrise, realistic feathers, gentle wind, biblical landscape, vertical 9:16, no text, no logo, no watermark",
            "close cinematic view of sparrows feeding peacefully among wild grasses and seeds, warm natural sunlight, highly realistic wildlife photography look, vertical 9:16, no text, no logo, no watermark",
            "wide ancient Middle Eastern countryside with birds crossing a bright sky above fields and distant hills, peaceful biblical-era atmosphere, photoreal cinematic, vertical 9:16, no text, no logo, no watermark",
            "small bird perched on an olive branch with soft sunlight behind it, detailed feathers and leaves, tranquil spiritual nature scene, photorealistic, vertical 9:16, no text, no logo, no watermark",
            "compassionate human hands placing clean water for a small bird in a natural garden, respectful animal care, realistic cinematic close-up, vertical 9:16, no text, no logo, no watermark",
            "flock of birds flying toward a luminous sunset over mountains and fields, hopeful peaceful creation scene, premium photorealistic cinematic lighting, vertical 9:16, no text, no logo, no watermark",
        ],
        "queries": [
            "sparrows birds sunrise nature",
            "sparrow feeding wildlife",
            "birds biblical landscape",
            "bird olive branch nature",
            "caring for bird water",
            "birds sunset mountains",
        ],
    },
    "2": {
        "title": "El justo cuida a los animales | Proverbios 12:10",
        "topic": "Compasión por los animales y responsabilidad ante la creación",
        "reference": "Proverbios 12:10; Génesis 9:9-10",
        "description": (
            "Proverbios 12:10 enseña que la persona justa se preocupa por sus animales. "
            "Génesis 9:9-10 recuerda además que la alianza después del diluvio alcanza también a los seres vivientes."
        ),
        "lines": [
            "La Biblia también habla de cómo tratamos a los animales. La fe no se limita a palabras: se refleja en la manera en que cuidamos la vida.",
            "Proverbios 12:10 enseña que el justo se preocupa por su ganado, mientras que la crueldad caracteriza al corazón que se aleja del bien.",
            "Eso nos deja una enseñanza concreta: alimentar, proteger y tratar con respeto a un animal puede ser una expresión sencilla de responsabilidad y misericordia.",
            "Después del diluvio, Génesis 9:9 y 10 presenta la alianza de Dios con Noé, sus descendientes y también con los animales que salieron del arca.",
            "La creación no es un objeto sin valor. Somos llamados a administrarla con prudencia, sin maltrato, sin crueldad y reconociendo que la vida merece cuidado.",
            "Que nuestra fe pueda verse en actos: una mano que protege, agua para el sediento, alimento para el que depende de nosotros y compasión por toda criatura. Amén.",
        ],
        "visuals": [
            "healthy sheep and goats resting peacefully beside a caring shepherd in a sunlit rural biblical landscape, realistic animal behavior, premium photoreal cinematic scene, vertical 9:16, no text, no logo, no watermark",
            "close-up of gentle hands giving fresh water to a sheep, humane animal care, warm natural light, photorealistic cinematic detail, vertical 9:16, no text, no logo, no watermark",
            "peaceful mixed farm animals sheep goats donkey and cattle under shade with clean water and food, responsible care, photorealistic cinematic, vertical 9:16, no text, no logo, no watermark",
            "Noah's ark after the rain with pairs of animals safely gathered on green land, rainbow in distant sky, reverent biblical atmosphere, premium photoreal cinematic, vertical 9:16, no text, no logo, no watermark",
            "doves deer sheep and other animals peacefully moving across fresh green land after a storm, hopeful creation theme, photorealistic cinematic realism, vertical 9:16, no text, no logo, no watermark",
            "compassionate caretaker gently tending an injured small lamb in a clean peaceful field, non-graphic, humane care, warm sunrise, photorealistic cinematic, vertical 9:16, no text, no logo, no watermark",
        ],
        "queries": [
            "sheep goats shepherd care",
            "giving water sheep animal care",
            "farm animals humane care",
            "Noah ark animals rainbow",
            "animals peaceful field doves deer",
            "caring for lamb humane",
        ],
    },
}


def _animal_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    index = os.getenv("DIOS_ANIMAL_SHORT_INDEX", "1").strip()
    if index not in PRESETS:
        raise RuntimeError(f"DIOS_ANIMAL_SHORT_INDEX no valido: {index}")

    preset = PRESETS[index]
    metadata = fast._fast_local_metadata(channel, previous)
    metadata = deepcopy(metadata)

    scenes = list(metadata.get("scenes") or [])
    while len(scenes) < 6:
        scenes.append({})
    for i in range(6):
        scenes[i]["narration"] = preset["lines"][i]
        scenes[i]["visual_prompt"] = preset["visuals"][i]
        scenes[i]["stock_query"] = preset["queries"][i]

    metadata["scenes"] = scenes[:6]
    metadata["title"] = preset["title"]
    metadata["topic"] = preset["topic"]
    metadata["content_family"] = f"animales_y_biblia_{index}"
    metadata["bible_reference"] = preset["reference"]
    metadata["description"] = preset["description"]
    metadata["hashtags"] = ["#Dios", "#Jesus", "#Biblia", "#Animales", "#Shorts"]
    metadata["tags"] = [
        "dios", "jesus", "biblia", "animales", "creacion", "fe", "palabra de dios",
        "dios habla hoy", "compasion", "naturaleza", "shorts cristianos",
    ]
    metadata["cta"] = "Si esta enseñanza habló a tu corazón, compartila y elegí hoy una acción de cuidado y compasión."
    metadata["pinned_comment_candidate"] = (
        f"📖 {preset['reference']} — ¿Qué enseñanza te deja hoy el cuidado de los animales y de la creación? "
        "Te leo. Amén. 🙏"
    )
    metadata["metadata_provider"] = "verified_animal_bible_pack:vatican_refs:v1"
    metadata["animal_bible_pack"] = True
    metadata["animal_bible_short_index"] = index
    return metadata


pipeline.generate_metadata = _animal_metadata


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
