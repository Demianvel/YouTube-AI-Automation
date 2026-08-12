#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

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

# Busca primero nombres típicos de clientes OAuth descargados desde Google Cloud.
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
  read -r -p "Elegí el número del archivo correcto: " CHOICE
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
echo "OAuth client copiado de forma segura a: $ROOT/client_secret.json"

if [ -d "$ROOT/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
else
  echo "No encontré .venv; usando el Python actual."
fi

python "$ROOT/scripts/authorize_channel.py" --client-secrets "$ROOT/client_secret.json"
