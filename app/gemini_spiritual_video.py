from __future__ import annotations

import base64
import os
import re
import time
from pathlib import Path

from google import genai


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"


def available() -> bool:
    enabled = os.getenv("GEMINI_VIDEO_ENABLED", "true").strip().lower() == "true"
    return enabled and bool(os.getenv("GEMINI_API_KEY", "").strip()) and bool(_reference_paths())


def _reference_paths() -> list[Path]:
    files = sorted(REFERENCE_DIR.glob("jesus_reference_*.*"))
    return [p for p in files if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}][:3]


def _mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "image/png"
    if suffix == ".webp":
        return "image/webp"
    return "image/jpeg"


def _spoken_line(meta: dict, max_words: int = 20) -> str:
    candidates: list[str] = []
    for scene in meta.get("scenes") or []:
        narration = " ".join(str(scene.get("narration") or "").split()).strip()
        if narration:
            candidates.append(narration)
    for key in ("hook", "message", "description", "narration"):
        value = " ".join(str(meta.get(key) or "").split()).strip()
        if value:
            candidates.append(value)

    if not candidates:
        return "No tengas miedo. Dios conoce tu camino y su amor puede sostenerte hoy."

    clean = candidates[0]
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    chosen = sentences[0] if sentences else clean
    words = chosen.split()
    if len(words) > max_words:
        chosen = " ".join(words[:max_words]).rstrip(",;:-") + "."
    elif chosen[-1:] not in ".!?":
        chosen += "."
    return chosen


def _visual_context(meta: dict) -> str:
    scene = (meta.get("scenes") or [{}])[0]
    visual = " ".join(str(scene.get("visual_prompt") or "").split()).strip()
    topic = " ".join(str(meta.get("topic") or "esperanza, amor y fe").split()).strip()
    return visual or topic


def _prompt(meta: dict, spoken_line: str) -> str:
    visual = _visual_context(meta)
    return f"""
Create a premium photorealistic live-action style vertical 9:16 cinematic video, one single continuous unbroken shot, no scene cuts, about 8 to 10 seconds.

Use <IMAGE_REF_0>, <IMAGE_REF_1> and <IMAGE_REF_2> only as subject references for the SAME recurring fully synthetic respectful representation of Jesus. Preserve the same facial identity, approximate age, shoulder-length wavy dark-brown hair, full groomed brown beard, warm hazel-brown eyes, natural skin texture and proportions. He wears an ivory/cream woven linen robe with a soft beige mantle, occasionally a muted deep-red cloth accent only when visually coherent. Do not imitate any actor, celebrity, public figure or identifiable real person.

Visual direction: {visual}. Golden sunrise or sunset light, natural mountains/valley/river/lake or olive-grove environment, physically plausible atmosphere, cinematic depth of field, subtle wind in hair and robe, realistic skin and cloth detail. Camera slowly dollies toward him at chest-to-waist framing. He looks directly into camera with a compassionate calm expression, breathes naturally, blinks, makes tiny eye refocusing movements, gently extends one open hand toward the viewer and uses a second subtle natural hand gesture while speaking. Correct anatomy, five fingers per hand, natural shoulders/elbows/wrists, natural torso weight shift. No frozen pose, no mannequin motion, no plastic CGI skin, no cartoon, no illustration, no anime, no videogame look.

Dialogue and sound: the character speaks EXACTLY this Spanish line and nothing else: "{spoken_line}"
Voice performance: adult male low warm baritone, human and intimate, neutral Latin-American Spanish, serene, compassionate, emotionally present, cinematic, soft natural breath, slow and confident but not theatrical. The voice should convey peace, love, hope and spiritual warmth. No robotic cadence, no advertising voice, no shouting, no exaggerated echo or artificial cathedral reverb. Add only very subtle natural ambience and a barely audible original cinematic spiritual pad underneath the dialogue.

Mouth, jaw, cheeks, tongue visibility when appropriate, facial muscles, head motion and body gestures must follow the spoken performance naturally. Prioritize convincing audio-visual speech timing and natural lip synchronization. Keep the face stable and recognizable throughout the whole clip.

No readable text, no captions, no subtitles, no logos, no visible watermark, no extra people, no duplicate character. This is an artistic synthetic character and must look like premium live-action cinema rather than animation. Use the supplied images as references, not as literal frozen opening frames.
""".strip()


