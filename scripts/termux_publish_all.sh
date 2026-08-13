#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"
ROUNDS="${ROUNDS:-4}"
DELAY="${DELAY:-12}"

if ! command -v gh >/dev/null 2>&1; then
  echo "Falta GitHub CLI. Instala con: pkg install gh -y"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Primero inicia sesion con: gh auth login"
  exit 1
fi

echo "Publicador multicanal"
echo "Canales: BrotaVida, Dinero Claro, EnViKids"
echo "DemianVelo: EXCLUIDO"
echo "Rondas: $ROUNDS"

for i in $(seq 1 "$ROUNDS"); do
  echo ""
  echo "===== RONDA $i/$ROUNDS ====="

  echo "[Short] BrotaVida"
  gh workflow run shorts.yml -R "$REPO" \
    -f channel=brotavida \
    -f content_mode=auto \
    -f dry_run=false
  sleep "$DELAY"

  echo "[Short] Dinero Claro"
  gh workflow run shorts.yml -R "$REPO" \
    -f channel=dineroclaro \
    -f content_mode=voice \
    -f dry_run=false
  sleep "$DELAY"

  echo "[Short] EnViKids"
  gh workflow run shorts.yml -R "$REPO" \
    -f channel=envikids \
    -f content_mode=voice \
    -f dry_run=false
  sleep "$DELAY"

  echo "[Largo] BrotaVida + Dinero Claro"
  gh workflow run long-5min.yml -R "$REPO" \
    -f channel=both \
    -f publish=true
  sleep "$DELAY"

  if [ $((i % 2)) -eq 0 ]; then
    MINUTES=10
  else
    MINUTES=5
  fi

  echo "[Largo] EnViKids ${MINUTES} min"
  gh workflow run envikids-long.yml -R "$REPO" \
    -f minutes="$MINUTES" \
    -f publish=true

  if [ "$i" -lt "$ROUNDS" ]; then
    sleep "$DELAY"
  fi
done

echo ""
echo "Solicitudes enviadas a GitHub Actions."
echo "Objetivo por ROUNDS=4:"
echo "- BrotaVida: 4 Shorts + 4 largos"
echo "- Dinero Claro: 4 Shorts + 4 largos"
echo "- EnViKids: 4 Shorts + 4 largos"
echo "- DemianVelo: 0 publicaciones"
echo ""
echo "Ver estado:"
echo "gh run list -R $REPO --limit 30"
