#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

REPO="Demianvel/YouTube-AI-Automation"
EXPECTED_HANDLE="@dioshablahoyia"
SECRET_NAME="YOUTUBE_TOKEN_DIOSHABLAHOYIA"
TOKEN_FILE="${TMPDIR:-$HOME}/yt-dioshablahoyia-token.json"
DOWNLOAD_DIR="/storage/emulated/0/Download"
REQUIRED_COMMENT_SCOPE="https://www.googleapis.com/auth/youtube.force-ssl"
BACKFILL_VIDEO_ID="${DIOS_BACKFILL_VIDEO_ID:-A4p_vWPLfMI}"

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
  if [ ! -d "$HOME/storage" ]; then
    echo "Solicitando permiso de almacenamiento de Android..."
    termux-setup-storage || true
  fi

  if [ ! -d "$DOWNLOAD_DIR" ]; then
    echo "No encuentro la carpeta $DOWNLOAD_DIR"
    echo "Ejecuta termux-setup-storage, acepta el permiso y vuelve a intentarlo."
    exit 1
  fi

  mapfile -t MATCHES < <(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -iname 'client_secret*.json' -o -iname '*googleusercontent*.json' \) -print 2>/dev/null | sort)

  if [ "${#MATCHES[@]}" -eq 0 ]; then
    echo ""
    echo "No encontre un cliente OAuth de Google en Descargas."
    echo "En Google Cloud:"
    echo "1) Selecciona o crea tu proyecto."
    echo "2) Habilita YouTube Data API v3."
    echo "3) Configura Google Auth Platform / OAuth consent screen."
    echo "4) Crea un OAuth Client ID tipo Desktop app."
    echo "5) Descarga el JSON en la carpeta Descargas del telefono."
    echo "Luego vuelve a ejecutar este mismo script."
    exit 1
  fi

  if [ "${#MATCHES[@]}" -gt 1 ]; then
    echo "Encontre varios clientes OAuth en Descargas:"
    for i in "${!MATCHES[@]}"; do
      printf '%d) %s\n' "$((i+1))" "${MATCHES[$i]}"
    done
    read -r -p "Elegi el numero del cliente OAuth que corresponde a tu proyecto de YouTube: " CHOICE
    IDX=$((CHOICE-1))
    if [ "$IDX" -lt 0 ] || [ "$IDX" -ge "${#MATCHES[@]}" ]; then
      echo "Seleccion invalida."
      exit 1
    fi
    SRC="${MATCHES[$IDX]}"
  else
    SRC="${MATCHES[0]}"
  fi

  cp "$SRC" "$ROOT/client_secret.json"
  chmod 600 "$ROOT/client_secret.json"
  echo "Cliente OAuth copiado de forma privada a $ROOT/client_secret.json"
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
echo "Google mostrara una URL de autorizacion."
echo "Inicia sesion con la cuenta que administra $EXPECTED_HANDLE."
echo "IMPORTANTE: acepta TODOS los permisos de YouTube que aparezcan."
echo "Si esa cuenta administra varios canales o Brand Accounts, selecciona Dios Habla Hoy IA."
echo ""

python "$ROOT/scripts/authorize_channel.py" \
  --client-secrets "$ROOT/client_secret.json" \
  --expected-handle "$EXPECTED_HANDLE" \
  --output "$TOKEN_FILE"

if [ ! -s "$TOKEN_FILE" ]; then
  echo "No se genero un token OAuth valido."
  exit 1
fi

python - "$TOKEN_FILE" "$REQUIRED_COMMENT_SCOPE" <<'PY'
import json
import sys

path, required = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
scopes = set(data.get("scopes") or [])
print("\nScopes OAuth que se guardaran en GitHub:")
for scope in sorted(scopes):
    print(" -", scope)
if required not in scopes:
    raise SystemExit(
        "ERROR: falta youtube.force-ssl. NO se actualizo el secret. "
        "Repite la autorizacion aceptando todos los permisos de YouTube."
    )
print("OK: youtube.force-ssl verificado. Los comentarios superiores pueden publicarse por API.")
PY

chmod 600 "$TOKEN_FILE"
gh secret set "$SECRET_NAME" --repo "$REPO" < "$TOKEN_FILE"
rm -f "$TOKEN_FILE"

echo ""
echo "Secret actualizado. Esperando propagacion en GitHub Actions..."
sleep 6

echo "Verificando canal y scope dentro de GitHub Actions..."
gh workflow run verify-dioshablahoyia-oauth.yml -R "$REPO" --ref main
sleep 5
VERIFY_RUN="$(gh run list -R "$REPO" --workflow verify-dioshablahoyia-oauth.yml --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId')"
if [ -z "$VERIFY_RUN" ] || [ "$VERIFY_RUN" = "null" ]; then
  echo "ERROR: no pude localizar la ejecucion de verificacion OAuth."
  exit 1
fi
echo "OAuth verify run: $VERIFY_RUN"
gh run watch -R "$REPO" "$VERIFY_RUN" --exit-status

echo ""
echo "OAuth confirmado. Reparando el comentario CTA del Short ya publicado $BACKFILL_VIDEO_ID..."
gh workflow run dioshablahoyia-comment.yml \
  -R "$REPO" \
  --ref main \
  -f video_id="$BACKFILL_VIDEO_ID"
sleep 5
COMMENT_RUN="$(gh run list -R "$REPO" --workflow dioshablahoyia-comment.yml --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId')"
if [ -z "$COMMENT_RUN" ] || [ "$COMMENT_RUN" = "null" ]; then
  echo "ERROR: no pude localizar la ejecucion del comentario CTA."
  exit 1
fi
echo "Comment run: $COMMENT_RUN"
gh run watch -R "$REPO" "$COMMENT_RUN" --exit-status

echo ""
echo "Conexion completada."
echo "Canal verificado: $EXPECTED_HANDLE"
echo "Secret GitHub actualizado: $SECRET_NAME"
echo "Scope de comentarios verificado: youtube.force-ssl"
echo "Comentario CTA solicitado para: $BACKFILL_VIDEO_ID"
echo "NOTA: la API oficial permite publicar el comentario superior, pero no fijarlo/pinnearlo automaticamente."
echo "El token OAuth fue guardado cifrado en GitHub Actions y el archivo temporal fue eliminado."
