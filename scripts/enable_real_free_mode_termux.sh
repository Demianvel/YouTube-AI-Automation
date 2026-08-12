#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"
ROOT="$HOME/YouTube-AI-Automation"

pkg update -y >/dev/null
pkg install -y git gh curl >/dev/null

if [ ! -d "$ROOT/.git" ]; then
  cd "$HOME"
  git clone "https://github.com/$REPO.git" YouTube-AI-Automation
fi

cd "$ROOT"
git pull --ff-only

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub necesita autorizar este Termux una sola vez."
  gh auth login --hostname github.com --git-protocol https --web
fi

echo
echo "Abriremos Pexels para obtener una API key gratuita."
echo "Inicia sesion/crea tu cuenta y solicita la API key. No la envies por chat."
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "https://www.pexels.com/api/" || true
else
  echo "Abri en Chrome: https://www.pexels.com/api/"
fi

echo
read -r -s -p "Pega aqui tu PEXELS API KEY (no se mostrara): " PEXELS_KEY
echo

if [ -z "$PEXELS_KEY" ]; then
  echo "No se ingreso ninguna clave."
  exit 1
fi

# Validate without printing the secret.
HTTP_CODE="$(curl -sS -o /tmp/pexels_check.json -w '%{http_code}' \
  -H "Authorization: $PEXELS_KEY" \
  "https://api.pexels.com/v1/videos/search?query=plant%20growth&per_page=1")"

if [ "$HTTP_CODE" != "200" ]; then
  echo "La clave Pexels no fue aceptada (HTTP $HTTP_CODE). No se guardo nada."
  unset PEXELS_KEY
  rm -f /tmp/pexels_check.json
  exit 1
fi
rm -f /tmp/pexels_check.json

printf '%s' "$PEXELS_KEY" | gh secret set PEXELS_API_KEY --repo "$REPO"
unset PEXELS_KEY

gh variable set ENABLE_FREE_AUTO --body true --repo "$REPO"
gh variable set ENABLE_PREMIUM_AUTO --body false --repo "$REPO" 2>/dev/null || true

echo
echo "OK: PEXELS_API_KEY guardada en GitHub Secrets."
echo "OK: modo automatico gratuito habilitado como fallback de GitHub."

N8N_VALUE="$(gh variable get N8N_PRIMARY --repo "$REPO" 2>/dev/null || true)"
if [ "$N8N_VALUE" = "true" ]; then
  echo "N8N_PRIMARY=true: n8n seguira controlando los horarios; GitHub no duplicara el schedule."
else
  echo "N8N_PRIMARY no esta activo: GitHub usara los horarios internos del workflow."
fi

echo
echo "Lanzando pruebas SIN publicar para comprobar Pexels + audio..."
gh workflow run shorts.yml --repo "$REPO" -f channel=brotavida -f dry_run=true
sleep 3
gh workflow run shorts.yml --repo "$REPO" -f channel=dineroclaro -f dry_run=true

echo
echo "Pruebas enviadas. Mira el estado con:"
echo "gh run list --repo $REPO --workflow shorts.yml --limit 5"
