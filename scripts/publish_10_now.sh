#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO="Demianvel/YouTube-AI-Automation"

command -v gh >/dev/null 2>&1 || { echo "Falta GitHub CLI (gh). Instala con: pkg install gh"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "GitHub CLI no esta autenticado. Ejecuta: gh auth login"; exit 1; }

echo "Lanzando 5 rondas. Cada ronda publica 1 Short + 1 video largo por canal."
echo "Total objetivo: 10 publicaciones por canal (5 Shorts + 5 largos)."

for i in 1 2 3 4 5; do
  echo ""
  echo "===== RONDA $i/5 ====="

  gh workflow run shorts.yml -R "$REPO" --ref main \
    -f channel=brotavida -f content_mode=asmr -f dry_run=false

  gh workflow run shorts.yml -R "$REPO" --ref main \
    -f channel=dineroclaro -f content_mode=voice -f dry_run=false

  gh workflow run shorts.yml -R "$REPO" --ref main \
    -f channel=envikids -f content_mode=voice -f dry_run=false

  gh workflow run long-5min.yml -R "$REPO" --ref main \
    -f channel=both -f publish=true

  if [ $((i % 2)) -eq 0 ]; then
    MINUTES=10
  else
    MINUTES=5
  fi

  gh workflow run envikids-long.yml -R "$REPO" --ref main \
    -f minutes="$MINUTES" -f publish=true

  echo "Ronda $i enviada a GitHub Actions."
  sleep 5
done

echo ""
echo "Todas las rondas fueron enviadas. Los jobs se ejecutan/encolan en GitHub Actions."
echo ""
gh run list -R "$REPO" --limit 40
