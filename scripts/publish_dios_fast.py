from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from app import pipeline
from app import spiritual_image
from app import spiritual_reference_generation as reference_generation
from app import spiritual_tts
from app.fast_spiritual_metadata import build_fast_metadata
from app.generator_resilient import _local_metadata
from app.spiritual_free_media import download_fresh_free_image
from app.spiritual_fresh_reference_bank import (
    choose_new_jesus_reference,
    choose_reference_for_prompt,
    is_jesus_prompt,
    is_noah_prompt,
    subject_prompt,
)
from app.visual_variety_v2 import attach_visual_pack_v2

ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = ROOT / "state" / "history.jsonl"


def _fast_local_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    metadata = _local_metadata(channel, previous)
    metadata = build_fast_metadata(metadata, channel, previous)
    print(
        f"Modo rapido: guion local NUEVO sobre {metadata.get('bible_reference')} para reservar Gemini exclusivamente para Voz de Luz/Algenib."
    )
    return metadata


def _fast_animate(source: Path, out: Path, duration: int, index: int) -> None:
    fps = 24
    frames = max(1, duration * fps)
    zoom_rate = 0.00072 + (index % 4) * 0.00006
    x_modes = (
        "iw/2-(iw/zoom/2)",
        "min(iw-iw/zoom,(iw-iw/zoom)*on/max(1,duration*24))",
        "max(0,(iw-iw/zoom)*(1-on/max(1,duration*24)))",
    )
    y_modes = (
        "ih/2-(ih/zoom/2)",
        "min(ih-ih/zoom,(ih-ih/zoom)*on/max(1,duration*24))",
        "max(0,(ih-ih/zoom)*(1-on/max(1,duration*24)))",
    )
    x_expr = x_modes[index % len(x_modes)]
    y_expr = y_modes[(index // 2) % len(y_modes)]
    vf = (
        "scale=1620:2880:force_original_aspect_ratio=increase,"
        "crop=1620:2880,"
        f"zoompan=z='min(zoom+{zoom_rate:.5f},1.085)':x='{x_expr}':y='{y_expr}':d={frames}:s=1080x1920:fps={fps},"
        "setsar=1,eq=contrast=1.02:saturation=1.04:brightness=0.003"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(source),
            "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
        ],
        check=True,
    )


def _history_provider_text(limit: int = 160) -> str:
    if not HISTORY_FILE.exists():
        return ""
    chunks: list[str] = []
    rows = HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
    for raw in rows:
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") != "dioshablahoyia":
            continue
        providers = row.get("generated_visual_provider") or []
        if isinstance(providers, str):
            providers = [providers]
        chunks.extend(str(provider) for provider in providers)
    return "\n".join(chunks)


def _remote_source_marker(provider: str) -> str:
    match = re.search(r"\bsource=([^ |]+)", str(provider))
    return match.group(1).strip() if match else ""


def _source_was_used(provider: str) -> bool:
    source = _remote_source_marker(provider)
    if not source:
        return False
    return source in _history_provider_text()


def _local_variant_was_used(provider: str) -> bool:
    """Reject only the exact repository reference+variant combination already published."""
    marker = str(provider).strip()
    if not marker:
        return False
    return marker in _history_provider_text()


def _hf_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ("zerogpu quota", "quota", "402", "429", "seconds requested", "too_many_requests"))


def _open_hf_circuit_if_quota(exc: Exception) -> None:
    if _hf_quota_error(exc) and os.getenv("HF_REMOTE_CIRCUIT_BREAKER", "true").lower() == "true":
        reference_generation._REMOTE_CIRCUIT_OPEN = True
        print("HF ZeroGPU sin cuota: circuito abierto para no repetir esperas durante este Short.")


def _text_only_reference(seed: int) -> Path:
    """Return any repository marker path; FLUX text mode never reads its image bytes."""
    refs = reference_generation._reference_files()
    if not refs:
        raise RuntimeError("No hay ningun marcador de referencia disponible para etiquetar la generacion text-to-image.")
    safe = int(seed) & 0x7FFFFFFF
    return refs[safe % len(refs)]


