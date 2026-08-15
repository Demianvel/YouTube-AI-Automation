#!/usr/bin/env bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"
ROOT="${HOME}/YouTube-AI-Automation"

cd "$ROOT" || {
  echo "ERROR: no existe $ROOT"
  exit 1
}

echo "Actualizando main..."
git pull --ff-only

command -v gh >/dev/null 2>&1 || {
  echo "ERROR: falta GitHub CLI (gh)."
  exit 1
}

gh auth status >/dev/null

ACTIVE="$(gh run list \
  -R "$REPO" \
  --workflow shorts.yml \
  --limit 30 \
  --json status \
  --jq '[.[] | select(.status == "queued" or .status == "in_progress")] | length')"

if [ "$ACTIVE" -gt 0 ]; then
  echo "Hay $ACTIVE run(s) de Shorts en cola o ejecucion. No lanzo otro para evitar duplicados/spam."
  gh run list -R "$REPO" --workflow shorts.yml --limit 8
  exit 2
fi

BEFORE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Solicitando UN Short original para @dioshablahoyia ($BEFORE)..."

gh workflow run shorts.yml \
  -R "$REPO" \
  --ref main \
  -f channel=dioshablahoyia \
  -f content_mode=voice \
  -f dry_run=false

sleep 6
RUN_ID="$(gh run list \
  -R "$REPO" \
  --workflow shorts.yml \
  --event workflow_dispatch \
  --limit 1 \
  --json databaseId \
  --jq '.[0].databaseId')"

if [ -z "$RUN_ID" ] || [ "$RUN_ID" = "null" ]; then
  echo "ERROR: no pude resolver el nuevo run."
  exit 1
fi

echo "Run: $RUN_ID"
echo "El pipeline aplica: rotacion tematica + historial + gate anti-repeticion + voz continua + control de calidad + upload."

gh run watch -R "$REPO" "$RUN_ID" --exit-status

echo
echo "Resultado final:"
gh run view -R "$REPO" "$RUN_ID"
