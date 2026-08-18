from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Importing the fast publisher installs the same fresh-visual and fixed-Algenib
# runtime used by current Dios Habla Hoy Shorts, but does not publish by itself.
import scripts.publish_dios_fast as fast_runtime  # noqa: F401
from app import pipeline, spiritual_tts
from app.config import load_channel
from app.generator_resilient import _local_metadata
from app.youtube import _youtube_for_channel

ROOT = Path(__file__).resolve().parents[1]
NEW_RECORDS = ROOT / "state" / "recovery_new_records.jsonl"
RESULT = ROOT / "output" / "dios_missing_recovery.json"
HISTORY = ROOT / "state" / "history.jsonl"

TARGETS = (
    {
        "old_id": "NMHhIe2vgOs",
        "family": "como orar cuando no sabes que decir",
        "topic": "Romanos 8 y la oración cuando faltan las palabras",
        "title": "Cuando no sabés qué decir al orar | Romanos 8:26",
        "reference": "Romanos 8:26-27",
        "keyword": "oración a Dios",
        "lines": [
            "Hay momentos en que querés orar, pero el cansancio es tan grande que las palabras simplemente no aparecen.",
            "Romanos 8:26 recuerda que nuestra debilidad no cancela la oración y que Dios conoce lo que ocurre dentro del corazón.",
            "No necesitás construir una frase perfecta para acercarte: podés presentarte con sinceridad, incluso si solamente podés guardar silencio.",
            "Decile a Dios lo que sí podés nombrar: tu miedo, tu cansancio, una persona que amás o una decisión pendiente.",
            "Después quedate unos segundos en calma y recordá que una oración sencilla también puede ser un acto profundo de confianza.",
            "Cuando no encuentres palabras, no te alejes. Permanecé delante de Dios con un corazón sincero y seguí caminando. Amén.",
        ],
    },
    {
        "old_id": "qerN6TsgLJw",
        "family": "Jesus llama a los cansados a encontrar descanso",
        "topic": "Mateo 11 y entregar las cargas a Jesús",
        "title": "Jesús te invita a descansar tus cargas | Mateo 11:28",
        "reference": "Mateo 11:28-30",
        "keyword": "Jesús",
        "lines": [
            "Si sentís que llevás demasiadas cosas al mismo tiempo, recordá la invitación que Jesús hace a los cansados.",
            "En Mateo 11:28-30, Jesús llama a acercarse a quienes están cargados y ofrece un descanso que empieza en el corazón.",
            "Descansar en Dios no significa abandonar responsabilidades; significa dejar de sostener solo aquello que también podés presentar en oración.",
            "Elegí hoy una carga concreta y preguntate qué parte podés resolver, cuál podés compartir y cuál necesitás entregar a Dios.",
            "Permitite también descansar, pedir ayuda y recuperar fuerzas sin sentir que eso disminuye tu fe ni tu compromiso.",
            "Jesús no te invita a fingir fortaleza. Acercate con lo que llevás y caminá un paso a la vez. Amén.",
        ],
    },
    {
        "old_id": "o3fe1fwibpw",
        "family": "profecia mesianica de Isaias 9",
        "topic": "Isaías 9, luz en la oscuridad y esperanza mesiánica",
        "title": "Una luz que vence la oscuridad | Isaías 9",
        "reference": "Isaías 9:2,6",
        "keyword": "profecía bíblica",
        "lines": [
            "Isaías 9 nació en un contexto de oscuridad e incertidumbre, pero anuncia una luz capaz de cambiar la mirada del pueblo.",
            "El pasaje habla de esperanza y presenta al niño prometido con títulos que apuntan al gobierno, la justicia y la paz.",
            "Para los cristianos, esta profecía encuentra su cumplimiento mesiánico en Jesús y recuerda que la oscuridad no tiene la última palabra.",
            "Cuando el presente parece confuso, la Biblia no invita a inventar fechas ni señales, sino a permanecer fieles y esperanzados.",
            "Podés llevar esta promesa a tu día buscando paz, actuando con justicia y compartiendo luz con quien atraviesa una etapa difícil.",
            "Que la esperanza de Isaías 9 fortalezca tu fe y te recuerde que Dios sigue siendo digno de confianza. Amén.",
        ],
    },
)


