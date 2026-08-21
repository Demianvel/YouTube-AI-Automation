#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_ROOT="${DHH_MODEL_ROOT:-/opt/dhh-models/dios_sovereign}"

command -v python >/dev/null || { echo "Falta python" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "Falta ffmpeg" >&2; exit 1; }

python -m pip install --upgrade pip
python -m pip install -r "$ROOT/requirements-sovereign.txt"

mkdir -p \
  "$MODEL_ROOT/image/base" \
  "$MODEL_ROOT/image/lora" \
  "$MODEL_ROOT/voice" \
  "$MODEL_ROOT/training/jesus_identity"

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "GPU detectada:"
  nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
else
  echo "Sin NVIDIA: se podrá usar el fallback cinematográfico de referencias, pero entrenar/generar difusión profesional será lento o no estará disponible."
fi

if command -v piper >/dev/null 2>&1; then
  echo "Piper OK: $(command -v piper)"
else
  echo "Piper no quedó disponible en PATH; revisá la instalación de piper-tts."
fi

echo "Runner soberano preparado. Modelo persistente: $MODEL_ROOT"
echo "Siguiente paso: ejecutar scripts/dios_sovereign_bootstrap_weights.py una sola vez."
