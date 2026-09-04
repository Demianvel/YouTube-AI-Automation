from __future__ import annotations

import os

from app import pipeline, spiritual_image
from app.spiritual_visual_motion import render_still_motion
import scripts.publish_dios_hybrid as hybrid


def _premium_animate(source, out, duration: int, index: int) -> None:
    """Higher-quality motion render for manual premium Shorts.

    The manual two-Short publisher now shares the canonical hybrid publisher,
    so voice identity, premium visual guards, automatic unique thumbnails and
    YouTube thumbnail verification are identical to the daily recovery path.
    Only the animation quality is overridden here.
    """
    short_salt = os.getenv("SPIRITUAL_MOTION_SALT", "manual-premium").strip() or "manual-premium"
    label = render_still_motion(
        source,
        out,
        duration,
        index,
        width=1080,
        height=1920,
        fps=30,
        preset="medium",
        crf=17,
        salt=f"dios-premium-v6|{short_salt}",
    )
    print(f"Movimiento premium escena {index + 1}: {label}", flush=True)


def main() -> dict:
    hybrid.configure_hybrid_publisher()
    # Override only animation quality. The canonical hybrid publisher keeps
    # Algenib/Voz de Luz, locked synthetic biblical visuals, thumbnail
    # generation/deduplication and verified YouTube thumbnails.
    spiritual_image._animate = _premium_animate
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
