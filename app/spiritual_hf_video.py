from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from .spiritual_tts import make_spiritual_spanish_voice
from .hf_video import _normalize, _provider_video, _safe_seed, _space_video, available
from .spiritual_continuity import ensure_spoken_text, fit_and_validate_spiritual_voice
from .spiritual_image import _animate as _animate_spiritual_image
from .spiritual_image import _download as _download_spiritual_image
from .spiritual_lipsync import apply_musetalk_lipsync, available as lipsync_available
from .spiritual_voice import polish_voice


def _seed(meta: dict, index: int) -> int:
    marker = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    signatures = meta.get("visual_variety_signatures") or []
    signature = signatures[index] if 0 <= index < len(signatures) else ""
    raw = (
        f"spiritual-character-v3|{meta.get('topic','')}|{meta.get('title','')}|"
        f"{index}|{signature}|{marker}"
    )
    return _safe_seed(int(hashlib.sha256(raw.encode()).hexdigest()[:8], 16))


def _character_style() -> str:
    return (
        "The SAME recurring fully synthetic photoreal human representation of Jesus whenever Jesus appears, visually like premium live-action cinema rather than animation: "
        "serene adult Middle Eastern/Mediterranean-looking man, shoulder-length wavy dark-brown hair with individual natural strands, full groomed brown beard, warm hazel-brown eyes, natural skin pores, subtle facial lines and realistic teeth, "
        "ivory or cream woven linen robe, beige mantle or occasional muted deep-red mantle, historically inspired simple clothing, no resemblance to any actor, celebrity or identifiable real person. "
        "When speaking, the synthetic character performs like a real human actor: natural mouth and jaw motion, cheek motion, blinking, breathing, eye refocusing, head turns and restrained nods, "
        "realistic shoulder, elbow, wrist and finger articulation, five fingers on each hand, natural open-palm gestures, torso weight shifts, hip and knee motion, believable full-body walking when visible, robe folds reacting to legs and wind. "
        "The setting supports the biblical message about Jesus and God: real valleys, mountains, rivers, lakes, olive groves, desert paths, forests, coasts, gardens, stone villages, snow or starry skies. "
        "Physically plausible sunlight or moonlight, realistic atmospheric depth, natural water, cloud and vegetation motion, cinematic depth of field, slow dolly orbit or tracking camera. "
        "ABSOLUTELY NO unrelated people, celebrities, politics, sports, news, brands, social networks, screens, articles, Wikipedia, Wikimedia, stock footage, reused third-party media, cartoon, illustration, painting, anime, stylized 3D, videogame look, plastic CGI skin, doll face, frozen mannequin pose, malformed hands or extra fingers. "
        "No readable text, no subtitles, no logo, no watermark. This is synthetic AI imagery, not a recording of a real person or a claim of literal divine footage. Vertical 9:16 premium YouTube Short."
    )


def _symbolic_style() -> str:
    return (
        "Create a reverent premium live-action cinematic cutaway about God without depicting God as a literal human character. "
        "Use one clear biblical symbol or natural manifestation of hope: an open Bible in warm light, a simple cross at dawn, an empty tomb entrance, a white dove, a shepherd staff beside a calm sheep, a lamp among olive branches, sunlight opening through storm clouds, a luminous path, living water or creation. "
        "Jesus may appear only as a secondary distant or profile figure if requested by the scene; do not force another centered talking portrait. "
        "Use real photographic materials, natural motion in pages fabric water clouds plants or birds, physically plausible light and a distinct camera composition from adjacent scenes. "
        "No fantasy deity, giant face in the sky, supernatural humanoid God, text, subtitles, logo, watermark, cartoon, painting, anime, stylized 3D, plastic CGI, stock footage or recognizable real person. Vertical 9:16 premium live-action cinema."
    )


def _is_symbolic(scene: dict) -> bool:
    visual = " ".join(str(scene.get("visual_prompt") or "").lower().split())
    markers = (
        "symbolic", "cutaway", "open bible", "wooden cross", "empty tomb",
        "white dove", "scripture", "presence of god", "divine-light",
        "light symbolize", "lamp", "shepherd staff", "gate of warm light",
    )
    return any(marker in visual for marker in markers)


def _prompt(scene: dict, index: int, total: int) -> str:
    visual = " ".join(str(scene.get("visual_prompt") or scene.get("stock_query") or "").split())
    if _is_symbolic(scene):
        progression = (
            f"Scene {index + 1} of {total}. This is a symbolic visual break: use a new focal object, "
            "camera distance and movement unlike the previous scene. "
        )
        return f"{visual}. {progression}{_symbolic_style()}"

    continuity = (
        "Preserve the same face, hair, beard, approximate age, eye color and body proportions used in prior Jesus scenes, but change pose, camera distance, movement and environment. "
        if index > 0 else
        "Establish the recurring face and body identity clearly so later Jesus scenes preserve the same person. "
    )
    progression = (
        f"Scene {index + 1} of {total}. {continuity}Never repeat the exact framing or body action of an adjacent scene. "
    )
    return f"{visual}. {progression}{_character_style()}"


