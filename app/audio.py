from __future__ import annotations

import base64
import math
import os
import random
import struct
import subprocess
import wave
from pathlib import Path


def make_original_music(path: Path, duration: int, seed: int) -> None:
    """Create an original instrumental bed from synthesized tones."""
    sample_rate = 22050
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xB70A)
    roots = rng.sample([196.00, 220.00, 246.94, 261.63, 293.66], 4)
    phases = [rng.random() * math.tau for _ in range(4)]

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        chunk = bytearray()
        for i in range(total):
            t = i / sample_rate
            root = roots[int(t // 4) % len(roots)]
            chord = (
                math.sin(math.tau * root * t + phases[0]) * .42
                + math.sin(math.tau * root * 1.25 * t + phases[1]) * .25
                + math.sin(math.tau * root * 1.50 * t + phases[2]) * .20
                + math.sin(math.tau * (root / 2) * t + phases[3]) * .18
            )
            pulse_phase = t % 2.0
            pulse = math.exp(-4.0 * pulse_phase) * math.sin(math.tau * (root / 4) * t) * .12
            fade = min(1.0, t / 1.0, max(0.0, (duration - t) / 1.0))
            sample = max(-1.0, min(1.0, (chord + pulse) * .20 * fade))
            chunk += struct.pack("<h", int(sample * 32767))
            if len(chunk) >= 65536:
                wf.writeframes(chunk)
                chunk.clear()
        if chunk:
            wf.writeframes(chunk)


def make_natural_spanish_voice(path: Path, text: str) -> None:
    """Generate natural Spanish narration with Gemini TTS."""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY para generar la voz natural de Dinero Claro.")

    model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    voice = os.getenv("GEMINI_TTS_VOICE", "Sadaltager")
    client = genai.Client(api_key=api_key)

    prompt = (
        "Voz adulta, humana y natural. Castellano argentino claro y neutro, sin exagerar el acento. "
        "Tono educativo, cercano y confiable, ritmo conversacional, pausas naturales, buena diccion. "
        "No sonar como locutor comercial ni como robot. No agregues palabras ni cambies el contenido. "
        "Lee exactamente este texto:\n\n" + text
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


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")
    music = out.with_name("original_music.wav")
    make_original_music(music, duration, seed)

    if mode == "music_only":
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(video), "-i", str(music),
                "-filter_complex", "[1:a]volume=0.72[a]",
                "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
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
            "-i", str(video), "-i", str(music), "-i", str(voice_path),
            "-filter_complex",
            f"[1:a]volume=0.08[m];[2:a]highpass=f=80,lowpass=f=8000,acompressor,volume=1.08,apad=pad_dur={duration}[v];[m][v]amix=inputs=2:duration=first[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ],
        check=True,
    )
