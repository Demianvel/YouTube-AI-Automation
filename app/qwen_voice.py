from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import soundfile as sf

_MODEL = None
_MODEL_KEY = None


def _load_model():
    global _MODEL, _MODEL_KEY

    import torch
    from qwen_tts import Qwen3TTSModel

    model_id = os.getenv(
        "HF_QWEN_TTS_MODEL",
        "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
    ).strip()
    device_pref = os.getenv("HF_QWEN_TTS_DEVICE", "auto").strip().lower()
    if device_pref == "auto":
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    else:
        device = device_pref

    key = (model_id, device)
    if _MODEL is not None and _MODEL_KEY == key:
        return _MODEL

    if device.startswith("cuda"):
        kwargs = {
            "device_map": device,
            "dtype": torch.bfloat16,
            "attn_implementation": "flash_attention_2",
            "low_cpu_mem_usage": True,
        }
    else:
        # GitHub-hosted runners do not expose a CUDA GPU. Qwen3-TTS 0.6B is
        # therefore loaded in the official CPU-compatible SDPA path.
        torch.set_num_threads(max(1, int(os.getenv("HF_QWEN_CPU_THREADS", "2"))))
        kwargs = {
            "device_map": "cpu",
            "dtype": torch.float32,
            "attn_implementation": "sdpa",
            "low_cpu_mem_usage": True,
        }

    print(f"QWEN_TTS_LOAD model={model_id} device={device}", flush=True)
    _MODEL = Qwen3TTSModel.from_pretrained(model_id, **kwargs)
    _MODEL_KEY = key
    return _MODEL


def _chunks(text: str, max_chars: int = 520) -> list[str]:
    clean = " ".join(str(text or "").split()).strip()
    if not clean:
        return []
    words = clean.split()
    result: list[str] = []
    current: list[str] = []
    size = 0
    for word in words:
        projected = size + len(word) + (1 if current else 0)
        if current and projected > max_chars:
            result.append(" ".join(current))
            current = []
            size = 0
        current.append(word)
        size += len(word) + (1 if size else 0)
    if current:
        result.append(" ".join(current))
    return result


def _instruction() -> str:
    return (
        "Habla en español latinoamericano neutro, con voz masculina adulta, cálida y serena. "
        "Tono espiritual cercano, humano y profesional; dicción clara, barítono moderado, ritmo natural, "
        "sin voz de locutor comercial, sin dramatismo de tráiler, sin susurros y sin pausas largas. "
        "Transmití paz, fe, esperanza y compasión con una cadencia fluida y estable."
    )


def generate_qwen_premium_voice(path: Path, text: str) -> str:
    """Local Hugging Face fallback for premium Spanish narration.

    This is intentionally a backup identity, not an assertion that Qwen is the
    same voice as Gemini Algenib. It is used only when the primary provider is
    unavailable and keeps the channel's downstream Voz de Luz mastering chain.
    """
    model = _load_model()
    speaker = os.getenv("HF_QWEN_TTS_SPEAKER", "Ryan").strip() or "Ryan"
    language = os.getenv("HF_QWEN_TTS_LANGUAGE", "Spanish").strip() or "Spanish"
    chunks = _chunks(text)
    if not chunks:
        raise RuntimeError("QWEN_TTS: texto vacio.")

    pieces: list[np.ndarray] = []
    sample_rate: int | None = None
    for index, chunk in enumerate(chunks, start=1):
        print(f"QWEN_TTS_CHUNK {index}/{len(chunks)} speaker={speaker} language={language}", flush=True)
        wavs, sr = model.generate_custom_voice(
            text=chunk,
            language=language,
            speaker=speaker,
            instruct=_instruction(),
        )
        if not wavs:
            raise RuntimeError(f"QWEN_TTS: chunk {index} no devolvio audio.")
        audio = np.asarray(wavs[0], dtype=np.float32).reshape(-1)
        if audio.size < 1000:
            raise RuntimeError(f"QWEN_TTS: chunk {index} demasiado corto/invalido.")
        sample_rate = int(sr)
        pieces.append(audio)
        if index < len(chunks):
            pieces.append(np.zeros(int(sample_rate * 0.14), dtype=np.float32))

    assert sample_rate is not None
    merged = np.concatenate(pieces)
    peak = float(np.max(np.abs(merged))) if merged.size else 0.0
    if peak > 0.98:
        merged = merged * (0.98 / peak)

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), merged, sample_rate, subtype="PCM_16")
    if not path.exists() or path.stat().st_size < 4000:
        raise RuntimeError("QWEN_TTS: archivo de salida invalido.")

    model_id = os.getenv("HF_QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
    return f"huggingface-local:{model_id}:{speaker}:{language}:voz_de_luz_qwen_backup_v1"
