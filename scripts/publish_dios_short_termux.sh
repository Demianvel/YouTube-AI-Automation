#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/YouTube-AI-Automation"
cd "$ROOT" || {
  echo "ERROR: no existe $ROOT"
  exit 1
}

# GitHub-hosted runners pueden quedar bloqueados por cuota/billing en repos privados.
# Este wrapper ya NO despacha Actions: usa el publisher local real.
echo "Modo local directo: no se usaran minutos de GitHub Actions."

TMP_SCRIPT="${TMPDIR:-/tmp}/publish_dios_10_termux_local.sh"
rm -f "$TMP_SCRIPT"

# Trae solamente la version mas reciente del script sin hacer git pull ni tocar
# cambios locales (por ejemplo config/channels.json o presets locales).
if command -v git >/dev/null 2>&1 && git fetch origin main --quiet 2>/dev/null; then
  if git show origin/main:scripts/publish_dios_10_termux_local.sh > "$TMP_SCRIPT" 2>/dev/null && [ -s "$TMP_SCRIPT" ]; then
    chmod +x "$TMP_SCRIPT"
    exec bash "$TMP_SCRIPT"
  fi
fi

# Fallback si no hay red/git: usa la copia local ya instalada.
if [ -s "$ROOT/scripts/publish_dios_10_termux_local.sh" ]; then
  exec bash "$ROOT/scripts/publish_dios_10_termux_local.sh"
fi

echo "ERROR: no pude obtener scripts/publish_dios_10_termux_local.sh."
echo "Ejecuta primero: git fetch origin main"
exit 1
