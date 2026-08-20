from __future__ import annotations

import json
import os
import re
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
from app.spiritual_visual_motion import render_still_motion
from app.visual_variety_v3 import attach_visual_pack_v3

ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = ROOT / "state" / "history.jsonl"
_LOCAL_VARIANTS_THIS_RUN: set[str] = set()
_LOCAL_BASES_THIS_RUN: set[str] = set()


def _fast_local_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    metadata = _local_metadata(channel, previous)
    metadata = build_fast_metadata(metadata, channel, previous)
    print(
        f"Modo rapido: guion local NUEVO sobre {metadata.get('bible_reference')} para reservar Gemini exclusivamente para Voz de Luz/Algenib."
    )
    return metadata


def _fast_animate(source: Path, out: Path, duration: int, index: int) -> None:
    label = render_still_motion(
        source,
        out,
        duration,
        index,
        width=1080,
        height=1920,
        fps=24,
        preset="veryfast",
        crf=20,
        salt="dios-short-v3",
    )
    print(f"Movimiento cinematografico escena {index + 1}: {label}")


def _history_rows(limit: int = 200) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    rows: list[dict] = []
    for raw in HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get("channel") == "dioshablahoyia":
            rows.append(row)
    return rows


def _history_provider_text(limit: int = 200) -> str:
    chunks: list[str] = []
    for row in _history_rows(limit):
        providers = row.get("generated_visual_provider") or []
        if isinstance(providers, str):
            providers = [providers]
        chunks.extend(str(provider) for provider in providers)
    return "\n".join(chunks)


def _remote_source_marker(provider: str) -> str:
    text = str(provider or "")
    source = re.search(r"\bsource=([^ |]+)", text)
    if source:
        return f"source:{source.group(1).strip()}"
    pexels = re.search(r"\bid=([0-9]+)", text)
    if pexels and text.startswith("Pexels"):
        return f"pexels:{pexels.group(1)}"
    local = re.search(r"reference:([^/|]+\.jpg)", text)
    if local and "local_project_jesus_reference" in text:
        return f"local-reference:{local.group(1)}"
    return ""


def _source_was_used(provider: str) -> bool:
    marker = _remote_source_marker(provider)
    if not marker:
        return False
    history = _history_provider_text()
    raw_marker = marker.split(":", 1)[1] if ":" in marker else marker
    return raw_marker in history


def _local_base_marker(provider: str) -> str:
    match = re.search(r"reference:([^/|]+\.jpg)", str(provider or ""))
    return match.group(1) if match else ""


def _local_base_recently_used(provider: str, video_window: int = 18) -> bool:
    base = _local_base_marker(provider)
    if not base:
        return True
    if base in _LOCAL_BASES_THIS_RUN:
        return True
    for row in _history_rows(video_window):
        providers = row.get("generated_visual_provider") or []
        if isinstance(providers, str):
            providers = [providers]
        if any(base in str(item) for item in providers):
            return True
    return False


def _local_variant_was_used(provider: str) -> bool:
    marker = str(provider).strip()
    if not marker:
        return False
    return marker in _LOCAL_VARIANTS_THIS_RUN or marker in _history_provider_text()


def _hf_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ("zerogpu quota", "quota", "402", "429", "seconds requested", "too_many_requests"))


def _open_hf_circuit_if_quota(exc: Exception) -> None:
    if _hf_quota_error(exc) and os.getenv("HF_REMOTE_CIRCUIT_BREAKER", "true").lower() == "true":
        reference_generation._REMOTE_CIRCUIT_OPEN = True
        print("HF ZeroGPU sin cuota: circuito abierto para no repetir esperas durante este Short.")


def _text_only_reference(seed: int) -> Path:
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
    if getattr(reference_generation, "_REMOTE_CIRCUIT_OPEN", False):
        raise RuntimeError("HF free-image circuit abierto para esta ejecucion; fallback inmediato.")

    subject = subject_prompt(full_prompt)

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


