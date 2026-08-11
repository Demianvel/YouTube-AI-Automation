# n8n + YouTube AI Automation

Este directorio contiene un workflow importable para usar n8n como capa de orquestación del repositorio `Demianvel/YouTube-AI-Automation`.

## Arquitectura

n8n (horarios/control) -> GitHub Actions -> Gemini (idea/SEO) -> generador de video -> YouTube Data API -> historial anti-duplicados.

El workflow n8n NO contiene secretos y se importa desactivado.

## Archivo para importar

`n8n/workflows/youtube-ai-orchestrator.json`

## Horarios configurados (America/Argentina/Buenos_Aires)

- BrotaVida AI: 00:00, 06:00, 12:00 y 18:00.
- Dinero Claro AI: 08:00, 13:00, 17:00 y 21:00.

## 1. Crear cuenta/instancia n8n

Puede usarse n8n Cloud o una instancia self-hosted. Importa el JSON desde Workflows > Import from File.

## 2. Crear un token GitHub de alcance mínimo

En GitHub crea un Fine-grained personal access token restringido SOLO al repositorio `Demianvel/YouTube-AI-Automation` y concede `Actions: Read and write`. GitHub documenta que `Create a workflow dispatch event` requiere permiso de repositorio `Actions: write` para fine-grained tokens.

No guardes ese token en el workflow ni en archivos del repositorio.

## 3. Crear credencial segura en n8n

En n8n crea una credencial `Header Auth`:

- Name/header: `Authorization`
- Value: `Bearer TU_TOKEN_FINE_GRAINED`

Luego abre el nodo `Dispatch GitHub Action` del workflow importado y selecciona esa credencial.

## 4. Probar sin publicar

Ejecuta manualmente el workflow. Las ejecuciones manuales fuerzan `dry_run=true` y por defecto prueban BrotaVida. El workflow de GitHub generará el contenido pero no debería subirlo a YouTube.

## 5. Hacer que n8n sea el programador principal

Antes de activar el Schedule de n8n, en GitHub ve a:

`Settings > Secrets and variables > Actions > Variables > New repository variable`

Crea:

- Name: `N8N_PRIMARY`
- Value: `true`

El workflow de GitHub ya está preparado para omitir sus propios horarios cuando esta variable vale `true`, evitando publicaciones duplicadas. Las ejecuciones manuales/dispatch enviadas por n8n siguen funcionando.

Si después querés volver a los horarios internos de GitHub, cambia `N8N_PRIMARY` a `false` o elimina la variable.

## YouTube

La subida real sigue usando OAuth de YouTube en GitHub mediante secretos separados:

- `YOUTUBE_TOKEN_BROTAVIDA`
- `YOUTUBE_TOKEN_DINEROCLARO`

Nunca pegues esos tokens en este JSON ni los publiques en el repositorio.

### Alternativa futura: YouTube directo desde n8n

n8n tiene un nodo oficial de YouTube con operación `Upload a video`. En n8n Cloud, Google OAuth puede conectarse con `Sign in with Google`; en self-hosted hay que configurar el OAuth Client y el redirect URI. Este repositorio conserva por ahora la subida en GitHub para no duplicar el manejo del archivo de video ni exponer credenciales en dos lugares.

## Seguridad

- No guardar Gemini API key, OAuth client secret, refresh tokens ni PAT en archivos.
- Usar credenciales de n8n y GitHub Secrets.
- Restringir el PAT de n8n al único repositorio y a Actions write.
- Mantener el workflow n8n desactivado hasta completar una prueba manual.
