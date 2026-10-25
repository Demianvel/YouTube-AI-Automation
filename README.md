# Dios Habla Hoy IA — YouTube Automation

Repositorio dedicado exclusivamente a **Dios Habla Hoy IA** (`@dioshablahoyia`), Shorts cristianos en español (es-419).

## ⚠️ Antes que nada: GitHub Actions está bloqueado

Hoy **todas las ejecuciones de Actions fallan en segundos a nivel de cuenta** (límite de minutos / gasto de un repositorio privado). Ningún workflow puede publicar hasta destrabarlo. Opciones:

1. **Hacer el repositorio público** (Actions en runners estándar es gratis para repos públicos). Revisá antes que no haya secretos en archivos: todos deben estar en *Secrets*.
2. **Billing**: en `Settings > Billing and plans` subir el límite de gasto de Actions o agregar un método de pago / comprar minutos.
3. **Runner self-hosted** (por ejemplo una PC o VPS propia): registrarlo en `Settings > Actions > Runners` y cambiar `runs-on: ubuntu-latest` por `runs-on: self-hosted` en `dios-orchestrator.yml`.

## Arquitectura (octubre 2026)

```
dios-orchestrator.yml  (único publicador programado, 10 slots/día)
  └─ scripts/dios_orchestrator.py            plan: slots vencidos vs Shorts confirmados hoy
       └─ scripts/dioshablahoyia_catchup_shorts_hybrid.py   publica lo que falta (máx. 2 por ejecución)
            └─ scripts/publish_dios_hybrid.py               publicador probado
                 ├─ app/pipeline.py                         guion → SEO → anti-spam → render → subida
                 ├─ app/dios_brain/                         "Cerebro": agentes editoriales
                 ├─ app/spiritual_tts.py                    Voz de Luz (Gemini TTS) + respaldo Qwen3-TTS local
                 ├─ app/spiritual_image.py / render_quality.py   escenas + encode 1080x1920
                 └─ app/youtube.py                          subida, miniatura, divulgación de contenido sintético
```

Un Short **solo cuenta cuando tiene `video_id` real** de YouTube. El historial vive en `state/history.jsonl` y se guarda con el ciclo `git fetch / reset / append / push` (5 reintentos) para no pisar otras ejecuciones.

### Orquestador: 10 Shorts 24/7

`.github/workflows/dios-orchestrator.yml` — "Dios Habla Hoy IA - Orquestador 10 Shorts 24/7".

- **10 slots diarios (hora Argentina, UTC-3)**: 07:30, 09:00, 10:30, 12:00, 13:30, 15:00, 16:30, 18:00, 19:30 y 21:00. Los crons corren 7 minutos después de cada slot (en UTC) para evitar la congestión del minuto 0.
- Cada ejecución cuenta los Shorts confirmados hoy y los compara con los slots ya vencidos; publica lo que falta, **máximo 2 por ejecución** y nunca más de 10 por día.
- Si ya está al día, termina en segundos sin instalar nada (ahorra minutos).
- `concurrency` compartida con el publicador de emergencia: nunca hay dos publicadores en paralelo.
- Timeout de 60 minutos (el paso de publicación se corta a los 48 para alcanzar a guardar el historial).
- Ejecución manual: `Actions > Orquestador > Run workflow`, input `count` (0 = automático según slots).

**Todos los demás workflows de publicación quedaron sin `schedule:`** (siguen disponibles a mano con `workflow_dispatch`). Programados que se mantienen: respuestas a comentarios (cada 3 h), playlist (diaria), analytics / radar / growth semanales y el planificador visual diario (no publican).

### Cerebro: `app/dios_brain/`

| Agente | Qué hace |
|---|---|
| `strategist.py` (estratega) | Elige el pilar (paz, amor, esperanza, oración, promesas, enseñanzas de Jesús) y el tema bíblico, evitando pilares, referencias y temas recientes; usa `state/growth/*.json` si existe. |
| `writer.py` (redactor/SEO) | Gancho en los primeros 2 segundos, guion con oraciones completas dentro del presupuesto de palabras, título ≤ 70 caracteres con la palabra clave al inicio, descripción (2 primeras líneas = gancho + palabra clave), 5 hashtags con `#Shorts` y etiquetas. |
| `cta.py` (rotador de CTA) | CTA suave y variado, hablado al cierre y en la descripción ("Escribí Amén si lo recibís", "Guardalo para cuando lo necesites", "Compartilo con alguien que lo necesite", "Suscribite para tu mensaje diario"…). |
| `editor.py` (editor de calidad) | Rechaza guiones/metadatos repetidos, demasiado largos, engañosos o contra políticas de YouTube: hablar como si fuera literalmente Dios, promesas médicas o de dinero, profecías con fecha, "compartí o mala suerte". Mantiene la divulgación de contenido sintético. |
| `analyst.py` (analista) | Guarda en el historial pilar, gancho, plantilla de título y CTA usados; con datos suficientes (vistas/hora, likes, comentarios) prefiere las variantes ganadoras (bandit UCB1). Sin datos, rota. |

