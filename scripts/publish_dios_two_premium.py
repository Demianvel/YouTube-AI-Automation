from __future__ import annotations

import os

from app import pipeline, spiritual_image
from app.spiritual_visual_motion import render_still_motion
import scripts.publish_dios_locked as locked


def _premium_animate(source, out, duration: int, index: int) -> None:
    """Higher-quality motion render for manual premium Shorts.

    Keep the existing cinematic motion engine but use a per-Short salt plus
    smoother 30 fps and a higher-quality H.264 encode. This prevents two manual
    premium Shorts from reusing the same camera-motion sequence.
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
        salt=f"dios-premium-v5|{short_salt}",
    )
    print(f"Movimiento premium escena {index + 1}: {label}", flush=True)


def main() -> dict:
    locked.configure_locked_publisher()
    # Override only animation quality. Voice and realistic Jesus identity stay
    # under the permanent locks installed by configure_locked_publisher().
    spiritual_image._animate = _premium_animate
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
    return result


if __name__ == "__main__":
    main()
