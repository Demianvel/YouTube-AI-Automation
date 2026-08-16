from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# Importa el respondedor existente desde este mismo directorio sin duplicar
# la logica de OAuth, filtros anti-spam ni control de respuestas repetidas.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import dioshablahoyia_comment_responder as responder


def _reply_text_spanish_only(comment_id: str, text: str) -> tuple[str, str]:
    """Genera siempre una respuesta espiritual en español.

    El idioma del comentario entrante no cambia el idioma de salida. YouTube
    puede ofrecer traduccion al espectador cuando la necesite.
    """
    category = responder._category(text)
    bank = responder._REPLY_BANK_ES[category]
    marker = hashlib.sha256(
        f"{comment_id}|{responder._normalize(text)}|{category}|es".encode("utf-8")
    ).hexdigest()
    reply = bank[int(marker[:8], 16) % len(bank)]
    return reply, "es"


# Bloqueo duro: ninguna respuesta automatica puede seleccionar el banco ingles.
responder._language = lambda _text: "es"
responder._REPLY_BANK_EN = responder._REPLY_BANK_ES
responder._reply_text = _reply_text_spanish_only


if __name__ == "__main__":
    responder.run()
