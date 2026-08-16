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

from .audio import fit_voice_to_duration, make_natural_spanish_voice, make_pleasant_original_music
from .config import OUTPUT_DIR, ROOT, load_channel
from .hf_video import _provider_video, _safe_seed, _space_video
from .spiritual_lipsync import apply_musetalk_lipsync, available as lipsync_available
from .spiritual_reference_generation import generate_reference_guided_image
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
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


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
    # Keep roughly 128 spoken words per minute across the full video. The
    # lower floor is deliberately small enough for the new 5-minute format.
    target_words = max(115, min(270, round((minutes * 128) / max(1, sections))))
    return f"""
Eres guionista senior de documentales y reflexiones cristianas para YouTube.
Canal: {channel['display_name']} ({channel['handle']}).
Duracion objetivo exacta del montaje: {minutes} minutos.
Cantidad de secciones: {sections}.

IDENTIDAD VISUAL OBLIGATORIA:
Representacion humana digital fotorrealista y reverente de Jesus, completamente sintetica por IA pero visualmente equivalente a una filmacion live-action premium: hombre adulto de aspecto mediterraneo/oriental medio, cabello castaño oscuro ondulado hasta los hombros, barba completa cuidada, ojos avellana, piel humana con poros y detalle natural, tunica de lino marfil o crema y manto beige. Mantener exactamente la misma identidad facial y corporal durante todo el video. No copiar a ningun actor, celebridad ni persona identificable.

ESTETICA:
Solo fotorrealismo cinematografico. Prohibido dibujo, ilustracion, pintura, anime, cartoon, personaje de videojuego, 3D estilizado, piel plastica CGI o aspecto de muñeco. Fondos de apariencia real: naturaleza, valles, rios, montañas, bosque, lago, costa, nieve, aurora boreal, desierto y caminos de piedra. Luz fisicamente plausible, profundidad fotografica real y movimiento de camara cinematografico.

ACTUACION DEL PERSONAJE:
Cuando aparezca hablando, debe hacerlo como un actor humano real: movimiento continuo de labios y mandibula, mejillas, respiracion, parpadeo, cabeza y mirada; manos con cinco dedos, brazos, hombros, torso, cadera, piernas y pasos naturales cuando se vea el cuerpo entero. Gestos suaves y coherentes, ropa reaccionando al cuerpo y al viento. Evitar poses congeladas.

TEMAS PERMITIDOS:
Biblia, Dios, Jesucristo, fe, esperanza, oracion, consuelo, perdon, amor al projimo, perseverancia, promesas biblicas y profecias biblicas explicadas con contexto.

REFERENCIAS SEGURAS PARA INSPIRAR EL VIDEO:
{refs}

REGLAS BIBLICAS:
- Cuando uses un pasaje, identifica la referencia.
- Prefiere resumir o parafrasear la idea; no inventes versiculos.
- Una cita literal, si aparece, debe ser breve.
- Si el tema es profecia, explica contexto y evita fijar fechas o presentar especulacion como certeza.
- Cuando existan interpretaciones cristianas diferentes, dilo con prudencia.
- No usar miedo, amenazas ni sensacionalismo.

NARRACION CONTINUA:
Voz masculina calida, serena, profunda, neutra en español y humana. El texto de cada seccion debe enlazar directamente con la siguiente como un unico discurso. Aproximadamente {target_words} a {target_words + 20} palabras por seccion. Evita silencios dramaticos, puntos suspensivos, frases sueltas de una sola linea y nuevos saludos. Usa oraciones fluidas conectadas por transiciones naturales. La voz debe poder reproducirse como una unica pista continua sin cortes entre escenas.

VISUALES:
Cada visual_prompt debe describir una escena horizontal 16:9 live-action fotorrealista con movimiento humano visible y fondo realista. Alterna primeros planos hablando, planos medios con manos, planos de cuerpo entero caminando y planos ambientales. No texto, no logos, no marcas de agua.

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
      "narration": "narracion continua y conectada"
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
        row["visual_prompt"] = " ".join(str(row.get("visual_prompt") or "").split())[:1700]
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
    data["character_reference_profile"] = "dioshablahoyia_photoreal_human_v4_reference_guided"
    data["reference_seed"] = refs
    data["photoreal_human_required"] = True
    data["no_cartoon_no_3d_animation"] = True
    data["continuous_speech_requested"] = True
    data["lip_sync_requested"] = True
    data["full_body_motion_requested"] = True
    return data


def _character_style() -> str:
    return (
        "Same recurring fully synthetic photoreal human representation of Jesus throughout the film, visually indistinguishable from premium live-action cinema: "
        "adult Middle Eastern/Mediterranean-looking man, shoulder-length wavy dark-brown hair with natural strands, full groomed brown beard, hazel-brown eyes, natural skin pores and fine facial detail, "
        "ivory or cream woven linen robe and beige mantle, no resemblance to any identifiable real person. Natural continuous speaking performance with realistic lips, jaw, cheeks, blinking, breathing, head turns, "
        "five-finger hand gestures, shoulders, elbows, torso, hips, knees and believable walking balance. Real-looking valleys rivers alpine mountains forests lakes coastlines desert dunes snow and aurora borealis as appropriate. "
        "Photographic optics, physically plausible light, cinematic depth of field, natural fabric and environmental motion. Absolutely no cartoon, illustration, painting, anime, stylized 3D, videogame look, plastic CGI skin or doll face. "
        "Horizontal 16:9, no text, no subtitles, no logo, no watermark."
    )


def _download_image(prompt: str, out: Path, seed: int) -> str:
    full_prompt = f"{prompt}. {_character_style()}"
    try:
        provider, _ = generate_reference_guided_image(
            full_prompt,
            out,
            seed,
            target_size=(W, H),
        )
        return provider
    except Exception as exc:
        print(f"Hugging Face reference-guided long image no disponible ({exc}); usando respaldo Flux/Pollinations.")

    key = os.getenv("POLLINATIONS_API_KEY", "").strip()
    url = POLLINATIONS_BASE + quote(full_prompt, safe="")
    params = {
        "model": os.getenv("POLLINATIONS_IMAGE_MODEL", "flux"),
        "width": W,
        "height": H,
        "seed": _safe_seed(seed),
        "nologo": "true",
        "enhance": "true",
    }
    headers = {"User-Agent": "YouTube-AI-Automation/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    response = requests.get(url, params=params, headers=headers, timeout=(20, 180))
    response.raise_for_status()
    if len(response.content) < 20_000:
        raise RuntimeError("No se genero una imagen espiritual fotorrealista valida.")
    out.write_bytes(response.content)
    return "Pollinations Flux photoreal image"


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
        provider = _space_video(f"{prompt}. {_character_style()}", raw, 8, _safe_seed(seed))
    except Exception as first:
        try:
            provider = _provider_video(f"{prompt}. {_character_style()}", raw, _safe_seed(seed))
        except Exception as second:
            raise RuntimeError(f"LTX ZeroGPU: {first}; Inference Provider: {second}") from second
    _landscape_loop_video(raw, out, 8, 0)
    return provider


def _visual_for_section(meta: dict, section: dict, index: int, workdir: Path, ai_slots: int, duration: int) -> tuple[Path, str]:
    prompt = section["visual_prompt"]
    require_live = os.getenv("SPIRITUAL_REQUIRE_LIVE_ACTION", "true").lower().strip() == "true"
    allow_still = os.getenv("SPIRITUAL_ALLOW_STILL_FALLBACK", "false").lower().strip() == "true"

    if index < ai_slots:
        ai_clip = workdir / f"spiritual_ai_key_{index + 1}.mp4"
        try:
            provider = _try_text_to_video(prompt, ai_clip, _seed(meta, index))
            extended = workdir / f"spiritual_visual_{index + 1}.mp4"
            _landscape_loop_video(ai_clip, extended, duration, index)
            return extended, provider
        except Exception as exc:
            if require_live and not allow_still:
                raise RuntimeError(
                    f"Text-to-video live-action no disponible para seccion {index + 1}; se bloquea el fallback fijo para mantener calidad fotorrealista: {exc}"
                ) from exc
            print(f"Text-to-video no disponible para seccion {index + 1}: {exc}; usando imagen fotorrealista solo porque el fallback fue habilitado.")
    elif require_live and not allow_still:
        raise RuntimeError(
            f"La seccion {index + 1} quedo fuera de SPIRITUAL_LONG_AI_CLIPS y el canal exige live-action. Aumenta SPIRITUAL_LONG_AI_CLIPS."
        )

    image = workdir / f"spiritual_image_{index + 1}.jpg"
    visual = workdir / f"spiritual_visual_{index + 1}.mp4"
    image_provider = _download_image(prompt, image, _seed(meta, index))
    _image_motion(image, visual, duration, index)
    return visual, f"{image_provider} + cinematic motion fallback"


def _visual_segment(visual: Path, out: Path, duration: int) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual),
        "-t", str(duration), "-an", "-c:v", "copy", "-movflags", "+faststart", str(out),
    ], check=True)


def _concat_voice_chunks(chunks: list[Path], out: Path) -> None:
    if not chunks:
        raise RuntimeError("No hay fragmentos de voz para unir.")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for chunk in chunks:
        cmd.extend(["-i", str(chunk)])
    filters: list[str] = []
    labels: list[str] = []
    for index in range(len(chunks)):
        label = f"v{index}"
        filters.append(f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono[{label}]")
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(chunks)}:v=0:a=1[voice]")
    cmd.extend([
        "-filter_complex", ";".join(filters), "-map", "[voice]", "-c:a", "pcm_s16le", str(out),
    ])
    subprocess.run(cmd, check=True)


def _assemble(meta: dict, channel: dict, workdir: Path, minutes: int) -> Path:
    sections = list(meta["sections"])
    total_seconds = minutes * 60
    section_duration = total_seconds // len(sections)
    extra = total_seconds - section_duration * len(sections)
    require_live = os.getenv("SPIRITUAL_REQUIRE_LIVE_ACTION", "true").lower().strip() == "true"
    default_ai_slots = len(sections) if require_live else min(4, len(sections))
    ai_slots = max(0, min(int(os.getenv("SPIRITUAL_LONG_AI_CLIPS", str(default_ai_slots))), len(sections)))
    visuals: list[Path] = []
    voice_chunks: list[Path] = []
    providers: list[str] = []
    tts_used: list[str] = []

    # Build narration separately from visuals. Voice never restarts at visual cuts.
    for index, section in enumerate(sections):
        voice = workdir / f"spiritual_voice_{index + 1}.wav"
        tts_used.append(make_natural_spanish_voice(voice, section["narration"]))
        voice_chunks.append(voice)

    continuous_voice = workdir / "spiritual_continuous_voice.wav"
    _concat_voice_chunks(voice_chunks, continuous_voice)
    fit_voice_to_duration(continuous_voice, total_seconds)

    for index, section in enumerate(sections):
        duration = section_duration + (1 if index < extra else 0)
        visual, provider = _visual_for_section(meta, section, index, workdir, ai_slots, duration)
        providers.append(provider)
        segment = workdir / f"spiritual_visual_segment_{index + 1}.mp4"
        _visual_segment(visual, segment, duration)
        visuals.append(segment)

    manifest = workdir / "spiritual_long_visual_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in visuals), encoding="utf-8")
    visual_video = workdir / "spiritual_visual_video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-an", "-c:v", "copy", "-movflags", "+faststart", str(visual_video),
    ], check=True)

    lip_visual = visual_video
    meta["lip_sync_requested"] = True
    if os.getenv("SPIRITUAL_LONG_LIPSYNC_ENABLED", "true").lower().strip() == "true" and lipsync_available():
        synced = workdir / "spiritual_visual_video_lipsynced.mp4"
        try:
            meta["lip_sync_provider"] = apply_musetalk_lipsync(visual_video, continuous_voice, synced)
            meta["lip_sync_mode"] = "audio_driven_exact_mouth_sync"
            lip_visual = synced
        except Exception as exc:
            meta["lip_sync_failed"] = str(exc)
            meta["lip_sync_mode"] = "prompted_natural_speech_motion_fallback"
            print(f"Lip-sync exacto no disponible en video largo ({exc}); se conserva movimiento facial generado por el motor de video.")
    else:
        meta["lip_sync_mode"] = "prompted_natural_speech_motion_no_gpu"

    music_seed = _seed(meta, 999)
    music = workdir / "spiritual_original_music_60s.wav"
    make_pleasant_original_music(music, 60, music_seed)
    final = workdir / f"dioshablahoyia_{minutes}min.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(lip_visual), "-i", str(continuous_voice), "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        f"[1:a]highpass=f=65,lowpass=f=11000,acompressor=threshold=-18dB:ratio=1.7:attack=10:release=130,loudnorm=I=-16:TP=-1.5:LRA=7,apad=pad_dur={total_seconds}[v];"
        "[2:a]volume=0.026,lowpass=f=7600[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0.25[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(total_seconds),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final),
    ], check=True)

    meta["visual_providers"] = providers
    meta["tts_providers"] = sorted(set(tts_used))
    meta["voice_delivery"] = "single_continuous_track_across_all_scene_cuts"
    meta["text_to_video_key_scenes_requested"] = ai_slots
    meta["render_quality"] = "1920x1080_30fps_spiritual_reference_guided_long"
    meta["music_source"] = "original_instrumental_generated_locally"
    meta["spiritual_quality_profile"] = "premium_long_reference_guided_photoreal_v5"
    meta["photoreal_human_required"] = True
    meta["no_cartoon_no_3d_animation"] = True
    return final


def _thumbnail(video: Path, workdir: Path) -> Path:
    out = workdir / "thumbnail.jpg"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(video), "-frames:v", "1",
        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", "-q:v", "2", str(out),
    ], check=True)
    return out


def run(minutes: int, publish: bool = False) -> dict:
    if minutes not in {5, 10, 15, 20, 30, 40}:
        raise ValueError("minutes debe ser 5, 10, 15, 20, 30 o 40")
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
        "voice_delivery": meta.get("voice_delivery"),
        "lip_sync_mode": meta.get("lip_sync_mode"),
        "text_to_video_key_scenes_requested": meta.get("text_to_video_key_scenes_requested"),
        "visual_providers": meta.get("visual_providers"),
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[5, 10, 15, 20, 30, 40])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(args.minutes, publish=args.publish)


if __name__ == "__main__":
    main()
