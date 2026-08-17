from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import spiritual_image
from . import spiritual_reference_generation as reference_generation
from .spiritual_free_media import download_fresh_free_image
from .spiritual_fresh_reference_bank import (
    choose_new_jesus_reference,
    choose_reference_for_prompt,
    is_jesus_prompt,
    is_noah_prompt,
    subject_prompt,
)

ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = ROOT / "state" / "history.jsonl"
_INSTALLED = False
_ORIGINAL_DOWNLOAD = None


def _history_provider_text(limit: int = 220) -> str:
    if not HISTORY_FILE.exists():
        return ""
    chunks: list[str] = []
    for raw in HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
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


def _provider_marker(provider: str) -> str:
    text = str(provider or "")
    source = re.search(r"\bsource=([^ |]+)", text)
    if source:
        return source.group(1).strip()
    pexels = re.search(r"\bid=([0-9]+)", text)
    if text.startswith("Pexels") and pexels:
        return f"pexels-id={pexels.group(1)}"
    return ""


def _provider_was_used(provider: str) -> bool:
    marker = _provider_marker(provider)
    if not marker:
        return False
    history = _history_provider_text()
    if marker.startswith("pexels-id="):
        return f"id={marker.split('=', 1)[1]}" in history
    return marker in history


def _quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in (
        "zerogpu quota", "quota", "402", "429", "seconds requested", "too_many_requests"
    ))


def _open_circuit(exc: Exception) -> None:
    if _quota_error(exc) and os.getenv("HF_REMOTE_CIRCUIT_BREAKER", "true").lower() == "true":
        reference_generation._REMOTE_CIRCUIT_OPEN = True
        print("HF ZeroGPU sin cuota: circuito abierto para las escenas restantes; no se repetiran esperas.")


def generate_fresh_reference_guided_image(
    full_prompt: str,
    out: Path,
    seed: int,
    target_size: tuple[int, int] = (1080, 1920),
) -> tuple[str, str]:
    if getattr(reference_generation, "_REMOTE_CIRCUIT_OPEN", False):
        raise RuntimeError("HF free-image circuit abierto para esta ejecucion; fallback inmediato.")

    subject = subject_prompt(full_prompt)

    if is_noah_prompt(subject):
        chosen = choose_reference_for_prompt(subject, seed)
        noah_prompt = (
            "Use the supplied image only as a visual style and story reference for Noah's Ark. "
            "Create a clearly NEW photorealistic cinematic biblical scene with a different camera position, "
            "background arrangement, animal placement, lighting and composition. Never copy pixels or recreate the source frame. "
            f"Scene request: {subject}. Vertical 9:16, realistic materials and animals, no text, no logo, no watermark."
        )
        try:
            provider = reference_generation._generate_reference_zerogpu(
                chosen, noah_prompt, out, seed, target_size
            )
            return provider.replace("reference:", "story-reference:"), chosen.name
        except Exception as exc:
            _open_circuit(exc)
            if getattr(reference_generation, "_REMOTE_CIRCUIT_OPEN", False):
                raise
            provider = reference_generation._generate_text_zerogpu(
                chosen,
                subject + ", new photoreal cinematic Noah's Ark scene, vertical 9:16, no text, no watermark",
                out,
                seed,
                target_size,
            )
            return provider.replace("style-reference:", "story-style:"), chosen.name

    if is_jesus_prompt(subject):
        chosen = choose_reference_for_prompt(subject, seed)
        previous_choose = reference_generation.choose_reference
        reference_generation.choose_reference = lambda _seed: chosen
        try:
            provider, _ = reference_generation.generate_reference_guided_image(
                full_prompt, out, seed, target_size=target_size
            )
            return provider, chosen.name
        finally:
            reference_generation.choose_reference = previous_choose

    # Pure landscape / symbolic scenes deliberately omit the generic Jesus
    # identity boilerplate so every Short contains truly different cutaways.
    reference = choose_new_jesus_reference(seed)
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
        _open_circuit(exc)
        raise


def _strict_fresh_download(prompt: str, out: Path, seed: int) -> str:
    assert _ORIGINAL_DOWNLOAD is not None
    primary_provider = ""
    primary_error: Exception | None = None
    try:
        primary_provider = _ORIGINAL_DOWNLOAD(prompt, out, seed)
        if not primary_provider.startswith("local_project_jesus_reference"):
            return primary_provider
        print("Referencia local antigua rechazada por la politica de visuales nuevos.")
    except Exception as exc:
        primary_error = exc
        print(f"HF principal no disponible ({exc}); buscando respaldo libre no usado.")

    errors: list[str] = []
    for attempt in range(10):
        retry_seed = int(seed) + attempt * 104729
        try:
            provider = download_fresh_free_image(prompt, out, retry_seed)
            if _provider_was_used(provider):
                errors.append(f"fuente ya usada: {_provider_marker(provider)}")
                print("Respaldo visual ya usado en el canal; buscando otro.")
                continue
            return provider + ":fresh_nonrepeat_fallback"
        except Exception as exc:
            errors.append(str(exc))

    if os.getenv("SPIRITUAL_REQUIRE_FRESH_VISUAL", "true").lower().strip() == "true":
        raise RuntimeError(
            "BLOQUEADO ANTI-REPETICION: no se encontro una imagen realmente nueva. "
            f"HF={primary_provider or primary_error}; respaldos={' | '.join(errors[-5:])}"
        )
    if primary_provider:
        return primary_provider
    raise RuntimeError("No se encontro una imagen visual valida.")


def install_fresh_visual_runtime() -> None:
    global _INSTALLED, _ORIGINAL_DOWNLOAD
    if _INSTALLED:
        return
    _ORIGINAL_DOWNLOAD = spiritual_image._download
    spiritual_image.generate_reference_guided_image = generate_fresh_reference_guided_image
    spiritual_image._download = _strict_fresh_download
    _INSTALLED = True
