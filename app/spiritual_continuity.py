from __future__ import annotations

import math
import re
import subprocess
from pathlib import Path

_SAFE_EXPANSIONS = (
    "Podemos llevar esta reflexión a la vida cotidiana con una oración sincera, pidiendo sabiduría para decidir, paciencia para esperar y un corazón dispuesto a amar al prójimo con hechos concretos.",
    "La fe bíblica no nos invita a ignorar lo difícil, sino a atravesarlo con esperanza, responsabilidad y confianza, buscando el bien incluso cuando todavía no entendemos todo lo que está ocurriendo.",
    "También podemos agradecer por lo pequeño, cuidar nuestras palabras, escuchar con atención y recordar que una acción sencilla de bondad puede convertirse en alivio para alguien que está pasando un momento difícil.",
    "Orar de manera sencilla también vale: podemos hablar con Dios con nuestras propias palabras, reconocer nuestras preocupaciones, agradecer lo recibido y pedir fortaleza para actuar con verdad, humildad y compasión.",
    "Cuando aparezca el cansancio, podemos volver a las enseñanzas de la Biblia, recordar que no estamos llamados a vivir desde el miedo y elegir un paso posible que acerque paz, reconciliación o ayuda a otra persona.",
    "La esperanza se fortalece cuando no queda solamente en palabras, sino que se convierte en paciencia, servicio, perdón, generosidad y una disposición real a acompañar a quien necesita consuelo.",
    "Que este momento sirva también para mirar nuestro interior con serenidad, reconocer lo que podemos mejorar y pedir a Dios un corazón firme para perseverar sin perder la ternura ni la capacidad de hacer el bien.",
    "Podemos transformar esta reflexión en una intención concreta: hablar con respeto, pedir perdón cuando corresponda, compartir con quien tiene menos, cuidar a los demás y ser una presencia de paz en nuestro entorno.",
    "La Biblia muestra una y otra vez que la fe puede convivir con preguntas, cansancio y espera; por eso no necesitamos fingir perfección, sino seguir avanzando con humildad y confianza.",
    "Incluso cuando no vemos una respuesta inmediata, podemos seguir cultivando gratitud, prudencia y esperanza, dejando que la oración nos ayude a ordenar el corazón y a elegir lo que construye en lugar de lo que lastima.",
    "Que esta palabra nos recuerde que cada día ofrece una nueva oportunidad para escuchar mejor, ayudar con generosidad y cuidar la dignidad de las personas que Dios pone en nuestro camino.",
    "Podemos detenernos por un instante interiormente, respirar con calma y presentar nuestras cargas en oración, pero sin desconectarnos de la realidad ni de la responsabilidad de hacer nuestra parte con amor y sabiduría.",
)


def _clean(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def ensure_spoken_text(text: str, target_seconds: float, seed: int = 0, words_per_minute: int = 136) -> tuple[str, dict]:
    """Ensure enough prose for the fixed natural Voz de Luz cadence.

    Duration is filled with spoken content rather than slowing or stretching the
    narrator. Added prose is general prayer/faith/application language and never
    invents a Bible quote or attributes a new direct statement to God.
    """
    clean = _clean(text)
    target_words = max(1, math.ceil((float(target_seconds) / 60.0) * words_per_minute * 0.98))
    words = len(clean.split())
    used: set[int] = set()
    cursor = 0
    additions: list[str] = []
    while words < target_words and cursor < len(_SAFE_EXPANSIONS) * 3:
        index = (seed + cursor * 5) % len(_SAFE_EXPANSIONS)
        cursor += 1
        if index in used and len(used) < len(_SAFE_EXPANSIONS):
            continue
        used.add(index)
        paragraph = _SAFE_EXPANSIONS[index]
        additions.append(paragraph)
        words += len(paragraph.split())
    if additions:
        clean = (clean + " " + " ".join(additions)).strip()
    return clean, {
        "target_words": target_words,
        "final_words": len(clean.split()),
        "continuity_expansions": len(additions),
    }


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(0.0, float(result.stdout.strip() or 0.0))


def _longest_silence(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "silencedetect=noise=-48dB:d=0.55", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    durations = [float(x) for x in re.findall(r"silence_duration:\s*([0-9.]+)", result.stderr or "")]
    return max(durations, default=0.0)


def fit_and_validate_spiritual_voice(
    path: Path,
    target_seconds: float,
    *,
    min_coverage: float = 0.94,
    max_silence_seconds: float = 1.15,
) -> dict:
    """Validate fixed natural narration and allow only tiny timing correction.

    The previous pipeline could slow narration substantially to fill the video.
    That is forbidden here. A mismatch beyond a few percent must be solved by
    regenerating/fitting the script, not by changing the narrator's speed.
    """
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("La pista de voz espiritual no existe o está vacía.")
    target = float(target_seconds)
    if target <= 2:
        raise RuntimeError("Duración objetivo inválida para narración espiritual.")

    before = _probe_duration(path)
    if before <= 1:
        raise RuntimeError("La narración espiritual generada es demasiado corta.")

    desired = target * 0.985
    tempo = before / desired

    # Never make Voz de Luz perceptibly slower. If narration is too short,
    # regenerate with more text instead of stretching it.
    if tempo < 0.965:
        raise RuntimeError(
            f"VOICE_CADENCE_LOCK: la voz dura {before:.1f}s para un video de {target:.1f}s. "
            "Se requiere más texto; está prohibido ralentizar Voz de Luz para rellenar tiempo."
        )
    if tempo > 1.055:
        raise RuntimeError(
            f"VOICE_CADENCE_LOCK: la narración dura {before:.1f}s para un video de {target:.1f}s. "
            "Se requiere ajustar el guion; está prohibido cambiar perceptiblemente la velocidad fija."
        )

    # Only a tiny correction is allowed, small enough not to alter perceived identity.
    applied_tempo = 1.0
    if abs(tempo - 1.0) >= 0.008:
        applied_tempo = tempo
        temp = path.with_name(path.stem + ".natural-fit.wav")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
            "-af", f"atempo={tempo:.7f}", "-ar", "48000", "-ac", "1", str(temp),
        ], check=True)
        if not temp.exists() or temp.stat().st_size < 1000:
            raise RuntimeError("FFmpeg no pudo aplicar el ajuste mínimo de sincronización.")
        temp.replace(path)

    after = _probe_duration(path)
    coverage = after / target
    longest = _longest_silence(path)
    if coverage < min_coverage:
        raise RuntimeError(
            f"BLOQUEADO: cobertura de voz {coverage:.1%}; se exige al menos {min_coverage:.0%}. "
            "Se regenerará el guion sin ralentizar la voz."
        )
    if longest > max_silence_seconds:
        raise RuntimeError(
            f"VOICE_CADENCE_LOCK: pausa de {longest:.2f}s; máximo permitido {max_silence_seconds:.2f}s. "
            "No se publicará una narración excesivamente pausada."
        )
    return {
        "voice_seconds_before_fit": round(before, 3),
        "voice_seconds_after_fit": round(after, 3),
        "voice_coverage_ratio": round(coverage, 5),
        "longest_voice_silence_seconds": round(longest, 3),
        "voice_tempo_adjustment": round(applied_tempo, 5),
        "voice_cadence_locked": True,
        "voice_slow_stretch_forbidden": True,
        "voice_continuity_passed": True,
    }