def _download_output(client, video_output, final: Path) -> None:
    data = getattr(video_output, "data", None)
    if data:
        final.write_bytes(base64.b64decode(data))
        return

    uri = str(getattr(video_output, "uri", "") or "").strip()
    if not uri:
        raise RuntimeError("Gemini Omni no devolvio datos ni URI de video.")

    match = re.search(r"files/([^/:?]+)", uri)
    if not match:
        raise RuntimeError(f"No pude resolver el file id de Gemini Omni: {uri}")
    file_name = f"files/{match.group(1)}"

    deadline = time.time() + 600
    while time.time() < deadline:
        info = client.files.get(name=file_name)
        state = str(getattr(getattr(info, "state", None), "name", None) or getattr(info, "state", ""))
        state = state.upper()
        if state == "ACTIVE":
            break
        if state == "FAILED":
            raise RuntimeError("Gemini Omni marco el video como FAILED.")
        time.sleep(5)
    else:
        raise TimeoutError("Gemini Omni excedio 10 minutos esperando el video.")

    video_bytes = client.files.download(file=uri)
    if hasattr(video_bytes, "read"):
        video_bytes = video_bytes.read()
    final.write_bytes(bytes(video_bytes))


def generate_gemini_spiritual_short(channel: dict, meta: dict, workdir: Path, final: Path) -> None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY para Gemini Omni.")

    refs = _reference_paths()
    if not refs:
        raise RuntimeError("No hay referencias visuales en assets/dioshablahoyia/reference.")

    inputs: list[dict] = []
    for ref in refs:
        inputs.append({
            "type": "image",
            "data": base64.b64encode(ref.read_bytes()).decode("ascii"),
            "mime_type": _mime(ref),
        })

    spoken_line = _spoken_line(meta)
    inputs.append({"type": "text", "text": _prompt(meta, spoken_line)})

    model = os.getenv("GEMINI_VIDEO_MODEL", "gemini-omni-flash-preview").strip()
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=model,
        input=inputs,
        response_format={"type": "video", "aspect_ratio": "9:16", "delivery": "uri"},
        generation_config={"video_config": {"task": "reference_to_video"}},
    )

    video_output = getattr(interaction, "output_video", None)
    if video_output is None:
        raise RuntimeError("Gemini Omni no devolvio output_video.")

    workdir.mkdir(parents=True, exist_ok=True)
    _download_output(client, video_output, final)
    if not final.exists() or final.stat().st_size < 100_000:
        raise RuntimeError("Gemini Omni genero un MP4 vacio o demasiado pequeno.")

    meta["visual_source"] = "gemini_omni_flash_reference_to_video"
    meta["text_to_video_engine"] = model
    meta["gemini_omni_primary"] = True
    meta["native_generated_audio"] = True
    meta["spoken_line"] = spoken_line
    meta["character_reference_images"] = [p.name for p in refs]
    meta["character_reference_profile"] = "dioshablahoyia_recurring_photoreal_reference_v3"
    meta["character_speaking_motion_requested"] = True
    meta["full_body_motion_requested"] = True
    meta["lip_sync_requested"] = True
    meta["lip_sync_mode"] = "native_audio_visual_generation_requested"
    meta["voice_profile"] = "warm_male_cinematic_spiritual_latam"
    meta["synthetic_visual"] = True
    meta["photoreal_live_action_look"] = True
    meta["render_quality"] = "gemini_omni_vertical_native_video"
