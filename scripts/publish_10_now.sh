#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${HOME}/YouTube-AI-Automation"
COUNT="${1:-10}"

cd "$ROOT" || {
  echo "ERROR: no existe $ROOT"
  exit 1
}

if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [ "$COUNT" -lt 1 ] || [ "$COUNT" -gt 10 ]; then
  echo "Uso: bash ./scripts/publish_10_now.sh [1-10]"
  exit 1
fi

echo "Publicador por lotes: SOLO Dios Habla Hoy."
echo "Objetivo de esta ejecucion: $COUNT Short(s)."
echo "EnViKids y DineroClaro no se ejecutan. BrotaVida mantiene su automatizacion separada."

for i in $(seq 1 "$COUNT"); do
  echo ""
  echo "========== DIOS SHORT $i/$COUNT =========="

  while true; do
    set +e
    bash ./scripts/publish_dios_short_termux.sh
    CODE=$?
    set -e

    if [ "$CODE" -eq 0 ]; then
      break
    fi

    if [ "$CODE" -eq 2 ]; then
      echo "Hay otro Short procesandose. Reintentando en 90 segundos..."
      sleep 90
      continue
    fi

    echo "La publicacion $i fallo con codigo $CODE. Se detiene el lote para evitar publicaciones defectuosas."
    exit "$CODE"
  done

done

echo ""
echo "OK: se completaron $COUNT Short(s) de Dios Habla Hoy."
