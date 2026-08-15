from __future__ import annotations

import os

WORKER = {
    "id": "celestial_cinema_engine",
    "name": "Motor Celestial Cinema",
    "role": "motor_grafico_ia",
    "owner": "video_generation",
}


def preferred_video_model() -> str:
    return os.getenv("GEMINI_VIDEO_MODEL", "gemini-omni-flash-preview").strip()


def render_directive(meta: dict, *, vertical: bool = True) -> str:
    topic = " ".join(str(meta.get("topic") or "amor, esperanza y presencia de Dios").split())
    framing = "vertical 9:16" if vertical else "horizontal 16:9"
    return (
        f"{WORKER['name']} owns the render. Create premium photorealistic live-action cinema in {framing}. "
        f"Theme: {topic}. Keep one stable recurring synthetic Jesus character across shots. "
        "Use physically plausible golden-hour lighting, realistic skin, hair and woven cloth, cinematic depth, "
        "natural environmental motion, accurate anatomy and expressive but restrained body acting. "
        "No cartoon, illustration, videogame look, plastic CGI skin, frozen stills, captions, logos or watermarks."
    )


def mark_render_metadata(meta: dict, *, format_name: str) -> dict:
    meta["worker_render_engine"] = WORKER["name"]
    meta["worker_render_engine_id"] = WORKER["id"]
    meta["worker_render_model"] = preferred_video_model()
    meta["worker_render_format"] = format_name
    meta["render_worker_separation"] = True
    return meta
