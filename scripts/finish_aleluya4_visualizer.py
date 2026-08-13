from __future__ import annotations

import glob
import json
import subprocess
from pathlib import Path

from app.config import load_channel
from app.youtube import upload_long_video

ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input_aleluya4"
OUT = ROOT / "output" / "aleluya4_final"
OUT.mkdir(parents=True, exist_ok=True)

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


def duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(r.stdout.strip())


def find_audio() -> Path:
    candidates = [
        Path(p) for p in glob.glob(str(INPUT_DIR / "**" / "*"), recursive=True)
        if Path(p).suffix.lower() in {".wav", ".mp3", ".flac", ".m4a"}
    ]
    if not candidates:
        raise RuntimeError("No se encontro el WAV de 4 minutos descargado del artifact anterior.")
    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    audio = candidates[0]
    d = duration(audio)
    if not 180 <= d <= 300:
        raise RuntimeError(f"El audio recuperado no esta entre 3 y 5 minutos: {d:.2f}s")
    print("AUDIO_RECOVERED", audio, "duration=", d, "bytes=", audio.stat().st_size)
    return audio


def render_visualizer(audio: Path) -> Path:
    d = duration(audio)
    final = OUT / "Aleluya_Hallelujah_x_DemianVelo_4min.mp4"
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    # Original, fully local motion-graphics master. No stock footage, no external clips and no paid provider.
    # The spectrum and waveform are driven directly by the finished ACE-Step song, so the visuals react to the music.
    filter_complex = (
        "[1:a]asplit=2[a_spec][a_wave];"
        "[a_spec]showspectrum=s=1920x540:mode=combined:color=fire:scale=log:slide=scroll:win_func=hann:legend=disabled," 
        "format=rgba,colorchannelmixer=aa=0.62[spec];"
        "[a_wave]showwaves=s=1500x150:mode=line:rate=30:colors=0xFFE7A3@0.90|0xFFFFFF@0.70," 
        "format=rgba[wave];"
        "[0:v]noise=alls=5:allf=t,eq=contrast=1.08:saturation=1.10:brightness=-0.015," 
        "vignette=PI/4.5[bg];"
        "[bg][spec]overlay=0:540:shortest=1[tmp1];"
        "[tmp1][wave]overlay=(W-w)/2:H-h-130:shortest=1[tmp2];"
        f"[tmp2]drawtext=fontfile={bold}:text='ALELUYA  ·  HALLELUJAH':fontcolor=white:fontsize=58:" 
        "x=(w-text_w)/2:y=145:enable='between(t,0,9)',"
        f"drawtext=fontfile={font}:text='DEMIANVELO':fontcolor=0xFFE7A3:fontsize=30:" 
        "x=(w-text_w)/2:y=225:enable='between(t,0,9)',"
        f"drawtext=fontfile={font}:text='Tu luz siempre estará':fontcolor=white@0.72:fontsize=34:" 
        f"x=(w-text_w)/2:y=820:enable='between(t,{max(0.0, d-12):.2f},{d:.2f})',"
        "fade=t=in:st=0:d=1.5,fade=t=out:st=" + f"{max(0.0, d-2.5):.2f}" + ":d=2.5[v]"
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=0x040815:s=1920x1080:r=30:d={d:.3f}",
            "-i", str(audio),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "1:a:0",
            "-t", f"{d:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "320k",
            "-movflags", "+faststart",
            str(final),
        ],
        check=True,
    )

    fd = duration(final)
    if not 180 <= fd <= 300:
        raise RuntimeError(f"Video final fuera de 3-5 minutos: {fd:.2f}s")
    if final.stat().st_size < 8_000_000:
        raise RuntimeError(f"Video final sospechosamente pequeno: {final.stat().st_size} bytes")
    print("VISUALIZER_OK", final, "duration=", fd, "bytes=", final.stat().st_size)
    return final


def publish(video: Path) -> str:
    channel = load_channel("demianvelo")
    metadata = {
        "title": "Aleluya (Hallelujah) x DemianVelo | Música Cristiana Electrónica",
        "description": (
            "Canción cristiana original de DemianVelo sobre Dios, Jesucristo, fe, esperanza y encontrar luz incluso "
            "en los momentos difíciles. Música y voz cantada creadas para esta producción con ACE-Step. "
            "El video utiliza un visualizador cinematográfico original y reactivo al audio, generado localmente para esta canción.\n\n"
            "LETRA:\n" + FULL_LYRICS
        ),
        "hashtags": ["#DemianVelo", "#Aleluya", "#Hallelujah", "#MusicaCristiana", "#Jesus"],
        "tags": [
            "DemianVelo", "Aleluya", "Hallelujah", "música cristiana", "musica cristiana electronica",
            "Jesus", "Dios", "fe", "esperanza", "electronic worship", "progressive house",
            "EDM cristiano", "Christian music", "Christian EDM", "worship electronic",
        ],
    }
    video_id = upload_long_video(channel, metadata, video, expected_minutes=4)
    result = {
        "status": "uploaded",
        "video_id": video_id,
        "title": metadata["title"],
        "duration_seconds": duration(video),
        "visual_mode": "original_local_cinematic_audio_reactive_visualizer",
        "music_engine": "ACE-Step",
    }
    (OUT / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("YOUTUBE_UPLOAD_SUCCESS", json.dumps(result, ensure_ascii=False))
    return video_id


def main() -> None:
    audio = find_audio()
    video = render_visualizer(audio)
    publish(video)


if __name__ == "__main__":
    main()
