from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from .dios_sovereign_ai import ENGINE_VERSION, ROOT, load_config
from .spiritual_continuity import ensure_spoken_text


VOICE_PROVIDER = "dhh-sovereign-local-voice-v1"
VOICE_PROFILE = "voz_de_luz_local_sovereign_v1"
VOICE_BRAND = "Voz de Luz Local"


def fit_script(text: str, duration: int, seed: int) -> tuple[str, dict]:
    """Fit text to the calm local Piper cadence without post-stretching audio."""
    clean = " ".join(str(text or "").split()).strip()
    try:
        target_wpm = int(os.getenv("DIOS_PIPER_TARGET_WPM", "126"))
    except ValueError:
        target_wpm = 126
    target_wpm = max(112, min(142, target_wpm))

    min_words = max(32, int(float(duration) * (target_wpm / 60.0) * 0.96))
    max_words = max(min_words + 4, int(float(duration) * (target_wpm / 60.0) * 1.06))
    original_words = len(clean.split())

    if original_words < min_words:
        clean, expansion = ensure_spoken_text(
            clean,
            duration,
            seed=seed,
            words_per_minute=target_wpm,
        )
    else:
        expansion = {
            "target_words": min_words,
            "final_words": original_words,
            "continuity_expansions": 0,
        }

    words = clean.split()
    if len(words) > max_words:
        # Prefer complete sentences when trimming.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
        selected: list[str] = []
        count = 0
        for sentence in sentences:
            n = len(sentence.split())
            if selected and count + n > max_words:
                break
            if count + n <= max_words:
                selected.append(sentence)
                count += n
        if selected:
            clean = " ".join(selected)
        else:
            clean = " ".join(words[:max_words]).rstrip(" ,;:") + "."

    final_words = len(clean.split())
    return clean, {
        **expansion,
        "original_words": original_words,
        "final_words": final_words,
        "natural_voice_word_budget_min": min_words,
        "natural_voice_word_budget_max": max_words,
        "script_adjusted_for_fixed_voice_cadence": final_words != original_words,
        "voice_rate_policy": f"piper_local_fixed_calm_{target_wpm}wpm_no_post_stretch",
    }


def _master(path: Path, target_lufs: float) -> None:
    temp = path.with_name(path.stem + ".sovereign-master.wav")
    filters = (
        "highpass=f=55,"
        "lowpass=f=10800,"
        "equalizer=f=120:t=q:w=0.9:g=1.0,"
        "equalizer=f=260:t=q:w=1.0:g=0.35,"
        "equalizer=f=2850:t=q:w=1.0:g=0.55,"
        "acompressor=threshold=-22dB:ratio=1.55:attack=18:release=180:makeup=1.1,"
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=5.5"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-af", filters, "-ar", "48000", "-ac", "1", str(temp)],
        check=True,
    )
    if not temp.exists() or temp.stat().st_size < 1000:
        raise RuntimeError("No se pudo masterizar Voz de Luz Local.")
    temp.replace(path)


def make_voice(path: Path, text: str) -> str:
    config = load_config()
    voice_cfg = config["voice"]
    model = ROOT / voice_cfg["model_path"]
    model_cfg = ROOT / voice_cfg["config_path"]
    if not model.exists() or not model_cfg.exists():
        raise RuntimeError(
            "VOICE_LOCAL_MODEL_MISSING: faltan los pesos Piper de Voz de Luz Local. "
            f"Esperados: {model} y {model_cfg}."
        )

    try:
        length_scale = float(os.getenv("DIOS_PIPER_LENGTH_SCALE", "1.18"))
    except ValueError:
        length_scale = 1.18
    length_scale = max(1.02, min(1.36, length_scale))

    try:
        sentence_silence = float(os.getenv("DIOS_PIPER_SENTENCE_SILENCE", "0.05"))
    except ValueError:
        sentence_silence = 0.05
    sentence_silence = max(0.0, min(0.18, sentence_silence))

    piper_bin = os.getenv("PIPER_BIN", "piper").strip() or "piper"
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        piper_bin,
        "--model", str(model),
        "--config", str(model_cfg),
        "--output_file", str(path),
        "--length_scale", f"{length_scale:.3f}",
        "--noise_scale", os.getenv("DIOS_PIPER_NOISE_SCALE", "0.58"),
        "--noise_w", os.getenv("DIOS_PIPER_NOISE_W", "0.46"),
        "--sentence_silence", f"{sentence_silence:.3f}",
    ]
    proc = subprocess.run(
        command,
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Piper local fallo: {proc.stderr[-1400:]}")
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Piper local no produjo audio valido.")

    _master(path, float(voice_cfg.get("master_lufs") or -16.5))
    return (
        f"{VOICE_PROVIDER}:{VOICE_PROFILE}:length_scale={length_scale:.3f}:"
        f"sentence_silence={sentence_silence:.3f}:{ENGINE_VERSION}"
    )
