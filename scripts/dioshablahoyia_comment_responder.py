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
_QUESTION_RE = re.compile(
    r"\?|\b(por que|por qué|como|cómo|que significa|qué significa|quien|quién|cuando|cuándo|why|how|what does|who|when)\b",
    re.IGNORECASE,
)

_SKIP_TERMS = (
    "sub4sub", "suscribete a mi canal", "suscríbete a mi canal", "subscribe to my channel",
    "ganar dinero rapido", "ganar dinero rápido", "make money fast", "casino", "apuestas",
    "betting", "bitcoin", "crypto", "telegram", "whatsapp", "porno", "porn", "sexo explicito",
    "sexo explícito", "nudes", "drogas", "drugs", "arma", "weapon", "matar", "kill",
    "suicidio", "suicide", "odio", "hate", "estafa", "scam", "phishing",
)

_ENGLISH_MARKERS = (
    "god", "jesus", "lord", "faith", "hope", "love", "bless", "blessed", "blessing",
    "thank you", "thanks", "pray", "prayer", "peace", "bible", "christ", "savior", "amen",
    "my family", "my heart", "i need", "please pray", "beautiful message", "glory to god",
    "healing", "strength", "grief", "lost", "mother", "father", "children",
)

_SPANISH_MARKERS = (
    "dios", "jesus", "jesús", "señor", "fe", "esperanza", "amor", "bendicion", "bendición",
    "bendiciones", "gracias", "oracion", "oración", "paz", "biblia", "cristo", "mi familia",
    "mi corazon", "mi corazón", "necesito", "oren por", "hermoso mensaje", "gloria a dios",
    "sanidad", "fuerza", "duelo", "perdí", "perdi", "madre", "padre", "hijos",
)

