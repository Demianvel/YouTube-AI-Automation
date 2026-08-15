from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


TOKEN_ENV = "YOUTUBE_TOKEN_DIOSHABLAHOYIA"
FORCE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
MAX_REPLIES_PER_RUN = max(1, min(12, int(os.getenv("COMMENT_REPLY_MAX", "6"))))
MAX_THREADS = max(10, min(100, int(os.getenv("COMMENT_THREAD_SCAN_MAX", "50"))))

_URL_RE = re.compile(r"https?://|www\.|\.com\b|\.net\b|\.org\b", re.IGNORECASE)
_QUESTION_RE = re.compile(r"\?|\b(por que|por qué|como|cómo|que significa|qué significa|quien|quién|cuando|cuándo)\b", re.IGNORECASE)

_SKIP_TERMS = (
    "sub4sub", "suscribete a mi canal", "suscríbete a mi canal", "ganar dinero rapido",
    "ganar dinero rápido", "casino", "apuestas", "bitcoin", "crypto", "telegram",
    "whatsapp", "porno", "sexo explicito", "sexo explícito", "nudes", "drogas",
    "arma", "matar", "suicidio", "odio", "estafa", "phishing",
)

_REPLY_BANK = {
    "amen": (
        "Amén 🙏 Que la paz de Dios acompañe tu corazón y renueve tu esperanza cada día.",
        "Amén. Que Dios te fortalezca, te dé serenidad y mantenga viva tu fe. 🙏",
        "Amén 🙏 Que el amor de Dios llene tu vida de paz, esperanza y consuelo.",
        "Amén. Que hoy puedas caminar con fe y descansar en la paz de Dios. 🤍",
        "Amén 🙏 Que Jesús sea luz en tu camino y esperanza en cada paso.",
        "Amén. Que la gracia y la paz de Dios estén presentes en tu día. 🙏",
    ),
    "gratitude": (
        "Gracias por compartirlo 🙏 Que Dios bendiga tu vida y te regale mucha paz.",
        "Gracias de corazón. Que la esperanza y el amor de Dios te acompañen siempre. 🤍",
        "Gracias por estar acá 🙏 Que Jesús renueve tu fe y llene tu corazón de serenidad.",
        "Gracias por tu mensaje. Que Dios te conceda un día lleno de paz y esperanza. 🙏",
        "Muchas gracias 🤍 Que la Palabra de Dios siga sembrando amor y fe en tu corazón.",
    ),
    "support": (
        "Que Dios te sostenga en este momento y te dé fuerzas para seguir un paso a la vez. 🙏",
        "Que encuentres consuelo, serenidad y esperanza en Dios. No dejes de acercarte a Él en oración. 🤍",
        "Que Jesús te acompañe y te dé paz en medio de lo que estás atravesando. 🙏",
        "Que la fe te dé fuerzas hoy. Salmo 23 nos recuerda que podemos caminar confiando en el cuidado de Dios. 🤍",
        "Que Dios renueve tus fuerzas y te conceda calma para afrontar este día con esperanza. 🙏",
        "Que el amor de Dios abrace tu corazón y te ayude a seguir con fe y paciencia. 🤍",
    ),
    "faith": (
        "Que tu fe siga creciendo y que la paz de Dios acompañe cada decisión de tu vida. 🙏",
        "Jesús nos invita a caminar con fe, amor y esperanza. Que esa paz permanezca en tu corazón. 🤍",
        "Que Dios siga guiando tu camino y fortaleciendo tu confianza en Él. 🙏",
        "La fe también se construye un día a la vez. Que Dios te dé paz y perseverancia. 🤍",
        "Que la Palabra de Dios sea luz para tu camino y fuente de esperanza cada día. 🙏",
        "Que Jesús te conceda serenidad para el presente y esperanza para lo que viene. 🤍",
    ),
    "love": (
        "Bendiciones 🙏 Que el amor de Dios llene tu hogar de paz, unión y esperanza.",
        "Que Dios te bendiga y que su amor te acompañe en cada paso. 🤍",
        "Bendiciones para vos y tu familia. Que nunca falten la fe, la paz y el amor. 🙏",
        "Que el amor de Jesús inspire tus palabras, tus decisiones y tu manera de tratar a los demás. 🤍",
        "Que Dios derrame paz sobre tu vida y te ayude a compartir amor con quienes te rodean. 🙏",
    ),
    "general": (
        "Que Dios te bendiga y te acompañe con paz, fe y esperanza. 🙏",
        "Que Jesús sea luz en tu camino y que su amor te dé serenidad cada día. 🤍",
        "Que la paz de Dios permanezca en tu corazón y fortalezca tu esperanza. 🙏",
        "Que hoy encuentres un motivo para confiar, agradecer y seguir caminando con fe. 🤍",
        "Que Dios te conceda sabiduría, paz y un corazón lleno de esperanza. 🙏",
        "Que la gracia de Dios te acompañe y que tu fe siga creciendo cada día. 🤍",
    ),
}


