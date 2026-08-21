from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app import pipeline, spiritual_audio, spiritual_image, spiritual_tts, youtube as youtube_module
from app import spiritual_reference_generation as reference_generation
import scripts.publish_dios_fast as fast


VOICE_PROVIDER = "gemini_tts"
VOICE_NAME = "Algenib"
VOICE_BRAND = "Voz de Luz"
VOICE_PROFILE = "voz_de_luz_serena_original_v1"
VISUAL_LOCK_VERSION = "dios-realistic-reference-lock-v1"
REFERENCE_DIR = Path(__file__).resolve().parents[1] / "assets" / "dioshablahoyia" / "reference"
REFERENCE_NAMES = (
    "jesus_reference_a.jpg",
    "jesus_reference_b.jpg",
    "jesus_reference_c.jpg",
)


def _assert_permanent_voice_environment() -> None:
    provider = os.getenv("TTS_PROVIDER", "").strip().lower()
    requested = os.getenv("GEMINI_TTS_VOICE", "").strip()
    brand = os.getenv("SPIRITUAL_VOICE_BRAND", "").strip()
    profile = os.getenv("SPIRITUAL_VOICE_PROFILE", "").strip()
    locked = os.getenv("SPIRITUAL_VOICE_LOCKED", "").strip().lower()
    require_primary = os.getenv("SPIRITUAL_REQUIRE_PRIMARY_VOICE", "").strip().lower()
    kokoro = os.getenv("TTS_FALLBACK_KOKORO", "").strip().lower()

    errors: list[str] = []
    if provider != VOICE_PROVIDER:
        errors.append(f"TTS_PROVIDER={provider or 'vacio'}")
    if requested.lower() != VOICE_NAME.lower():
        errors.append(f"GEMINI_TTS_VOICE={requested or 'vacio'}")
    if brand != VOICE_BRAND:
        errors.append(f"SPIRITUAL_VOICE_BRAND={brand or 'vacio'}")
    if profile != VOICE_PROFILE:
        errors.append(f"SPIRITUAL_VOICE_PROFILE={profile or 'vacio'}")
    if locked != "true":
        errors.append(f"SPIRITUAL_VOICE_LOCKED={locked or 'vacio'}")
    if require_primary != "true":
        errors.append(f"SPIRITUAL_REQUIRE_PRIMARY_VOICE={require_primary or 'vacio'}")
    if kokoro != "false":
        errors.append(f"TTS_FALLBACK_KOKORO={kokoro or 'vacio'}")

    if errors:
        raise RuntimeError(
            "VOICE_IDENTITY_LOCK: configuracion incompatible con Voz de Luz / Algenib: "
            + ", ".join(errors)
        )


def _reference_bank() -> list[Path]:
    refs = [REFERENCE_DIR / name for name in REFERENCE_NAMES]
    missing = [str(path) for path in refs if not path.exists()]
    if missing:
        raise RuntimeError(
            "VISUAL_IDENTITY_LOCK: faltan referencias realistas historicas de Jesus: "
            + ", ".join(missing)
        )
    return refs


