#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"
EXPECTED_HANDLE="@dioshablahoyia"
TOKEN_FILE="$ROOT/.youtube_token_dioshablahoyia.json"
SECRET_NAME="YOUTUBE_TOKEN_DIOSHABLAHOYIA"
REPO="Demianvel/YouTube-AI-Automation"

if [ ! -d "$HOME/storage" ]; then
  echo "Solicitando acceso al almacenamiento de Android..."
  termux-setup-storage || true
fi

DOWNLOAD_DIR="/storage/emulated/0/Download"
if [ ! -d "$DOWNLOAD_DIR" ]; then
  echo "No encuentro la carpeta $DOWNLOAD_DIR"
  echo "Ejecuta termux-setup-storage y acepta el permiso de archivos."
  exit 1
fi

mapfile -t MATCHES < <(find "$DOWNLOAD_DIR" -maxdepth 1 -type f \( -iname 'client_secret*.json' -o -iname '*googleusercontent*.json' \) -print 2>/dev/null | sort)

if [ "${#MATCHES[@]}" -eq 0 ]; then
  echo "No encontré un archivo OAuth de Google en Descargas."
  echo "Descarga desde Google Cloud el cliente OAuth tipo Desktop app y vuelve a ejecutar este script."
  exit 1
fi

if [ "${#MATCHES[@]}" -gt 1 ]; then
  echo "Encontré varios archivos OAuth:"
  for i in "${!MATCHES[@]}"; do
    printf '%d) %s\n' "$((i+1))" "${MATCHES[$i]}"
  done
  read -r -p "Elegí el número del cliente OAuth correspondiente a Dios Habla Hoy: " CHOICE
  IDX=$((CHOICE-1))
  if [ "$IDX" -lt 0 ] || [ "$IDX" -ge "${#MATCHES[@]}" ]; then
    echo "Selección inválida."
    exit 1
  fi
  SRC="${MATCHES[$IDX]}"
else
  SRC="${MATCHES[0]}"
fi

cp "$SRC" "$ROOT/client_secret.json"
chmod 600 "$ROOT/client_secret.json"
echo "OAuth client preparado localmente."

deactivate 2>/dev/null || true

if ! python -c 'import cryptography' >/dev/null 2>&1; then
  echo "Reparando Python/cryptography de Termux..."
  pkg update -y
  pkg install -y python python-pip python-cryptography
fi

if [ -d "$ROOT/.venv" ]; then
  if ! "$ROOT/.venv/bin/python" -c 'import cryptography' >/dev/null 2>&1; then
    echo "Recreando .venv incompatible..."
    rm -rf "$ROOT/.venv"
  fi
fi

if [ ! -d "$ROOT/.venv" ]; then
  python -m venv --system-site-packages "$ROOT/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
if ! python -c 'import cryptography' >/dev/null 2>&1; then
  python -m pip uninstall -y cryptography >/dev/null 2>&1 || true
fi

python -m pip install -q --upgrade pip setuptools wheel
python -m pip install -q --upgrade google-auth google-auth-oauthlib google-api-python-client

rm -f "$TOKEN_FILE"
echo "Abrí en el navegador el enlace que aparecerá y autorizá únicamente el canal $EXPECTED_HANDLE."
python "$ROOT/scripts/authorize_channel.py" \
  --client-secrets "$ROOT/client_secret.json" \
  --expected-handle "$EXPECTED_HANDLE" \
  --output "$TOKEN_FILE"
chmod 600 "$TOKEN_FILE"

# Validación local final antes de reemplazar el Secret remoto.
YOUTUBE_TOKEN_DIOSHABLAHOYIA="$(cat "$TOKEN_FILE")" python - <<'PY'
import json, os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
info = json.loads(os.environ["YOUTUBE_TOKEN_DIOSHABLAHOYIA"])
creds = Credentials.from_authorized_user_info(info, scopes=info.get("scopes"))
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
items = yt.channels().list(part="id,snippet", mine=True).execute().get("items", [])
if not items:
    raise SystemExit("El token nuevo no identifica ningún canal.")
actual = str(items[0].get("snippet", {}).get("customUrl") or "").lower().lstrip("/")
if actual != "@dioshablahoyia":
    raise SystemExit(f"Canal incorrecto: {actual}")
print("Token OAuth nuevo validado para @dioshablahoyia.")
PY

UPDATED=false
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh secret set "$SECRET_NAME" --repo "$REPO" < "$TOKEN_FILE"
  UPDATED=true
  echo "Secret $SECRET_NAME actualizado de forma segura en GitHub."
else
  echo "GitHub CLI no está autenticado; no se imprimirá el token por seguridad."
  echo "Autenticá GitHub CLI y ejecutá:"
  echo "  gh auth login"
  echo "  gh secret set $SECRET_NAME --repo $REPO < '$TOKEN_FILE'"
fi

if [ "$UPDATED" = true ]; then
  # El monitor horario detectará el faltante. Además, disparar recovery ahora.
  git pull --rebase origin main
  mkdir -p triggers
  printf '%s\n' "$(date -Iseconds) | OAuth renovado; ejecutar HF-credit recovery para completar solo faltantes." > triggers/dioshablahoyia-hf-credit-recovery.txt
  git add triggers/dioshablahoyia-hf-credit-recovery.txt
  git commit -m "chore: resume Dios publishing after OAuth renewal" || true
  git push origin main || true
  echo "Recuperación solicitada. Se conservarán Voz de Luz/Algenib y referencias realistas bloqueadas."
fi

echo "Por seguridad, elimina el token local cuando confirmes que GitHub lo recibió: rm -f '$TOKEN_FILE' '$ROOT/client_secret.json'"
