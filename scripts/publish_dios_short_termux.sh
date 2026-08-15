#!/usr/bin/env bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"
ROOT="${HOME}/YouTube-AI-Automation"

cd "$ROOT" || {
  echo "ERROR: no existe $ROOT"
  exit 1
}

command -v gh >/dev/null 2>&1 || {
  echo "ERROR: falta GitHub CLI. Instala con: pkg install gh"
  exit 1
}

gh auth status >/dev/null 2>&1 || {
  echo "ERROR: GitHub CLI no esta autenticado. Ejecuta: gh auth login"
  exit 1
}

# IMPORTANTE: no hacemos git pull. El workflow se ejecuta directamente desde
# main remoto, por lo que tus cambios locales en config/channels.json no pueden
# bloquear ni ser sobreescritos.
echo "Preparando publicacion desde main remoto (sin tocar config local)..."
git fetch origin main --quiet 2>/dev/null || true
REMOTE_SHA="$(git rev-parse --short origin/main 2>/dev/null || echo remoto)"
echo "main remoto: $REMOTE_SHA"

ACTIVE="$(gh run list -R "$REPO" --workflow shorts.yml --limit 30 --json status --jq '[.[] | select(.status == "queued" or .status == "in_progress" or .status == "waiting" or .status == "pending")] | length')"
if [ "$ACTIVE" -gt 0 ]; then
  echo "Hay $ACTIVE ejecucion(es) de Shorts activas. Espera a que terminen para no duplicar contenido."
  exit 2
fi

BEFORE="$(gh run list -R "$REPO" --workflow shorts.yml --limit 1 --json databaseId --jq '.[0].databaseId // 0')"

echo "Lanzando un Short de Dios Habla Hoy con subida real..."
gh workflow run shorts.yml -R "$REPO" --ref main \
  -f channel=dioshablahoyia \
  -f content_mode=voice \
  -f dry_run=false

RUN_ID=""
for attempt in $(seq 1 15); do
  sleep 4
  RUN_ID="$(gh run list -R "$REPO" --workflow shorts.yml --limit 10 --json databaseId,event,status --jq --argjson before "$BEFORE" '[.[] | select(.event == "workflow_dispatch" and .databaseId != $before)][0].databaseId // empty')"
  if [ -n "$RUN_ID" ]; then
    break
  fi
done

if [ -z "$RUN_ID" ]; then
  echo "ERROR: GitHub acepto el dispatch pero no pude identificar la ejecucion nueva."
  echo "Revisa con: gh run list -R $REPO --workflow shorts.yml --limit 10"
  exit 1
fi

echo "Run ID: $RUN_ID"
echo "Esperando generacion y subida..."
gh run watch "$RUN_ID" -R "$REPO" --exit-status

echo "OK: la ejecucion termino correctamente."
gh run view "$RUN_ID" -R "$REPO" --json conclusion,url --jq '"Estado: \(.conclusion)\nURL: \(.url)"'
