from __future__ import annotations

import math
import os
import random
import shutil
import struct
import subprocess
import wave
from pathlib import Path


def make_pleasant_original_music(path: Path, duration: int, seed: int) -> None:
    """Gentle original instrumental bed generated locally; no third-party song source."""
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xB70A)
    chords = [
        (261.63, 329.63, 392.00),
        (196.00, 246.94, 293.66),
        (174.61, 220.00, 261.63),
        (261.63, 329.63, 392.00),
    ]
    melody = [392.00, 440.00, 523.25, 440.00, 392.00, 329.63, 392.00, 523.25]
    phases = [rng.random() * math.tau for _ in range(5)]

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buffer = bytearray()
        for i in range(total):
            t = i / sample_rate
            chord_index = min(len(chords) - 1, int((t / max(duration, 0.01)) * len(chords)))
            chord = chords[chord_index]
            pad = 0.0
            for j, freq in enumerate(chord):
                pad += math.sin(math.tau * freq * t + phases[j]) * (0.20 - j * 0.025)
                pad += math.sin(math.tau * freq * 2 * t + phases[j]) * 0.025

            beat = int(t / 0.75)
            note = melody[beat % len(melody)]
            local = t % 0.75
            pluck_env = math.exp(-4.8 * local)
            pluck = (
                math.sin(math.tau * note * t + phases[3]) * 0.12
                + math.sin(math.tau * note * 2 * t + phases[4]) * 0.035
            ) * pluck_env
            sparkle_env = math.exp(-8.0 * (t % 1.5))
            sparkle = math.sin(math.tau * note * 3 * t) * sparkle_env * 0.018

            fade = min(1.0, t / 0.45, max(0.0, (duration - t) / 0.55))
            sample = max(-1.0, min(1.0, (pad + pluck + sparkle) * 0.30 * fade))
            buffer += struct.pack("<h", int(sample * 32767))
            if len(buffer) >= 65536:
                wf.writeframes(buffer)
                buffer.clear()
        if buffer:
            wf.writeframes(buffer)


def make_botanical_asmr(path: Path, duration: int, seed: int) -> None:
    """Soft synthetic foley: soil rustle, leaf texture and gentle water droplets; no music or voice."""
    sample_rate = 32000
    total = int(duration * sample_rate)
    rng = random.Random(seed ^ 0xA55A)
    drops = sorted(rng.uniform(0.35, max(0.5, duration - 0.25)) for _ in range(max(4, int(duration * 0.9))))
    soil_lp = 0.0
    leaf_lp = 0.0

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        buffer = bytearray()
        for i in range(total):
            t = i / sample_rate
            white = rng.uniform(-1.0, 1.0)
            soil_lp += 0.012 * (white - soil_lp)
            leaf_white = rng.uniform(-1.0, 1.0)
            leaf_lp += 0.045 * (leaf_white - leaf_lp)
            slow = 0.55 + 0.45 * math.sin(math.tau * 0.19 * t + 0.8)
            soil = soil_lp * 0.18
            leaves = (leaf_white - leaf_lp) * (0.045 + 0.025 * slow)
            water = 0.0
            for drop_time in drops:
                dt = t - drop_time
                if 0.0 <= dt < 0.16:
                    env = math.exp(-25.0 * dt)
                    freq = 980.0 - 280.0 * min(1.0, dt / 0.16)
                    water += math.sin(math.tau * freq * dt) * env * 0.23
                    water += math.sin(math.tau * freq * 1.8 * dt) * env * 0.065
            local = t % 1.7
            micro = rng.uniform(-1.0, 1.0) * math.exp(-65 * local) * 0.035 if local < 0.05 else 0.0
            fade = min(1.0, t / 0.25, max(0.0, (duration - t) / 0.35))
            sample = max(-0.92, min(0.92, (soil + leaves + water + micro) * fade))
            buffer += struct.pack("<h", int(sample * 32767))
            if len(buffer) >= 65536:
                wf.writeframes(buffer)
                buffer.clear()
        if buffer:
            wf.writeframes(buffer)


