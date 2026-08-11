# YouTube AI Automation

Automatización para dos canales de YouTube Shorts:

- **BrotaVida AI** — https://www.youtube.com/@BrotaVidaAI
- **Dinero Claro AI** — https://www.youtube.com/@DineroClaroAi

## Qué hace

1. Gemini genera un concepto, hook, título, descripción SEO, hashtags, tags y escenas.
2. El sistema compara el concepto con el historial reciente y vuelve a generar si es demasiado parecido.
3. El renderer gratuito local crea el Short vertical 9:16 usando Pillow + FFmpeg; para DineroClaro también genera visuales educativos y narración local con eSpeak. Para BrotaVida anima el crecimiento progresivo de una planta con variaciones determinísticas.
4. YouTube Data API lo sube al canal correcto con su OAuth independiente.
5. Se guarda el historial para evitar duplicados futuros.
6. Si un workflow falla, GitHub Actions abre un issue de alerta.
7. n8n puede usarse como orquestador externo de horarios y control.

## Frecuencia inicial

Se empieza con **4 Shorts diarios por canal (8 al día en total)**, no con publicación masiva. Los horarios están escalonados en hora Argentina.

## Secrets obligatorios

En GitHub: `Settings > Secrets and variables > Actions > New repository secret`.

- `GEMINI_API_KEY`
- `YOUTUBE_TOKEN_BROTAVIDA`
- `YOUTUBE_TOKEN_DINEROCLARO`

Nunca subas esos valores como archivos al repositorio.

## Autorización de YouTube (una sola vez por canal)

1. En Google Cloud habilita **YouTube Data API v3**.
2. Crea un OAuth Client de tipo Desktop y descarga el JSON como `client_secret.json`.
3. Instala dependencias: `pip install -r requirements.txt`.
4. Ejecuta: `python scripts/authorize_channel.py --client-secrets client_secret.json`.
5. Abre la URL que muestra el script, inicia sesión y selecciona el canal correcto.
6. El script muestra el canal autorizado para verificar que no se mezclen cuentas.
7. Copia el JSON final como `YOUTUBE_TOKEN_BROTAVIDA` o `YOUTUBE_TOKEN_DINEROCLARO`.
8. Repite el consentimiento para el segundo canal.

## Gemini / video

El pipeline usa `gemini-3.6-flash` para estrategia, SEO y variedad de contenido. El renderer predeterminado es `VIDEO_PROVIDER=procedural`, por lo que la generación visual no llama a Veo ni consume una API de video paga. Veo 3.1 permanece como proveedor opcional si en el futuro se configura `VIDEO_PROVIDER=veo`.

El renderer gratuito sirve para automatización y pruebas, pero su calidad visual es de animación generada por código, no equivalente a un modelo generativo cinematográfico.

## n8n

Se agregó un workflow importable en:

`n8n/workflows/youtube-ai-orchestrator.json`

Y la guía en:

`n8n/README.md`

El workflow se importa desactivado y dispara GitHub Actions mediante un token de alcance mínimo. Si n8n pasa a ser el programador principal, crea la Repository Variable `N8N_PRIMARY=true`; el schedule interno de GitHub se desactiva automáticamente para evitar duplicados.

## Prueba segura

En la pestaña **Actions**, ejecuta `Generate and publish Shorts` manualmente con `dry_run=true`. Esto genera el Short pero no lo publica.

Cuando ambos tokens estén correctos, una ejecución manual con `dry_run=false` publica inmediatamente. Los horarios programados publican automáticamente si todas las credenciales están presentes.

## Nota de YouTube API

Los proyectos API no verificados pueden tener sus uploads restringidos a `private` hasta completar la auditoría de cumplimiento de YouTube. El código solicita el estado configurado en `config/channels.json`, pero YouTube puede imponer esa restricción del proyecto.
