from __future__ import annotations

import hashlib
import os
from typing import Any

from . import dios_premium_editorial_v7 as v7

ENGINE_VERSION = "dhh-premium-editorial-v8"

BROAD_HOOKS = (
    "Si hoy creés, dudás o simplemente necesitás un poco de paz, quedate con esta idea:",
    "Aunque no tengas todas las respuestas sobre la fe, esta palabra puede acompañarte hoy:",
    "Si venís cargando ansiedad, cansancio o demasiadas preguntas, escuchá esto:",
    "Antes de seguir desplazando la pantalla, regalate un minuto para pensar en esto:",
    "No hace falta sentirte fuerte para empezar de nuevo; considerá esta verdad:",
    "Para quien hoy necesita esperanza, crea mucho, poco o esté buscando, esta reflexión es para vos:",
    "Si tu cabeza no para y el corazón está cansado, esta enseñanza bíblica puede darte un punto de apoyo:",
    "Hay momentos en los que una sola verdad puede ordenar el ruido del día:",
)

VISUAL_MOTIFS = (
    "a fresh AI-generated symbolic biblical sunrise over a quiet Judean valley, physically plausible light, premium cinematic realism, no text, no logo, no watermark",
    "an original AI-generated open Bible on weathered olive wood beside a clay oil lamp, pages moving naturally, premium photoreal cinema, no readable text",
    "a simple wooden cross on a distant hill after rain while storm clouds open to warm sunlight, original synthetic cinematic scene, no people, no text",
    "living water flowing through dark stones toward warm sunrise light, symbolic biblical hope, original AI photoreal scene, no people, no text",
    "an empty ancient stone path leading toward dawn between olive trees, historically inspired biblical atmosphere, original synthetic photography look",
    "a white dove crossing a dramatic but peaceful sky above a river valley, realistic anatomy, original AI cinematic frame, no text",
    "a small lamb resting safely near an adult sheep in a green field at golden hour, realistic animals, symbolic biblical imagery, original AI scene",
    "a modest church interior with empty wooden pews and natural sunlight entering through a window, cinematic realism, no text, no logos",
    "hands offering water to another person in a simple act of compassion, faces outside frame, premium realistic synthetic cinema, no text",
    "a person seen from behind on a mountain trail before sunrise, universal human silhouette, hopeful cinematic realism, no identifiable real person",
    "a quiet bedroom at blue hour with an open Bible beside a glass of water, intimate realistic AI-generated scene, no readable text",
    "rain ending over a vast green valley with a subtle natural rainbow in distant mist, premium photoreal synthetic landscape",
    "a single new plant growing between stones after rain, macro cinematic realism, symbolic renewal, original AI-generated frame",
    "a calm shoreline after a storm with waves becoming gentle under breaking sunlight, premium cinematic synthetic photography",
    "a star-filled night sky above a silent desert valley with one warm oil lamp in the foreground, reverent original AI scene",
    "ancient stone doorway opening toward a bright valley, symbolic new beginning, premium photoreal AI cinema, no text",
    "olive branches moving in wind beside a clay cup and simple bread on a wooden table, biblical everyday symbolism, original synthetic photograph",
    "snowy Norwegian mountains and a still fjord beneath aurora light, awe of creation, photoreal AI-generated cinematic landscape",
    "a powerful waterfall in a mossy canyon with natural spray catching sunlight, creation and hope, original synthetic cinematic photograph",
    "warm rays entering an old forest and illuminating mist between trees, quiet spiritual symbolism, premium original AI scene",
    "a small boat on calm water before sunrise viewed from shore, symbolic trust and journey, historically neutral, photoreal AI cinema",
    "two people sitting at a respectful distance in supportive conversation, faces not identifiable, warm natural light, original synthetic cinema",
    "a candle beside closed hands resting calmly on a table, quiet prayer symbolism, premium photoreal AI-generated frame, no text",
    "a long road through dry landscape reaching green hills under changing weather, symbolic perseverance, original AI cinematic realism",
)

JESUS_MOTIFS = (
    "recurring synthetic Jesus walking beside the Sea of Galilee at dawn, compassionate adult male, natural linen clothing, realistic human anatomy, premium live-action cinematic look",
    "recurring synthetic Jesus seated beside an olive tree listening with a calm compassionate expression, natural daylight, premium photoreal biblical cinema",
    "recurring synthetic Jesus extending an open hand beside living water, medium three-quarter shot, realistic skin and fabric, reverent cinematic realism",
    "recurring synthetic Jesus walking along a mountain path after rain, wide environmental portrait, natural wind in linen robe, photoreal cinematic scene",
    "recurring synthetic Jesus beside an open Scripture in a quiet stone room near morning light, intimate realistic biblical cinema, no readable text",
    "recurring synthetic Jesus on a shoreline as storm clouds begin to clear, restrained hopeful expression, natural waves and light, premium photoreal cinema",
    "recurring synthetic Jesus speaking gently on a green hillside with distant listeners out of focus, documentary biblical cinema, natural daylight",
    "recurring synthetic Jesus standing beneath a starry sky before dawn, side profile, warm oil lamp nearby, reverent photoreal cinematic realism",
)

