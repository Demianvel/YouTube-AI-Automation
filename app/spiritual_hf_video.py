from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .audio import fit_voice_to_duration, make_natural_spanish_voice
from .hf_video import _normalize, _provider_video, _safe_seed, _space_video, available
from .spiritual_image import _animate as _animate_spiritual_image
from .spiritual_image import _download as _download_spiritual_image
from .spiritual_lipsync import apply_musetalk_lipsync, available as lipsync_available


def _seed(meta: dict, index: int) -> int:
    """Use one visual identity seed per video so scene changes do not reshuffle the face."""
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    raw = f"spiritual-character-v2|{meta.get('topic','')}|{meta.get('title','')}|{marker}"
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


def _character_style() -> str:
    return (
        "The SAME recurring fully synthetic photoreal human representation of Jesus in every scene, visually like premium live-action cinema rather than animation: "
        "serene adult Middle Eastern/Mediterranean-looking man, shoulder-length wavy dark-brown hair with individual natural strands, full groomed brown beard, warm hazel-brown eyes, natural skin pores, subtle facial lines and realistic teeth, "
        "ivory or cream woven linen robe, beige mantle or occasional muted deep-red mantle, historically inspired simple clothing, no resemblance to any actor, celebrity or identifiable real person. "
        "The synthetic character must perform like a real human actor: continuous speaking performance without frozen pauses, natural phoneme-like mouth and jaw motion, cheek motion, blinking, breathing, tiny eye refocusing, head turns and nods, "
        "realistic shoulder, elbow, wrist and finger articulation, five fingers on each hand, natural open-palm gestures, torso weight shifts, hip and knee motion, believable full-body walking when visible, robe folds reacting to legs and wind. "
        "Real landscapes only in appearance: green valleys and rivers, alpine mountains, Nordic aurora borealis, desert dunes, rocky coastline, olive groves, snowy ridges, forests after rain, lakes and mountain paths. "
        "Physically plausible sunlight or moonlight, realistic atmospheric depth, natural water, cloud and vegetation motion, cinematic depth of field, slow dolly/orbit/tracking camera. "
        "ABSOLUTELY NO cartoon, no illustration, no painting, no anime, no stylized 3D, no videogame look, no plastic CGI skin, no doll face, no frozen mannequin pose, no malformed hands, no extra fingers. "
        "No readable text, no subtitles, no logo, no watermark. This is synthetic AI imagery, not a recording of a real person or a claim of literal divine footage. Vertical 9:16 premium YouTube Short."
    )


def _prompt(scene: dict, index: int, total: int) -> str:
    visual = " ".join(str(scene.get("visual_prompt") or scene.get("stock_query") or "").split())
    continuity = (
        "Preserve identical face, hair, beard, approximate age, eye color, body proportions and robe palette from all previous scenes. "
        if index > 0 else
        "Establish the recurring face and body identity clearly so later scenes preserve the same person. "
    )
    progression = f"Scene {index + 1} of {total}. {continuity}"
    return f"{visual}. {progression}{_character_style()}"


def _continuous_voice(meta: dict, workdir: Path, duration: int) -> tuple[Path, str]:
    text = " ".join(
        str(scene.get("narration") or "").strip()
        for scene in (meta.get("scenes") or [])
        if str(scene.get("narration") or "").strip()
    )
    if not text:
        raise RuntimeError("No hay narracion para generar la voz continua del Short espiritual.")
    voice = workdir / "spiritual_continuous_voice.wav"
    used = make_natural_spanish_voice(voice, text)
    fit_voice_to_duration(voice, duration)
    return voice, used


def _image_scene(prompt: str, workdir: Path, index: int, duration: int, seed: int) -> tuple[Path, str]:
    image = workdir / f"spiritual_hf_image_{index + 1}.jpg"
    clip = workdir / f"spiritual_hf_image_scene_{index + 1}.mp4"
    provider = _download_spiritual_image(prompt, image, seed)
    _animate_spiritual_image(image, clip, duration, index)
    return clip, f"{provider} + cinematic motion"