# Replies are assembled from three independently selected parts. This creates
# hundreds of safe combinations per category and language instead of repeating
# a small fixed bank verbatim.
_REPLY_PARTS_ES = {
    "amen": {
        "open": ("Amén 🙏", "Amén, así sea. 🤍", "Amén de corazón. 🙏", "Amén. Gracias por acompañar este mensaje."),
        "body": (
            "Que la paz de Dios encuentre lugar en tu corazón.",
            "Que Jesús renueve tu fe y tu esperanza.",
            "Que la Palabra siga iluminando cada paso.",
            "Que hoy puedas descansar en el amor de Dios.",
            "Que la gracia del Señor te sostenga con serenidad.",
            "Que tu confianza en Dios crezca aun en los procesos difíciles.",
        ),
        "close": ("Bendiciones.", "Un abrazo en la fe.", "Que tengas un día lleno de paz.", "Seguimos caminando con esperanza."),
    },
    "gratitude": {
        "open": ("Gracias por compartirlo. 🙏", "Gracias de corazón por tu mensaje. 🤍", "Qué lindo saber que esta reflexión te acompañó.", "Gracias por estar acá y sumar tu palabra."),
        "body": (
            "Que Dios siga sembrando paz y esperanza en tu vida.",
            "Que esta enseñanza bíblica permanezca con vos durante el día.",
            "Que Jesús fortalezca tu corazón con amor y serenidad.",
            "Que siempre encuentres en la Biblia una luz para seguir.",
            "Que la gratitud abra espacio para más calma y confianza.",
            "Que el Señor te conceda sabiduría para cada nuevo paso.",
        ),
        "close": ("Bendiciones para vos.", "Gracias por formar parte de esta comunidad.", "Que la paz te acompañe.", "Seguimos compartiendo fe con respeto."),
    },
    "prayer": {
        "open": ("Gracias por compartir tu intención. 🙏", "Recibimos tu mensaje con mucho respeto.", "Tu pedido expresa un corazón que busca a Dios. 🤍", "Gracias por confiar y escribir lo que estás viviendo."),
        "body": (
            "Que Dios te conceda calma, sabiduría y fuerzas para este momento.",
            "Que puedas sentir consuelo al acercarte al Señor en oración.",
            "Que Jesús acompañe tu camino y sostenga tu esperanza paso a paso.",
            "Que la paz de Dios guarde tu mente y tu corazón.",
            "Que encuentres claridad para lo que podés hacer hoy y descanso para lo que no podés controlar.",
            "Que la Palabra sea refugio y orientación mientras atravesás este proceso.",
        ),
        "close": ("Que no te falten fe y compañía.", "Un abrazo respetuoso en la fe.", "Que hoy recibas serenidad.", "Seguimos confiando un día a la vez."),
    },
    "family": {
        "open": ("Gracias por pensar en tu familia con tanto amor. 🙏", "Tu mensaje por tu familia fue recibido con respeto.", "Que hermoso es poner a la familia delante de Dios. 🤍", "Gracias por compartir esta preocupación familiar."),
        "body": (
            "Que Dios les dé diálogo, unidad y paciencia para caminar juntos.",
            "Que la paz de Jesús habite en su hogar y los ayude a cuidarse mutuamente.",
            "Que encuentren fortaleza para acompañarse sin perder la esperanza.",
            "Que el amor, el perdón y la sabiduría guíen cada conversación.",
            "Que el Señor les conceda serenidad frente a lo que hoy no pueden resolver.",
            "Que cada integrante del hogar pueda sentirse escuchado, amado y acompañado.",
        ),
        "close": ("Bendiciones para toda tu familia.", "Que la paz alcance su hogar.", "Un abrazo para ustedes.", "Que sigan unidos en la esperanza."),
    },
    "health": {
        "open": ("Gracias por compartir este momento delicado. 🙏", "Lamento que estés atravesando una preocupación de salud.", "Recibimos tu mensaje con cariño y prudencia. 🤍", "Que importante es no llevar esta carga en silencio."),
        "body": (
            "Que Dios te dé paz, fortaleza y buenas personas que te acompañen.",
            "Que encuentres atención médica adecuada y serenidad para seguir cada indicación profesional.",
            "Que Jesús sostenga tu ánimo mientras avanzás con el cuidado que necesitás.",
            "Que la fe te acompañe sin reemplazar la ayuda médica y el apoyo cercano.",
            "Que puedas descansar, pedir ayuda y transitar este proceso un día a la vez.",
            "Que el Señor guarde tu esperanza y te conceda claridad para tomar decisiones cuidadosas.",
        ),
        "close": ("Te enviamos un abrazo respetuoso.", "Que no te falte compañía.", "Mucha paz para este proceso.", "Cuidate y buscá apoyo cuando lo necesites."),
    },
    "grief": {
        "open": ("Siento mucho la pérdida que estás atravesando. 🤍", "Gracias por confiar un dolor tan profundo.", "No hay palabras simples para un momento así.", "Recibimos tu mensaje con respeto y cariño."),
        "body": (
            "Que Dios te sostenga en el duelo y te permita recordar con amor.",
            "Que encuentres consuelo en la compañía de personas cercanas y en la fe.",
            "Que Jesús abrace tu corazón en los días en que la ausencia pesa más.",
            "Que puedas darte tiempo para llorar, descansar y recibir ayuda.",
            "Que la esperanza no borre tu dolor, sino que te acompañe mientras lo atravesás.",
            "Que la paz llegue de a poco, sin apuro y con mucha ternura.",
        ),
        "close": ("Un abrazo muy respetuoso.", "Que no tengas que caminar esto en soledad.", "Mucha paz para vos y tu familia.", "Estamos agradecidos de que hayas compartido tu sentir."),
    },
    "love": {
        "open": ("Bendiciones para vos. 🙏", "Gracias por compartir tanto cariño. 🤍", "Que hermoso leer un mensaje lleno de amor.", "Recibimos tus bendiciones con gratitud."),
        "body": (
            "Que el amor de Dios se refleje en tus palabras y acciones.",
            "Que Jesús llene tu hogar de paz, respeto y unidad.",
            "Que puedas seguir sembrando bondad en quienes te rodean.",
            "Que la misericordia y el perdón fortalezcan tus vínculos.",
            "Que la gracia de Dios acompañe cada decisión de tu vida.",
            "Que tu fe se convierta en gestos concretos de compasión.",
        ),
        "close": ("Que el amor siga dando fruto.", "Paz para tu corazón.", "Un abrazo en Cristo.", "Que tengas una jornada bendecida."),
    },
    "faith": {
        "open": ("Gracias por expresar tu fe. 🙏", "Qué bueno encontrarnos alrededor de la Palabra.", "Tu mensaje refleja una esperanza valiosa. 🤍", "Seguimos aprendiendo a confiar juntos."),
        "body": (
            "Que Dios guíe tu camino con sabiduría y paciencia.",
            "Que Jesús sea una luz serena en cada decisión.",
            "Que la Biblia siga fortaleciendo tu confianza y tu manera de amar.",
            "Que tu fe crezca sin miedo y se sostenga también en los días difíciles.",
            "Que encuentres paz para el presente y esperanza para lo que viene.",
            "Que la gracia del Señor te ayude a perseverar con humildad.",
        ),
        "close": ("Bendiciones en tu camino.", "Seguimos firmes en la esperanza.", "Que la paz de Dios te acompañe.", "Gracias por caminar con esta comunidad."),
    },
    "general": {
        "open": ("Gracias por dejar tu mensaje. 🙏", "Qué alegría encontrarte por acá. 🤍", "Recibimos tus palabras con gratitud.", "Gracias por ser parte de este espacio."),
        "body": (
            "Que Dios te acompañe con paz, fe y esperanza.",
            "Que hoy encuentres serenidad para lo que estás viviendo.",
            "Que Jesús ilumine tu camino y fortalezca tu corazón.",
            "Que la Palabra de Dios te inspire a seguir haciendo el bien.",
            "Que tengas sabiduría para cada decisión y paciencia para cada proceso.",
            "Que el amor de Dios te recuerde que tu vida tiene valor.",
        ),
        "close": ("Bendiciones.", "Que tengas un día de paz.", "Un abrazo en la fe.", "Seguimos compartiendo esperanza."),
    },
}

