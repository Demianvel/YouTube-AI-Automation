# Dios Habla Hoy IA — YouTube Automation

Repositorio dedicado exclusivamente a **Dios Habla Hoy IA** (`@dioshablahoyia`).

## Objetivo diario

- **10 Shorts por día**, aproximadamente 60 segundos cada uno.
- **4 videos largos por día** en hora Argentina:
  - 12:00 — 10 min — historia bíblica.
  - 15:00 — 15 min — oración.
  - 18:00 — 20 min — reflexión bíblica.
  - 21:00 — 30 min — oración de la noche.

El watchdog revisa faltantes y recupera publicaciones sin duplicar ejecuciones activas.

## Voz permanente

La identidad de voz del canal es **Voz de Luz**. Gemini TTS **Algenib** es la base masculina obligatoria para las publicaciones automáticas. La automatización no debe cambiar silenciosamente a otra voz si Algenib no está disponible.

## Visuales nuevos y antirrepetición

Hugging Face es la ruta visual principal gratuita:

- `black-forest-labs/FLUX.1-Kontext-Dev` para generación guiada por el banco de referencias renovado.
- `black-forest-labs/FLUX.1-schnell` para escenas originales y paisajes.

El motor rota Jesús, escenas bíblicas, Biblia y símbolos de fe, Noruega, aurora boreal, fiordos, montañas, ríos, naturaleza y Arca de Noé cuando corresponde. El historial de prompts, referencias y proveedores se usa para bloquear repeticiones recientes. Si Hugging Face no tiene capacidad gratuita, solo se admite un respaldo visual libre y nuevo; una imagen antigua repetida no debe publicarse.

## Secrets

En `Settings > Secrets and variables > Actions`:

- `GEMINI_API_KEY`
- `HF_TOKEN`
- `YOUTUBE_TOKEN_DIOSHABLAHOYIA`
- `PEXELS_API_KEY` es opcional como respaldo de material visual nuevo.

Nunca guardar claves o tokens dentro del repositorio.

## Workflows principales

- `shorts.yml` — programación permanente de 10 Shorts diarios.
- `dioshablahoyia-catchup-shorts.yml` — completa el déficit hasta 10 Shorts del día.
- `dioshablahoyia-long.yml` — videos largos individuales según horario/duración.
- `dioshablahoyia-publish-all.yml` — completa las cuatro duraciones largas faltantes.
- `dioshablahoyia-watchdog.yml` — comprueba el objetivo 10 + 4 y recupera faltantes.
- `dioshablahoyia-comment-responder.yml` — respuestas automáticas en español.
- `dioshablahoyia-visual-optimizer.yml` — optimización de variedad visual.
- `analytics-monitor.yml` — analytics exclusivo del canal.

## Seguridad editorial

- Contenido cristiano reverente sobre Biblia, Dios, Jesús, fe, oración, esperanza y reflexión.
- Las representaciones de Jesús son sintéticas y no deben imitar a actores o personas identificables.
- Sin logos, marcas de agua ni texto visual no solicitado.
- Las profecías se presentan con referencia y contexto, sin fijar fechas ni convertir especulación actual en certeza bíblica.
- El historial evita repetir guiones, temas y composiciones visuales recientes.
