from __future__ import annotations

# Compatibility entry point used by the normal Shorts pipeline. The actual
# selector is v2: a large combinatorial scene/camera/light/atmosphere engine
# with a 100-publication anti-repeat window.
from .spiritual_runtime_fresh import install_fresh_visual_runtime
from .visual_variety_v2 import attach_visual_pack_v2

# Install the strict HF-first / no-old-local-image runtime as soon as the
# spiritual visual selector is imported. Other channel renderers do not use
# app.spiritual_image, so this does not change EnViKids/DineroClaro/BrotaVida.
install_fresh_visual_runtime()


def attach_visual_pack(metadata: dict, previous: list[dict], content_type: str = "short") -> dict:
    return attach_visual_pack_v2(metadata, previous, content_type=content_type)
