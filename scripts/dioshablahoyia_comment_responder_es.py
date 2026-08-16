from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Reutiliza el respondedor principal para OAuth, filtros anti-spam,
# control anti-duplicados y variedad contextual. Solo fijamos el idioma.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import dioshablahoyia_comment_responder as responder


# Regla permanente del canal: responder siempre en español, sin importar
# el idioma del comentario entrante. No tocamos la estructura interna de
# los bancos de frases para evitar roturas cuando evolucionen.
responder._language = lambda _text: "es"


def self_test() -> None:
    samples = (
        "God bless you and thank you for this beautiful message",
        "Amen, please pray for my family",
        "Gracias por este mensaje de fe",
        "Que Dios bendiga a todos",
    )
    for index, text in enumerate(samples):
        reply, language, category = responder._reply_text(f"self-test-{index}", text)
        if language != "es":
            raise RuntimeError(f"El respondedor intentó usar idioma {language!r} para: {text!r}")
        if not reply.strip():
            raise RuntimeError("Se generó una respuesta vacía.")
        if category not in responder._REPLY_PARTS_ES:
            raise RuntimeError(f"Categoría desconocida: {category}")
    print("Spanish-only responder self-test: OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test()
    if not args.self_test:
        responder.run()


if __name__ == "__main__":
    main()
