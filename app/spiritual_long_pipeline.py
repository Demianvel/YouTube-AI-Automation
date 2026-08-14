from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from google import genai
from google.genai import types

from .audio import make_natural_spanish_voice, make_pleasant_original_music
from .config import OUTPUT_DIR, ROOT, load_channel
from .hf_video import _provider_video, _space_video
from .youtube import upload_long_video

W, H, FPS = 1920, 1080, 30
POLLINATIONS_BASE = "https://gen.pollinations.ai/image/"
TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-3.6-flash")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(0.0, float(result.stdout.strip() or 0.0))


def _seed(meta: dict, index: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"dioshablahoyia-long|{meta.get('topic','')}|{meta.get('title','')}|{index}|{marker}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _references() -> list[dict]:
    path = ROOT / "config" / "dioshablahoyia_bible_references.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_reference_seed(minutes: int) -> list[dict]:
    refs = _references()
    marker = os.getenv("GITHUB_RUN_NUMBER", "").strip()
    seed = int(marker) if marker.isdigit() else int(datetime.now(timezone.utc).strftime("%Y%m%d%H"))
    rng = random.Random(seed ^ minutes ^ 0xD105)
    refs = list(refs)
    rng.shuffle(refs)
    return refs[: min(10, len(refs))]


def _metadata_prompt(channel: dict, minutes: int, sections: int, references: list[dict]) -> str:
    refs = "\n".join(f"- {item['reference']}: {item['theme']}" for item in references)
    target_words = 210 if minutes <= 20 else 190
    return f"""
Eres guionista senior de documentales y reflexiones cristianas para YouTube.
Canal: {channel['display_name']} ({channel['handle']}).
Duracion objetivo exacta del montaje: {minutes} minutos.
Cantidad de secciones: {sections}.

IDENTIDAD VISUAL:
Representacion artistica reverente y original de Jesus como personaje recurrente: hombre adulto sereno, cabello largo castaño oscuro ondulado, barba completa cuidada, ojos calidos, tunica de lino clara o beige, manto crema o rojo apagado ocasional, sin parecerse deliberadamente a ningun actor real. Paisajes cinematograficos de montañas, valles, rios, lagos, caminos de piedra, arboles, cielos, amaneceres y atardeceres dorados. Mantener el mismo diseño facial y vestuario base durante todo el video.

TEMAS PERMITIDOS:
Biblia, Dios, Jesucristo, fe, esperanza, oracion, consuelo, perdon, amor al projimo, perseverancia, promesas biblicas y profecias biblicas explicadas con contexto.

REFERENCIAS SEGURAS PARA INSPIRAR EL VIDEO:
{refs}

REGLAS BIBLICAS:
- Cuando uses un pasaje, identifica la referencia.
- Prefiere resumir o parafrasear la idea; no inventes versiculos.
- Una cita literal, si aparece, debe ser breve.
- No uses Bible Gateway ni otra traduccion como texto para copiar en bloques largos.
- Si el tema es profecia, explica contexto y evita fijar fechas o presentar especulacion sobre noticias actuales como certeza.
- Cuando existan interpretaciones cristianas diferentes, dilo con prudencia.
- No usar miedo, amenazas ni sensacionalismo.

NARRACION:
Voz masculina calida, serena, profunda y humana. Cada seccion debe sentirse conectada con la siguiente, como un solo video. Cada narration debe tener aproximadamente {target_words} a {target_words + 35} palabras. Alterna reflexion, explicacion biblica, aplicacion practica y momentos breves de oracion. No empieces cada seccion con un saludo nuevo.

VISUALES:
Cada visual_prompt debe describir una escena cinematografica horizontal 16:9 con movimiento visible: Jesus caminando, extendiendo una mano, contemplando un lago, cruzando un sendero, viento suave moviendo la ropa, agua y nubes en movimiento, rayos de luz cambiando. No texto, no logos, no marcas de agua, no actor real.

Devuelve SOLO JSON valido:
{{
  "topic": "tema principal",
  "title": "titulo natural de YouTube, maximo 95 caracteres",
  "description": "descripcion de 5 a 8 lineas",
  "hashtags": ["#Dios", "#Jesus", "#Biblia", "#Fe"],
  "tags": ["..."],
  "sections": [
    {{
      "heading": "titulo breve de seccion",
      "bible_reference": "referencia biblica o cadena vacia",
      "visual_prompt": "prompt cinematografico horizontal 16:9",
      "narration": "narracion conectada"
    }}
  ]
}}

Reglas de salida:
- sections debe contener exactamente {sections} elementos.
- hashtags entre 3 y 5.
- tags entre 10 y 18.
- Ningun visual_prompt puede quedar vacio.
- Ninguna narration puede quedar vacia.
- Nada de markdown fuera del JSON.
""".strip()


def _generate_metadata(channel: dict, minutes: int) -> dict:
    sections = max(5, minutes // 2)
    refs = _pick_reference_seed(minutes)
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=TEXT_MODEL,
        contents=_metadata_prompt(channel, minutes, sections, refs),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    rows = data.get("sections") or []
    if len(rows) != sections:
        raise RuntimeError(f"Gemini genero {len(rows)} secciones; se requieren {sections}.")
    for index, row in enumerate(rows, start=1):
        row["heading"] = " ".join(str(row.get("heading") or f"Seccion {index}").split())[:100]
        row["bible_reference"] = " ".join(str(row.get("bible_reference") or "").split())[:80]
        row["visual_prompt"] = " ".join(str(row.get("visual_prompt") or "").split())[:1400]
        row["narration"] = " ".join(str(row.get("narration") or "").split())
        if not row["visual_prompt"] or not row["narration"]:
            raise RuntimeError(f"Seccion {index} incompleta.")
    data["title"] = " ".join(str(data.get("title") or "Dios, fe y esperanza").split())[:95]
    data["description"] = str(data.get("description") or "").strip()
    data["hashtags"] = [str(x).strip() for x in (data.get("hashtags") or []) if str(x).strip()][:5]
    data["tags"] = [str(x).strip() for x in (data.get("tags") or []) if str(x).strip()][:18]
    data["duration_seconds"] = minutes * 60
    data["target_minutes"] = minutes
    data["contains_synthetic_media"] = True
    data["character_reference_profile"] = "dioshablahoyia_recurring_jesus_v1"
    data["reference_seed"] = refs
    return data


def _character_style() -> str:
    return (
        "Same recurring original reverent Jesus character throughout the entire film: serene adult man, long wavy dark-brown hair, full neat brown beard, "
        "warm hazel-brown eyes, compassionate face, cream or ivory linen robe, beige mantle or occasional muted deep-red mantle, no resemblance to a specific actor or celebrity. "
        "Premium photoreal cinematic spiritual drama, realistic skin and fabric, warm golden sunrise or sunset, mountains valleys rivers lakes olive trees and stone paths, "
        "natural movement, peaceful hopeful atmosphere, horizontal 16:9, no text, no subtitles, no logo, no watermark, no horror."
    )


def _download_image(prompt: str, out: Path, seed: int) -> None:
    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    url = POLLINATIONS_BASE + quote(f"{prompt}, {_character_style()}", safe="")
    params = {
        "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        "width": W,
        "height": H,
        "seed": seed,
        "nologo": "true",
        "enhance": "true",
    }
    headers = {"User-Agent": "YouTube-AI-Automation/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    response = requests.get(url, params=params, headers=headers, timeout=(20, 180))
    response.raise_for_status()
    if len(response.content) < 20_000:
        raise RuntimeError("No se genero una imagen espiritual valida.")
    out.write_bytes(response.content)


def _landscape_loop_video(source: Path, out: Path, duration: int, index: int) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},"
        "eq=contrast=1.025:saturation=1.04:brightness=0.003,unsharp=5:5:0.12:5:5:0"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def _image_motion(source: Path, out: Path, duration: int, index: int) -> None:
    frames = duration * FPS
    if index % 3 == 0:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "ih/2-(ih/zoom/2)"
    elif index % 3 == 1:
        x_expr = "min(iw-iw/zoom,(iw-iw/zoom)*on/max(1,duration*30))"
        y_expr = "ih/2-(ih/zoom/2)"
    else:
        x_expr = "iw/2-(iw/zoom/2)"
        y_expr = "min(ih-ih/zoom,(ih-ih/zoom)*on/max(1,duration*30))"
    vf = (
        f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
        f"zoompan=z='min(zoom+0.00035,1.07)':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps={FPS},"
        "setsar=1,eq=contrast=1.025:saturation=1.04:brightness=0.003"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)


def _try_text_to_video(prompt: str, out: Path, seed: int) -> str:
    raw = out.with_name(out.stem + "_raw.mp4")
    try:
        provider = _space_video(f"{prompt}. {_character_style()}", raw, 8, seed)
    except Exception as first:
        try:
            provider = _provider_video(f"{prompt}. {_character_style()}", raw, seed)
        except Exception as second:
            raise RuntimeError(f"LTX ZeroGPU: {first}; Inference Provider: {second}") from second
    _landscape_loop_video(raw, out, 8, 0)
    return provider


def _visual_for_section(meta: dict, section: dict, index: int, workdir: Path, ai_slots: int, duration: int) -> tuple[Path, str]:
    prompt = section["visual_prompt"]
    if index < ai_slots:
        ai_clip = workdir / f"spiritual_ai_key_{index + 1}.mp4"
        try:
            provider = _try_text_to_video(prompt, ai_clip, _seed(meta, index))
            extended = workdir / f"spiritual_visual_{index + 1}.mp4"
            _landscape_loop_video(ai_clip, extended, duration, index)
            return extended, provider
        except Exception as exc:
            print(f"Text-to-video no disponible para seccion {index + 1}: {exc}; usando imagen IA cinematografica.")

    image = workdir / f"spiritual_image_{index + 1}.jpg"
    visual = workdir / f"spiritual_visual_{index + 1}.mp4"
    _download_image(prompt, image, _seed(meta, index))
    _image_motion(image, visual, duration, index)
    return visual, "Pollinations image + cinematic motion fallback"


def _chapter_segment(visual: Path, voice: Path, out: Path, duration: int) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(voice),
        "-filter_complex", f"[1:a]highpass=f=65,lowpass=f=11000,loudnorm=I=-16:TP=-1.5:LRA=7,apad=pad_dur={duration}[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ], check=True)


def _assemble(meta: dict, channel: dict, workdir: Path, minutes: int) -> Path:
    sections = list(meta["sections"])
    total_seconds = minutes * 60
    section_duration = total_seconds // len(sections)
    extra = total_seconds - section_duration * len(sections)
    ai_slots = max(0, min(int(os.getenv("SPIRITUAL_LONG_AI_CLIPS", "4")), len(sections)))
    segments: list[Path] = []
    providers: list[str] = []
    tts_used: list[str] = []

    for index, section in enumerate(sections):
        duration = section_duration + (1 if index < extra else 0)
        voice = workdir / f"spiritual_voice_{index + 1}.wav"
        tts_used.append(make_natural_spanish_voice(voice, section["narration"]))
        visual, provider = _visual_for_section(meta, section, index, workdir, ai_slots, duration)
        providers.append(provider)
        segment = workdir / f"spiritual_segment_{index + 1}.mp4"
        _chapter_segment(visual, voice, segment, duration)
        segments.append(segment)

    manifest = workdir / "spiritual_long_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in segments), encoding="utf-8")
    voice_video = workdir / "spiritual_voice_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-c", "copy", "-movflags", "+faststart", str(voice_video),
    ], check=True)

    music_seed = _seed(meta, 999)
    music = workdir / "spiritual_original_music_60s.wav"
    make_pleasant_original_music(music, 60, music_seed)
    final = workdir / f"dioshablahoyia_{minutes}min.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(voice_video), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex", "[0:a]volume=1.0[v];[1:a]volume=0.035,lowpass=f=7600[m];[v][m]amix=inputs=2:duration=first:dropout_transition=2[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(total_seconds),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final),
    ], check=True)

    meta["visual_providers"] = providers
    meta["tts_providers"] = sorted(set(tts_used))
    meta["text_to_video_key_scenes_requested"] = ai_slots
    meta["render_quality"] = "1920x1080_30fps_spiritual_long"
    meta["music_source"] = "original_instrumental_generated_locally"
    return final


