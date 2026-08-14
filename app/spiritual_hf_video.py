from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .hf_video import _normalize, _provider_video, _safe_seed, _space_video, available


def _seed(meta: dict, index: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"spiritual|{meta.get('topic','')}|{meta.get('title','')}|{index}|{marker}"
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


def _character_style() -> str:
    return (
        "Reverent original artistic representation of Jesus as the SAME recurring fictional character in every scene: "
        "serene adult man, long wavy dark-brown hair, full neat brown beard, warm hazel-brown eyes, compassionate expression, "
        "natural cream or ivory linen robe, beige mantle or occasional muted deep-red mantle, historically inspired simple clothing, "
        "no resemblance to a specific actor or celebrity. Premium photoreal cinematic spiritual drama, realistic skin and fabric, "
        "warm golden sunrise or sunset light, subtle volumetric rays, mountains, valleys, rivers, lakes, olive trees or stone paths when appropriate. "
        "When the scene calls for speaking, show restrained natural speech motion: subtle mouth and jaw articulation, gentle breathing, occasional blinks, "
        "small head movement, calm eye contact toward camera and one or two slow open-hand gestures. Avoid exaggerated lip movement or theatrical acting. "
        "Visible natural motion throughout the shot: walking, extending a hand, robe moving in a light breeze, water ripples, clouds drifting, leaves moving, "
        "camera dolly or slow orbit. Respectful peaceful mood. No claim that this is a real recording or a real actor. No horror, no sensational apocalypse imagery, "
        "no readable text, no subtitles, no logo, no watermark. Vertical 9:16 composition for a premium YouTube Short."
    )


def _prompt(scene: dict, index: int, total: int) -> str:
    visual = " ".join(str(scene.get("visual_prompt") or scene.get("stock_query") or "").split())
    continuity = (
        "Preserve identical face, hair, beard, approximate age, robe palette and body proportions from all previous scenes. "
        if index > 0 else
        "Establish the recurring character clearly so later scenes can preserve the same face, hair, beard, age and robe palette. "
    )
    progression = f"Scene {index + 1} of {total}. {continuity}"
    return f"{visual}. {progression}{_character_style()}"


def generate_spiritual_hf_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    if not available():
        raise RuntimeError("HF video esta deshabilitado.")

    scene_duration = int(channel["scene_seconds"])
    scenes = list(meta.get("scenes") or [])
    clips: list[Path] = []
    prompts: list[str] = []
    providers: list[str] = []

    for index, scene in enumerate(scenes):
        prompt = _prompt(scene, index, len(scenes))
        prompts.append(prompt)
        raw = workdir / f"spiritual_hf_raw_{index + 1}.mp4"
        clip = workdir / f"spiritual_hf_scene_{index + 1}.mp4"
        space_error = None
        try:
            provider_label = _space_video(prompt, raw, scene_duration, _seed(meta, index))
        except Exception as exc:
            space_error = exc
            try:
                provider_label = _provider_video(prompt, raw, _seed(meta, index))
            except Exception as provider_exc:
                raise RuntimeError(
                    f"No hubo text-to-video de Hugging Face disponible. LTX ZeroGPU: {space_error}; provider: {provider_exc}"
                ) from provider_exc
        _normalize(raw, clip, scene_duration)
        clips.append(clip)
        providers.append(provider_label)

    if not clips:
        raise RuntimeError("No se generaron escenas espirituales de IA.")

    manifest = workdir / "spiritual_hf_concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / "spiritual_hf_visual.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(visual),
    ], check=True)

    total_duration = int(channel["scenes_per_short"]) * scene_duration
    meta["generated_visual_provider"] = providers
    meta["generated_video_prompts"] = prompts
    meta["synthetic_visual"] = True
    meta["text_to_video_engine"] = "huggingface_ltx23_then_wan22_spiritual"
    meta["character_reference_profile"] = "dioshablahoyia_recurring_jesus_v1"
    meta["character_speaking_motion_requested"] = True
    meta["render_quality"] = "1080x1920_30fps_hf_ai_video"
    apply_audio_fn(visual, final, channel, meta, total_duration, _seed(meta, 999))