THUMBNAIL_MOTIFS = (
    "close emotional composition with a recurring synthetic Jesus in three-quarter profile and strong natural eye light, dramatic sky opening behind him, premium photoreal cinematic thumbnail, no text",
    "wide symbolic cross silhouette above clouds with a single beam of sunrise light, high visual contrast, premium photoreal AI thumbnail, no text",
    "open Bible and warm oil lamp in foreground with storm clearing outside a window, cinematic depth, premium realistic AI thumbnail, no readable text",
    "recurring synthetic Jesus extending an open hand toward camera beside a bright natural horizon, realistic skin and fabric, premium cinematic thumbnail, no text",
    "lone person from behind facing a huge sunrise over mountains, hopeful universal composition, premium photoreal AI thumbnail, no text",
    "calm water reflecting golden light beneath dramatic clouds, simple cross far in background, premium symbolic AI thumbnail, no text",
)


def _seed(previous: list[dict]) -> int:
    run = os.getenv("GITHUB_RUN_ID", "") or os.getenv("GITHUB_RUN_NUMBER", "")
    nonce = os.getenv("DIOS_SOVEREIGN_VARIATION_NONCE", "")
    raw = f"{ENGINE_VERSION}|{run}|{nonce}|{len(previous)}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16], 16)


def _recent_prompt_hashes(previous: list[dict], limit: int = 45) -> set[str]:
    result: set[str] = set()
    for row in previous[-limit:]:
        for value in row.get("visual_prompt_hashes") or []:
            if str(value).strip():
                result.add(str(value).strip())
    return result


def _hash_prompt(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _fresh_prompts(previous: list[dict], seed: int, count: int) -> list[str]:
    used = _recent_prompt_hashes(previous)
    pool = list(VISUAL_MOTIFS) + list(JESUS_MOTIFS)
    prompts: list[str] = []
    local_hashes: set[str] = set()
    start = seed % len(pool)
    step = 11
    for offset in range(len(pool) * 2):
        base = pool[(start + offset * step) % len(pool)]
        variant = (
            f"{base}; camera variation {(seed + offset) % 9}; lighting variation {(seed // 7 + offset) % 8}; "
            f"composition fingerprint {hashlib.sha256(f'{seed}:{offset}'.encode()).hexdigest()[:10]}"
        )
        ph = _hash_prompt(variant)
        if ph in used or ph in local_hashes:
            continue
        prompts.append(variant)
        local_hashes.add(ph)
        if len(prompts) >= count:
            return prompts
    raise RuntimeError("PREMIUM_V8: no se pudieron construir suficientes prompts visuales unicos.")


def generate_metadata(channel: dict, previous: list[dict], retries: int = 5) -> dict:
    metadata = v7.generate_metadata(channel, previous, retries=retries)
    seed = _seed(previous)
    scenes = list(metadata.get("scenes") or [])
    prompts = _fresh_prompts(previous, seed, len(scenes))

    for index, scene in enumerate(scenes):
        scene["visual_prompt"] = prompts[index]
        scene["stock_query"] = "cinematic biblical hope nature faith"

    hook = BROAD_HOOKS[seed % len(BROAD_HOOKS)]
    if scenes:
        original = str(scenes[0].get("narration") or "").strip()
        scenes[0]["narration"] = f"{hook} {original}"
        metadata["hook"] = scenes[0]["narration"]

    thumb = THUMBNAIL_MOTIFS[(seed // 13) % len(THUMBNAIL_MOTIFS)]
    thumb = f"{thumb}; unique thumbnail fingerprint {hashlib.sha256(f'thumb:{seed}'.encode()).hexdigest()[:12]}"

    metadata["scenes"] = scenes
    metadata["visual_prompt_hashes"] = [_hash_prompt(item) for item in prompts]
    metadata["thumbnail_prompt"] = thumb
    metadata["thumbnail_prompt_hash"] = _hash_prompt(thumb)
    metadata["visual_engine_version"] = ENGINE_VERSION
    metadata["premium_editorial_version"] = ENGINE_VERSION
    metadata["audience_bridge_mode"] = "believers_seekers_and_nonbelievers_without_pressure"
    metadata["synthetic_media_disclosure"] = "ai_generated_symbolic_biblical_visuals"
    metadata["viral_quality_policy"] = "strong_opening_relevance_emotional_clarity_biblical_grounding_no_false_promises"
    return metadata


def restore_unique_packaging(metadata: dict, previous: list[dict] | None = None) -> dict:
    metadata = v7.restore_unique_packaging(metadata, previous)
    metadata["premium_editorial_version"] = ENGINE_VERSION
    metadata["visual_engine_version"] = ENGINE_VERSION
    return metadata
