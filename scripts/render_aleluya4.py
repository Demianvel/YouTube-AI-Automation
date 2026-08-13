from __future__ import annotations

import base64
import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client

from app.config import load_channel
from app.music_video import _get_real_segment
from app.youtube import upload_long_video

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output" / "aleluya4"
MUSIC_DIR = WORK / "music"
WAN_DIR = WORK / "wan"
FINAL_DIR = WORK / "final"

PROMPT = (
    "original Christian electronic worship, cinematic pop and progressive house, 122 BPM, "
    "warm deep original male singer, soft Argentine Spanish pronunciation, magnetic emotional vocal tone, "
    "intimate verses, ascending pre-chorus, huge uplifting chorus, luminous synth build and melodic electronic drop, "
    "modern professional mix, wide stereo image, polished dynamics, hopeful spiritual atmosphere, "
    "no imitation of any real singer, no copyrighted melody, no commercial samples"
)

FULL_LYRICS = """[INTRO]
Cuando la noche parece no terminar,
Tu luz me encuentra y me vuelve a levantar.

[VERSO 1]
Caminé entre preguntas buscando una señal,
y en medio del silencio escuché Tu verdad.
No fue el ruido del mundo ni una explicación,
fue Tu paz encendiendo de nuevo el corazón.

[PRE-CORO]
Y aunque tiemble el suelo bajo mis pies,
si Tu mano me sostiene, vuelvo a creer.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[POST-CORO / DROP]
Oh-oh, Aleluya,
oh-oh, Hallelujah,
Tu amor no se termina,
Tu luz siempre estará.

[VERSO 2]
Si el miedo me visita y me quiere detener,
Tu palabra me recuerda que puedo renacer.
No necesito verlo para saber que estás,
porque incluso en la tormenta me enseñás a confiar.

[PRE-CORO]
Y aunque el mundo cambie alrededor,
Tu promesa sigue hablando al corazón.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[PUENTE]
Dios de vida, Dios eterno,
cuando caigo, estás de nuevo.
En la cima, en el desierto,
Tu amor sigue siendo cierto.
Y si un día pierdo el rumbo,
Tu voz me vuelve a llamar.
No hay distancia, no hay silencio,
que me aparte de Tu paz.

[BUILD]
Aleluya…
Hallelujah…
Que lo escuche el cielo entero,
que lo cante el corazón.

[CORO FINAL]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
para siempre sos mi Dios.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[OUTRO]
Aleluya… Hallelujah…
Tu luz siempre estará."""

SECTIONS = [
    """[INTRO]
Cuando la noche parece no terminar,
Tu luz me encuentra y me vuelve a levantar.

[VERSO 1]
Caminé entre preguntas buscando una señal,
y en medio del silencio escuché Tu verdad.
No fue el ruido del mundo ni una explicación,
fue Tu paz encendiendo de nuevo el corazón.

[PRE-CORO]
Y aunque tiemble el suelo bajo mis pies,
si Tu mano me sostiene, vuelvo a creer.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.""",
    """[CORO]
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[POST-CORO / DROP]
Oh-oh, Aleluya,
oh-oh, Hallelujah,
Tu amor no se termina,
Tu luz siempre estará.

[VERSO 2]
Si el miedo me visita y me quiere detener,
Tu palabra me recuerda que puedo renacer.
No necesito verlo para saber que estás,
porque incluso en la tormenta me enseñás a confiar.""",
    """[PRE-CORO]
Y aunque el mundo cambie alrededor,
Tu promesa sigue hablando al corazón.

[CORO]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
late fuerte el corazón.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[PUENTE]
Dios de vida, Dios eterno,
cuando caigo, estás de nuevo.
En la cima, en el desierto,
Tu amor sigue siendo cierto.""",
    """[PUENTE]
Y si un día pierdo el rumbo,
Tu voz me vuelve a llamar.
No hay distancia, no hay silencio,
que me aparte de Tu paz.

[BUILD]
Aleluya…
Hallelujah…
Que lo escuche el cielo entero,
que lo cante el corazón.

[CORO FINAL]
Aleluya, Hallelujah,
mi esperanza vive en Vos.
Aleluya, Hallelujah,
para siempre sos mi Dios.
Cuando todo se oscurece,
Tu presencia trae la luz.
Aleluya, Hallelujah,
mi camino es con Jesús.

[OUTRO]
Aleluya… Hallelujah…
Tu luz siempre estará.""",
]