def _continuous_voice(meta: dict, workdir: Path, duration: int) -> tuple[Path, str]:
    text = " ".join(
        str(scene.get("narration") or "").strip()
        for scene in (meta.get("scenes") or [])
        if str(scene.get("narration") or "").strip()
    )
    if not text:
        raise RuntimeError("No hay narracion para generar la voz continua del Short espiritual.")
    text, text_stats = ensure_spoken_text(text, duration, seed=_seed(meta, 700))
    meta["spoken_text_continuity"] = text_stats
    meta["spoken_text_final_words"] = text_stats["final_words"]
    voice = workdir / "spiritual_continuous_voice.wav"
    used = make_spiritual_spanish_voice(voice, text)
    voice_master = polish_voice(voice)
    continuity = fit_and_validate_spiritual_voice(voice, duration)
    meta.update(continuity)
    if voice_master != "unprocessed":
        used = f"{used}+{voice_master}"
    return voice, used


def _image_scene(prompt: str, workdir: Path, index: int, duration: int, seed: int) -> tuple[Path, str]:
    image = workdir / f"spiritual_hf_image_{index + 1}.jpg"
    clip = workdir / f"spiritual_hf_image_scene_{index + 1}.mp4"
    provider = _download_spiritual_image(prompt, image, seed)
    _animate_spiritual_image(image, clip, duration, index)
    return clip, f"{provider} + original cinematic motion"


def generate_spiritual_hf_short(channel: dict, meta: dict, workdir: Path, final: Path, apply_audio_fn) -> None:
    if not available():
        raise RuntimeError("HF video esta deshabilitado.")

    scene_duration = int(channel["scene_seconds"])
    scenes = list(meta.get("scenes") or [])
    total_duration = int(channel["scenes_per_short"]) * scene_duration
    voice_path, voice_provider = _continuous_voice(meta, workdir, total_duration)
    meta["_precomputed_voice_path"] = str(voice_path)
    meta["_precomputed_tts_provider"] = voice_provider
    meta["voice_delivery"] = "single_continuous_full_duration_validated_narration_track"
    meta["voice_profile"] = os.getenv("SPIRITUAL_VOICE_PROFILE", "voz_de_luz_serena_original_v1")
    meta["voice_brand"] = os.getenv("SPIRITUAL_VOICE_BRAND", "Voz de Luz")
    meta["character_identity_seed"] = _seed(meta, 0)

    ai_slots = max(0, min(int(os.getenv("SPIRITUAL_SHORT_AI_CLIPS", "3")), len(scenes)))
    clips: list[Path] = []
    prompts: list[str] = []
    providers: list[str] = []
    symbolic_indices: list[int] = []
    visual_seeds: list[int] = []

    for index, scene in enumerate(scenes):
        prompt = _prompt(scene, index, len(scenes))
        prompts.append(prompt)
        visual_seed = _seed(meta, index)
        visual_seeds.append(visual_seed)
        if _is_symbolic(scene):
            symbolic_indices.append(index)

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
                print(f"T2V espiritual no disponible en escena {index + 1} ({exc}); usando imagen original generada/local del proyecto.")

        clip, provider_label = _image_scene(prompt, workdir, index, scene_duration, visual_seed)
        clips.append(clip)
        providers.append(provider_label)

    if not clips:
        raise RuntimeError("No se generaron escenas espirituales originales.")

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
    meta["visual_scene_seeds"] = visual_seeds
    meta["symbolic_cutaway_scene_indices"] = symbolic_indices
    meta["source_credits"] = []
    meta["mixed_licensed_nature_fallback"] = False
    meta["external_media_allowed"] = False
    meta["original_generated_media_only"] = True
    meta["synthetic_visual"] = True
    meta["text_to_video_engine"] = "huggingface_ltx23_then_wan22_plus_original_generated_image_fallback"
    meta["text_to_video_key_scenes_requested"] = ai_slots
    meta["character_reference_profile"] = "dioshablahoyia_photoreal_human_v3_high_variety"
    meta["character_speaking_motion_requested"] = True
    meta["full_body_motion_requested"] = True
    meta["photoreal_human_required"] = True
    meta["no_cartoon_no_3d_animation"] = True
    meta["render_quality"] = "1080x1920_30fps_hf_ai_original_live_action_high_variety"
    apply_audio_fn(audio_visual, final, channel, meta, total_duration, _seed(meta, 999))