def _kokoro_voice(path: Path, text: str) -> None:
    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    voice = os.getenv("KOKORO_VOICE", "em_alex").strip() or "em_alex"
    speed = float(os.getenv("KOKORO_SPEED", "0.95"))
    pipeline = KPipeline(lang_code="e")
    chunks: list[np.ndarray] = []
    clean_text = " ".join(str(text).split())
    for _graphemes, _phonemes, audio in pipeline(clean_text, voice=voice, speed=speed, split_pattern=r"(?<=[.!?])\s+"):
        if audio is not None and len(audio):
            chunks.append(np.asarray(audio, dtype=np.float32))
    if not chunks:
        raise RuntimeError("Kokoro no genero audio en español.")
    pause = np.zeros(int(24000 * 0.035), dtype=np.float32)
    joined: list[np.ndarray] = []
    for index, chunk in enumerate(chunks):
        if index:
            joined.append(pause)
        joined.append(chunk)
    combined = np.concatenate(joined)
    peak = float(np.max(np.abs(combined))) if len(combined) else 0.0
    if peak > 0.98:
        combined = combined * (0.96 / peak)
    sf.write(str(path), combined, 24000, subtype="PCM_16")


def _chatterbox_general_voice(path: Path, text: str) -> None:
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_pretrained(device=device, t3_model="v3")
    kwargs: dict = {
        "language_id": "es",
        "exaggeration": float(os.getenv("CHATTERBOX_EXAGGERATION", "0.62")),
        "cfg_weight": float(os.getenv("CHATTERBOX_CFG_WEIGHT", "0.38")),
        "temperature": float(os.getenv("CHATTERBOX_TEMPERATURE", "0.80")),
    }
    ref = os.getenv("CHATTERBOX_REFERENCE_AUDIO", "").strip()
    if ref:
        if not Path(ref).exists():
            raise RuntimeError("CHATTERBOX_REFERENCE_AUDIO no existe en el runner.")
        kwargs["audio_prompt_path"] = ref
    clean_text = " ".join(str(text).split())
    wav = model.generate(clean_text, **kwargs)
    ta.save(str(path), wav.cpu(), model.sr)


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        return
    try:
        dst.symlink_to(src)
    except OSError:
        shutil.copy2(src, dst)


def _latam_model_dir() -> Path:
    """Merge official base companion assets with the official LatAm Spanish V3 finetune.

    ResembleAI's LatAm pack contains its regional T3 and V3 S3Gen assets, while the shared
    base repository contains the voice encoder/default conditionals. Chatterbox's from_local
    loader accepts an arbitrary .safetensors T3 filename, so the two official snapshots can
    be combined without modifying model weights.
    """
    from huggingface_hub import snapshot_download

    cache = Path(os.getenv("CHATTERBOX_LATAM_CACHE", Path.home() / ".cache/chatterbox-latam-v3")).expanduser()
    marker = cache / ".ready"
    if marker.exists():
        return cache

    base = Path(snapshot_download(
        repo_id="ResembleAI/chatterbox",
        repo_type="model",
        allow_patterns=["ve.pt", "conds.pt"],
        token=os.getenv("HF_TOKEN") or None,
    ))
    latam = Path(snapshot_download(
        repo_id="ResembleAI/Chatterbox-Multilingual-es-mx-latam",
        repo_type="model",
        allow_patterns=["t3_es_mx_latam.safetensors", "s3gen_v3.pt", "grapheme_mtl_merged_expanded_v1.json"],
        token=os.getenv("HF_TOKEN") or None,
    ))
    cache.mkdir(parents=True, exist_ok=True)
    _link_or_copy(base / "ve.pt", cache / "ve.pt")
    if (base / "conds.pt").exists():
        _link_or_copy(base / "conds.pt", cache / "conds.pt")
    _link_or_copy(latam / "t3_es_mx_latam.safetensors", cache / "t3_es_mx_latam.safetensors")
    _link_or_copy(latam / "s3gen_v3.pt", cache / "s3gen.pt")
    _link_or_copy(latam / "grapheme_mtl_merged_expanded_v1.json", cache / "grapheme_mtl_merged_expanded_v1.json")
    marker.write_text("official ResembleAI LatAm Spanish V3 pack\n", encoding="utf-8")
    return cache


def _chatterbox_latam_voice(path: Path, text: str) -> None:
    import torch
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxMultilingualTTS.from_local(
        _latam_model_dir(),
        device=device,
        t3_model="t3_es_mx_latam.safetensors",
    )
    kwargs: dict = {
        "language_id": "es",
        "exaggeration": float(os.getenv("CHATTERBOX_EXAGGERATION", "0.62")),
        "cfg_weight": float(os.getenv("CHATTERBOX_CFG_WEIGHT", "0.38")),
        "temperature": float(os.getenv("CHATTERBOX_TEMPERATURE", "0.80")),
    }
    ref = os.getenv("CHATTERBOX_REFERENCE_AUDIO", "").strip()
    if ref:
        if not Path(ref).exists():
            raise RuntimeError("CHATTERBOX_REFERENCE_AUDIO no existe en el runner.")
        kwargs["audio_prompt_path"] = ref
    clean_text = " ".join(str(text).split())
    wav = model.generate(clean_text, **kwargs)
    ta.save(str(path), wav.cpu(), model.sr)


