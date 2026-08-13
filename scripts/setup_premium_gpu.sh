#!/usr/bin/env bash
set -euo pipefail

ROOT="${AI_MODELS_ROOT:-$HOME/ai-models}"
LTX_ROOT="$ROOT/LTX-2"
ACE_ROOT="$ROOT/ACE-Step-1.5"
LTX_MODEL_DIR="$ROOT/models/ltx-2.3"
GEMMA_DIR="$ROOT/models/gemma-3-12b"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: este setup premium requiere una GPU NVIDIA/CUDA visible por nvidia-smi." >&2
  exit 1
fi

mkdir -p "$ROOT" "$ROOT/models"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v hf >/dev/null 2>&1; then
  python3 -m pip install --user -U huggingface_hub
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ ! -d "$LTX_ROOT/.git" ]; then
  git clone https://github.com/Lightricks/LTX-2.git "$LTX_ROOT"
else
  git -C "$LTX_ROOT" pull --ff-only
fi
(
  cd "$LTX_ROOT"
  uv sync --frozen
)

mkdir -p "$LTX_MODEL_DIR"
HF_ARGS=()
if [ -n "${HF_TOKEN:-}" ]; then
  HF_ARGS+=(--token "$HF_TOKEN")
fi

# Official LTX-2.3 distilled checkpoint and required spatial upscaler.
hf download Lightricks/LTX-2.3 \
  ltx-2.3-22b-distilled-1.1.safetensors \
  ltx-2.3-spatial-upscaler-x2-1.1.safetensors \
  --local-dir "$LTX_MODEL_DIR" "${HF_ARGS[@]}"

# Official Gemma encoder used by the current LTX-2 monolithic pipeline.
# This repository can require accepting Google's model terms in Hugging Face first.
hf download google/gemma-3-12b-it-qat-q4_0-unquantized \
  --local-dir "$GEMMA_DIR" "${HF_ARGS[@]}"

if [ ! -d "$ACE_ROOT/.git" ]; then
  git clone https://github.com/ace-step/ACE-Step-1.5.git "$ACE_ROOT"
else
  git -C "$ACE_ROOT" pull --ff-only
fi
(
  cd "$ACE_ROOT"
  uv sync
)

cat <<EOF

✅ Premium GPU stack preparado.

Usa estas variables en el runner:
export LTX2_ENABLED=true
export LTX2_REPO_ROOT="$LTX_ROOT"
export LTX2_CHECKPOINT="$LTX_MODEL_DIR/ltx-2.3-22b-distilled-1.1.safetensors"
export LTX2_SPATIAL_UPSAMPLER="$LTX_MODEL_DIR/ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
export LTX2_GEMMA_ROOT="$GEMMA_DIR"
export LTX2_OFFLOAD=cpu
export LTX2_ENHANCE_PROMPT=true

ACE-Step instalado en:
$ACE_ROOT

Para iniciar su API local:
cd "$ACE_ROOT"
uv run acestep-api --host 127.0.0.1 --port 8001

Luego:
export ACESTEP_API_URL=http://127.0.0.1:8001

EOF