def _locked_choose_reference(seed: int) -> Path:
    refs = _reference_bank()
    safe = int(seed) & 0x7FFFFFFF
    return refs[(safe // 31) % len(refs)]


def _strict_algenib_voice(path: Path, text: str) -> str:
    """Generate only the permanent Voz de Luz / Algenib identity.

    There is deliberately no local/Kokoro/espeak fallback here. If Gemini TTS is
    unavailable, publication stops instead of changing the narrator.
    """
    _assert_permanent_voice_environment()
    used = spiritual_tts._gemini_spiritual_voice(path, text)
    low = str(used or "").lower()
    if "gemini" not in low or ":algenib:" not in low or "fallback" in low or "kokoro" in low:
        raise RuntimeError(f"VOICE_IDENTITY_LOCK: proveedor inesperado: {used}")
    spiritual_tts._brand_master(path)
    return used


def _local_reference_cinematic_variant(out: Path, seed: int) -> tuple[str, str]:
    """Create a high-quality 9:16 scene directly from the locked Jesus bank.

    This is not procedural art and it does not invent another face. It preserves
    the historical reference pixels and only applies cinematic framing, depth,
    mild grade and deterministic composition so publishing can continue when a
    remote reference editor has no quota.
    """
    reference = _locked_choose_reference(seed)
    reference_name = reference.name
    safe = int(seed) & 0x7FFFFFFF
    target = (1080, 1920)
    out.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(reference) as opened:
        src = ImageOps.exif_transpose(opened).convert("RGB")
        src_ratio = src.width / max(1, src.height)
        target_ratio = target[0] / target[1]

        # Full-bleed whenever the source is already close to portrait. Otherwise
        # preserve the complete person over a softly defocused version of the
        # very same reference, avoiding destructive face/body crops.
        if abs(src_ratio - target_ratio) <= 0.10:
            cx = 0.47 + ((safe % 7) - 3) * 0.008
            cy = 0.47 + (((safe // 7) % 7) - 3) * 0.006
            frame = ImageOps.fit(
                src,
                target,
                method=Image.Resampling.LANCZOS,
                centering=(max(0.40, min(0.60, cx)), max(0.40, min(0.58, cy))),
            )
        else:
            bg = ImageOps.fit(
                src,
                target,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.46),
            )
            bg = bg.filter(ImageFilter.GaussianBlur(radius=30))
            bg = ImageEnhance.Brightness(bg).enhance(0.74)
            bg = ImageEnhance.Contrast(bg).enhance(1.05)

            fg = src.copy()
            fg.thumbnail((1010, 1810), Image.Resampling.LANCZOS)
            zoom = 1.0 + (safe % 5) * 0.008
            if zoom > 1.0:
                fg = fg.resize(
                    (max(1, int(fg.width * zoom)), max(1, int(fg.height * zoom))),
                    Image.Resampling.LANCZOS,
                )
            offset_x = ((safe // 11) % 25) - 12
            offset_y = ((safe // 17) % 31) - 15
            x = (target[0] - fg.width) // 2 + offset_x
            y = (target[1] - fg.height) // 2 + offset_y
            mask = Image.new("L", fg.size, 255).filter(ImageFilter.GaussianBlur(radius=7))
            frame = bg.copy()
            frame.paste(fg, (x, y), mask)

        # Restrained grade only; facial structure and identity remain untouched.
        brightness = 0.99 + (safe % 4) * 0.008
        contrast = 1.025 + ((safe // 5) % 4) * 0.008
        color = 1.005 + ((safe // 19) % 4) * 0.006
        frame = ImageEnhance.Brightness(frame).enhance(brightness)
        frame = ImageEnhance.Contrast(frame).enhance(contrast)
        frame = ImageEnhance.Color(frame).enhance(color)
        frame = ImageEnhance.Sharpness(frame).enhance(1.06)
        frame.save(out, format="JPEG", quality=96, subsampling=0, optimize=True)

    if not out.exists() or out.stat().st_size < 25_000:
        raise RuntimeError("VISUAL_IDENTITY_LOCK: la variante cinematografica local quedo invalida.")

    provider = (
        "Local reference-guided image / direct cinematic reference transform / "
        f"reference:{reference_name}"
    )
    return provider, reference_name


def _locked_reference_download(prompt: str, out: Path, seed: int) -> str:
    """Create every scene from the historical Jesus reference identity.

    Prefer remote reference editing when available. If its quota is unavailable,
    use a direct cinematic transform of the same locked reference bank. Never use
    stock portraits, symbolic-only substitutes, text-only generation, or local
    procedural art that invents another identity.
    """
    _reference_bank()
    full_prompt = (
        f"{prompt}, {spiritual_image._style()}, "
        "preserve the same recurring realistic Jesus identity from the supplied reference bank, "
        "live-action photographic realism, natural human skin and fabric, reverent cinematic scene"
    )

    try:
        provider, reference_name = reference_generation.generate_reference_guided_image(
            full_prompt,
            out,
            seed,
            target_size=(1080, 1920),
        )
    except Exception as exc:
        print(
            "Referencia remota no disponible; usando transformacion cinematografica directa "
            f"del banco Jesus bloqueado. Motivo: {exc}"
        )
        provider, reference_name = _local_reference_cinematic_variant(out, seed)

    if reference_name not in REFERENCE_NAMES:
        raise RuntimeError(
            f"VISUAL_IDENTITY_LOCK: referencia inesperada: {reference_name or 'vacia'}"
        )

    low = str(provider or "").lower()
    if "style-reference:" in low or "text-to-image" in low:
        raise RuntimeError(
            "VISUAL_IDENTITY_LOCK: se rechazo un fallback text-only porque puede perder la identidad visual de Jesus."
        )
    if (
        "reference editor" not in low
        and "reference-guided image" not in low
        and "direct cinematic reference transform" not in low
    ):
        raise RuntimeError(
            f"VISUAL_IDENTITY_LOCK: proveedor no guiado por referencia: {provider}"
        )
    if f"reference:{reference_name}" not in str(provider):
        raise RuntimeError(
            f"VISUAL_IDENTITY_LOCK: el proveedor no acredito la referencia {reference_name}: {provider}"
        )

    print(
        f"{VISUAL_LOCK_VERSION}: escena realista guiada por {reference_name}; "
        "sin fallback simbolico, procedural ni voz alternativa."
    )
    return f"{provider}:{VISUAL_LOCK_VERSION}"


_ORIGINAL_VISUAL_GUARD = youtube_module._enforce_spiritual_visual_guard


def _locked_visual_upload_guard(channel: dict, metadata: dict) -> None:
    if youtube_module._is_spiritual_channel(channel):
        labels = metadata.get("generated_visual_provider") or metadata.get("visual_providers") or []
        if isinstance(labels, str):
            labels = [labels]
        labels = [str(item) for item in labels]
        if not labels:
            raise RuntimeError("VISUAL_IDENTITY_LOCK: no hay trazabilidad visual antes de YouTube.")
        for label in labels:
            if VISUAL_LOCK_VERSION not in label:
                raise RuntimeError(
                    f"VISUAL_IDENTITY_LOCK: escena fuera del motor de referencias historicas: {label}"
                )
            if not any(f"reference:{name}" in label for name in REFERENCE_NAMES):
                raise RuntimeError(
                    f"VISUAL_IDENTITY_LOCK: escena sin referencia Jesus autorizada: {label}"
                )
        metadata["visual_identity_locked"] = True
        metadata["visual_identity_profile"] = "realistic_jesus_reference_abc_v1"
        metadata["visual_identity_reference_bank"] = list(REFERENCE_NAMES)
        metadata["visual_symbolic_fallback_allowed"] = False
        metadata["visual_local_procedural_fallback_allowed"] = False

    _ORIGINAL_VISUAL_GUARD(channel, metadata)


def configure_locked_publisher() -> None:
    _assert_permanent_voice_environment()
    _reference_bank()

    # Keep the successful local metadata/SEO and cinematic movement from the
    # earlier publisher, but hard-lock both narrator and visual identity.
    pipeline.generate_metadata = fast._fast_local_metadata
    pipeline.attach_visual_pack = fast.attach_visual_pack_v3
    spiritual_image._download = _locked_reference_download
    spiritual_image._animate = fast._fast_animate
    spiritual_audio.make_spiritual_spanish_voice = _strict_algenib_voice
    spiritual_tts.make_spiritual_spanish_voice = _strict_algenib_voice
    reference_generation.choose_reference = _locked_choose_reference
    youtube_module._enforce_spiritual_visual_guard = _locked_visual_upload_guard


def main() -> dict:
    configure_locked_publisher()
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