def make_natural_spanish_voice(path: Path, text: str) -> str:
    """Prefer official LatAm Spanish V3, then general V3, then Kokoro."""
    provider = os.getenv("TTS_PROVIDER", "chatterbox_latam").lower().strip()
    if provider in {"chatterbox_latam", "chatterbox-latam", "latam"}:
        try:
            _chatterbox_latam_voice(path, text)
            used = "chatterbox-v3-latam-es-419"
        except Exception as latam_exc:
            print(f"Chatterbox LatAm V3 no disponible ({latam_exc}); intentando V3 general.")
            try:
                _chatterbox_general_voice(path, text)
                used = "chatterbox-v3-general-fallback"
            except Exception as general_exc:
                if os.getenv("TTS_FALLBACK_KOKORO", "true").lower() != "true":
                    raise
                print(f"Chatterbox V3 general no disponible ({general_exc}); usando Kokoro.")
                _kokoro_voice(path, text)
                used = "kokoro-fallback"
    elif provider == "chatterbox":
        try:
            _chatterbox_general_voice(path, text)
            used = "chatterbox-v3"
        except Exception as exc:
            if os.getenv("TTS_FALLBACK_KOKORO", "true").lower() != "true":
                raise
            print(f"Chatterbox V3 no disponible ({exc}); usando Kokoro como respaldo.")
            _kokoro_voice(path, text)
            used = "kokoro-fallback"
    elif provider == "kokoro":
        _kokoro_voice(path, text)
        used = "kokoro"
    else:
        raise RuntimeError(f"TTS_PROVIDER no soportado: {provider}")

    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError(f"{used} genero un archivo de voz invalido.")
    return used


def apply_audio(video: Path, out: Path, channel: dict, meta: dict, duration: int, seed: int) -> None:
    mode = channel.get("audio_mode", "voice_music")
    meta["audio_mode_used"] = mode

    if mode == "asmr":
        asmr = out.with_name("botanical_asmr.wav")
        make_botanical_asmr(asmr, duration, seed)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(asmr),
            "-filter_complex", "[1:a]highpass=f=45,lowpass=f=11000,loudnorm=I=-20:TP=-2:LRA=7[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ], check=True)
        meta["tts_provider_used"] = "none"
        meta["audio_source"] = "original_synthetic_asmr_foley"
        return

    if mode == "music_only":
        music = out.with_name("pleasant_original_music.wav")
        make_pleasant_original_music(music, duration, seed)
        fade_in = min(0.30, max(0.05, duration * 0.12))
        fade_out = min(0.75, max(0.05, duration * 0.20))
        fade_out_start = max(0.0, duration - fade_out)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(music),
            "-filter_complex", f"[1:a]afade=t=in:st=0:d={fade_in:.2f},afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f},volume=0.72[a]",
            "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out),
        ], check=True)
        meta["tts_provider_used"] = "none"
        meta["audio_source"] = "original_instrumental_generated_in_repo"
        return

    text = " ".join(scene.get("narration", "").strip() for scene in meta.get("scenes", []) if scene.get("narration", "").strip())
    if not text:
        raise RuntimeError("El canal requiere narracion y no se genero texto.")

    requested = os.getenv("TTS_PROVIDER", "chatterbox_latam").lower().strip()
    voice_path = out.with_name(f"narration_{requested.replace('-', '_')}.wav")
    used = make_natural_spanish_voice(voice_path, text)
    meta["tts_provider_used"] = used

    music = out.with_name("soft_music.wav")
    make_pleasant_original_music(music, duration, seed ^ 0xD1E0)
    music_volume = "0.032"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(voice_path), "-i", str(music),
        "-filter_complex",
        f"[1:a]highpass=f=70,lowpass=f=10000,acompressor=threshold=-18dB:ratio=1.75:attack=10:release=140,loudnorm=I=-16:TP=-1.5:LRA=8,apad=pad_dur={duration}[v];"
        f"[2:a]volume={music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    ], check=True)
    meta["audio_source"] = "continuous_latam_spanish_voice_plus_original_instrumental"
