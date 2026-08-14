from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import time
from pathlib import Path

from gradio_client import Client
from huggingface_hub import InferenceClient

W, H, FPS = 1080, 1920, 30
LTX_SPACE = os.getenv("HF_ZERO_VIDEO_SPACE", "Lightricks/LTX-2-3").strip()
MAX_SIGNED_SEED = 2_147_483_647


def available() -> bool:
    return os.getenv("HF_VIDEO_ENABLED", "true").lower() == "true"


def _safe_seed(value: int) -> int:
    # Gradio/LTX uses a signed 32-bit integer input. Keep every renderer seed in
    # the same portable range so retries/providers receive a valid value.
    return int(value) % MAX_SIGNED_SEED


def _seed(meta: dict, index: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{index}|{marker}"
    value = int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16)
    return _safe_seed(value)


def _botanical_phase(index: int, total: int) -> str:
    if total <= 1:
        return (
            "Show the complete accelerated germination sequence: seed hydration and swelling, seed coat splitting, primary root emergence, "
            "secondary roots branching, hypocotyl rising, shoot breaking the soil surface, cotyledons opening and first leaves unfolding."
        )
    progress = index / max(1, total - 1)
    if progress < 0.34:
        return (
            "EARLY GERMINATION PHASE: begin with one dry seed centered just below moist soil. Show hydration, visible swelling, seed coat softening "
            "and splitting, then the first white radicle emerging and bending downward under gravity. Keep the seed shell visibly connected."
        )
    if progress < 0.67:
        return (
            "ROOT AND SHOOT PHASE: continue the same species and same cross-section setup. The primary root lengthens downward, fine lateral roots branch, "
            "while the hypocotyl curves upward and pushes toward the soil surface. Growth must be continuous and biologically plausible."
        )
    return (
        "EMERGENCE PHASE: continue the same species and same cross-section setup. The shoot breaks the soil surface, the stem straightens, cotyledons open, "
        "and the first small true leaves begin unfolding while the root system remains visible below the soil."
    )


def _channel_prompt(channel: dict, scene: dict, index: int, total: int) -> str:
    visual = " ".join(str(scene.get("visual_prompt") or scene.get("stock_query") or "").split())
    mode = str(channel.get("visual_mode") or "").lower()

    if "botanical" in mode:
        phase = _botanical_phase(index, total)
        style = (
            "SEED GERMINATION TIME LAPSE. Premium scientific macro botanical documentary, vertical 9:16. "
            "Use a locked-off macro camera and a transparent glass/acrylic soil cross-section so underground roots and the above-ground shoot can be seen together. "
            "Composition: dark or neutral studio background, moist dark soil filling most of the lower frame, clear horizontal soil surface, one seed centered as the focal point. "
            "Soft fixed diffused studio lighting with no flicker, high contrast on white roots and fresh green tissue, photorealistic soil texture and moisture. "
            f"{phase} "
            "The entire clip should feel like many real days compressed into seconds: smooth chronological progression, tiny organic plant movements, no camera shake, no dramatic transitions. "
            "Keep exactly one identifiable seed and the exact same species throughout. Preserve realistic botany: root grows down, shoot grows up, lateral roots branch naturally. "
            "No magical morphing, no sudden mature plant, no species change, no duplicate seedlings, no plastic appearance, no hands, no tools, no labels, no readable text, no logos, no watermark. "
            "Satisfying educational macro time-lapse aesthetic suitable for a premium YouTube Short."
        )
    elif "kids" in mode:
        style = (
            "Original premium 3D family animation for young children, vertical 9:16. Create completely original fictional characters with rounded expressive shapes, "
            "clear silhouettes, appealing facial expressions and safe playful actions. Cinematic soft lighting, polished colorful materials, detailed whimsical environment, "
            "smooth character animation, purposeful camera movement and a strong visual event within the first two seconds. The scene must visibly progress rather than remain static. "
            "Warm educational and adventurous mood, visual storytelling understandable without text. No copyrighted characters, no franchise lookalikes, no logos, no readable text, "
            "no watermark, no real people, no fear, weapons or dangerous behavior."
        )
    else:
        style = (
            "Premium vertical text-to-video scene for an educational finance and entrepreneurship channel, 9:16. Cinematic creator-video aesthetic with visible action and progression: "
            "modern small business, ecommerce packing, pricing decisions, inventory, calculator, product photography, customer service, workspace or cash-flow visual metaphors as appropriate. "
            "Use realistic lighting, controlled handheld or slider-style camera movement, clean composition, credible generic fictional adults only when needed, and multiple meaningful actions during the shot. "
            "No brands, no logos, no readable text, no watermark, no politicians, no luxury-money fantasy, no misleading piles of cash, no static slideshow look."
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


def _result_path(video_ref) -> Path:
    if hasattr(video_ref, "path"):
        return Path(str(video_ref.path))
    if isinstance(video_ref, dict):
        for key in ("path", "name", "video"):
            if video_ref.get(key):
                return Path(str(video_ref[key]))
    return Path(str(video_ref))


def _space_video(prompt: str, out: Path, duration: int, seed: int) -> str:
    attempts = max(1, int(os.getenv("HF_ZERO_RETRIES", "2")))
    last_error: Exception | None = None
    seed = _safe_seed(seed)
    for attempt in range(1, attempts + 1):
        try:
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
            source = _result_path(video_ref)
            if not source.exists():
                raise RuntimeError("LTX ZeroGPU no devolvio un archivo de video local.")
            shutil.copyfile(source, out)
            if out.stat().st_size < 50_000:
                raise RuntimeError("LTX ZeroGPU devolvio un video invalido.")
            return f"Hugging Face Space {LTX_SPACE} / LTX-2.3 Distilled ZeroGPU"
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(3 * attempt)
    raise RuntimeError(f"LTX ZeroGPU fallo tras {attempts} intento(s): {last_error}")


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
        seed=_safe_seed(seed),
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
    scenes = list(meta.get("scenes") or [])
    clips: list[Path] = []
    prompts: list[str] = []
    providers: list[str] = []

    for index, scene in enumerate(scenes):
        prompt = _channel_prompt(channel, scene, index, len(scenes))
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
                    f"No hubo text-to-video de Hugging Face disponible. LTX ZeroGPU: {space_error}; Wan2.2 provider: {provider_exc}"
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
    meta["text_to_video_engine"] = "huggingface_ltx23_then_wan22"
    meta["render_quality"] = "1080x1920_30fps_hf_ai_video"
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