def _accept_local_variant(provider: str) -> str | None:
    if not provider.startswith("local_project_jesus_reference"):
        return None
    if _local_variant_was_used(provider) or _local_base_recently_used(provider):
        return None
    base = _local_base_marker(provider)
    _LOCAL_VARIANTS_THIS_RUN.add(provider)
    if base:
        _LOCAL_BASES_THIS_RUN.add(base)
    print(f"Fallback local excepcional: referencia base NO usada recientemente: {provider}")
    return provider + ":fresh_local_variant_nonrepeat:last_resort_only"


def _fresh_free_media(prompt: str, out: Path, seed: int, attempts: int = 18) -> str:
    errors: list[str] = []
    for attempt in range(attempts):
        retry_seed = int(seed) + (attempt + 1) * 104729
        try:
            provider = download_fresh_free_image(prompt, out, retry_seed)
            if _source_was_used(provider):
                errors.append(f"fuente ya usada: {_remote_source_marker(provider)}")
                continue
            return provider + ":fresh_source_nonrepeat_v3"
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("No se encontro fuente visual gratuita nueva: " + " | ".join(errors[-5:]))


def _symbolic_prompt_for_jesus(prompt: str) -> str:
    return (
        "symbolic Christian faith cutaway instead of a repeated portrait: open Bible, simple wooden cross, olive branches, "
        "living water, sunrise through clouds, peaceful biblical landscape, premium photoreal cinematic composition, "
        "no human portrait, no text, no logo, no watermark. Context: " + str(prompt)
    )


def _fresh_download(prompt: str, out: Path, seed: int) -> str:
    """Generate first; when GPU is unavailable, prefer a genuinely new source over recycling a base portrait."""
    original_provider = ""
    original_error: Exception | None = None
    try:
        original_provider = _ORIGINAL_DOWNLOAD(prompt, out, seed)
        if not original_provider.startswith("local_project_jesus_reference"):
            return original_provider
        print("El generador principal devolvio una referencia local; no se acepta automaticamente porque visualmente puede repetirse.")
    except Exception as exc:
        original_error = exc
        print(f"Generador principal no disponible ({exc}); activando diversidad visual de respaldo v3.")

    jesus_scene = is_jesus_prompt(subject_prompt(prompt))

    # For scenic/symbolic scenes, a fresh remote CC0/Pexels source is much more
    # diverse than another crop of the same Jesus portrait.
    free_prompt = _symbolic_prompt_for_jesus(prompt) if jesus_scene else prompt
    try:
        return _fresh_free_media(free_prompt, out, seed, attempts=20)
    except Exception as free_exc:
        print(f"No se encontro fuente libre nueva ({free_exc}).")

    # Only a Jesus-specific scene may use a local Jesus base, only once per Short,
    # and only when that base did not appear in the recent channel history.
    if jesus_scene:
        local_errors: list[str] = []
        for attempt in range(1, 30):
            retry_seed = int(seed) + attempt * 130363
            try:
                provider = spiritual_image._local_reference(out, retry_seed)
                accepted = _accept_local_variant(provider)
                if accepted:
                    return accepted
                local_errors.append(f"base/variante reciente: {provider}")
            except Exception as local_exc:
                local_errors.append(str(local_exc))
        raise RuntimeError(
            "Se rechazo repetir el retrato local de Jesus. "
            f"primary={original_provider or original_error}; local={' | '.join(local_errors[-5:])}"
        )

    strict = os.getenv("SPIRITUAL_REQUIRE_FRESH_VISUAL", "true").lower().strip() == "true"
    if strict:
        raise RuntimeError(
            "Se rechazo sustituir una escena de paisaje/simbolo por un retrato local repetitivo. "
            f"primary={original_provider or original_error}"
        )
    if original_provider:
        return original_provider
    raise RuntimeError("No se encontro una imagen visual valida y nueva.")


def _quota_resilient_gemini_voice(path: Path, text: str) -> str:
    return _ORIGINAL_GEMINI_VOICE(path, text)


pipeline.generate_metadata = _fast_local_metadata
pipeline.attach_visual_pack = attach_visual_pack_v3
spiritual_image.generate_reference_guided_image = _fresh_bank_reference_guided
spiritual_image._download = _fresh_download
spiritual_image._animate = _fast_animate
spiritual_tts._gemini_spiritual_voice = _quota_resilient_gemini_voice

if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
