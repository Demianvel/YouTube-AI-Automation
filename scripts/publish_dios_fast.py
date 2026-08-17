from __future__ import annotations

from app import pipeline
from app.generator_resilient import _local_metadata


def _fast_local_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    del retries
    metadata = _local_metadata(channel, previous)
    metadata["metadata_provider"] = str(metadata.get("metadata_provider") or "local") + ":fast_voice_quota_reserved"
    print("Modo rapido: metadata local para reservar la cuota Gemini exclusivamente para Voz de Luz/Algenib.")
    return metadata


pipeline.generate_metadata = _fast_local_metadata

if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
