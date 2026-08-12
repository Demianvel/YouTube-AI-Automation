#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
REPO="Demianvel/YouTube-AI-Automation"

if [ ! -f client_secret.json ]; then
  echo "No encuentro client_secret.json. Ejecutando buscador de OAuth..."
  bash scripts/setup_oauth_termux.sh || true
fi

if [ ! -f client_secret.json ]; then
  echo "Falta client_secret.json en $ROOT"
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "Instalando GitHub CLI..."
  pkg install -y gh
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Vas a autorizar GitHub una sola vez desde el navegador."
  gh auth login --hostname github.com --git-protocol https --web
fi

if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

TMP_BROTA="${TMPDIR:-$HOME}/yt-brotavida-token.json"
TMP_DINERO="${TMPDIR:-$HOME}/yt-dineroclaro-token.json"
trap 'rm -f "$TMP_BROTA" "$TMP_DINERO"' EXIT

rm -f "$TMP_BROTA" "$TMP_DINERO"

echo
echo "=== 1/2 Autorizar BrotaVida AI ==="
python scripts/authorize_channel.py \
  --client-secrets client_secret.json \
  --expected-handle @BrotaVidaAI \
  --output "$TMP_BROTA"

gh secret set YOUTUBE_TOKEN_BROTAVIDA --repo "$REPO" < "$TMP_BROTA"
rm -f "$TMP_BROTA"
echo "YOUTUBE_TOKEN_BROTAVIDA guardado en GitHub."

echo
echo "=== 2/2 Autorizar Dinero Claro AI ==="
python scripts/authorize_channel.py \
  --client-secrets client_secret.json \
  --expected-handle @DineroClaroAi \
  --output "$TMP_DINERO"

gh secret set YOUTUBE_TOKEN_DINEROCLARO --repo "$REPO" < "$TMP_DINERO"
rm -f "$TMP_DINERO"
echo "YOUTUBE_TOKEN_DINEROCLARO guardado en GitHub."

echo
echo "Los dos canales quedaron vinculados. Disparando una publicación real de prueba para cada canal..."
gh workflow run shorts.yml --repo "$REPO" -f channel=brotavida -f dry_run=false
gh workflow run shorts.yml --repo "$REPO" -f channel=dineroclaro -f dry_run=false

echo
echo "Listo. GitHub Actions recibió las dos ejecuciones de publicación."
