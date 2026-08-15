#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"
ROUNDS="${ROUNDS:-1}"
DELAY="${DELAY:-15}"

if ! command -v gh >/dev/null 2>&1; then
  echo "Falta GitHub CLI. Instala con: pkg install gh -y"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Primero inicia sesion con: gh auth login"
  exit 1
fi

echo "Publicador manual: SOLO canales activos"
echo "- BrotaVida"
echo "- Dios Habla Hoy"
echo "Dinero Claro y EnViKids estan desactivados."
echo "Rondas: $ROUNDS"

for i in $(seq 1 "$ROUNDS"); do
  echo ""
  echo "===== RONDA $i/$ROUNDS ====="

  echo "[Short] BrotaVida"
  gh workflow run shorts.yml -R "$REPO" --ref main \
    -f channel=brotavida \
    -f content_mode=asmr \
    -f dry_run=false
  sleep "$DELAY"

  echo "[Short] Dios Habla Hoy"
  gh workflow run shorts.yml -R "$REPO" --ref main \
    -f channel=dioshablahoyia \
    -f content_mode=voice \
    -f dry_run=false

  if [ "$i" -lt "$ROUNDS" ]; then
    sleep "$DELAY"
  fi
done

echo ""
echo "Solicitudes enviadas a GitHub Actions."
echo "Ver estado con: gh run list -R $REPO --workflow shorts.yml --limit 30"
