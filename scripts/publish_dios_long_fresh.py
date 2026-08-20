from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from app import spiritual_long_pipeline as base
from app.spiritual_long_fresh_visual import download_fresh_long_visual
from app.spiritual_long_resilient_runner import run
from app.spiritual_long_visual_variety import apply_long_visual_diversity
from app.spiritual_visual_motion import render_still_motion

ROOT = Path(__file__).resolve().parents[1]
LONG_HISTORY = ROOT / "state" / "dioshablahoyia_long_history.jsonl"
VOICE_LOCK_VERSION = "voz-de-luz-algenib-v3-natural-fixed"


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return max(0.0, float(result.stdout.strip() or 0.0))


def _natural_long_voice_fit(path: Path, target_seconds: float) -> None:
    """Never slow Voz de Luz to fill a long-form timeline."""
    target = float(target_seconds)
    if target <= 1 or not path.exists():
        return
    current = _probe_duration(path)
    if current <= 1:
        raise RuntimeError("VOICE_CADENCE_LOCK: narracion larga vacia o invalida.")

    coverage = current / target
    if coverage < 0.90:
        raise RuntimeError(
            f"VOICE_CADENCE_LOCK: la narracion ocupa solo {coverage:.1%} del video. "
            "Se debe regenerar con mas texto; no se ralentizara Voz de Luz."
        )

    if current <= target * 1.005:
        return

    tempo = current / (target * 0.995)
    if tempo > 1.055:
        raise RuntimeError(
            f"VOICE_CADENCE_LOCK: la narracion excede demasiado la duracion ({current:.1f}s/{target:.1f}s). "
            "Se debe ajustar el guion, no cambiar perceptiblemente la voz."
        )

    temp = path.with_name(path.stem + ".natural-long-fit.wav")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
        "-af", f"atempo={tempo:.7f}", "-ar", "48000", "-ac", "1", str(temp),
    ], check=True)
    if not temp.exists() or temp.stat().st_size < 1000:
        raise RuntimeError("VOICE_CADENCE_LOCK: no se pudo aplicar el ajuste minimo de voz larga.")
    temp.replace(path)


def _extract_visual_fingerprints(providers: list[str]) -> tuple[list[str], list[str]]:
    sha_values: list[str] = []
    dhash_values: list[str] = []
    for provider in providers:
        text = str(provider or "")
        sha_match = re.search(r"image_sha256=([0-9a-f]{64})", text, flags=re.IGNORECASE)
        dhash_match = re.search(r"image_dhash=([0-9a-f]{64})", text, flags=re.IGNORECASE)
        if sha_match and sha_match.group(1).lower() not in sha_values:
            sha_values.append(sha_match.group(1).lower())
        if dhash_match and dhash_match.group(1).lower() not in dhash_values:
            dhash_values.append(dhash_match.group(1).lower())
    return sha_values, dhash_values


def _enrich_last_history(result: dict) -> None:
    if not LONG_HISTORY.exists():
        return
    raw_lines = LONG_HISTORY.read_text(encoding="utf-8").splitlines()
    if not raw_lines:
        return
    try:
        last = json.loads(raw_lines[-1])
    except Exception:
        return

    providers = [str(item) for item in (result.get("visual_providers") or [])]
    sha_values, dhash_values = _extract_visual_fingerprints(providers)
    last["visual_providers"] = providers
    last["visual_asset_sha256"] = sha_values
    last["visual_asset_dhash"] = dhash_values
    last["visual_freshness_verified"] = bool(sha_values or providers)
    last["visual_fingerprint_mode"] = "sha256_plus_256bit_dhash_plus_semantic_motion_v3"
    last["voice_identity_locked"] = True
    last["voice_profile"] = "voz_de_luz_serena_original_v1"
    last["voice_expected_provider"] = "Gemini TTS/Algenib"
    last["voice_lock_version"] = VOICE_LOCK_VERSION
    last["voice_cadence_locked"] = True
    last["voice_slow_stretch_forbidden"] = True
    last["long_visual_diversity_version"] = "2026.08.20-semantic-motion-v3"
    raw_lines[-1] = json.dumps(last, ensure_ascii=False)
    LONG_HISTORY.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")


def _fresh_long_motion(source: Path, out: Path, duration: int, index: int) -> None:
    label = render_still_motion(
        source,
        out,
        duration,
        index,
        width=1920,
        height=1080,
        fps=30,
        preset="medium",
        crf=19,
        salt="dios-long-v3",
    )
    print(f"Movimiento cinematografico largo seccion {index + 1}: {label}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[10, 15, 25, 30])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()

    original_download = base._download_image
    original_fit = base.fit_voice_to_duration
    original_generate = base._generate_metadata
    original_motion = base._image_motion

    def _diverse_metadata(channel: dict, minutes: int) -> dict:
        return apply_long_visual_diversity(original_generate(channel, minutes))

    base._download_image = download_fresh_long_visual
    base.fit_voice_to_duration = _natural_long_voice_fit
    base._generate_metadata = _diverse_metadata
    base._image_motion = _fresh_long_motion
    try:
        result = run(args.minutes, publish=args.publish)
        _enrich_last_history(result)
    finally:
        base._download_image = original_download
        base.fit_voice_to_duration = original_fit
        base._generate_metadata = original_generate
        base._image_motion = original_motion
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
