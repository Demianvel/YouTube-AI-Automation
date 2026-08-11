from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai import types

VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "veo-3.1-generate-preview")
VIDEO_RESOLUTION = os.getenv("VIDEO_RESOLUTION", "720p")


def _scene_prompt(channel: dict, scene: dict, index: int) -> str:
    narration = (scene.get("narration") or "").strip()
    audio = f'Native audio. Calm Argentine Spanish narrator says exactly: "{narration}".' if narration else "Native ambient audio only, no speech."
    return (
        f"Vertical YouTube Short scene {index + 1}/{channel['scenes_per_short']}. "
        f"{scene['visual_prompt']} "
        f"{audio} No subtitles, no captions, no logos, no watermarks, no on-screen text. "
        "Strong visual composition, clean subject separation, seamless ending suitable for concatenation."
    )


def generate_scene(client: genai.Client, channel: dict, scene: dict, index: int, out: Path) -> None:
    operation = client.models.generate_videos(
        model=VIDEO_MODEL,
        prompt=_scene_prompt(channel, scene, index),
        config=types.GenerateVideosConfig(
            aspect_ratio="9:16",
            duration_seconds=channel["scene_seconds"],
            resolution=VIDEO_RESOLUTION,
            number_of_videos=1,
        ),
    )
    while not operation.done:
        time.sleep(10)
        operation = client.operations.get(operation)
    if not operation.response or not operation.response.generated_videos:
        raise RuntimeError(f"Veo no devolvio video para la escena {index + 1}")
    generated = operation.response.generated_videos[0]
    client.files.download(file=generated.video)
    generated.video.save(str(out))


def concat_scenes(scene_files: list[Path], output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output_file.parent / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in scene_files), encoding="utf-8")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output_file),
    ]
    subprocess.run(cmd, check=True)


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    workdir.mkdir(parents=True, exist_ok=True)
    scene_files: list[Path] = []
    for index, scene in enumerate(metadata["scenes"]):
        out = workdir / f"scene_{index + 1}.mp4"
        generate_scene(client, channel, scene, index, out)
        scene_files.append(out)
    final = workdir / "short.mp4"
    concat_scenes(scene_files, final)
    return final