def _fresh_bank_reference_guided(
    full_prompt: str,
    out: Path,
    seed: int,
    target_size: tuple[int, int] = (1080, 1920),
) -> tuple[str, str]:
    """New GitHub references for Jesus/Noah; clean FLUX text generation for scenery."""
    if getattr(reference_generation, "_REMOTE_CIRCUIT_OPEN", False):
        raise RuntimeError("HF free-image circuit abierto para esta ejecucion; fallback inmediato.")

    subject = subject_prompt(full_prompt)

    # Noah's Ark has its own reference bank and must never be confused with the
    # substring 'ark' inside the word 'watermark'.
    if is_noah_prompt(subject):
        try:
            chosen = choose_reference_for_prompt(subject, seed)
        except Exception as ref_exc:
            chosen = _text_only_reference(seed)
            print(f"Referencia de Noe invalida ({ref_exc}); usando FLUX ZeroGPU en modo texto puro.")
            provider = reference_generation._generate_text_zerogpu(
                chosen,
                subject + ", fresh photoreal cinematic Noah's Ark scene, vertical 9:16, realistic materials and animals, no text, no logo, no watermark",
                out,
                seed,
                target_size,
            )
            return provider.replace("style-reference:", "story-text-only:"), f"text-only:{chosen.name}"

        noah_prompt = (
            "Use the supplied image only as a visual style and story reference for Noah's Ark. "
            "Create a clearly NEW photorealistic cinematic biblical scene with a different camera position, "
            "background arrangement, animal placement, lighting and composition. Do not copy pixels or recreate the source frame. "
            f"Scene request: {subject}. Vertical 9:16, realistic materials and animals, no text, no logo, no watermark."
        )
        try:
            provider = reference_generation._generate_reference_zerogpu(
                chosen, noah_prompt, out, seed, target_size
            )
            return provider.replace("reference:", "story-reference:"), chosen.name
        except Exception as exc:
            _open_hf_circuit_if_quota(exc)
            if getattr(reference_generation, "_REMOTE_CIRCUIT_OPEN", False):
                raise
            provider = reference_generation._generate_text_zerogpu(
                chosen, subject + ", fresh photoreal cinematic Noah's Ark scene, vertical 9:16, no text, no watermark", out, seed, target_size
            )
            return provider.replace("style-reference:", "story-style:"), chosen.name

    if is_jesus_prompt(subject):
        try:
            chosen = choose_reference_for_prompt(subject, seed)
        except Exception as ref_exc:
            chosen = _text_only_reference(seed)
            print(f"Referencias de Jesus invalidas ({ref_exc}); usando FLUX ZeroGPU en modo texto puro.")
            jesus_prompt = (
                subject
                + ", original synthetic adult Jesus character, shoulder-length wavy dark-brown hair, groomed beard, "
                  "warm compassionate expression, cream linen robe, premium photorealistic live-action cinema, "
                  "natural anatomy and hands, vertical 9:16, no text, no captions, no logo, no watermark, no celebrity resemblance"
            )
            try:
                provider = reference_generation._generate_text_zerogpu(
                    chosen, jesus_prompt, out, seed, target_size
                )
                return provider.replace("style-reference:", "jesus-text-only:"), f"text-only:{chosen.name}"
            except Exception as exc:
                _open_hf_circuit_if_quota(exc)
                raise

        previous_choose = reference_generation.choose_reference
        reference_generation.choose_reference = lambda _seed: chosen
        try:
            provider, _ = reference_generation.generate_reference_guided_image(
                full_prompt, out, seed, target_size=target_size
            )
            return provider, chosen.name
        finally:
            reference_generation.choose_reference = previous_choose

    # Landscapes, Bible still lifes and symbolic cutaways are intentionally
    # generated without the generic Jesus identity boilerplate. This keeps the
    # Short visually varied instead of turning every scene into the same portrait.
    try:
        reference = choose_new_jesus_reference(seed)
    except Exception:
        reference = _text_only_reference(seed)
    scenic_prompt = (
        subject
        + ", completely new premium photorealistic cinematic spiritual cutaway, realistic optics and natural light, "
          "vertical 9:16, no text, no captions, no logo, no watermark, no celebrity resemblance"
    )
    try:
        provider = reference_generation._generate_text_zerogpu(
            reference, scenic_prompt, out, seed, target_size
        )
        return provider.replace("style-reference:", "fresh-scenic-generation:"), reference.name
    except Exception as exc:
        _open_hf_circuit_if_quota(exc)
        raise


_ORIGINAL_DOWNLOAD = spiritual_image._download
_ORIGINAL_GEMINI_VOICE = spiritual_tts._gemini_spiritual_voice


def _fresh_download(prompt: str, out: Path, seed: int) -> str:
    """HF first; then unseen local variant; then previously unused free-media URL."""
    original_provider = ""
    original_error: Exception | None = None
    try:
        original_provider = _ORIGINAL_DOWNLOAD(prompt, out, seed)
        if not original_provider.startswith("local_project_jesus_reference"):
            return original_provider
        if not _local_variant_was_used(original_provider):
            print(f"HF sin cuota: usando variante local INEDITA y controlada: {original_provider}")
            return original_provider + ":fresh_local_variant_nonrepeat"
        print("La variante local exacta ya fue publicada; buscando una fuente nueva.")
    except Exception as exc:
        original_error = exc
        print(f"Generador Hugging Face principal no disponible ({exc}); buscando respaldo libre NUEVO.")

    free_errors: list[str] = []
    for attempt in range(8):
        retry_seed = int(seed) + (attempt * 104729)
        try:
            provider = download_fresh_free_image(prompt, out, retry_seed)
            if _source_was_used(provider):
                free_errors.append(f"fuente ya usada: {_remote_source_marker(provider)}")
                print("Fuente libre ya utilizada en un Short anterior; buscando otra.")
                continue
            return provider + ":fresh_nonrepeat_fallback"
        except Exception as fresh_exc:
            free_errors.append(str(fresh_exc))

    strict = os.getenv("SPIRITUAL_REQUIRE_FRESH_VISUAL", "true").lower().strip() == "true"
    if strict:
        raise RuntimeError(
            "Se rechazo publicar una escena visual repetida. "
            f"HF/local={original_provider or original_error}; fresh-free={' | '.join(free_errors[-4:])}"
        )
    if original_provider:
        return original_provider
    raise RuntimeError("No se encontro una imagen visual valida y nueva.")


def _quota_resilient_gemini_voice(path: Path, text: str) -> str:
    """Delegate quota-aware retries to the permanent Voz de Luz TTS implementation."""
    return _ORIGINAL_GEMINI_VOICE(path, text)


pipeline.generate_metadata = _fast_local_metadata
pipeline.attach_visual_pack = attach_visual_pack_v2
spiritual_image.generate_reference_guided_image = _fresh_bank_reference_guided
spiritual_image._download = _fresh_download
spiritual_image._animate = _fast_animate
spiritual_tts._gemini_spiritual_voice = _quota_resilient_gemini_voice

if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
