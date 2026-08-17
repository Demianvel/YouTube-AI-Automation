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
    return _queries_from_prompt(prompt)[0]


def _queries_from_prompt(prompt: str) -> list[str]:
    text = " ".join(str(prompt or "").lower().split())
    if any(k in text for k in ("tromso", "lofoten", "senja", "norway", "norwegian", "fjord", "aurora")):
        return ["Norway fjord", "Norway mountains", "Lofoten Norway", "Norwegian landscape", "aurora Norway"]
    if any(k in text for k in ("bible", "scripture", "cross", "dove", "tomb", "shepherd", "prayer")):
        return ["Bible", "Christian cross", "church sunlight", "prayer Bible", "shepherd landscape"]
    if any(k in text for k in ("jerusalem", "judean", "galilee", "olive grove", "bethlehem")):
        return ["Jerusalem old city", "Judean desert", "Sea of Galilee", "olive grove Israel", "Bethlehem landscape"]
    if any(k in text for k in ("noah", "samaritan", "moses", "david", "ancient road")):
        return ["ancient desert road", "desert landscape Israel", "ancient stone road", "biblical landscape"]
    if any(k in text for k in ("waterfall", "river", "lake", "forest", "mountain", "ocean", "desert", "valley")):
        return ["mountain river", "waterfall forest", "alpine lake", "green valley", "mountain sunrise"]
    if any(k in text for k in ("rainbow", "storm clouds", "sun rays", "sunrise", "horizon")):
        return ["sun rays clouds", "rainbow mountains", "sunrise mountains", "storm clouds landscape"]
    return ["peaceful mountains", "sunrise landscape", "river valley", "nature mountains"]


def _seed(prompt: str, seed: int) -> int:
    raw = f"fresh-free-media-v3|{prompt}|{seed}|{os.getenv('GITHUB_RUN_ID','')}"
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
    return f"Pexels fresh free photo | id={chosen.get('id')} | artist={photographer} | query={query}"


def _license_is_usable(license_name: str) -> bool:
    value = license_name.lower().strip()
    if value.startswith("cc0") or value.startswith("public domain"):
        return True
    # CC BY permits commercial use with attribution. Explicitly exclude ShareAlike
    # variants because normal YouTube licensing is not a good fit for CC BY-SA.
    if value.startswith("cc by") and "by-sa" not in value and "sharealike" not in value:
        return True
    return False


def _commons_candidates(query: str) -> list[dict[str, str]]:
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
        license_name = _clean(metadata.get("LicenseShortName"))
        if not _license_is_usable(license_name):
            continue
        url = str(info.get("url") or "")
        source = str(info.get("descriptionurl") or "")
        marker = f"commons:{url}"
        if not url or marker in _USED_REMOTE_IDS:
            continue
        candidates.append({
            "url": url,
            "source": source,
            "marker": marker,
            "license": license_name or "Public Domain/CC0",
            "artist": _clean(metadata.get("Artist")) or "Wikimedia Commons contributor",
            "mime": mime,
            "query": query,
        })
    return candidates


def _commons_free_image(prompt: str, out: Path, seed: int) -> str:
    all_candidates: list[dict[str, str]] = []
    for query in _queries_from_prompt(prompt):
        try:
            found = _commons_candidates(query)
        except Exception:
            found = []
        all_candidates.extend(found)
        if len(all_candidates) >= 12:
            break

    unique: dict[str, dict[str, str]] = {item["marker"]: item for item in all_candidates}
    candidates = list(unique.values())
    if not candidates:
        raise RuntimeError("Wikimedia Commons no encontro raster CC0/dominio publico/CC BY nuevo para esta escena.")

    rng = random.Random(_seed(prompt, seed) ^ 0xC0A110)
    rng.shuffle(candidates)
    decode_errors: list[str] = []
    for chosen in candidates[:20]:
        try:
            _normalize_image(_download(chosen["url"]), out, seed)
            _USED_REMOTE_IDS.add(chosen["marker"])
            return (
                "Wikimedia fresh free raster"
                f" | license={chosen['license']}"
                f" | artist={chosen['artist']}"
                f" | source={chosen['source']}"
                f" | query={chosen['query']}"
            )
        except Exception as exc:
            decode_errors.append(str(exc))
    raise RuntimeError("Wikimedia encontro material libre, pero no pudo decodificarlo: " + " | ".join(decode_errors[-3:]))


def append_free_media_credits(metadata: dict) -> dict:
    providers = metadata.get("generated_visual_provider") or []
    if isinstance(providers, str):
        providers = [providers]
    credits: list[str] = []
    for provider in providers:
        text = str(provider)
        if not text.startswith("Wikimedia fresh free raster"):
            continue
        fields: dict[str, str] = {}
        for part in text.split(" | ")[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                fields[key.strip()] = value.strip()
        artist = fields.get("artist") or "Wikimedia Commons contributor"
        license_name = fields.get("license") or "CC BY/Public Domain"
        source = fields.get("source") or "Wikimedia Commons"
        line = f"{artist} — {license_name} — {source}"
        if line not in credits:
            credits.append(line)
    if not credits:
        return metadata
    block = "\n\nCréditos visuales de material libre (Wikimedia Commons):\n" + "\n".join(f"• {line}" for line in credits)
    description = str(metadata.get("description") or "").rstrip()
    metadata["description"] = (description + block)[:4900]
    metadata["free_visual_credits"] = credits
    return metadata


def download_fresh_free_image(prompt: str, out: Path, seed: int) -> str:
    """Return a genuinely different free image when generative GPU capacity is unavailable."""
    errors: list[str] = []
    try:
        return _pexels_image(prompt, out, seed)
    except Exception as exc:
        errors.append(f"Pexels: {exc}")
    try:
        return _commons_free_image(prompt, out, seed)
    except Exception as exc:
        errors.append(f"Wikimedia: {exc}")
    raise RuntimeError("; ".join(errors))
