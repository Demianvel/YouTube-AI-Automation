#!/usr/bin/env bash
set -euo pipefail

ROOT="${HOME}/YouTube-AI-Automation"
cd "$ROOT" || {
  echo "ERROR: no existe $ROOT"
  exit 1
}

export PYTHONPATH="$ROOT"
export TZ="America/Argentina/Buenos_Aires"

# Carga credenciales locales sin imprimirlas. .env esta ignorado por Git.
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT/.env"
  set +a
fi

# Permite mantener el OAuth de YouTube en un archivo local ignorado por Git.
if [ -z "${YOUTUBE_TOKEN_DIOSHABLAHOYIA:-}" ] && [ -s "$ROOT/.youtube_token_dioshablahoyia.json" ]; then
  export YOUTUBE_TOKEN_DIOSHABLAHOYIA="$(cat "$ROOT/.youtube_token_dioshablahoyia.json")"
fi

if [ -z "${GEMINI_API_KEY:-}" ]; then
  echo "ERROR: falta GEMINI_API_KEY en $ROOT/.env"
  exit 2
fi
if [ -z "${YOUTUBE_TOKEN_DIOSHABLAHOYIA:-}" ]; then
  echo "ERROR: falta YOUTUBE_TOKEN_DIOSHABLAHOYIA en .env o .youtube_token_dioshablahoyia.json"
  exit 2
fi

for cmd in python ffmpeg ffprobe; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: falta $cmd en Termux. Instala dependencias antes de publicar."
    exit 3
  }
done

# Mismos bloqueos de identidad que el publisher canonico de GitHub.
export CHANNEL="dioshablahoyia"
export CONTENT_MODE="voice"
export GEMINI_TEXT_MODEL="${GEMINI_TEXT_MODEL:-gemini-3.6-flash}"
export GEMINI_TTS_MODEL="${GEMINI_TTS_MODEL:-gemini-2.5-flash-preview-tts}"
export GEMINI_TTS_VOICE="Algenib"
export GEMINI_TTS_MAX_ATTEMPTS="${GEMINI_TTS_MAX_ATTEMPTS:-2}"
export SPIRITUAL_MALE_GEMINI_VOICE="Algenib"
export SPIRITUAL_VOICE_PROFILE="voz_de_luz_serena_original_v1"
export SPIRITUAL_VOICE_BRAND="Voz de Luz"
export SPIRITUAL_VOICE_REFERENCE_MODE="fixed_original_identity_no_speaker_clone"
export SPIRITUAL_VOICE_LOCKED="true"
export SPIRITUAL_VOICEOVER_MODE="true"
export SPIRITUAL_LIPSYNC_ENABLED="false"
export SPIRITUAL_REQUIRE_PRIMARY_VOICE="true"
export TTS_PROVIDER="gemini_tts"
export TTS_FALLBACK_KOKORO="false"

export SPIRITUAL_SHORT_SECONDS="60"
export SPIRITUAL_SHORT_SCENE_SECONDS="10"
export SPIRITUAL_SHORT_AI_CLIPS="0"
export SPIRITUAL_ALLOW_STILL_FALLBACK="true"
export SPIRITUAL_FAST_RENDER="true"
export SPIRITUAL_VISUAL_VARIETY_LEVEL="maximum"
export SPIRITUAL_EDITORIAL_VARIETY_LEVEL="high"
export SPIRITUAL_CTA_OVERLAY="false"
export SPIRITUAL_REQUIRE_FRESH_VISUAL="true"
export SPIRITUAL_VISUAL_REFERENCE_LOCKED="true"
export SPIRITUAL_VISUAL_REFERENCE_PROFILE="realistic_jesus_reference_abc_v1"
export SPIRITUAL_ALLOW_SYMBOLIC_JESUS_FALLBACK="false"
export SPIRITUAL_ALLOW_LOCAL_PROCEDURAL_VISUAL="false"

# Evita gastar cuotas HF en el fallback local. publish_dios_locked conserva la
# misma identidad de Jesus mediante transformacion cinematografica de A/B/C.
export GEMINI_VIDEO_ENABLED="false"
export HF_VIDEO_ENABLED="false"
export HF_REFERENCE_IMAGE_ENABLED="false"
export HF_REFERENCE_EDITOR_ENABLED="false"
export HF_TEXT_ZERO_ENABLED="false"
export HF_INFERENCE_PROVIDER_ENABLED="false"
export HF_REMOTE_CIRCUIT_BREAKER="true"
export MUSIC_PROVIDER="local"

# No esperar horas ante cuota temporal: intenta la identidad bloqueada y falla
# de forma explicita antes de cambiar de voz o publicar contenido degradado.
export DIOS_CATCHUP_PUBLISH_ATTEMPTS="${DIOS_CATCHUP_PUBLISH_ATTEMPTS:-1}"
export DIOS_CATCHUP_RETRY_WAIT_SECONDS="${DIOS_CATCHUP_RETRY_WAIT_SECONDS:-0}"

for ref in \
  assets/dioshablahoyia/reference/jesus_reference_a.jpg \
  assets/dioshablahoyia/reference/jesus_reference_b.jpg \
  assets/dioshablahoyia/reference/jesus_reference_c.jpg; do
  test -s "$ref" || {
    echo "ERROR: falta referencia visual $ref"
    exit 4
  }
done

python - <<'PY'
import importlib
mods = [
    'google.genai', 'googleapiclient.discovery', 'google.oauth2.credentials',
    'PIL', 'requests', 'numpy', 'soundfile'
]
missing = []
for name in mods:
    try:
        importlib.import_module(name)
    except Exception:
        missing.append(name)
if missing:
    raise SystemExit(
        'ERROR: faltan modulos Python: ' + ', '.join(missing) +
        '. Instala las dependencias del proyecto antes de publicar.'
    )
print('Dependencias Python OK')
PY

echo "Publicacion LOCAL: completando solamente los Shorts faltantes hasta 10/10..."
python scripts/dioshablahoyia_catchup_shorts.py

echo "OK: catch-up local finalizado. Revisa state/history.jsonl para los video_id confirmados."
