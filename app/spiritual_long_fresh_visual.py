from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .spiritual_free_media import download_fresh_free_image
from .spiritual_reference_generation import generate_reference_guided_image

LONG_SIZE = (1920, 1080)


def download_fresh_long_visual(prompt: str, out: Path, seed: int) -> str:
    """Generate a fresh 16:9 visual; never reuse the old local Jesus still bank."""
    errors: list[str] = []
    try:
        provider, _ = generate_reference_guided_image(
            prompt,
            out,
            seed,
            target_size=LONG_SIZE,
        )
        if out.exists() and out.stat().st_size >= 20_000:
            return provider
        errors.append("Hugging Face devolvio archivo invalido")
    except Exception as exc:
        errors.append(f"Hugging Face: {exc}")

    temporary = out.with_name(out.stem + "_fresh_source.jpg")
    try:
        provider = download_fresh_free_image(prompt, temporary, seed)
        with Image.open(temporary) as source:
            source.load()
            image = ImageOps.fit(
                source.convert("RGB"),
                LONG_SIZE,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            image.save(out, format="JPEG", quality=95, optimize=True)
        if not out.exists() or out.stat().st_size < 20_000:
            raise RuntimeError("El respaldo libre no produjo una imagen horizontal valida")
        return provider + ":fresh_long_16x9"
    except Exception as exc:
        errors.append(f"fresh-free: {exc}")
    finally:
        temporary.unlink(missing_ok=True)

    raise RuntimeError(
        "No existe un visual NUEVO disponible para este segmento; se rechaza reutilizar una imagen antigua. "
        + "; ".join(errors)
    )