def _thumbnail(video: Path, workdir: Path) -> Path:
    out = workdir / "thumbnail.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(video), "-frames:v", "1",
        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", "-q:v", "2", str(out),
    ], check=True)
    return out


def run(minutes: int, publish: bool = False) -> dict:
    if minutes not in {10, 20, 30, 40}:
        raise ValueError("minutes debe ser 10, 20, 30 o 40")
    channel = load_channel("dioshablahoyia")
    meta = _generate_metadata(channel, minutes)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / "dioshablahoyia-long" / f"{minutes}min" / stamp
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    video = _assemble(meta, channel, workdir, minutes)
    thumbnail = _thumbnail(video, workdir)
    (workdir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    video_id = None
    status = "generated"
    if publish:
        video_id = upload_long_video(channel, meta, video, thumbnail_path=thumbnail, expected_minutes=minutes)
        status = "uploaded"

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": "dioshablahoyia",
        "minutes": minutes,
        "title": meta.get("title"),
        "video_id": video_id,
        "status": status,
        "path": str(video),
        "thumbnail": str(thumbnail),
        "text_to_video_key_scenes_requested": meta.get("text_to_video_key_scenes_requested"),
        "visual_providers": meta.get("visual_providers"),
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[10, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.minutes, publish=args.publish)


if __name__ == "__main__":
    main()
