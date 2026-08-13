from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

from gradio_client import Client, handle_file

from scripts.render_aqui_estas_demianvelo import STYLE_PROMPT

SECTIONS_45 = [
    """[INTRO]
En el silencio de esta habitación,
cuando me cuesta escuchar mi corazón,
respiro lento y vuelvo a recordar:
no estoy solo, nunca me dejás.

[VERSO 1]
Cuando el día pesa más de lo normal,
y cada puerta parece cerrar,
cuando las dudas quieren decidir por mí,
Tu paz me encuentra justo donde estoy aquí.""",
    """[VERSO 1]
No necesito tener todo bajo control,
ni conocer mañana para confiar en Vos.
Hay una calma que no puedo explicar,
y en medio de mi ruido me volvés a abrazar.

[PRE-CORO]
Si el miedo quiere hablar más fuerte que mi fe,
levanto la mirada y vuelvo a comprender:

[CORO]
Aquí estás,
más cerca que mi propia respiración.
Aquí estás,
sosteniendo en silencio el corazón.""",
    """[CORO]
Cuando pierdo fuerzas para continuar,
Tu amor me vuelve a despertar.
Dios eterno, mi refugio y mi verdad,
aquí estás.

[VERSO 2]
Hay caminos que demoran en abrir,
y hay respuestas que tardan en venir,
pero aprendí que esperar también es fe,
si en cada paso caminás al lado mío, sé.
Cuando la noche vuelve a cubrir la ciudad,
Tu luz no grita, pero nunca deja de alumbrar.""",
    """[VERSO 2]
Y aunque mis ojos no comprendan el final,
Tu compañía vuelve todo a su lugar.

[PRE-CORO]
No necesito ver el mapa hasta el final,
si Tu presencia me acompaña al caminar.

[CORO]
Aquí estás,
más cerca que mi propia respiración.
Aquí estás,
sosteniendo en silencio el corazón.
Cuando pierdo fuerzas para continuar,
Tu amor me vuelve a despertar.
Dios eterno, mi refugio y mi verdad,
aquí estás.""",
    """[PUENTE]
En la mañana y en la madrugada,
en mi alegría y en mis días sin palabras,
en cada herida que aprendió a sanar,
en cada sueño que se anima a comenzar.
Jesús, mi roca cuando todo se movió,
mi voz te busca y encuentra Tu amor.
Si vuelvo a caer, me ayudás a levantar,
y con cada nuevo día puedo declarar:

[BUILD]
Estás conmigo,
estás conmigo,
mi esperanza no se apaga si estás conmigo.
Estás conmigo,
estás conmigo,
y mi corazón aprende a descansar.""",
    """[CORO FINAL]
Aquí estás,
más cerca que mi propia respiración.
Aquí estás,
encendiendo nuevamente el corazón.
Cuando pierdo fuerzas para continuar,
Tu amor me vuelve a despertar.
Dios eterno, mi refugio y mi verdad,
aquí estás.

[POST-CORO]
Aquí estás,
en cada paso, en cada despertar.
Aquí estás,
y no necesito nada más.

[OUTRO]
Si todo cambia alrededor,
Tu amor permanece.
Aquí estás.""",
]

SPACE = "techfreakworm/ACE-Music-Studio"
SEED = 20260813
DURATION = 45.0


def _copy_result(result, out: Path) -> None:
    value = result[0] if isinstance(result, (list, tuple)) else result
    src = Path(str(value))
    if not src.exists() or not src.is_file():
        raise RuntimeError(f"ACE Music Studio did not return an audio file: {value!r}")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)
    if out.stat().st_size < 100_000:
        raise RuntimeError("ACE audio output is too small")


def generate_first(out: Path) -> None:
    client = Client(SPACE, token=os.getenv("HF_TOKEN") or None, verbose=False)
    prompt = (
        STYLE_PROMPT
        + ". Opening 45 seconds of one continuous four-to-five-minute song. Establish one distinctive original male Rioplatense Argentine singer identity. "
          "Keep the same key, singer, vocal placement, timbre, instrumentation and mix for all later extensions. No spoken commentary."
    )
    result = client.predict(
        prompt,
        SECTIONS_45[0],
        DURATION,
        "With vocals",
        8,
        7.0,
        "ode",
        SEED,
        0.0,
        1.0,
        1.0,
        False,
        True,
        True,
        True,
        True,
        0.85,
        0.9,
        0,
        2.0,
        "NO USER INPUT",
        82,
        "D",
        "4",
        "es",
        api_name="/on_generate_click",
    )
    _copy_result(result, out)
    print("ACE_CHAIN_FIRST_OK", out, out.stat().st_size)


def extend(section: int, seed_audio: Path, out: Path) -> None:
    if section < 2 or section > 6:
        raise ValueError("section must be 2..6")
    if not seed_audio.exists() or seed_audio.stat().st_size < 100_000:
        raise RuntimeError(f"invalid seed audio: {seed_audio}")
    client = Client(SPACE, token=os.getenv("HF_TOKEN") or None, verbose=False)
    extra = (
        STYLE_PROMPT
        + f". Continue section {section} seamlessly from the supplied song. Preserve EXACTLY the same original singer identity, vocal timbre, key, tempo, instrumentation, ambience and mix. "
          "Do not restart the song, do not introduce a new singer and do not add spoken commentary."
    )
    result = client.predict(
        handle_file(str(seed_audio)),
        extra,
        SECTIONS_45[section - 1],
        DURATION,
        1.5,
        "balanced",
        0.42,
        10,
        "auto",
        8,
        7.0,
        "ode",
        SEED,
        0.0,
        1.0,
        1.0,
        False,
        True,
        True,
        True,
        True,
        0.85,
        0.9,
        0,
        2.0,
        "NO USER INPUT",
        82,
        "D",
        "4",
        "es",
        api_name="/on_extend_click",
    )
    _copy_result(result, out)
    print("ACE_CHAIN_EXTEND_OK", section, out, out.stat().st_size)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", type=int, required=True, choices=range(1, 7))
    parser.add_argument("--seed-audio", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if args.section == 1:
        generate_first(out)
    else:
        if not args.seed_audio:
            raise SystemExit("--seed-audio is required for section 2..6")
        extend(args.section, Path(args.seed_audio), out)


if __name__ == "__main__":
    main()
