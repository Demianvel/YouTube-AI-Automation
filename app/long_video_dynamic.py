from __future__ import annotations

import subprocess
from pathlib import Path

from . import long_video as base
from .audio import make_pleasant_original_music


def generate_long_video(channel: dict, meta: dict, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    chapters = meta.get("chapters") or []
    chapter_seconds = int(meta.get("chapter_seconds") or 30)
    duration = int(meta.get("duration_seconds") or 600)
    expected = duration // chapter_seconds
    if len(chapters) != expected:
        raise RuntimeError(f"El video largo requiere exactamente {expected} capitulos; llegaron {len(chapters)}.")

    # Reutilizamos los selectores de metraje real/voz ya probados, pero con duracion dinamica.
    base.CHAPTER_SECONDS = chapter_seconds
    base.TOTAL_SECONDS = duration

    used_pexels: set[int] = set()
    used_commons: set[str] = set()
    clips: list[Path] = []
    credits: list[dict[str, str]] = []
    for index, chapter in enumerate(chapters):
        clip, credit = base._get_real_clip(channel, meta, chapter, index, workdir, used_pexels, used_commons)
        clips.append(clip)
        credits.append(credit)

    visual_manifest = workdir / "long_visual_concat.txt"
    visual_manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in clips), encoding="utf-8")
    visual = workdir / f"long_visual_{duration // 60}min.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(visual_manifest),
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(visual),
    ], check=True)

    voices, used_tts = base._generate_chapter_voices(meta, workdir)
    voice_full = base._normalize_voice_segments(voices, workdir)
    music = workdir / "long_music.wav"
    make_pleasant_original_music(music, duration, base._seed(meta, 999))

    final = workdir / f"video_{duration // 60}min.mp4"
    music_volume = "0.026" if "botanical" in channel.get("visual_mode", "") else "0.020"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(visual), "-i", str(voice_full), "-i", str(music),
        "-filter_complex", f"[1:a]volume=1.0[v];[2:a]volume={music_volume}[m];[v][m]amix=inputs=2:duration=first:dropout_transition=1[a]",
        "-map", "0:v:0", "-map", "[a]", "-t", str(duration),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final),
    ], check=True)

    meta["source_credits"] = credits
    meta["tts_provider_used"] = used_tts
    meta["render_quality"] = "1920x1080_30fps_premium"
    return final
