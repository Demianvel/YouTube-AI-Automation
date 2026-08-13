from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from gradio_client import Client, handle_file

ROOT = Path.cwd()
OUT = ROOT / "output" / "aqui_estas_demianvelo"
MUSIC_DIR = OUT / "music"
VIDEO_DIR = OUT / "video"
FINAL_DIR = OUT / "final"
REFERENCE_DIR = ROOT / "reference_aleluya"

TITLE = "Aquí Estás x DemianVelo | Música Cristiana para Volver a Creer"
BPM = 82
TARGET_SECONDS = 240

# Original direction only: contemporary worship/pop atmosphere, not a cover and not a melody imitation.
STYLE_PROMPT = (
    "Completely original melodic Christian pop worship song for DemianVelo, 82 BPM, D major with emotional B minor colors, "
    "premium organic cinematic production with intimate grand piano, acoustic guitar, clean electric guitar swells, "
    "deep rounded electric bass, tasteful live acoustic drums, cinematic strings, subtle pipe organ and a human choir in the final chorus, "
    "sweet warm original adult male tenor-baritone lead vocal in neutral Rioplatense Argentine Spanish, velvety intimate low register, "
    "clear gentle diction, believable breaths, controlled natural vibrato, emotional chest voice, luminous upper register, tender heart-filling delivery, "
    "professional radio-ready mix with strong vocal presence and natural dynamics. Build gradually from a quiet intro to a large "
    "hopeful worship chorus and emotional bridge, then finish with a powerful but tasteful final chorus. "
    "Theme: God's nearness when life feels uncertain, peace, restoration, faith, Jesus, gratitude and hope. "
    "Use a completely original melody, harmony, lyric phrasing and hook. Do not imitate any singer, song, worship recording or copyrighted melody. "
    "No synthesizer lead, no electronic pulse, no EDM, no dance beat, no trap, no reggaeton, no commercial samples."
)

LYRICS = """[INTRO]
En el silencio de esta habitación,
cuando me cuesta escuchar mi corazón,
respiro lento y vuelvo a recordar:
no estoy solo, nunca me dejás.

[VERSO 1]
Cuando el día pesa más de lo normal,
y cada puerta parece cerrar,
cuando las dudas quieren decidir por mí,
Tu paz me encuentra justo donde estoy aquí.
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
sosteniendo en silencio el corazón.
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
Tu luz no grita, pero nunca deja de alumbrar.
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
aquí estás.

[PUENTE]
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
y mi corazón aprende a descansar.

[CORO FINAL]
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
Aquí estás.
"""