WAN_PROMPTS = [
    "Original fictional adult male Christian electronic singer performing emotionally on a minimal cinematic stage, warm expressive face, natural body movement, volumetric blue and golden lighting, realistic premium music video cinematography, no celebrity resemblance, no logos, no text",
    "Epic sunrise over mountain landscape, golden rays breaking through dramatic clouds, smooth cinematic drone movement, hopeful spiritual atmosphere, photorealistic premium Christian electronic music video, no logos, no text",
    "Fictional adult male singer walking slowly through a rain-wet city street at blue hour, cinematic reflections, emotional performance, realistic commercial music video camera movement, no brands, no celebrity resemblance",
    "Ocean cliffs at golden hour, powerful waves and warm sun beams through clouds, cinematic aerial motion, spiritual hopeful atmosphere, photorealistic premium music video, no text, no logos",
]

STOCK_QUERIES = [
    "cinematic sunrise mountains golden hour",
    "ocean waves golden hour cinematic",
    "night city lights cinematic street",
    "empty highway night cinematic",
    "church architecture sunlight cinematic",
    "dramatic clouds sun rays cinematic",
    "forest sunlight rays cinematic",
    "mountain lake sunrise cinematic",
]


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def decode_audio(result: str, out: Path) -> None:
    if not isinstance(result, str) or not result.startswith("data:audio/") or ";base64," not in result:
        raise RuntimeError("ACE-Step no devolvio audio base64 valido")
    _, payload = result.split(";base64,", 1)
    out.write_bytes(base64.b64decode(payload))
    if out.stat().st_size < 100_000:
        raise RuntimeError("ACE-Step devolvio audio demasiado pequeno")


def generate_music() -> Path:
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    token = os.getenv("HF_TOKEN") or None
    client = Client("victor/ace-step-jam", token=token, verbose=False)
    final = MUSIC_DIR / "Aleluya_Hallelujah_x_DemianVelo_4min.wav"

    try:
        print("ACE-Step: intentando generacion continua de 240 segundos")
        result = client.predict(PROMPT, FULL_LYRICS, 240.0, 8, 7.0, -1, "", 0.8, api_name="/generate")
        decode_audio(result, final)
    except Exception as exc:
        print("ACE-Step 240s fallo; usando 4 secciones coherentes:", type(exc).__name__, exc)
        segments: list[Path] = []
        for i, lyrics in enumerate(SECTIONS, 1):
            result = client.predict(
                PROMPT + f", coherent continuous song section {i} of 4, preserve same singer and production identity",
                lyrics,
                60.0,
                8,
                7.0,
                1900 + i,
                "",
                0.8,
                api_name="/generate",
            )
            seg = MUSIC_DIR / f"section_{i}.wav"
            decode_audio(result, seg)
            segments.append(seg)

        command = ["ffmpeg", "-y", "-loglevel", "error"]
        for seg in segments:
            command += ["-i", str(seg)]
        command += [
            "-filter_complex",
            "[0:a][1:a]acrossfade=d=1:c1=tri:c2=tri[a01];"
            "[a01][2:a]acrossfade=d=1:c1=tri:c2=tri[a012];"
            "[a012][3:a]acrossfade=d=1:c1=tri:c2=tri[outa]",
            "-map", "[outa]", "-c:a", "pcm_s16le", str(final),
        ]
        subprocess.run(command, check=True)

    duration = probe_duration(final)
    if not 180 <= duration <= 300:
        raise RuntimeError(f"Duracion de cancion fuera del rango 3-5 min: {duration:.2f}s")
    print("MUSIC_OK", final, "duration=", duration, "bytes=", final.stat().st_size)
    return final


