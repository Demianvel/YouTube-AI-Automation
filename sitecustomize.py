"""Repository-wide runtime helpers loaded automatically by Python's site module.

If GitHub Actions exposes HF_TOKEN, inject it into Gradio Client calls that do not
already specify a token. This lets existing ZeroGPU Space integrations use the
authenticated Hugging Face quota without ever printing or committing the token.
"""
from __future__ import annotations

import os


def _patch_gradio_client() -> None:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        return
    try:
        import gradio_client
    except Exception:
        return

    original = gradio_client.Client.__init__
    if getattr(original, "_hf_token_injected", False):
        return

    def wrapped(self, *args, **kwargs):
        if not kwargs.get("token") and not kwargs.get("hf_token"):
            kwargs["token"] = token
        return original(self, *args, **kwargs)

    wrapped._hf_token_injected = True  # type: ignore[attr-defined]
    gradio_client.Client.__init__ = wrapped


_patch_gradio_client()
