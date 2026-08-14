#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"
MODE="${1:-short}"
MINUTES="${2:-10}"

if ! command -v gh >/dev/null 2>&1; then
  echo "Falta GitHub CLI. Instala con: pkg install gh"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Autoriza GitHub primero: gh auth login --hostname github.com --git-protocol https --web"
  exit 1
fi

case "$MODE" in
  short)
    gh workflow run shorts.yml \
      -R "$REPO" \
      --ref main \
      -f channel=dioshablahoyia \
      -f content_mode=voice \
      -f dry_run=false
    echo "Short de Dios Habla Hoy IA enviado a GitHub Actions para generacion y publicacion."
    ;;
  long)
    case "$MINUTES" in
      10|20|30|40) ;;
      *) echo "Duracion invalida. Usa 10, 20, 30 o 40."; exit 1 ;;
    esac
    gh workflow run dioshablahoyia-long.yml \
      -R "$REPO" \
      --ref main \
      -f minutes="$MINUTES" \
      -f publish=true
    echo "Video largo de ${MINUTES} minutos enviado a GitHub Actions para generacion y publicacion."
    ;;
  status)
    gh run list -R "$REPO" --limit 20
    ;;
  *)
    echo "Uso:"
    echo "  $0 short"
    echo "  $0 long 10"
    echo "  $0 long 20"
    echo "  $0 long 30"
    echo "  $0 long 40"
    echo "  $0 status"
    exit 1
    ;;
esac