def collect_video_files(value, files: list[Path]) -> None:
    if isinstance(value, str):
        p = Path(value)
        if p.exists() and p.suffix.lower() in {".mp4", ".webm", ".mov"}:
            files.append(p)
    elif isinstance(value, dict):
        for item in value.values():
            collect_video_files(item, files)
    elif isinstance(value, (list, tuple)):
        for item in value:
            collect_video_files(item, files)


def wan_args(spec: dict, prompt: str, seed: int) -> list:
    params = spec.get("parameters", [])
    names = [str(p.get("parameter_name") or "").lower().replace("-", "_") for p in params]
    if len(params) >= 9 and all(n.startswith("param_") or not n for n in names):
        args = [None, prompt, 704, 1280, 3.5, 10, 5.0, 5.0, seed]
        args += [p.get("default", None) for p in params[len(args):]]
        return args

    args = []
    for pos, p in enumerate(params):
        name = names[pos]
        default = p.get("default", None)
        if "image" in name:
            value = None
        elif "prompt" in name:
            value = prompt
        elif "height" in name:
            value = 704
        elif "width" in name:
            value = 1280
        elif "duration" in name or "seconds" in name:
            value = 3.5
        elif "sampling" in name or name == "steps":
            value = 10
        elif "guide" in name or "scale" in name:
            value = 5.0
        elif "shift" in name:
            value = 5.0
        elif "seed" in name:
            value = seed
        else:
            value = default
        args.append(value)
    return args


def generate_wan_scenes() -> list[Path]:
    WAN_DIR.mkdir(parents=True, exist_ok=True)
    token = os.getenv("HF_TOKEN") or None
    spaces = [
        "shafqat786/Wan-AI-Wan2.2-TI2V-5B",
        "Teheby63736363/Wan-AI-Wan2.2-TI2V-5B",
        "skrov/Wan-AI-Wan2.2-TI2V-5B",
        "anomen-2/Wan-AI-Wan2.2-TI2V-5B",
    ]
    outputs: list[Path] = []

    for scene_index, prompt in enumerate(WAN_PROMPTS, 1):
        errors = []
        for space in spaces:
            try:
                print("WAN_TRY", scene_index, space)
                client = Client(space, token=token, verbose=False)
                api = client.view_api(return_format="dict")
                named = api.get("named_endpoints", api)
                candidates = []
                for endpoint, spec in named.items():
                    if not isinstance(spec, dict):
                        continue
                    returns = " ".join(str(r.get("type") or "") for r in spec.get("returns", [])).lower()
                    if "video" in returns and len(spec.get("parameters", [])) >= 5:
                        candidates.append((endpoint, spec))
                if not candidates:
                    raise RuntimeError("sin endpoint de generacion de video")
                endpoint, spec = max(candidates, key=lambda item: len(item[1].get("parameters", [])))
                result = client.predict(*wan_args(spec, prompt, 2700 + scene_index), api_name=endpoint)
                files: list[Path] = []
                collect_video_files(result, files)
                if not files:
                    raise RuntimeError("Wan2.2 no devolvio archivo de video")
                src = files[0]
                dst = WAN_DIR / f"wan_{scene_index:02d}{src.suffix.lower()}"
                shutil.copy2(src, dst)
                if dst.stat().st_size < 50_000:
                    raise RuntimeError("clip Wan2.2 demasiado pequeno")
                outputs.append(dst)
                print("WAN_OK", scene_index, space, dst)
                break
            except Exception as exc:
                errors.append(f"{space}: {type(exc).__name__}: {exc}")
                print("WAN_FAIL", errors[-1])
        else:
            print("WAN_SCENE_SKIPPED", scene_index, " | ".join(errors))

    print("WAN_SCENES_TOTAL", len(outputs))
    return outputs


