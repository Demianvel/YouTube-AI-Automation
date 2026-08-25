from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download

VOICE_REPO = "rhasspy/piper-voices"
VOICE_ONNX = "es/es_MX/ald/medium/es_MX-ald-medium.onnx"
VOICE_JSON = "es/es_MX/ald/medium/es_MX-ald-medium.onnx.json"


def bootstrap_voice(model_root: Path) -> dict:
    voice_dir = model_root / "voice"
    cache_dir = model_root / ".bootstrap_voice"
    voice_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    onnx_src = Path(hf_hub_download(repo_id=VOICE_REPO, filename=VOICE_ONNX, local_dir=str(cache_dir)))
    json_src = Path(hf_hub_download(repo_id=VOICE_REPO, filename=VOICE_JSON, local_dir=str(cache_dir)))

    voice_onnx = voice_dir / "voz_de_luz_local.onnx"
    voice_json = voice_dir / "voz_de_luz_local.onnx.json"
    shutil.copy2(onnx_src, voice_onnx)
    shutil.copy2(json_src, voice_json)

    manifest = {
        "engine": "dhh-sovereign-v1",
        "voice_base": {
            "repo": VOICE_REPO,
            "files": [VOICE_ONNX, VOICE_JSON],
            "path": str(voice_dir),
            "profile_name": "Voz de Luz Local",
            "exact_algenib": False,
            "note": "Voz neural local independiente para el modo sin cuotas de inferencia; no etiquetar como Algenib.",
        },
        "inference_after_bootstrap": "offline_local_only",
        "remote_inference_credits_required": False,
    }
    (model_root / "VOICE_BOOTSTRAP_SOURCES.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-root", required=True)
    args = parser.parse_args()
    print(json.dumps(bootstrap_voice(Path(args.model_root)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
