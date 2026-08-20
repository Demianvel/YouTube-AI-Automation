from __future__ import annotations

from pathlib import Path

from app import pipeline, spiritual_image
from app.spiritual_free_media import download_fresh_free_image
import scripts.publish_dios_fast as fast


def _local_first_download(prompt: str, out: Path, seed: int) -> str:
    """Emergency zero-HF path: fresh local variants first, then unused free media."""
    local_errors: list[str] = []
    for attempt in range(36):
        retry_seed = int(seed) + attempt * 104729
        try:
            provider = spiritual_image._local_reference(out, retry_seed)
            accepted = fast._accept_local_variant(provider)
            if accepted:
                return accepted
            local_errors.append(f"variante ya usada: {provider}")
        except Exception as exc:
            local_errors.append(str(exc))

    free_errors: list[str] = []
    for attempt in range(12):
        retry_seed = int(seed) + 4_000_003 + attempt * 104729
        try:
            provider = download_fresh_free_image(prompt, out, retry_seed)
            if fast._source_was_used(provider):
                free_errors.append(f"fuente ya usada: {fast._remote_source_marker(provider)}")
                continue
            return provider + ":fresh_nonrepeat_emergency_fallback"
        except Exception as exc:
            free_errors.append(str(exc))

    raise RuntimeError(
        "EMERGENCY_FRESH_VISUAL_EXHAUSTED: no se encontro variante local o fuente libre inedita. "
        f"local={' | '.join(local_errors[-5:])}; free={' | '.join(free_errors[-5:])}"
    )


# publish_dios_fast already installs metadata, voice and animation patches on import.
# Override only the image download path so this emergency route never spends HF quota.
spiritual_image._download = _local_first_download


if __name__ == "__main__":
    result = pipeline.run("dioshablahoyia", dry_run=False, content_mode="voice")
    print(result)