def build_video(audio: Path, wan_scenes: list[Path]) -> tuple[Path, list[dict]]:
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    target = probe_duration(audio)
    meta = {"topic": "Aleluya Hallelujah Christian electronic worship", "title": "Aleluya (Hallelujah) x DemianVelo"}
    used: set[str] = set()
    stock: list[Path] = []
    credits: list[dict] = []

    for i, query in enumerate(STOCK_QUERIES, 1):
        clip, credit = _get_real_segment(query, FINAL_DIR, 100 + i, 30, False, used, 9000 + i, target_4k=False)
        stock.append(clip)
        credits.append(credit)

    wan_norm: list[Path] = []
    for i, src in enumerate(wan_scenes, 1):
        dst = FINAL_DIR / f"wan_norm_{i}.mp4"
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,"
            "eq=contrast=1.05:saturation=1.08,unsharp=5:5:0.15:5:5:0,fps=30"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(src), "-t", "5",
             "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
             "-pix_fmt", "yuv420p", str(dst)],
            check=True,
        )
        wan_norm.append(dst)

    sequence: list[Path] = []
    wi = 0
    for i, clip in enumerate(stock):
        sequence.append(clip)
        if wi < len(wan_norm) and i in {0, 2, 4, 6}:
            sequence.append(wan_norm[wi])
            wi += 1
    while wi < len(wan_norm):
        sequence.append(wan_norm[wi])
        wi += 1

    manifest = FINAL_DIR / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in sequence), encoding="utf-8")
    visual = FINAL_DIR / "visual_1080p.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-f", "concat", "-safe", "0",
         "-i", str(manifest), "-t", f"{target:.3f}", "-an", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual)],
        check=True,
    )

    final = FINAL_DIR / "Aleluya_Hallelujah_x_DemianVelo_4min.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(audio),
         "-map", "0:v:0", "-map", "1:a:0", "-t", f"{target:.3f}", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(final)],
        check=True,
    )

    duration = probe_duration(final)
    if not 180 <= duration <= 300 or final.stat().st_size < 5_000_000:
        raise RuntimeError(f"Video final invalido: duration={duration:.2f}, size={final.stat().st_size}")
    print("VIDEO_OK", final, "duration=", duration, "wan_scenes=", len(wan_norm))
    return final, credits


def upload(video: Path, credits: list[dict], wan_count: int) -> str:
    channel = load_channel("demianvelo")
    description = (
        "Canción cristiana original de DemianVelo sobre Dios, Jesucristo, fe, esperanza y encontrar luz incluso "
        "en los momentos difíciles. Música y voz cantada generadas para esta producción con ACE-Step. "
        f"El videoclip combina montaje cinematográfico real con {wan_count} escena(s) generada(s) con Wan2.2.\n\n"
        "LETRA:\n" + FULL_LYRICS
    )
    metadata = {
        "title": "Aleluya (Hallelujah) x DemianVelo | Música Cristiana Electrónica",
        "description": description,
        "hashtags": ["#DemianVelo", "#Aleluya", "#Hallelujah", "#MusicaCristiana", "#Jesus"],
        "tags": [
            "DemianVelo", "Aleluya", "Hallelujah", "música cristiana", "musica cristiana electronica",
            "Jesus", "Dios", "fe", "esperanza", "electronic worship", "progressive house",
            "EDM cristiano", "Christian music", "Christian EDM",
        ],
        "source_credits": credits,
    }
    video_id = upload_long_video(channel, metadata, video, expected_minutes=4)
    result = {
        "status": "uploaded",
        "video_id": video_id,
        "title": metadata["title"],
        "duration_seconds": probe_duration(video),
        "wan_scenes": wan_count,
    }
    (FINAL_DIR / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("YOUTUBE_UPLOAD_SUCCESS", json.dumps(result, ensure_ascii=False))
    return video_id


def main() -> None:
    for path in (MUSIC_DIR, WAN_DIR, FINAL_DIR):
        path.mkdir(parents=True, exist_ok=True)
    audio = generate_music()
    wan = generate_wan_scenes()
    # Wan is a premium enhancement. If free public Spaces are unavailable, keep the production zero-cost
    # and finish with licensed real cinematic footage rather than switching to a paid provider.
    final, credits = build_video(audio, wan)
    upload(final, credits, len(wan))


if __name__ == "__main__":
    main()
