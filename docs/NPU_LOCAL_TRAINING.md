# Alien NPU — entrenamiento local sin cuota

El entrenamiento automático del canal `dioshablahoyia` se ejecuta cada hora y usa solamente archivos locales del repositorio.

## Fuentes internas

- `state/history.jsonl`
- `state/growth/dioshablahoyia_growth.json` (último snapshot ya guardado)
- `state/growth/dioshablahoyia_seo_brain.json`
- `state/growth/dioshablahoyia_npu_brain.json`
- `state/growth/dioshablahoyia_internal_brain.json`

## Política

- Cero llamadas a YouTube Data API o Analytics durante el entrenamiento automático.
- Cero llamadas a Hugging Face, Gemini u otros modelos durante el entrenamiento automático.
- El refresco externo del Growth Engine queda manual.
- Si no existen datos locales nuevos, el ciclo termina sin crear un commit innecesario.
- El aprendizaje nunca bloquea la publicación.
- La calidad tiene prioridad sobre clickbait y volumen vacío.
- Tono editorial: emotivo, esperanzador, entusiasta, humano, claro y reverente.
- El sistema no posee emociones ni conciencia: estas son reglas editoriales computacionales.

## Bucle

`crear -> publicar -> registrar -> comparar -> aprender -> variar -> mejorar`
