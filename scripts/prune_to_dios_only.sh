#!/usr/bin/env bash
set -euo pipefail

# Remove projects/assets/workflows that do not belong to Dios Habla Hoy.
git rm -r -f --ignore-unmatch assets/aqui-estas assets/dios-actua presets/demianvelo config/presets n8n
git rm -f --ignore-unmatch requirements-chatterbox.txt state/kickoff-both.txt state/latest_demianvelo_upload.json

git rm -f --ignore-unmatch \
  .github/workflows/aleluya4-finish.yml \
  .github/workflows/aleluya4-publish.yml \
  .github/workflows/aqui-estas-cinematic-release.yml \
  .github/workflows/brotavida-watchdog.yml \
  .github/workflows/demianvelo-aleluya-premium.yml \
  .github/workflows/demianvelo-aqui-estas-wan22.yml \
  .github/workflows/demianvelo-music.yml \
  .github/workflows/dios-actua-noruega-release.yml \
  .github/workflows/finalize-aqui-estas-existing-audio.yml \
  .github/workflows/publish-aqui-estas-organic-master.yml \
  .github/workflows/release-aleluya-wan22.yml \
  .github/workflows/render-aleluya-zero.yml \
  .github/workflows/render-aleluya-zero-v2.yml \
  .github/workflows/render-aleluya-zero-v3.yml \
  .github/workflows/render-aleluya-zero-v4.yml \
  .github/workflows/render-aqui-estas-chain45-free.yml \
  .github/workflows/render-aqui-estas-demianvelo.yml \
  .github/workflows/render-aqui-estas-parallel-free.yml \
  .github/workflows/render-aqui-estas-xl-chain-free.yml \
  .github/workflows/update-aqui-estas-thumbnail.yml \
  .github/workflows/validate-chatterbox.yml \
  .github/workflows/validate.yml \
  .github/workflows/hf-zero-ace-probe.yml \
  .github/workflows/premium-gpu.yml

# Remove scripts from the retired channels/music projects. Shared modules stay until
# dependency scans prove they are unused by Dios Habla Hoy.
git rm -f --ignore-unmatch \
  scripts/aqui_estas* \
  scripts/*aleluya* \
  scripts/brotavida* \
  scripts/*demianvelo* \
  scripts/dios_actua* \
  scripts/connect_all_youtube_termux.sh

# Old trigger markers for retired projects.
git rm -f --ignore-unmatch \
  triggers/.keep-hallelujah \
  triggers/hallelujah* \
  triggers/aqui-estas* \
  triggers/aqui_estas* \
  triggers/dios-actua* \
  triggers/dios_actua*

# Keep only Dios Habla Hoy records in the shared Shorts history.
python - <<'PY'
import json
from pathlib import Path
p = Path('state/history.jsonl')
if p.exists():
    kept = []
    for raw in p.read_text(encoding='utf-8').splitlines():
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if row.get('channel') == 'dioshablahoyia':
            kept.append(raw)
    p.write_text(''.join(line + '\n' for line in kept), encoding='utf-8')
PY

git add -A

echo "Repository pruned to Dios Habla Hoy-specific projects plus required shared runtime modules."