def _exists_on_owner_api(video_id: str) -> bool:
    channel = load_channel("dioshablahoyia")
    youtube = _youtube_for_channel(channel)
    response = youtube.videos().list(part="id,status", id=video_id).execute()
    return bool(response.get("items"))


def _script_hash(lines: list[str]) -> str:
    clean = " ".join(" ".join(lines).lower().split())
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


def _metadata_builder(target: dict):
    def build(channel: dict, previous: list[dict], retries: int = 5) -> dict:
        del retries
        metadata = _local_metadata(channel, previous)
        count = int(channel.get("scenes_per_short") or 6)
        rows = list(metadata.get("scenes") or [])
        while len(rows) < count:
            rows.append({})
        for index in range(count):
            rows[index]["narration"] = target["lines"][index % len(target["lines"])]
        metadata["scenes"] = rows[:count]
        metadata["content_family"] = target["family"] + " — recuperación renovada"
        metadata["topic"] = target["topic"] + " — recuperación renovada"
        metadata["title"] = target["title"]
        metadata["bible_reference"] = target["reference"]
        metadata["seo_primary_keyword"] = target["keyword"]
        metadata["hook"] = target["lines"][0]
        metadata["script_hash"] = _script_hash(target["lines"])
        metadata["description"] = (
            f"Reflexión cristiana basada en {target['reference']}. "
            "Un mensaje sobre Dios, Jesús, la Biblia, la fe, la oración y la esperanza para acompañarte hoy."
        )
        metadata["hashtags"] = ["#Dios", "#Jesus", "#Biblia", "#Fe", "#Oracion"]
        metadata["tags"] = [
            "Dios", "Jesús", "Biblia", "fe", "oración", "esperanza",
            target["reference"], target["keyword"], "Dios Habla Hoy",
        ]
        metadata["recovery_of_missing_video_id"] = target["old_id"]
        metadata["recovery_mode"] = "missing_video_safe_reupload_fresh_visuals_fixed_voice"
        return metadata
    return build


def _append_latest_record() -> dict:
    rows = [line for line in HISTORY.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise RuntimeError("La publicación terminó sin agregar registro al historial.")
    latest = json.loads(rows[-1])
    NEW_RECORDS.parent.mkdir(parents=True, exist_ok=True)
    with NEW_RECORDS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(latest, ensure_ascii=False) + "\n")
    return latest


def main() -> None:
    # Reduce TTS request count while preserving the exact same Algenib voice.
    # About 60 seconds of Spanish prose fits safely in two Gemini chunks.
    original_chunker = spiritual_tts.safe_tts_chunks
    spiritual_tts.safe_tts_chunks = lambda text, max_words=42, max_chars=300: original_chunker(
        text, max_words=64, max_chars=480
    )

    NEW_RECORDS.unlink(missing_ok=True)
    results: list[dict] = []
    for target in TARGETS:
        old_id = target["old_id"]
        if _exists_on_owner_api(old_id):
            results.append({"old_id": old_id, "status": "skipped_original_still_exists"})
            continue

        pipeline.generate_metadata = _metadata_builder(target)
        print(f"RECOVERING_MISSING_SHORT old_id={old_id} topic={target['topic']}")
        try:
            output = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
            record = _append_latest_record()
            results.append({
                "old_id": old_id,
                "status": "reuploaded",
                "new_id": record.get("video_id") or output.get("video_id"),
                "title": record.get("title") or target["title"],
            })
        except Exception as exc:
            results.append({"old_id": old_id, "status": "failed", "error": f"{type(exc).__name__}: {exc}"})
            print(f"RECOVERY_FAILED old_id={old_id}: {exc}")

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    failed = [item for item in results if item["status"] == "failed"]
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
