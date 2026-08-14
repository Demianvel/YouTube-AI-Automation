#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

REPO="Demianvel/YouTube-AI-Automation"
EXPECTED_HANDLE="@dioshablahoyia"
SECRET_NAME="YOUTUBE_TOKEN_DIOSHABLAHOYIA"
TOKEN_FILE="${TMPDIR:-$HOME}/yt-dioshablahoyia-token.json"

cleanup() {
  rm -f "$TOKEN_FILE"
}
trap cleanup EXIT

if ! command -v gh >/dev/null 2>&1; then
  echo "Instalando GitHub CLI..."
  pkg install -y gh
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "Primero autoriza GitHub desde el navegador."
  gh auth login --hostname github.com --git-protocol https --web
fi

if [ ! -f "$ROOT/client_secret.json" ]; then
  echo ""
  echo "Falta $ROOT/client_secret.json"
  echo "En Google Cloud habilita YouTube Data API v3, crea un OAuth Client ID tipo Desktop app"
  echo "y descarga el JSON. Guardalo en Descargas y ejecuta:"
  echo "  bash scripts/setup_oauth_termux.sh"
  echo "Luego vuelve a ejecutar este script."
  exit 1
fi

if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

python -c 'from google_auth_oauthlib.flow import InstalledAppFlow; from googleapiclient.discovery import build' >/dev/null 2>&1 || {
  echo "Instalando librerias OAuth de Google..."
  python -m pip install --upgrade google-auth google-auth-oauthlib google-api-python-client
}

rm -f "$TOKEN_FILE"

echo ""
echo "=== Autorizar Dios Habla Hoy IA ==="
echo "Google abrira el flujo OAuth. Inicia sesion con la cuenta que administra $EXPECTED_HANDLE."
echo "Si Google muestra varios canales/perfiles, selecciona Dios Habla Hoy IA."
echo ""

python "$ROOT/scripts/authorize_channel.py" \
  --client-secrets "$ROOT/client_secret.json" \
  --expected-handle "$EXPECTED_HANDLE" \
  --output "$TOKEN_FILE"

if [ ! -s "$TOKEN_FILE" ]; then
  echo "No se genero un token OAuth valido."
  exit 1
fi

chmod 600 "$TOKEN_FILE"
gh secret set "$SECRET_NAME" --repo "$REPO" < "$TOKEN_FILE"
rm -f "$TOKEN_FILE"

echo ""
echo "Conexion completada."
echo "Canal esperado: $EXPECTED_HANDLE"
echo "Secret GitHub: $SECRET_NAME"
echo "El token se guardo cifrado en GitHub Actions y el archivo temporal fue eliminado."
echo ""
echo "Verificacion de presencia del secret:"
gh secret list --repo "$REPO" | grep -F "$SECRET_NAME" || true