SECTIONS = [
    """[INTRO]
En el silencio de esta habitación,
cuando me cuesta escuchar mi corazón,
respiro lento y vuelvo a recordar:
no estoy solo, nunca me dejás.

[VERSO 1]
Cuando el día pesa más de lo normal,
y cada puerta parece cerrar,
cuando las dudas quieren decidir por mí,
Tu paz me encuentra justo donde estoy aquí.
No necesito tener todo bajo control,
ni conocer mañana para confiar en Vos.
Hay una calma que no puedo explicar,
y en medio de mi ruido me volvés a abrazar.

[PRE-CORO]
Si el miedo quiere hablar más fuerte que mi fe,
levanto la mirada y vuelvo a comprender:""",
    """[CORO]
Aquí estás,
más cerca que mi propia respiración.
Aquí estás,
sosteniendo en silencio el corazón.
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
aquí estás.

[PUENTE]
En la mañana y en la madrugada,
en mi alegría y en mis días sin palabras,
en cada herida que aprendió a sanar,
en cada sueño que se anima a comenzar.""",
    """[PUENTE]
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
y mi corazón aprende a descansar.

[CORO FINAL]
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

WAN_PROMPTS = [
    "Original fictional adult male Christian pop singer performing an intimate verse on a minimal cinematic stage, warm expressive face, natural breathing and body movement, elegant dark neutral wardrobe without logos, volumetric golden backlight and deep blue atmosphere, photorealistic premium commercial music video, smooth slow dolly-in, no celebrity resemblance, no text, 16:9",
    "Original fictional adult male singer performing a powerful worship chorus on a wide cinematic stage, tasteful haze, moving warm spotlights, emotional natural hand gestures, polished realistic skin and fabric, premium contemporary music video camera orbit, no celebrity resemblance, no brands, no text, 16:9",
    "Solitary silhouette walking along a mountain ridge just before sunrise, first golden rays breaking through dramatic clouds, hopeful spiritual atmosphere, smooth cinematic drone movement, photorealistic premium music video, no logos, no text, 16:9",
    "Rain-wet city street at blue hour with warm window reflections, original fictional adult male singer walking slowly toward camera while singing emotionally, cinematic shallow depth of field, natural body motion, premium commercial color grade, no celebrity resemblance, no logos, no text, 16:9",
]

STOCK_QUERIES = [
    "cinematic sunrise mountains golden hour",
    "ocean waves golden hour cinematic",
    "waterfall forest sunlight cinematic",
    "wildflowers wind golden hour cinematic",
    "church architecture sunlight cinematic",
    "dramatic clouds sun rays cinematic",
    "forest sunlight rays cinematic",
    "mountain lake sunrise cinematic",
    "hands praying silhouette sunset cinematic",
    "open bible candlelight cinematic",
]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("RUN", " ".join(cmd))
    return subprocess.run(cmd, check=check, text=True, capture_output=False)


def media_duration(path: Path) -> float:
    cp = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(cp.stdout.strip())


def decode_audio_result(result: Any, out: Path) -> Path:
    if isinstance(result, str):
        p = Path(result)
        if p.exists() and p.is_file():
            shutil.copy2(p, out)
            return out
        s = result.strip()
        if ";base64," in s and s.startswith("data:audio/"):
            out.write_bytes(base64.b64decode(s.split(";base64,", 1)[1]))
            return out
        try:
            raw = base64.b64decode(s, validate=True)
            if len(raw) > 100_000:
                out.write_bytes(raw)
                return out
        except Exception:
            pass
    if isinstance(result, dict):
        for value in result.values():
            try:
                return decode_audio_result(value, out)
            except Exception:
                continue
    if isinstance(result, (list, tuple)):
        for value in result:
            try:
                return decode_audio_result(value, out)
            except Exception:
                continue
    raise RuntimeError("ACE-Step no devolvió audio utilizable")


def _reference_audio() -> Path | None:
    candidates = []
    if REFERENCE_DIR.exists():
        for ext in ("*.wav", "*.mp3", "*.flac", "*.m4a"):
            candidates.extend(REFERENCE_DIR.rglob(ext))
    return candidates[0] if candidates else None


def _try_official_reference_generation(final: Path, reference: Path) -> bool:
    """Try the official ACE-Step 1.5 Space with the previous DemianVelo vocal as acoustic reference.

    The official interface evolves, so the call is built from its current Gradio endpoint metadata.
    If the free ZeroGPU quota or endpoint shape prevents this, the stable public fallback is used.
    """
    token = os.getenv("HF_TOKEN") or None
    try:
        client = Client("ACE-Step/Ace-Step-v1.5", token=token, verbose=False)
        api = client.view_api(return_format="dict")
        named = api.get("named_endpoints", api)
        choices: list[tuple[str, dict[str, Any]]] = []
        for endpoint, spec in named.items():
            if not isinstance(spec, dict):
                continue
            names = [str(p.get("parameter_name") or "").lower() for p in spec.get("parameters", [])]
            returns = " ".join(str(r.get("component") or r.get("type") or "") for r in spec.get("returns", [])).lower()
            if any("reference_audio" in n or "refer_audio" in n for n in names) and any("lyric" in n for n in names) and ("audio" in returns or "generate" in endpoint.lower()):
                choices.append((endpoint, spec))
        if not choices:
            print("ACE_REFERENCE_NO_ENDPOINT")
            return False
        endpoint, spec = max(choices, key=lambda x: len(x[1].get("parameters", [])))
        args: list[Any] = []
        for p in spec.get("parameters", []):
            name = str(p.get("parameter_name") or "").lower().replace("-", "_")
            default = p.get("default", None)
            if "reference_audio" in name or "refer_audio" in name:
                value = handle_file(str(reference))
            elif "src_audio" in name or "source_audio" in name:
                value = None
            elif name in {"prompt", "caption", "music_prompt", "description"} or ("prompt" in name and "negative" not in name):
                value = STYLE_PROMPT
            elif "lyric" in name:
                value = LYRICS
            elif "task_type" in name:
                value = "text2music"
            elif "instrumental" in name:
                value = False
            elif "vocal_language" in name or name in {"language", "lang"}:
                value = "es"
            elif name == "bpm" or name.endswith("_bpm"):
                value = BPM
            elif "duration" in name and "repaint" not in name:
                value = float(TARGET_SECONDS)
            elif "inference_step" in name or name == "steps":
                value = 8
            elif "guidance_scale" in name:
                value = 7.0
            elif "thinking" in name:
                value = True
            elif "random_seed" in name:
                value = False
            elif name in {"seed", "manual_seed"}:
                value = 20260813
            elif "cover_strength" in name or "ref_audio_strength" in name:
                value = 0.55
            else:
                value = default
            args.append(value)
        print("ACE_REFERENCE_ENDPOINT", endpoint)
        result = client.predict(*args, api_name=endpoint)
        decode_audio_result(result, final)
        duration = media_duration(final)
        if 180 <= duration <= 300:
            print("ACE_REFERENCE_OK", duration, final.stat().st_size)
            return True
        final.unlink(missing_ok=True)
    except Exception as exc:
        print("ACE_REFERENCE_FAIL", type(exc).__name__, exc)
        final.unlink(missing_ok=True)
    return False


def generate_music() -> tuple[Path, str]:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    final = MUSIC_DIR / "Aqui_Estas_x_DemianVelo.wav"
    reference = _reference_audio()
    if reference and _try_official_reference_generation(final, reference):
        return final, "ACE-Step 1.5 official + Aleluya acoustic reference"

    token = os.getenv("HF_TOKEN") or None
    client = Client("victor/ace-step-jam", token=token, verbose=False)
    stable_seed = 20260813

    try:
        print("ACE_STEP: intentando canción continua de 240 segundos")
        result = client.predict(STYLE_PROMPT, LYRICS, 240.0, 8, 7.0, stable_seed, "", 0.8, api_name="/generate")
        decode_audio_result(result, final)
        duration = media_duration(final)
        if not 180 <= duration <= 300:
            raise RuntimeError(f"duración fuera de 3-5 min: {duration}")
        print("ACE_STEP_CONTINUOUS_OK", duration, final.stat().st_size)
        return final, "ACE-Step 1.5 continuous"
    except Exception as exc:
        print("ACE_STEP_CONTINUOUS_FAIL", type(exc).__name__, exc)
        final.unlink(missing_ok=True)

    section_files: list[Path] = []
    for index, lyrics in enumerate(SECTIONS, start=1):
        print("ACE_STEP_SECTION", index)
        result = client.predict(
            STYLE_PROMPT + f". This is section {index} of the same continuous song. Keep exactly the same singer timbre, vocal placement, production palette, tonal center and emotional identity across all sections.",
            lyrics,
            60.0,
            8,
            7.0,
            stable_seed,
            "",
            0.8,
            api_name="/generate",
        )
        section = MUSIC_DIR / f"section_{index}.wav"
        decode_audio_result(result, section)
        if media_duration(section) < 50:
            raise RuntimeError(f"ACE-Step sección {index} demasiado corta")
        section_files.append(section)

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for section in section_files:
        cmd += ["-i", str(section)]
    cmd += [
        "-filter_complex",
        "[0:a]loudnorm=I=-15:TP=-1.2:LRA=10[a0];[1:a]loudnorm=I=-15:TP=-1.2:LRA=10[a1];"
        "[2:a]loudnorm=I=-15:TP=-1.2:LRA=10[a2];[3:a]loudnorm=I=-15:TP=-1.2:LRA=10[a3];"
        "[a0][a1]acrossfade=d=0.6:c1=tri:c2=tri[a01];[a01][a2]acrossfade=d=0.6:c1=tri:c2=tri[a012];"
        "[a012][a3]acrossfade=d=0.6:c1=tri:c2=tri[outa]",
        "-map", "[outa]", "-c:a", "pcm_s16le", str(final),
    ]
    run(cmd)
    duration = media_duration(final)
    if not 180 <= duration <= 300:
        raise RuntimeError(f"canción final fuera de 3-5 minutos: {duration}")
    print("ACE_STEP_SEGMENTED_OK", duration, final.stat().st_size)
    return final, "ACE-Step 1.5 segmented stable-vocal-seed"


def _collect_video_files(value: Any, files: list[Path]) -> None:
    if isinstance(value, str):
        p = Path(value)
        if p.exists() and p.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}:
            files.append(p)
    elif isinstance(value, dict):
        for v in value.values():
            _collect_video_files(v, files)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _collect_video_files(v, files)


def _call_known_wan(prompt: str, seed: int) -> Path:
    token = os.getenv("HF_TOKEN") or None
    client = Client("OpenKing/wan2-video-generation", token=token, verbose=False)
    result = client.predict(prompt, None, 1280, 704, 73, 20, 5.0, seed, api_name="/generate_video")
    files: list[Path] = []
    _collect_video_files(result, files)
    if not files:
        raise RuntimeError("Wan2.2 no devolvió video")
    return files[0]


def _call_dynamic_wan(space: str, prompt: str, seed: int) -> Path:
    token = os.getenv("HF_TOKEN") or None
    client = Client(space, token=token, verbose=False)
    api = client.view_api(return_format="dict")
    named = api.get("named_endpoints", api)
    candidates: list[tuple[str, dict[str, Any]]] = []
    for endpoint, spec in named.items():
        if not isinstance(spec, dict):
            continue
        names = [str(p.get("parameter_name") or "").lower() for p in spec.get("parameters", [])]
        returns = " ".join(str(r.get("component") or r.get("type") or "") for r in spec.get("returns", [])).lower()
        if any("prompt" in n for n in names) and ("video" in endpoint.lower() or "video" in returns):
            candidates.append((endpoint, spec))
    if not candidates:
        raise RuntimeError(f"{space}: sin endpoint de video")
    endpoint, spec = max(candidates, key=lambda x: len(x[1].get("parameters", [])))
    args: list[Any] = []
    for p in spec.get("parameters", []):
        name = str(p.get("parameter_name") or "").lower().replace("-", "_")
        default = p.get("default", None)
        if "image" in name:
            value = None
        elif "prompt" in name and "negative" not in name:
            value = prompt
        elif "negative" in name:
            value = "blurry, low quality, text, watermark, logo, duplicate people, deformed anatomy, celebrity resemblance"
        elif "height" in name:
            value = 704
        elif "width" in name:
            value = 1280
        elif "duration" in name or "seconds" in name:
            value = 3.0
        elif "frame" in name:
            value = 73
        elif "sampling" in name or "inference_step" in name or name == "steps":
            value = 12
        elif "guidance" in name:
            value = 5.0
        elif "seed" in name:
            value = seed
        elif "random" in name and "seed" in name:
            value = False
        else:
            value = default
        args.append(value)
    result = client.predict(*args, api_name=endpoint)
    files: list[Path] = []
    _collect_video_files(result, files)
    if not files:
        raise RuntimeError(f"{space}: no devolvió video")
    return files[0]


def generate_wan_scenes() -> list[Path]:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    spaces = [
        "OpenKing/wan2-video-generation",
        "shafqat786/Wan-AI-Wan2.2-TI2V-5B",
        "Teheby63736363/Wan-AI-Wan2.2-TI2V-5B",
        "skrov/Wan-AI-Wan2.2-TI2V-5B",
    ]
    produced: list[Path] = []
    errors: list[str] = []
    for index, prompt in enumerate(WAN_PROMPTS, start=1):
        for space in spaces:
            try:
                src = _call_known_wan(prompt, 4200 + index) if space == spaces[0] else _call_dynamic_wan(space, prompt, 4200 + index)
                dst = VIDEO_DIR / f"wan_scene_{index:02d}{src.suffix.lower()}"
                shutil.copy2(src, dst)
                if dst.stat().st_size < 50_000:
                    raise RuntimeError("archivo de video demasiado pequeño")
                produced.append(dst)
                print("WAN_SCENE_OK", index, space, dst.stat().st_size)
                break
            except Exception as exc:
                msg = f"scene {index} {space}: {type(exc).__name__}: {exc}"
                errors.append(msg)
                print("WAN_SCENE_FAIL", msg)
    (VIDEO_DIR / "wan_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WAN_SCENES_TOTAL", len(produced))
    return produced


def _download_stock(seconds_by_block: list[int]) -> tuple[list[Path], list[dict[str, str]]]:
    from app.music_video import _get_real_segment

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []
    meta = {"topic": "Aquí Estás Christian worship DemianVelo", "title": TITLE}
    for index, (query, seconds) in enumerate(zip(STOCK_QUERIES, seconds_by_block), start=1):
        clip, credit = _get_real_segment(query, FINAL_DIR, 200 + index, seconds, False, used, 12000 + index, target_4k=False)
        clips.append(clip)
        credits.append(credit)
    return clips, credits


def build_video(audio: Path, wan_scenes: list[Path]) -> tuple[Path, list[dict[str, str]]]:
    target = media_duration(audio)
    if not 180 <= target <= 300:
        raise RuntimeError(f"audio fuera de 3-5 min: {target}")

    # Eight ~30-second cinematic blocks. A Wan hero shot replaces 6 seconds of a block when available.
    hero_count = min(4, len(wan_scenes), 8)
    seconds_by_block = [24 if i < hero_count else 30 for i in range(8)]
    stock, credits = _download_stock(seconds_by_block)

    wan_norm: list[Path] = []
    for index, src in enumerate(wan_scenes[:hero_count], start=1):
        dst = FINAL_DIR / f"wan_norm_{index}.mp4"
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(src), "-t", "6",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,eq=contrast=1.06:saturation=1.08:brightness=0.004,unsharp=5:5:0.16:5:5:0,fps=30",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(dst),
        ])
        wan_norm.append(dst)

    sequence: list[Path] = []
    for i, stock_clip in enumerate(stock):
        if i < len(wan_norm):
            sequence.append(wan_norm[i])
        sequence.append(stock_clip)

    manifest = FINAL_DIR / "concat.txt"
    manifest.write_text("\n".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'" for p in sequence), encoding="utf-8")
    visual = FINAL_DIR / "visual_1080p.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-t", f"{target:.3f}", "-an", "-vf", "eq=contrast=1.025:saturation=1.04,unsharp=5:5:0.10:5:5:0,fps=30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
    ])

    final = FINAL_DIR / "Aqui_Estas_x_DemianVelo.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(audio),
        "-map", "0:v:0", "-map", "1:a:0", "-t", f"{target:.3f}",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(final),
    ])
    duration = media_duration(final)
    if not 180 <= duration <= 300 or final.stat().st_size < 5_000_000:
        raise RuntimeError(f"video final inválido: duration={duration}, bytes={final.stat().st_size}")
    return final, credits


def make_thumbnail(video: Path) -> Path:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

    frame = FINAL_DIR / "thumbnail_source.jpg"
    out = FINAL_DIR / "thumbnail_aqui_estas.jpg"
    premium = ROOT / "assets" / "aqui-estas" / "thumbnail-aqui-estas-demianvelo.jpg"
    if premium.exists() and 0 < premium.stat().st_size < 1_900_000:
        shutil.copy2(premium, out)
        return out
    second = max(8, int(media_duration(video) * 0.15))
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", str(second), "-i", str(video), "-frames:v", "1",
        "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", str(frame),
    ])
    img = Image.open(frame).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.12)

    # Cinematic focus: slightly darken/blur left backdrop while preserving the visual subject.
    blurred = img.filter(ImageFilter.GaussianBlur(radius=7))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, 760, 720), fill=(0, 0, 0, 118))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    def font(size: int, bold: bool = True):
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        ]
        for path in paths:
            if Path(path).exists():
                return ImageFont.truetype(path, size=size)
        return ImageFont.load_default()

    draw = ImageDraw.Draw(img)
    big = font(105, True)
    mid = font(38, True)
    small = font(28, True)
    draw.text((58, 230), "AQUÍ", font=big, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    draw.text((58, 338), "ESTÁS", font=big, fill=(255, 244, 205), stroke_width=4, stroke_fill=(0, 0, 0))
    draw.text((64, 472), "DEMIANVELO", font=mid, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    draw.rounded_rectangle((60, 535, 405, 587), radius=18, fill=(255, 255, 255))
    draw.text((82, 545), "NUEVA CANCIÓN", font=small, fill=(20, 20, 20))
    img.save(out, "JPEG", quality=90, optimize=True)
    if out.stat().st_size > 1_900_000:
        img.save(out, "JPEG", quality=82, optimize=True)
    frame.unlink(missing_ok=True)
    return out


def _credits_text(credits: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for credit in credits:
        if credit.get("provider") == "Wikimedia Commons":
            creator = credit.get("creator") or "Wikimedia Commons contributor"
            license_name = credit.get("license") or "license shown at source"
            source = credit.get("source_url") or ""
            lines.append(f"Visual: {creator} — {license_name} — {source}".strip())
    return "\n".join(lines[:12])


def upload(video: Path, thumbnail: Path, credits: list[dict[str, str]]) -> str:
    from app.config import load_channel
    from app.youtube import upload_long_video

    channel = load_channel("demianvelo")
    credit_text = _credits_text(credits)
    description = (
        "Aquí Estás x DemianVelo es una canción cristiana original sobre esos momentos en los que todo parece incierto, "
        "pero la presencia de Dios sigue cerca. Una canción sobre fe, paz, restauración, esperanza y Jesús.\n\n"
        "Si esta canción te acompaña, guardala, compartila con alguien que la necesite y suscribite para escuchar las próximas canciones de DemianVelo.\n\n"
        "LETRA:\n" + LYRICS.strip() + "\n\n"
        + ("CRÉDITOS VISUALES CUANDO CORRESPONDE:\n" + credit_text + "\n\n" if credit_text else "")
        + "#DemianVelo #AquiEstas #MusicaCristiana #Jesus #Adoracion"
    )
    meta = {
        "title": TITLE,
        "description": description,
        "hashtags": ["#DemianVelo", "#AquiEstas", "#MusicaCristiana", "#Jesus", "#Adoracion"],
        "tags": [
            "DemianVelo", "Aquí Estás", "Aqui Estas", "música cristiana", "musica cristiana", "Jesús", "Jesus", "Dios",
            "fe", "esperanza", "adoración", "adoracion", "worship", "christian music", "canción cristiana", "Argentina",
            "música de fe", "música para orar",
        ],
        "duration_minutes": 4,
        "long_form": True,
        "thumbnail_text": "AQUÍ ESTÁS",
        "source_credits": credits,
    }
    video_id = upload_long_video(channel, meta, video, thumbnail_path=thumbnail, expected_minutes=4)
    result = {"status": "uploaded", "video_id": video_id, "title": TITLE, "video": str(video), "thumbnail": str(thumbnail)}
    (FINAL_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("YOUTUBE_UPLOAD_SUCCESS", json.dumps(result, ensure_ascii=False))
    return video_id


def main() -> None:
    publish = "--publish" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    audio, music_engine = generate_music()
    wan_scenes = generate_wan_scenes()
    video, credits = build_video(audio, wan_scenes)
    thumbnail = make_thumbnail(video)
    metadata = {
        "title": TITLE,
        "bpm": BPM,
        "duration_seconds": media_duration(audio),
        "music_engine": music_engine,
        "video_engine": "Wan2.2 hero shots + real-camera cinematic montage" if wan_scenes else "real-camera cinematic montage",
        "voice_direction": "warm magnetic original adult male, improved Rioplatense Argentine Spanish identity",
        "reference_audio_available": bool(_reference_audio()),
        "lyrics": LYRICS,
        "thumbnail": str(thumbnail),
        "publish_requested": publish,
    }
    (FINAL_DIR / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (FINAL_DIR / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    if publish:
        upload(video, thumbnail, credits)


if __name__ == "__main__":
    main()