_REPLY_PARTS_EN = {
    "amen": {
        "open": ("Amen 🙏", "Amen, may it be so. 🤍", "Amen from the heart. 🙏", "Amen. Thank you for sharing this moment."),
        "body": (
            "May God's peace find a home in your heart.",
            "May Jesus renew your faith and hope.",
            "May Scripture continue to light each step.",
            "May you rest today in God's love.",
            "May the Lord's grace hold you with serenity.",
            "May your trust in God grow even through difficult seasons.",
        ),
        "close": ("Blessings.", "A warm embrace in faith.", "May your day be filled with peace.", "Let us keep walking in hope."),
    },
    "gratitude": {
        "open": ("Thank you for sharing this. 🙏", "Thank you from the heart for your message. 🤍", "It is beautiful to know this reflection encouraged you.", "Thank you for being here and adding your voice."),
        "body": (
            "May God continue to plant peace and hope in your life.",
            "May this biblical teaching remain with you throughout the day.",
            "May Jesus strengthen your heart with love and serenity.",
            "May you always find light in Scripture for the road ahead.",
            "May gratitude make room for deeper calm and trust.",
            "May the Lord give you wisdom for each new step.",
        ),
        "close": ("Blessings to you.", "Thank you for being part of this community.", "May peace stay with you.", "We keep sharing faith with respect."),
    },
    "prayer": {
        "open": ("Thank you for sharing your prayer intention. 🙏", "We receive your message with great respect.", "Your words reflect a heart seeking God. 🤍", "Thank you for trusting us with what you are facing."),
        "body": (
            "May God give you calm, wisdom, and strength for this moment.",
            "May you find comfort as you draw near to the Lord in prayer.",
            "May Jesus walk with you and sustain your hope one step at a time.",
            "May God's peace guard your mind and heart.",
            "May you find clarity for what you can do today and rest for what you cannot control.",
            "May Scripture be a refuge and a guide as you move through this season.",
        ),
        "close": ("May faith and good company surround you.", "A respectful embrace in faith.", "May serenity meet you today.", "Let us keep trusting one day at a time."),
    },
    "family": {
        "open": ("Thank you for caring for your family with such love. 🙏", "We receive your message about your family with respect.", "It is meaningful to bring our families before God. 🤍", "Thank you for sharing this family concern."),
        "body": (
            "May God give you dialogue, unity, and patience as you walk together.",
            "May the peace of Jesus fill your home and help you care for one another.",
            "May you find strength to support each other without losing hope.",
            "May love, forgiveness, and wisdom guide every conversation.",
            "May the Lord give you serenity regarding what cannot be solved today.",
            "May every person in your home feel heard, loved, and supported.",
        ),
        "close": ("Blessings to your whole family.", "May peace reach your home.", "A warm embrace to all of you.", "May you remain united in hope."),
    },
    "health": {
        "open": ("Thank you for sharing such a delicate moment. 🙏", "I am sorry you are facing a health concern.", "We receive your message with care and wisdom. 🤍", "You do not have to carry this concern in silence."),
        "body": (
            "May God give you peace, strength, and caring people around you.",
            "May you receive appropriate medical care and calm to follow professional guidance.",
            "May Jesus sustain your spirit while you receive the care you need.",
            "May faith support you without replacing medical care and trusted help.",
            "May you rest, ask for support, and take this process one day at a time.",
            "May the Lord preserve your hope and give you clarity for careful decisions.",
        ),
        "close": ("Sending a respectful embrace.", "May you have good support around you.", "Much peace for this process.", "Please care for yourself and seek help when needed."),
    },
    "grief": {
        "open": ("I am deeply sorry for the loss you are facing. 🤍", "Thank you for trusting us with such deep pain.", "There are no simple words for a moment like this.", "We receive your message with respect and care."),
        "body": (
            "May God hold you through grief and help you remember with love.",
            "May you find comfort in trusted people and in faith.",
            "May Jesus embrace your heart on the days when absence feels heaviest.",
            "May you give yourself time to grieve, rest, and receive help.",
            "May hope accompany your pain rather than ask you to hide it.",
            "May peace return slowly, gently, and without pressure.",
        ),
        "close": ("A very respectful embrace.", "May you not have to walk through this alone.", "Much peace to you and your family.", "Thank you for sharing what is in your heart."),
    },
    "love": {
        "open": ("Blessings to you. 🙏", "Thank you for sharing so much kindness. 🤍", "It is beautiful to read a message filled with love.", "We receive your blessings with gratitude."),
        "body": (
            "May God's love be reflected in your words and actions.",
            "May Jesus fill your home with peace, respect, and unity.",
            "May you keep planting kindness in the people around you.",
            "May mercy and forgiveness strengthen your relationships.",
            "May God's grace accompany every decision in your life.",
            "May your faith become practical acts of compassion.",
        ),
        "close": ("May love continue to bear fruit.", "Peace to your heart.", "An embrace in Christ.", "May your day be blessed."),
    },
    "faith": {
        "open": ("Thank you for expressing your faith. 🙏", "It is good to gather around Scripture.", "Your message reflects a precious hope. 🤍", "We keep learning to trust together."),
        "body": (
            "May God guide your path with wisdom and patience.",
            "May Jesus be a gentle light in every decision.",
            "May the Bible strengthen your trust and the way you love others.",
            "May your faith grow without fear and remain steady on difficult days.",
            "May you find peace for today and hope for what is ahead.",
            "May the Lord's grace help you persevere with humility.",
        ),
        "close": ("Blessings on your journey.", "Let us remain firm in hope.", "May God's peace be with you.", "Thank you for walking with this community."),
    },
    "general": {
        "open": ("Thank you for leaving a message. 🙏", "It is a joy to see you here. 🤍", "We receive your words with gratitude.", "Thank you for being part of this space."),
        "body": (
            "May God walk with you in peace, faith, and hope.",
            "May you find serenity for what you are facing today.",
            "May Jesus light your path and strengthen your heart.",
            "May God's Word inspire you to keep doing good.",
            "May you have wisdom for every decision and patience for every process.",
            "May God's love remind you that your life has value.",
        ),
        "close": ("Blessings.", "May your day be peaceful.", "A warm embrace in faith.", "We keep sharing hope."),
    },
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


def _language(text: str) -> str:
    clean = _normalize(text)
    en_score = sum(1 for marker in _ENGLISH_MARKERS if _normalize(marker) in clean)
    es_score = sum(1 for marker in _SPANISH_MARKERS if _normalize(marker) in clean)
    if en_score > es_score:
        return "en"
    if es_score > en_score:
        return "es"
    return "es"


def _should_skip(text: str) -> tuple[bool, str]:
    clean = _normalize(text)
    if not clean:
        return True, "empty"
    if _URL_RE.search(text):
        return True, "contains_link"
    if _QUESTION_RE.search(text):
        return True, "question_manual_review"
    for term in _SKIP_TERMS:
        if _normalize(term) in clean:
            return True, f"blocked_term:{term}"
    return False, "ok"


def _category(text: str) -> str:
    clean = _normalize(text)
    if "amen" in clean:
        return "amen"
    if any(x in clean for x in ("fallecio", "murio", "perdi a", "duelo", "luto", "death", "died", "passed away", "lost my", "grief")):
        return "grief"
    if any(x in clean for x in ("salud", "enfermo", "enferma", "hospital", "operacion", "cancer", "sanidad", "health", "sick", "hospital", "surgery", "cancer", "healing")):
        return "health"
    if any(x in clean for x in ("familia", "hijo", "hija", "madre", "padre", "esposo", "esposa", "family", "son", "daughter", "mother", "father", "husband", "wife")):
        return "family"
    if any(x in clean for x in ("oren por", "ora por", "oracion por", "necesito oracion", "please pray", "pray for", "prayer request", "i need prayer")):
        return "prayer"
    if any(x in clean for x in ("gracias", "agradezco", "hermoso video", "hermoso mensaje", "thank you", "thanks", "beautiful video", "beautiful message")):
        return "gratitude"
    if any(x in clean for x in ("bendiciones", "amor", "bendiga", "bendecir", "blessing", "bless", "love")):
        return "love"
    if any(x in clean for x in ("dios", "jesus", "cristo", "biblia", "fe", "oracion", "god", "christ", "bible", "faith", "prayer", "lord")):
        return "faith"
    return "general"


def _pick(parts: tuple[str, ...], digest: str, offset: int) -> str:
    start = offset * 8
    marker = int(digest[start:start + 8], 16)
    return parts[marker % len(parts)]


def _reply_text(comment_id: str, text: str) -> tuple[str, str, str]:
    category = _category(text)
    language = _language(text)
    bank = (_REPLY_PARTS_EN if language == "en" else _REPLY_PARTS_ES)[category]
    digest = hashlib.sha256(
        f"voz-de-luz|{comment_id}|{_normalize(text)}|{category}|{language}".encode("utf-8")
    ).hexdigest()
    reply = " ".join((
        _pick(bank["open"], digest, 0),
        _pick(bank["body"], digest, 1),
        _pick(bank["close"], digest, 2),
    ))
    return reply[:480], language, category


def _already_replied(youtube, parent_id: str, channel_id: str, total_reply_count: int) -> bool:
    if total_reply_count <= 0:
        return False
    page_token = None
    while True:
        response = youtube.comments().list(
            part="snippet",
            parentId=parent_id,
            maxResults=100,
            textFormat="plainText",
            pageToken=page_token,
        ).execute()
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

        reply, language, category = _reply_text(top_id, text)
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
            "category": category,
            "language": language,
            "reply": reply,
        })

    result = {
        "channel_id": channel_id,
        "inspected": inspected,
        "replied": replied,
        "skipped": skipped,
        "max_replies_per_run": MAX_REPLIES_PER_RUN,
        "mode": "voz_de_luz_contextual_bilingual_high_variety_nonspam",
        "details": details,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":
    run()
