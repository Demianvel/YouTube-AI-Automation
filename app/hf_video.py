from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

from gradio_client import Client
from huggingface_hub import InferenceClient

W, H, FPS = 1080, 1920, 30
LTX_SPACE = os.getenv("HF_ZERO_VIDEO_SPACE", "Lightricks/LTX-2-3").strip()


def available() -> bool:
    return os.getenv("HF_VIDEO_ENABLED", "true").lower() == "true"


def _seed(meta: dict, index: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{index}|{marker}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)


def _channel_prompt(channel: dict, scene: dict) -> str:
    visual = " ".join(str(scene.get("visual_prompt") or scene.get("stock_query") or "").split())
    mode = str(channel.get("visual_mode") or "").lower()

    if "botanical" in mode:
        style = (
            "Premium botanical macro time-lapse visualization. One clearly identifiable seed remains the same species through the whole shot. "
            "Show physically coherent germination progression: seed coat softens and opens, a root emerges and grows downward, fine roots develop, "
            "a shoot pushes upward through moist soil, stem straightens, cotyledons or first leaves open. Locked macro camera or very slow cinematic push, "
            "natural soil texture, realistic moisture, believable plant anatomy, continuous growth with no magical morphing, no sudden species changes, "
            "no hands, no tools, no text, no logos, no watermark, no plastic plant, no duplicate plant, no fantasy colors. "
            "Vertical premium social-video composition, satisfying seed-germination time-lapse aesthetic."
        )
    elif "kids" in mode:
        style = (
            "Original premium 3D family animation, fictional child-safe characters, rounded expressive design, "
            "cinematic soft lighting, colorful detailed environment, clear character motion, playful camera movement, "
            "polished materials, warm educational mood, vertical social-video composition. "
            "No copyrighted characters, no logos, no text, no watermark, no real people."
        )
    else:
        style = (
            "Premium vertical creator video for an educational finance and entrepreneurship channel, cinematic social-video aesthetic, "
            "dynamic camera movement, modern small business environment, expressive but generic fictional adults when people are needed, "
            "clean product shots, cash-flow visual metaphors, ecommerce, shop, calculator, packaging or workspace details, "
            "high production value, realistic lighting, engaging motion. No brands, no logos, no readable text, no watermark, no politicians."
        )
    return f"{visual}. {style}"


def _normalize(source: Path, out: Path, duration: int) -> None:
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,fps={FPS},"
        "eq=contrast=1.02:saturation=1.04:brightness=0.003,"
        "unsharp=5:5:0.16:5:5:0"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(source),
        "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ], check=True)
    if not out.exists() or out.stat().st_size < 50_000:
        raise RuntimeError("El clip generado no pudo normalizarse correctamente.")


def _space_video(prompt: str, out: Path, duration: int, seed: int) -> str:
    client = Client(LTX_SPACE, verbose=False)
    result = client.predict(
        None,
        prompt,
        float(max(1, min(10, duration))),
        True,
        int(seed),
        False,
        1536,
        1024,
        api_name="/generate_video",
    )
    video_ref = result[0] if isinstance(result, (tuple, list)) else result
    source = Path(str(video_ref))
    if not source.exists():
        raise RuntimeError("LTX ZeroGPU no devolvio un archivo de video local.")
    shutil.copyfile(source, out)
    if out.stat().st_size < 50_000:
        raise RuntimeError("LTX ZeroGPU devolvio un video invalido.")
    return f"Hugging Face Space {LTX_SPACE} / LTX-2.3 Distilled ZeroGPU"


def _provider_video(prompt: str, out: Path, seed: int) -> str:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("No hay HF_TOKEN para Inference Providers.")
    provider = os.getenv("HF_VIDEO_PROVIDER", "auto").strip() or "auto"
    model = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B").strip()
    frames = int(os.getenv("HF_VIDEO_NUM_FRAMES", "81"))
    steps = int(os.getenv("HF_VIDEO_STEPS", "20"))
    guidance = float(os.getenv("HF_VIDEO_GUIDANCE", "5.0"))
    client = InferenceClient(provider=provider, api_key=token)
    video_bytes = client.text_to_video(
        prompt,
        model=model,
        seed=seed,
        num_frames=frames,
        num_inference_steps=steps,
        guidance_scale=guidance,
        negative_prompt=[
            "text", "logo", "watermark", "brand", "copyrighted character", "duplicate subject",
            "deformed hands", "extra fingers", "flicker", "low quality", "static image", "species morph",
            "plastic plant", "television static", "white noise visual"
        ],
    )
    out.write_bytes(video_bytes)
    if out.stat().st_size < 50_000:
        raise RuntimeError("Wan2.2 Inference Provider devolvio un video invalido.")
    return f"Hugging Face Inference Providers / {model}"


def generate_hf_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    if not available():
        raise RuntimeError("HF video esta deshabilitado.")

    scene_duration = int(channel["scene_seconds"])
    clips: list[Path] = []
    prompts: list[str] = []
    providers: list[str] = []

    for index, scene in enumerate(meta.get("scenes") or []):
        prompt = _channel_prompt(channel, scene)
        prompts.append(prompt)
        raw = workdir / f"hf_raw_{index + 1}.mp4"
        clip = workdir / f"hf_scene_{index + 1}.mp4"
        provider_label = ""
        space_error = None
        try:
            provider_label = _space_video(prompt, raw, scene_duration, _seed(meta, index))
        except Exception as exc:
            space_error = exc
            try:
                provider_label = _provider_video(prompt, raw, _seed(meta, index))
            except Exception as provider_exc:
                raise RuntimeError(
                    f"No hubo video gratuito disponible. LTX ZeroGPU: {space_error}; Wan2.2 provider: {provider_exc}"
                ) from provider_exc
        _normalize(raw, clip, scene_duration)
        clips.append(clip)
        providers.append(provider_label)

    if not clips:
        raise RuntimeError("Hugging Face no genero escenas.")

    manifest = workdir / "hf_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "hf_generated_visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(visual),
    ], check=True)

    total_duration = int(channel["scenes_per_short"]) * scene_duration
    meta["generated_visual_provider"] = providers
    meta["generated_video_prompts"] = prompts
    meta["synthetic_visual"] = True
    meta["render_quality"] = "1080x1920_30fps_hf_ai_video"
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