El cerebro se engancha después de toda la cadena SEO existente y antes del control anti-spam. **Ante cualquier error vuelve al comportamiento anterior** (`DIOS_BRAIN_ENABLED=false` lo desactiva). Validación offline: `PYTHONPATH=. python scripts/validate_dios_brain.py`.

## Voz: "Voz de Luz"

- Narrador único del canal, cálido, suave, sereno y pausado. **Es un narrador que reflexiona sobre la Biblia; nunca se presenta como la voz literal de Dios** (la descripción lo aclara).
- Gemini TTS, voz **Algieba** (masculina suave) por defecto, configurable con `DIOS_TTS_VOICE`; respaldo de voz en `DIOS_TTS_VOICE_FALLBACKS` (por defecto **Schedar**). Se reemplazó Algenib porque su timbre es áspero.
- Modelos: `gemini-3.8-flash-tts` (GA) y respaldo `gemini-3.1-flash-tts-preview` (`GEMINI_TTS_MODEL`, `GEMINI_TTS_MODEL_FALLBACKS`).
- Ritmo lento: `DIOS_NARRATION_WPM=110` (≈100–110 palabras por Short de 60 s). `DIOS_MIN_VOICE_COVERAGE=0.84` permite que la voz termine unos segundos antes y la música cierre el Short, sin estirar la voz.
- Si Gemini se queda sin cuota, el respaldo local **Qwen3-TTS** (Hugging Face) narra ese Short. Kokoro sigue deshabilitado.

## Calidad de video

- 1080x1920 vertical, 30 fps, x264 CRF 18 preset `medium`, AAC 192 kbps / 48 kHz (`app/render_quality.py`).
- `DIOS_RENDER_4K=true` existe como interruptor (2160x3840) pero **está apagado** en el orquestador: las imágenes base son 1080x1920 y el render 4K costaría mucho más tiempo de CPU sin ganancia real.

## Visuales nuevos y antirrepetición

Hugging Face es la ruta visual principal gratuita (`FLUX.1-Kontext-Dev` guiado por el banco de referencias y `FLUX.1-schnell`), con miniatura OpenAI `gpt-image-2` cuando hay clave. El motor rota Jesús, escenas bíblicas, Biblia, Noruega, aurora boreal, fiordos, montañas, ríos y Arca de Noé, y bloquea repeticiones recientes con hashes de prompts e imágenes.

## Secrets

En `Settings > Secrets and variables > Actions`:

- `GEMINI_API_KEY`
- `HF_TOKEN`
- `YOUTUBE_TOKEN_DIOSHABLAHOYIA`
- `OPENAI_API_KEY` (opcional, miniaturas)

Nunca guardar claves o tokens dentro del repositorio.

## Otros workflows (manuales)

- `dioshablahoyia-algenib-emergency.yml` — publicador de emergencia (mismo camino, ahora con Voz de Luz/Algieba).
- `dioshablahoyia-shorts-5min.yml`, `dioshablahoyia-catchup-shorts.yml`, `shorts.yml`, `dioshablahoyia-long.yml` y similares — solo `workflow_dispatch` / archivos trigger.
- `dioshablahoyia-comment-responder.yml` — respuestas automáticas en español (cada 3 h).
- `dioshablahoyia-playlist-sync.yml` — playlist automática (diaria).
- `analytics-monitor.yml`, `dioshablahoyia-growth-engine.yml`, `dioshablahoyia-market-monitor.yml` — análisis semanal.

## Seguridad editorial

- Contenido cristiano reverente sobre Biblia, Dios, Jesús, fe, oración, esperanza y reflexión.
- Las representaciones de Jesús son sintéticas y no imitan a actores o personas identificables; el video se marca como contenido sintético.
- Sin promesas médicas ni económicas, sin profecías con fecha y sin cebos de interacción.
- El historial evita repetir guiones, temas, ganchos, CTA y composiciones visuales recientes.
