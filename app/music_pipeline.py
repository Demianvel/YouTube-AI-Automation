from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from .acestep_client import generate_song
from .acestep_space import generate_song_space
from .channel_analytics import analytics_digest, collect_channel_analytics
from .config import OUTPUT_DIR, load_channel
from .music_audio import generate_original_electronic_track
from .music_generator import generate_music_metadata
from .music_video import render_music_video
from .thumbnail import generate_thumbnail_variants
from .youtube import upload_long_video, upload_video


def _ace_prompt(meta: dict) -> str:
    style = str(meta.get("music_style") or "pop_electronic")
    vocal = str(meta.get("vocal_character") or "voz calida, magnetica y original")
    faith = " Christian/faith-positive atmosphere, hopeful and respectful." if meta.get("faith_theme") else ""
    return (
        f"Original {style} song for DemianVelo. {vocal}. Spanish lyrics, charismatic lead vocal, "
        "memorable but original melodic phrasing, polished modern production, professional dynamics, "
        "clean stereo master, natural vocal phrasing, clear lead voice, wide but controlled mix, "
        "no imitation of any real singer, no copyrighted melody or sample." + faith
    )


def run(
    minutes: int,
    publish: bool = False,
    manual_style: str = "",
    lyrics: str = "",
    vocal_character: str = "",
    music_engine: str = "auto",
) -> dict:
    channel = load_channel("demianvelo")
    lyrics = lyrics.strip() or os.getenv("DEMIANVELO_LYRICS", "").strip()
    vocal_character = vocal_character.strip() or os.getenv("DEMIANVELO_VOCAL_CHARACTER", "").strip()
    music_engine = (music_engine or "auto").strip().lower()
    if music_engine not in {"auto", "local", "acestep"}:
        raise ValueError("music_engine debe ser auto, local o acestep.")

    try:
        snapshot = collect_channel_analytics(channel, days=90)
        channel["_analytics_digest"] = analytics_digest(snapshot)
    except Exception as exc:
        channel["_analytics_digest"] = "Analytics no disponible; explorar estilos de forma equilibrada y no inventar preferencias."
        print(f"DemianVelo Analytics no disponible: {exc}")

    meta = generate_music_metadata(
        channel,
        minutes,
        manual_style=manual_style,
        lyrics=lyrics,
        vocal_character=vocal_character,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    workdir = OUTPUT_DIR / "demianvelo" / f"{minutes}min" / stamp
    workdir.mkdir(parents=True, exist_ok=True)

    music = workdir / f"demianvelo_original_{minutes}min.wav"
    seed = abs(hash(f"{meta.get('title')}|{stamp}")) & 0x7FFFFFFF

    self_hosted_ace = bool(os.getenv("ACESTEP_API_URL", "").strip())
    hf_space_enabled = os.getenv("ACESTEP_HF_SPACE_ENABLED", "true").lower() == "true"
    use_ace = music_engine == "acestep" or (music_engine == "auto" and bool(lyrics) and (self_hosted_ace or hf_space_enabled))

    if use_ace:
        if self_hosted_ace:
            generate_song(
                music,
                prompt=_ace_prompt(meta),
                lyrics=lyrics,
                duration_seconds=int(meta["duration_seconds"]),
                bpm=int(meta.get("bpm") or 128),
                vocal_language="es",
                model=os.getenv("ACESTEP_MODEL", "acestep-v15-xl-turbo"),
            )
            meta["music_engine_used"] = "ACE-Step-1.5-self-hosted"
        elif hf_space_enabled:
            generate_song_space(
                music,
                prompt=_ace_prompt(meta),
                lyrics=lyrics,
                duration_seconds=int(meta["duration_seconds"]),
                bpm=int(meta.get("bpm") or 128),
                vocal_language="es",
            )
            meta["music_engine_used"] = "ACE-Step-1.5-XL-Turbo-HF-ZeroGPU"
        else:
            raise RuntimeError(
                "ACE-Step solicitado pero no hay servidor propio y ACESTEP_HF_SPACE_ENABLED=false."
            )
        meta["has_sung_vocals"] = bool(lyrics)
    else:
        if lyrics:
            raise RuntimeError(
                "Hay una letra del artista pero el motor local es instrumental y no debe ignorarla silenciosamente. "
                "Usa ACE-Step para una version cantada o ejecuta sin letra para instrumental."
            )
        generate_original_electronic_track(
            music,
            int(meta["duration_seconds"]),
            seed,
            bpm=int(meta.get("bpm") or 128),
            style=str(meta.get("music_style") or "progressive_house"),
            faith_theme=bool(meta.get("faith_theme")),
        )
        meta["music_engine_used"] = "local-original-synth"
        meta["has_sung_vocals"] = False

    video = render_music_video(meta, music, workdir)

    thumbnails = []
    if minutes > 1:
        thumbnails = generate_thumbnail_variants(video, meta, workdir)

    video_id = None
    status = "generated"
    if publish:
        if minutes == 1:
            video_id = upload_video(channel, meta, video)
        else:
            video_id = upload_long_video(
                channel,
                meta,
                video,
                thumbnail_path=thumbnails[0] if thumbnails else None,
                expected_minutes=minutes,
            )
        status = "uploaded"

    meta_file = workdir / "metadata.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "channel": "demianvelo",
        "handle": channel["handle"],
        "minutes": minutes,
        "title": meta.get("title"),
        "music_style": meta.get("music_style"),
        "music_engine_used": meta.get("music_engine_used"),
        "has_user_lyrics": bool(lyrics),
        "has_sung_vocals": meta.get("has_sung_vocals"),
        "faith_theme": meta.get("faith_theme"),
        "bpm": meta.get("bpm"),
        "video_id": video_id,
        "status": status,
        "video": str(video),
        "music": str(music),
        "analytics_used": bool(channel.get("_analytics_digest")),
    }
    (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", required=True, type=int, choices=[1, 5, 10, 30])
    parser.add_argument("--style", default="")
    parser.add_argument("--lyrics", default="")
    parser.add_argument("--vocal-character", default="")
    parser.add_argument("--music-engine", default="auto", choices=["auto", "local", "acestep"])
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    run(
        args.minutes,
        publish=args.publish,
        manual_style=args.style,
        lyrics=args.lyrics,
        vocal_character=args.vocal_character,
        music_engine=args.music_engine,
    )


if __name__ == "__main__":
    main()
