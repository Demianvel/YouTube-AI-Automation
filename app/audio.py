from __future__ import annotations

import base64
import math
import os
import random
import struct
import subprocess
import wave
from pathlib import Path


def make_pleasant_fallback_music(path: Path, duration: int, seed: int) -> None:
    """Pleasant original fallback bed: warm major-pentatonic tones, no dark drones."""
    sample_rate = 22050
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xB70A)
    roots = [220.00, 246.94, 293.66, 329.63]
    phases = [rng.random() * math.tau for _ in range(4)]

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        chunk = bytearray()
        for i in range(total):
            t = i / sample_rate
            root = roots[int(t // 2.0) % len(roots)]
            pad = (
                math.sin(math.tau * root * t + phases[0]) * .33
                + math.sin(math.tau * root * 1.25 * t + phases[1]) * .18
                + math.sin(math.tau * root * 1.50 * t + phases[2]) * .14
            )
            bell_env = math.exp(-3.8 * (t % 1.0))
            bell = math.sin(math.tau * root * 2.0 * t + phases[3]) * bell_env * .08
            fade = min(1.0, t / .7, max(0.0, (duration - t) / .7))
            sample = max(-1.0, min(1.0, (pad + bell) * .17 * fade))
            chunk += struct.pack("<h", int(sample * 32767))
            if len(chunk) >= 65536:
                wf.writeframes(chunk)
                chunk.clear()
        if chunk:
            wf.writeframes(chunk)


def make_lyria_music(path: Path) -> bool:
    """Generate a premium, pleasant instrumental clip with Lyria 3."""
    if os.getenv("MUSIC_PROVIDER", "lyria").lower() != "lyria":
        return False

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False

    from google import genai

    model = os.getenv("LYRIA_MODEL", "lyria-3-clip-preview")
    client = genai.Client(api_key=api_key)
    prompt = (
        "Instrumental only, absolutely no vocals and no spoken words. "
        "Create a beautiful, warm, uplifting nature soundtrack for a photorealistic plant-growth timelapse. "
        "Soft felt piano, delicate marimba, airy acoustic textures, gentle sparkling bells and subtle warm pads. "
        "Major-key feeling, peaceful, fresh, optimistic and pleasant to the ear. "
        "No ominous drones, no horror mood, no dissonance, no aggressive bass, no distorted synths, no dark cinematic tension. "
        "Premium clean production, elegant and relaxing, suitable for a short nature documentary."
    )
    try:
        interaction = client.interactions.create(model=model, input=prompt)
        output_audio = getattr(interaction, "output_audio", None)
        data = getattr(output_audio, "data", None) if output_audio is not None else None
        if not data:
            return False
        path.write_bytes(base64.b64decode(data))
        return path.exists() and path.stat().st_size > 1000
    except Exception:
        return False


def make_natural_spanish_voice(path: Path, text: str) -> None:
    """Generate warm, natural Castilian/Argentine Spanish narration with Gemini TTS."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY para generar la voz natural de Dinero Claro.")

    from google import genai

    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    voice = os.getenv("GEMINI_TTS_VOICE", "Sulafat")
    client = genai.Client(api_key=api_key)

    prompt = (
        "Sintetiza voz en castellano natural. Voz adulta, calida, humana y cercana; acento argentino/rioplatense leve y entendible. "
        "Tono educativo y confiable, como una persona explicando finanzas a un amigo. Ritmo conversacional, respiracion y pausas naturales, "
        "sin tono de robot, sin voz de GPS, sin exageracion publicitaria, sin gritar. Pronuncia numeros y conceptos financieros con claridad. "
        "No agregues palabras ni cambies el contenido. TRANSCRIPCION A LEER EXACTAMENTE:\n\n" + text
    )

    interaction = client.interactions.create(
        model=model,
        input=prompt,
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voice}]},
    )
    output_audio = getattr(interaction, "output_audio", None)
    data = getattr(output_audio, "data", None) if output_audio is not None else None
    if not data:
        raise RuntimeError("Gemini TTS no devolvio audio.")

    pcm = base64.b64decode(data)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm)


def _music_file(out: Path, duration: int, seed: int, premium: bool) -> Path:
    if premium:
        mp3 = out.with_name("premium_music.mp3")
        if make_lyria_music(mp3):
            return mp3
    wav = out.with_name("pleasant_original_music.wav")
    make_pleasant_fallback_music(wav, duration, seed)
    return wav


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")
    music = _music_file(out, duration, seed, premium=(mode == "music_only"))

    if mode == "music_only":
        fade_out_start = max(0.0, duration - 0.8)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(video), "-stream_loop", "-1", "-i", str(music),
                "-filter_complex", f"[1:a]afade=t=in:st=0:d=.35,afade=t=out:st={fade_out_start}:d=.8,volume=0.70[a]",
                "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart", str(out),
            ],
            check=True,
        )
        return

    text = " ... ".join(
        s.get("narration", "").strip()
        for s in meta.get("scenes", [])
        if s.get("narration", "").strip()
    )
    if not text:
        raise RuntimeError("Dinero Claro requiere narracion y no se genero texto.")

    voice_path = out.with_name("narration_natural.wav")
    make_natural_spanish_voice(voice_path, text)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(video), "-i", str(voice_path),
            "-filter_complex",
            f"[1:a]highpass=f=70,lowpass=f=8500,acompressor=threshold=-18dB:ratio=2.2:attack=15:release=180,volume=1.05,apad=pad_dur={duration}[v]",
            "-map", "0:v:0", "-map", "[v]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ],
        check=True,
    )