def generate_spiritual_hf_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    if not available():
        raise RuntimeError("HF video esta deshabilitado.")

    scene_duration = int(channel["scene_seconds"])
    scenes = list(meta.get("scenes") or [])
    total_duration = int(channel["scenes_per_short"]) * scene_duration
    voice_path, voice_provider = _continuous_voice(meta, workdir, total_duration)
    meta["_precomputed_voice_path"] = str(voice_path)
    meta["_precomputed_tts_provider"] = voice_provider
    meta["voice_delivery"] = "single_continuous_narration_track"
    meta["character_identity_seed"] = _seed(meta, 0)

    # A 3-minute Short does not need twelve expensive T2V calls. Use a few
    # key live-action clips, then keep continuity with HF photoreal images +
    # cinematic motion. This protects ZeroGPU quota while retaining variety.
    ai_slots = max(0, min(int(os.getenv("SPIRITUAL_SHORT_AI_CLIPS", "3")), len(scenes)))
    clips: list[Path] = []
    prompts: list[str] = []
    providers: list[str] = []

    for index, scene in enumerate(scenes):
        prompt = _prompt(scene, index, len(scenes))
        prompts.append(prompt)
        visual_seed = _seed(meta, index)

        if index < ai_slots:
            raw = workdir / f"spiritual_hf_raw_{index + 1}.mp4"
            clip = workdir / f"spiritual_hf_scene_{index + 1}.mp4"
            try:
                try:
                    provider_label = _space_video(prompt, raw, scene_duration, visual_seed)
                except Exception as space_error:
                    try:
                        provider_label = _provider_video(prompt, raw, visual_seed)
                    except Exception as provider_error:
                        raise RuntimeError(
                            f"LTX ZeroGPU: {space_error}; provider: {provider_error}"
                        ) from provider_error
                _normalize(raw, clip, scene_duration)
                clips.append(clip)
                providers.append(provider_label)
                continue
            except Exception as exc:
                print(f"T2V espiritual no disponible en escena {index + 1} ({exc}); usando imagen HF fotorrealista animada.")

        clip, provider_label = _image_scene(prompt, workdir, index, scene_duration, visual_seed)
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

    audio_visual = visual
    meta["lip_sync_requested"] = True
    if lipsync_available():
        synced = workdir / "spiritual_hf_visual_lipsynced.mp4"
        try:
            meta["lip_sync_provider"] = apply_musetalk_lipsync(visual, voice_path, synced)
            meta["lip_sync_mode"] = "audio_driven_exact_mouth_sync"
            audio_visual = synced
        except Exception as exc:
            meta["lip_sync_failed"] = str(exc)
            meta["lip_sync_mode"] = "prompted_natural_speech_motion_fallback"
            print(f"MuseTalk no pudo completar lip-sync ({exc}); se conserva movimiento facial generado por el motor de video.")
    else:
        meta["lip_sync_mode"] = "prompted_natural_speech_motion_no_gpu"
        meta["lip_sync_note"] = "Para sincronizacion fonema-a-fonema se requiere un runner CUDA con MUSETALK_DIR preparado."

    meta["generated_visual_provider"] = providers
    meta["generated_video_prompts"] = prompts
    meta["synthetic_visual"] = True
    meta["text_to_video_engine"] = "huggingface_ltx23_then_wan22_plus_hf_image_hybrid"
    meta["text_to_video_key_scenes_requested"] = ai_slots
    meta["character_reference_profile"] = "dioshablahoyia_photoreal_human_v2"
    meta["character_speaking_motion_requested"] = True
    meta["full_body_motion_requested"] = True
    meta["photoreal_human_required"] = True
    meta["no_cartoon_no_3d_animation"] = True
    meta["render_quality"] = "1080x1920_30fps_hf_ai_hybrid_live_action"
    apply_audio_fn(audio_visual, final, channel, meta, total_duration, _seed(meta, 999))
