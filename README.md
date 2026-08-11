# YouTube AI Automation

Automatización para dos canales de YouTube Shorts:

- **BrotaVida AI** — https://www.youtube.com/@BrotaVidaAI
- **Dinero Claro AI** — https://www.youtube.com/@DineroClaroAi

## Qué hace

1. Gemini genera un concepto, hook, título, descripción SEO, hashtags, tags y 3 escenas.
2. El sistema compara el concepto con el historial reciente y vuelve a generar si es demasiado parecido.
3. Veo genera 3 escenas verticales 9:16 de 8 segundos con audio nativo.
4. FFmpeg une las escenas en un Short de ~24 segundos.
5. YouTube Data API lo sube al canal correcto con su OAuth independiente.
6. Se guarda el historial para evitar duplicados futuros.
7. Si un workflow falla, GitHub Actions abre un issue de alerta.

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
6. Copia el JSON final como `YOUTUBE_TOKEN_BROTAVIDA` o `YOUTUBE_TOKEN_DINEROCLARO`.
7. Repite el consentimiento para el segundo canal.

## Gemini / Veo

El pipeline usa por defecto `gemini-3.6-flash` para estrategia/SEO y `veo-3.1-generate-preview` para video. Requiere una API key con acceso y facturación/cuota suficiente para Veo.

## Prueba segura

En la pestaña **Actions**, ejecuta `Generate and publish Shorts` manualmente con `dry_run=true`. Esto genera el Short pero no lo publica.

Cuando ambos tokens estén correctos, una ejecución manual con `dry_run=false` publica inmediatamente. Los horarios programados publican automáticamente si todas las credenciales están presentes.

## Nota de YouTube API

Los proyectos API no verificados pueden tener sus uploads restringidos a `private` hasta completar la auditoría de cumplimiento de YouTube. El código solicita el estado configurado en `config/channels.json`, pero YouTube puede imponer esa restricción del proyecto.
