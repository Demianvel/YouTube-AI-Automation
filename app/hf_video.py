from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from huggingface_hub import InferenceClient

W, H, FPS = 1080, 1920, 30


def available() -> bool:
    return bool(os.getenv("HF_TOKEN", "").strip()) and os.getenv("HF_VIDEO_ENABLED", "true").lower() == "true"


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
        raise RuntimeError("Hugging Face genero un clip que no pudo normalizarse correctamente.")


def generate_hf_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    if not available():
        raise RuntimeError("HF video no disponible: falta HF_TOKEN o HF_VIDEO_ENABLED=false.")

    token = os.environ["HF_TOKEN"].strip()
    provider = os.getenv("HF_VIDEO_PROVIDER", "auto").strip() or "auto"
    model = os.getenv("HF_VIDEO_MODEL", "Wan-AI/Wan2.2-TI2V-5B").strip()
    frames = int(os.getenv("HF_VIDEO_NUM_FRAMES", "81"))
    steps = int(os.getenv("HF_VIDEO_STEPS", "20"))
    guidance = float(os.getenv("HF_VIDEO_GUIDANCE", "5.0"))
    scene_duration = int(channel["scene_seconds"])

    client = InferenceClient(provider=provider, api_key=token)
    clips: list[Path] = []
    prompts: list[str] = []

    for index, scene in enumerate(meta.get("scenes") or []):
        prompt = _channel_prompt(channel, scene)
        prompts.append(prompt)
        raw = workdir / f"hf_raw_{index + 1}.mp4"
        clip = workdir / f"hf_scene_{index + 1}.mp4"
        video_bytes = client.text_to_video(
            prompt,
            model=model,
            seed=_seed(meta, index),
            num_frames=frames,
            num_inference_steps=steps,
            guidance_scale=guidance,
            negative_prompt=[
                "text", "logo", "watermark", "brand", "copyrighted character", "duplicate subject",
                "deformed hands", "extra fingers", "flicker", "low quality", "static image", "species morph",
                "plastic plant", "television static", "white noise visual"
            ],
        )
        raw.write_bytes(video_bytes)
        if raw.stat().st_size < 50_000:
            raise RuntimeError(f"Hugging Face devolvio un video invalido para la escena {index + 1}.")
        _normalize(raw, clip, scene_duration)
        clips.append(clip)

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
    meta["generated_visual_provider"] = f"Hugging Face Inference Providers / {model}"
    meta["generated_video_model"] = model
    meta["generated_video_prompts"] = prompts
    meta["synthetic_visual"] = True
    meta["render_quality"] = "1080x1920_30fps_hf_ai_video"
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
