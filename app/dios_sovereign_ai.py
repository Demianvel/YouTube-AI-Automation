from __future__ import annotations

import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from .fast_spiritual_metadata import build_fast_metadata
from .generator_resilient import _local_metadata


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "dios_sovereign_ai.json"
ENGINE_VERSION = "dhh-sovereign-v1"
VISUAL_PROVIDER = "dhh-sovereign-local-visual-v1"
VOICE_PROVIDER = "dhh-sovereign-local-voice-v1"
THEME_PROVIDER = "dhh-sovereign-local-theme-v1"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(f"Falta la configuracion soberana: {CONFIG_PATH}")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def enforce_offline_runtime() -> None:
    """Force model libraries into local-files-only mode.

    YouTube upload still needs network access at the final publishing step, but
    image, theme and voice generation must not call remote AI services.
    """
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["DIFFUSERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["DIOS_SOVEREIGN_OFFLINE"] = "true"


def _history_rows(limit: int = 300) -> list[dict]:
    history = ROOT / "state" / "history.jsonl"
    if not history.exists():
        return []
    rows: list[dict] = []
    for raw in history.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") == "dioshablahoyia":
            rows.append(row)
    return rows


def build_theme_metadata(channel: dict, previous: list[dict] | None = None) -> dict:
    """Generate the channel's biblical editorial package with no text API."""
    previous_rows = list(previous if previous is not None else _history_rows())
    base = _local_metadata(channel, previous_rows)
    metadata = build_fast_metadata(base, channel, previous_rows)
    metadata["metadata_provider"] = THEME_PROVIDER
    metadata["sovereign_ai_version"] = ENGINE_VERSION
    metadata["remote_text_ai_used"] = False
    return metadata


def _reference_files(config: dict[str, Any]) -> list[Path]:
    image_cfg = config["image"]
    ref_dir = ROOT / image_cfg["reference_dir"]
    refs = [ref_dir / name for name in image_cfg["references"]]
    missing = [str(path) for path in refs if not path.exists() or path.stat().st_size < 1000]
    if missing:
        raise RuntimeError("Faltan referencias visuales del canal: " + ", ".join(missing))
    return refs


def _choose_reference(seed: int, config: dict[str, Any]) -> Path:
    refs = _reference_files(config)
    return refs[(int(seed) & 0x7FFFFFFF) % len(refs)]


def _reference_cinematic_frame(out: Path, seed: int, config: dict[str, Any]) -> str:
    """No-credit fallback based only on the channel's own visual references."""
    reference = _choose_reference(seed, config)
    target = (int(config["image"]["width"]), int(config["image"]["height"]))
    safe = int(seed) & 0x7FFFFFFF

    with Image.open(reference) as opened:
        src = ImageOps.exif_transpose(opened).convert("RGB")
        src_ratio = src.width / max(1, src.height)
        target_ratio = target[0] / target[1]

        if abs(src_ratio - target_ratio) < 0.12:
            cx = 0.50 + (((safe // 7) % 9) - 4) * 0.006
            cy = 0.47 + (((safe // 13) % 7) - 3) * 0.006
            frame = ImageOps.fit(
                src,
                target,
                method=Image.Resampling.LANCZOS,
                centering=(max(0.43, min(0.57, cx)), max(0.41, min(0.56, cy))),
            )
        else:
            background = ImageOps.fit(src, target, method=Image.Resampling.LANCZOS, centering=(0.5, 0.47))
            background = background.filter(ImageFilter.GaussianBlur(radius=34))
            background = ImageEnhance.Brightness(background).enhance(0.72)
            background = ImageEnhance.Contrast(background).enhance(1.05)

            foreground = src.copy()
            foreground.thumbnail((int(target[0] * 0.94), int(target[1] * 0.94)), Image.Resampling.LANCZOS)
            scale = 1.0 + (safe % 5) * 0.009
            foreground = foreground.resize(
                (max(1, int(foreground.width * scale)), max(1, int(foreground.height * scale))),
                Image.Resampling.LANCZOS,
            )
            x = (target[0] - foreground.width) // 2 + (((safe // 19) % 31) - 15)
            y = (target[1] - foreground.height) // 2 + (((safe // 23) % 35) - 17)
            mask = Image.new("L", foreground.size, 255).filter(ImageFilter.GaussianBlur(radius=7))
            frame = background.copy()
            frame.paste(foreground, (x, y), mask)

        frame = ImageEnhance.Brightness(frame).enhance(0.995 + (safe % 4) * 0.007)
        frame = ImageEnhance.Contrast(frame).enhance(1.03 + ((safe // 5) % 4) * 0.008)
        frame = ImageEnhance.Color(frame).enhance(1.01 + ((safe // 11) % 4) * 0.006)
        frame = ImageEnhance.Sharpness(frame).enhance(1.07)

        out.parent.mkdir(parents=True, exist_ok=True)
        frame.save(out, format="JPEG", quality=96, subsampling=0, optimize=True)

    if not out.exists() or out.stat().st_size < 25_000:
        raise RuntimeError("El frame local soberano no se genero correctamente.")
    return f"{VISUAL_PROVIDER}/reference-transform/reference:{reference.name}/seed={safe}"


def _load_diffusion_pipeline(config: dict[str, Any]):
    image_cfg = config["image"]
    base_path = ROOT / image_cfg["base_model_path"]
    if not base_path.exists():
        return None

    enforce_offline_runtime()
    try:
        import torch
        from diffusers import AutoPipelineForText2Image
    except Exception as exc:
        raise RuntimeError(
            "El modelo visual local existe, pero faltan torch/diffusers en el runner."
        ) from exc

    use_cuda = bool(torch.cuda.is_available())
    dtype = torch.float16 if use_cuda else torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(
        str(base_path),
        torch_dtype=dtype,
        local_files_only=True,
        safety_checker=None,
    )

    lora_path = ROOT / image_cfg["lora_path"]
    if lora_path.exists():
        pipe.load_lora_weights(str(lora_path.parent), weight_name=lora_path.name)
        try:
            pipe.fuse_lora(lora_scale=0.82)
        except Exception:
            pass

    if use_cuda:
        pipe = pipe.to("cuda")
        try:
            pipe.enable_vae_slicing()
            pipe.enable_attention_slicing()
        except Exception:
            pass
    else:
        pipe = pipe.to("cpu")
    return pipe


_PIPELINE_CACHE = None
_PIPELINE_CACHE_READY = False


def generate_visual(prompt: str, out: Path, seed: int) -> str:
    """Generate a photorealistic spiritual image without remote inference credits.

    Priority:
      1. Local diffusion base + local channel LoRA, if weights are installed.
      2. Direct cinematic rendering of the locked Jesus reference bank.
    """
    global _PIPELINE_CACHE, _PIPELINE_CACHE_READY
    config = load_config()
    enforce_offline_runtime()

    if not _PIPELINE_CACHE_READY:
        _PIPELINE_CACHE = _load_diffusion_pipeline(config)
        _PIPELINE_CACHE_READY = True

    pipe = _PIPELINE_CACHE
    if pipe is None:
        return _reference_cinematic_frame(out, seed, config)

    import torch

    image_cfg = config["image"]
    render_width = 768
    render_height = 1344
    negative = str(image_cfg.get("negative_prompt") or "")
    reference = _choose_reference(seed, config)
    full_prompt = (
        "premium photorealistic live-action biblical cinema, artistic depiction of Jesus, "
        "natural adult human anatomy, natural skin texture, realistic eyes and hands, "
        "shoulder-length dark brown hair, groomed beard, cream linen robe, warm compassionate expression, "
        "cinematic natural light, realistic depth of field, no celebrity resemblance, "
        f"{prompt}"
    )

    generator = torch.Generator(device="cuda" if torch.cuda.is_available() else "cpu").manual_seed(int(seed) & 0x7FFFFFFF)
    result = pipe(
        prompt=full_prompt,
        negative_prompt=negative,
        width=render_width,
        height=render_height,
        num_inference_steps=int(image_cfg.get("steps") or 28),
        guidance_scale=float(image_cfg.get("guidance_scale") or 5.5),
        generator=generator,
    )
    if not result.images:
        raise RuntimeError("El modelo visual local no devolvio imagen.")

    image = result.images[0].convert("RGB")
    image = ImageOps.fit(
        image,
        (int(image_cfg["width"]), int(image_cfg["height"])),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.48),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, format="JPEG", quality=96, subsampling=0, optimize=True)
    if not out.exists() or out.stat().st_size < 25_000:
        raise RuntimeError("El modelo visual local produjo un archivo invalido.")

    lora_path = ROOT / image_cfg["lora_path"]
    lora_marker = lora_path.name if lora_path.exists() else "no-lora"
    return (
        f"{VISUAL_PROVIDER}/local-diffusion/reference:{reference.name}/"
        f"identity-adapter:{lora_marker}/seed={int(seed) & 0x7FFFFFFF}"
    )


def _master_voice(path: Path, target_lufs: float) -> None:
    temp = path.with_name(path.stem + ".sovereign-master.wav")
    filters = (
        "highpass=f=55,"
        "lowpass=f=10800,"
        "equalizer=f=120:t=q:w=0.9:g=1.0,"
        "equalizer=f=2800:t=q:w=1.0:g=0.6,"
        "acompressor=threshold=-22dB:ratio=1.6:attack=18:release=180:makeup=1.1,"
        f"loudnorm=I={target_lufs}:TP=-1.5:LRA=5.5"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-af", filters, "-ar", "48000", "-ac", "1", str(temp)],
        check=True,
    )
    if not temp.exists() or temp.stat().st_size < 1000:
        raise RuntimeError("No se pudo masterizar la voz local soberana.")
    temp.replace(path)


def make_voice(path: Path, text: str) -> str:
    """Synthesize the independent local channel voice with Piper-compatible weights.

    This deliberately does not claim to be Gemini/Algenib. Exact Algenib still
    requires Google's service. The local profile is the zero-credit alternative.
    """
    config = load_config()
    enforce_offline_runtime()
    voice_cfg = config["voice"]
    model = ROOT / voice_cfg["model_path"]
    model_cfg = ROOT / voice_cfg["config_path"]
    if not model.exists() or not model_cfg.exists():
        raise RuntimeError(
            "VOICE_LOCAL_MODEL_MISSING: faltan los pesos de Voz de Luz Local. "
            f"Esperados: {model} y {model_cfg}."
        )

    piper_bin = os.getenv("PIPER_BIN", "piper").strip() or "piper"
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [piper_bin, "--model", str(model), "--config", str(model_cfg), "--output_file", str(path)],
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Piper local fallo: {proc.stderr[-1200:]}")
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Piper local no produjo audio valido.")

    _master_voice(path, float(voice_cfg.get("master_lufs") or -16.5))
    return f"{VOICE_PROVIDER}:{voice_cfg['profile']}:{ENGINE_VERSION}"


def readiness() -> dict[str, Any]:
    config = load_config()
    image_cfg = config["image"]
    voice_cfg = config["voice"]
    base = ROOT / image_cfg["base_model_path"]
    lora = ROOT / image_cfg["lora_path"]
    voice_model = ROOT / voice_cfg["model_path"]
    voice_config = ROOT / voice_cfg["config_path"]
    refs = _reference_files(config)
    return {
        "engine": ENGINE_VERSION,
        "offline": True,
        "image_local_diffusion_ready": base.exists(),
        "image_identity_lora_ready": lora.exists(),
        "reference_fallback_ready": all(path.exists() for path in refs),
        "voice_local_ready": voice_model.exists() and voice_config.exists(),
        "exact_algenib_local": False,
        "theme_local_ready": True,
    }
