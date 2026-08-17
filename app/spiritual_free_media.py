from __future__ import annotations

import hashlib
import html
import os
import random
import re
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageEnhance, ImageOps

PEXELS_PHOTOS = "https://api.pexels.com/v1/search"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "YouTube-AI-Automation/1.0 (https://github.com/Demianvel/YouTube-AI-Automation)"
W, H = 1080, 1920
ALLOWED_RASTER_MIMES = {"image/jpeg", "image/png", "image/webp"}
_USED_REMOTE_IDS: set[str] = set()


def _clean(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    text = html.unescape(str(value or ""))
    return re.sub(r"<[^>]+>", "", text).strip()


def _query_from_prompt(prompt: str) -> str:
    text = " ".join(str(prompt or "").lower().split())
    if any(k in text for k in ("tromso", "lofoten", "senja", "norway", "norwegian", "fjord", "aurora")):
        return "Norway fjord aurora mountains nature"
    if any(k in text for k in ("bible", "scripture", "cross", "dove", "tomb", "shepherd", "prayer")):
        return "Bible prayer cross church sunlight peaceful"
    if any(k in text for k in ("jerusalem", "judean", "galilee", "olive grove", "bethlehem")):
        return "Jerusalem old city desert olive grove biblical landscape"
    if any(k in text for k in ("noah", "samaritan", "moses", "david", "ancient road")):
        return "ancient desert road mountains historical landscape"
    if any(k in text for k in ("waterfall", "river", "lake", "forest", "mountain", "ocean", "desert", "valley")):
        return "mountain river waterfall forest sunrise peaceful nature"
    if any(k in text for k in ("rainbow", "storm clouds", "sun rays", "sunrise", "horizon")):
        return "sun rays clouds rainbow mountains sunrise nature"
    return "peaceful mountains sunrise nature cinematic"


def _seed(prompt: str, seed: int) -> int:
    raw = f"fresh-free-media-v2|{prompt}|{seed}|{os.getenv('GITHUB_RUN_ID','')}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _normalize_image(raw: bytes, out: Path, seed: int) -> None:
    with Image.open(BytesIO(raw)) as source:
        source.load()
        source = source.convert("RGB")
        safe = int(seed) & 0x7FFFFFFF
        centerings = ((0.50, 0.50), (0.42, 0.50), (0.58, 0.50), (0.50, 0.42), (0.50, 0.58))
        image = ImageOps.fit(
            source,
            (W, H),
            method=Image.Resampling.LANCZOS,
            centering=centerings[safe % len(centerings)],
        )
        image = ImageEnhance.Contrast(image).enhance(1.02)
        image = ImageEnhance.Color(image).enhance(1.03)
        image.save(out, format="JPEG", quality=94, optimize=True)
    if not out.exists() or out.stat().st_size < 20_000:
        raise RuntimeError("El respaldo visual gratuito devolvio una imagen invalida.")


def _download(url: str) -> bytes:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=(15, 75))
    response.raise_for_status()
    if len(response.content) < 10_000:
        raise RuntimeError("La imagen remota gratuita esta vacia o es demasiado pequena.")
    return response.content


def _pexels_image(prompt: str, out: Path, seed: int) -> str:
    key = os.getenv("PEXELS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PEXELS_API_KEY no esta configurada.")

    query = _query_from_prompt(prompt)
    response = requests.get(
        PEXELS_PHOTOS,
        headers={"Authorization": key, "User-Agent": USER_AGENT},
        params={"query": query, "orientation": "portrait", "size": "large", "per_page": 80},
        timeout=(15, 45),
    )
    response.raise_for_status()
    photos = response.json().get("photos") or []
    candidates = [p for p in photos if f"pexels:{p.get('id')}" not in _USED_REMOTE_IDS and p.get("src")]
    if not candidates:
        candidates = [p for p in photos if p.get("src")]
    if not candidates:
        raise RuntimeError(f"Pexels no encontro una foto nueva para '{query}'.")

    rng = random.Random(_seed(prompt, seed))
    top = candidates[: min(45, len(candidates))]
    chosen = top[rng.randrange(len(top))]
    marker = f"pexels:{chosen.get('id')}"
    _USED_REMOTE_IDS.add(marker)
    src = chosen.get("src") or {}
    url = src.get("large2x") or src.get("portrait") or src.get("large") or src.get("original")
    if not url:
        raise RuntimeError("Pexels no devolvio una URL de imagen utilizable.")
    _normalize_image(_download(str(url)), out, seed)
    photographer = str(chosen.get("photographer") or "Pexels contributor")
    return f"Pexels fresh free photo / id:{chosen.get('id')} / {photographer} / query:{query}"


def _commons_public_domain_image(prompt: str, out: Path, seed: int) -> str:
    query = _query_from_prompt(prompt)
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 50,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "format": "json",
        "formatversion": 2,
        "origin": "*",
    }
    response = requests.get(COMMONS_API, params=params, headers={"User-Agent": USER_AGENT}, timeout=(15, 60))
    response.raise_for_status()
    pages = (response.json().get("query") or {}).get("pages") or []
    candidates: list[dict[str, str]] = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        mime = str(info.get("mime") or "").lower()
        if mime not in ALLOWED_RASTER_MIMES:
            continue
        metadata = info.get("extmetadata") or {}
        license_name = _clean(metadata.get("LicenseShortName")).lower()
        if not (license_name.startswith("cc0") or license_name.startswith("public domain")):
            continue
        url = str(info.get("url") or "")
        marker = f"commons:{url}"
        if not url or marker in _USED_REMOTE_IDS:
            continue
        candidates.append({
            "url": url,
            "marker": marker,
            "license": _clean(metadata.get("LicenseShortName")) or "Public domain/CC0",
            "artist": _clean(metadata.get("Artist")) or "Wikimedia Commons contributor",
            "mime": mime,
        })
    if not candidates:
        raise RuntimeError(f"Wikimedia Commons no encontro JPEG/PNG/WebP CC0 o dominio publico para '{query}'.")

    rng = random.Random(_seed(prompt, seed) ^ 0xC0A110)
    rng.shuffle(candidates)
    decode_errors: list[str] = []
    for chosen in candidates[:12]:
        try:
            raw = _download(chosen["url"])
            _normalize_image(raw, out, seed)
            _USED_REMOTE_IDS.add(chosen["marker"])
            return (
                f"Wikimedia fresh public-domain raster / {chosen['license']} / "
                f"{chosen['artist']} / query:{query}"
            )
        except Exception as exc:
            decode_errors.append(str(exc))
            continue
    raise RuntimeError(
        f"Wikimedia encontro candidatos para '{query}', pero ninguno de los raster pudo decodificarse: "
        + " | ".join(decode_errors[-3:])
    )


def download_fresh_free_image(prompt: str, out: Path, seed: int) -> str:
    """Return a genuinely different free image when generative GPU capacity is unavailable."""
    errors: list[str] = []
    try:
        return _pexels_image(prompt, out, seed)
    except Exception as exc:
        errors.append(f"Pexels: {exc}")
    try:
        return _commons_public_domain_image(prompt, out, seed)
    except Exception as exc:
        errors.append(f"Wikimedia: {exc}")
    raise RuntimeError("; ".join(errors))