def _normalize(value: object) -> str:
    text = " ".join(str(value or "").split()).lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _credentials() -> Credentials:
    token_json = os.getenv(TOKEN_ENV, "").strip()
    if not token_json:
        raise RuntimeError(f"Falta el secret {TOKEN_ENV}.")
    info = json.loads(token_json)
    scopes = list(info.get("scopes") or [])
    if scopes and FORCE_SSL_SCOPE not in scopes:
        raise RuntimeError(
            "El token OAuth no incluye youtube.force-ssl, necesario para responder comentarios. "
            "Renueva el token del canal incluyendo ese scope."
        )
    return Credentials.from_authorized_user_info(info, scopes=scopes or None)


def _youtube():
    return build("youtube", "v3", credentials=_credentials(), cache_discovery=False)


def _channel_id(youtube) -> str:
    response = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items") or []
    if not items:
        raise RuntimeError("No se pudo identificar el canal autorizado.")
    return str(items[0]["id"])


def _author_channel_id(snippet: dict) -> str:
    value = snippet.get("authorChannelId") or {}
    return str(value.get("value") or "") if isinstance(value, dict) else ""


def _should_skip(text: str) -> tuple[bool, str]:
    clean = _normalize(text)
    if not clean:
        return True, "empty"
    if _URL_RE.search(text):
        return True, "contains_link"
    if _QUESTION_RE.search(text):
        # Questions can need a nuanced theological/pastoral answer. Leave them for manual review.
        return True, "question_manual_review"
    for term in _SKIP_TERMS:
        if _normalize(term) in clean:
            return True, f"blocked_term:{term}"
    return False, "ok"


def _category(text: str) -> str:
    clean = _normalize(text)
    if "amen" in clean:
        return "amen"
    if any(x in clean for x in ("gracias", "agradezco", "hermoso video", "hermoso mensaje")):
        return "gratitude"
    if any(x in clean for x in (
        "triste", "miedo", "ansiedad", "dolor", "solo", "sola", "cansado", "cansada",
        "necesito oracion", "necesito oración", "oren por", "ora por", "ayuda", "familia", "salud",
    )):
        return "support"
    if any(x in clean for x in ("bendiciones", "amor", "bendiga", "bendecir")):
        return "love"
    if any(x in clean for x in ("dios", "jesus", "cristo", "biblia", "fe", "oracion", "oración")):
        return "faith"
    return "general"


def _reply_text(comment_id: str, text: str) -> str:
    category = _category(text)
    bank = _REPLY_BANK[category]
    marker = hashlib.sha256(f"{comment_id}|{_normalize(text)}|{category}".encode("utf-8")).hexdigest()
    return bank[int(marker[:8], 16) % len(bank)]


def _already_replied(youtube, parent_id: str, channel_id: str, total_reply_count: int) -> bool:
    if total_reply_count <= 0:
        return False
    page_token = None
    while True:
        request = youtube.comments().list(
            part="snippet",
            parentId=parent_id,
            maxResults=100,
            textFormat="plainText",
            pageToken=page_token,
        )
        response = request.execute()
        for item in response.get("items") or []:
            snippet = item.get("snippet") or {}
            if _author_channel_id(snippet) == channel_id:
                return True
        page_token = response.get("nextPageToken")
        if not page_token:
            return False


def run() -> dict:
    youtube = _youtube()
    channel_id = _channel_id(youtube)
    response = youtube.commentThreads().list(
        part="snippet,replies",
        allThreadsRelatedToChannelId=channel_id,
        order="time",
        moderationStatus="published",
        maxResults=MAX_THREADS,
        textFormat="plainText",
    ).execute()

    replied = 0
    skipped = 0
    inspected = 0
    replied_authors: set[str] = set()
    details: list[dict] = []

    for thread in response.get("items") or []:
        if replied >= MAX_REPLIES_PER_RUN:
            break
        inspected += 1
        thread_snippet = thread.get("snippet") or {}
        if thread_snippet.get("canReply") is False:
            skipped += 1
            continue

        top = thread_snippet.get("topLevelComment") or {}
        top_id = str(top.get("id") or "")
        snippet = top.get("snippet") or {}
        text = str(snippet.get("textDisplay") or snippet.get("textOriginal") or "").strip()
        author_id = _author_channel_id(snippet)

        if not top_id or author_id == channel_id:
            skipped += 1
            continue
        if author_id and author_id in replied_authors:
            skipped += 1
            continue

        skip, reason = _should_skip(text)
        if skip:
            skipped += 1
            details.append({"comment_id": top_id, "action": "skip", "reason": reason})
            continue

        total_reply_count = int(thread_snippet.get("totalReplyCount") or 0)
        if _already_replied(youtube, top_id, channel_id, total_reply_count):
            skipped += 1
            details.append({"comment_id": top_id, "action": "skip", "reason": "already_replied"})
            continue

        reply = _reply_text(top_id, text)
        youtube.comments().insert(
            part="snippet",
            body={"snippet": {"parentId": top_id, "textOriginal": reply}},
        ).execute()
        replied += 1
        if author_id:
            replied_authors.add(author_id)
        details.append({
            "comment_id": top_id,
            "action": "replied",
            "category": _category(text),
            "reply": reply,
        })

    result = {
        "channel_id": channel_id,
        "inspected": inspected,
        "replied": replied,
        "skipped": skipped,
        "max_replies_per_run": MAX_REPLIES_PER_RUN,
        "mode": "faith_hope_love_contextual_nonspam",
        "details": details,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
