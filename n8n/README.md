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

## 5. Activación

NO actives la programación n8n mientras también esté activo el `schedule:` de GitHub Actions, porque duplicaría publicaciones. Cuando n8n vaya a ser el scheduler principal, primero elimina/desactiva el schedule de `.github/workflows/shorts.yml` y deja solo `workflow_dispatch`.

## YouTube

La subida real sigue usando OAuth de YouTube en GitHub mediante secretos separados:

- `YOUTUBE_TOKEN_BROTAVIDA`
- `YOUTUBE_TOKEN_DINEROCLARO`

Nunca pegues esos tokens en este JSON ni los publiques en el repositorio.

## Seguridad

- No guardar Gemini API key, OAuth client secret, refresh tokens ni PAT en archivos.
- Usar credenciales de n8n y GitHub Secrets.
- Restringir el PAT de n8n al único repositorio y a Actions write.
- Mantener el workflow n8n desactivado hasta completar una prueba manual.
