from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download


DEFAULT_IMAGE_REPO = "stabilityai/stable-diffusion-xl-base-1.0"
DEFAULT_VOICE_REPO = "rhasspy/piper-voices"
DEFAULT_VOICE_ONNX = "es/es_MX/ald/medium/es_MX-ald-medium.onnx"
DEFAULT_VOICE_JSON = "es/es_MX/ald/medium/es_MX-ald-medium.onnx.json"


def bootstrap(model_root: Path, image_repo: str, force: bool) -> dict:
    base_dir = model_root / "image" / "base"
    lora_dir = model_root / "image" / "lora"
    voice_dir = model_root / "voice"
    lora_dir.mkdir(parents=True, exist_ok=True)
    voice_dir.mkdir(parents=True, exist_ok=True)

    if force and base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    snapshot_download(
        repo_id=image_repo,
        local_dir=str(base_dir),
        allow_patterns=[
            "model_index.json",
            "scheduler/**",
            "text_encoder/**",
            "text_encoder_2/**",
            "tokenizer/**",
            "tokenizer_2/**",
            "unet/**",
            "vae/**",
        ],
    )

    voice_cache = model_root / ".bootstrap_voice"
    voice_cache.mkdir(parents=True, exist_ok=True)
    onnx_src = Path(
        hf_hub_download(
            repo_id=DEFAULT_VOICE_REPO,
            filename=DEFAULT_VOICE_ONNX,
            local_dir=str(voice_cache),
        )
    )
    json_src = Path(
        hf_hub_download(
            repo_id=DEFAULT_VOICE_REPO,
            filename=DEFAULT_VOICE_JSON,
            local_dir=str(voice_cache),
        )
    )
    voice_onnx = voice_dir / "voz_de_luz_local.onnx"
    voice_json = voice_dir / "voz_de_luz_local.onnx.json"
    shutil.copy2(onnx_src, voice_onnx)
    shutil.copy2(json_src, voice_json)

    manifest = {
        "engine": "dhh-sovereign-v1",
        "image_base": {
            "repo": image_repo,
            "path": str(base_dir),
            "license": "OpenRAIL++ (verify upstream model card before redistribution)",
        },
        "voice_base": {
            "repo": DEFAULT_VOICE_REPO,
            "files": [DEFAULT_VOICE_ONNX, DEFAULT_VOICE_JSON],
            "path": str(voice_dir),
            "profile_name": "Voz de Luz Local",
            "exact_algenib": False,
            "note": "Independent local Spanish neural voice; do not label as Algenib.",
        },
        "inference_after_bootstrap": "offline_local_only",
        "remote_inference_credits_required": False,
    }
    (model_root / "BOOTSTRAP_SOURCES.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", required=True)
    parser.add_argument("--image-repo", default=DEFAULT_IMAGE_REPO)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = bootstrap(Path(args.model_root), args.image_repo, args.force)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
