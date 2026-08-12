from __future__ import annotations

import hashlib
import math
import os
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .audio import apply_audio
from .botanical import draw_plant

VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "veo").lower().strip()
VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "veo-3.1-generate-preview")
VIDEO_RESOLUTION = os.getenv("VIDEO_RESOLUTION", "1080p")
W, H, FPS = 720, 1280, 15


def _font(size: int, bold: bool = False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def _seed(meta: dict) -> int:
    raw = f"{meta.get('topic','')}|{meta.get('title','')}|{meta.get('hook','')}"
    return int(hashlib.sha256(raw.encode()).hexdigest()[:16], 16)


def _gradient(top, bottom):
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        d.line((0, y, W, y), fill=c)
    return img


def _wrap(draw, text: str, font, max_width: int):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        box = draw.textbbox((0, 0), trial, font=font)
        if box[2] - box[0] <= max_width:
            cur = trial
        elif cur:
            lines.append(cur)
            cur = word
        else:
            lines.append(word)
            cur = ""
    if cur:
        lines.append(cur)
    return lines[:5]


def _finance(frame: Image.Image, progress: float, meta: dict) -> None:
    d = ImageDraw.Draw(frame)
    topic = f"{meta.get('topic','')} {meta.get('title','')}".lower()
    business = any(k in topic for k in ("emprend", "negocio", "ventas", "margen", "cost", "precio", "inventario", "reinversion"))
    for y in range(180, H, 120):
        d.line((55, y, W - 55, y), fill=(42, 55, 72), width=2)
    if business:
        base_y = H - 250
        for i in range(4):
            x = 70 + i * 150
            h = int((180 + i * 65) * min(1, progress * 1.2))
            d.rounded_rectangle((x, base_y - h, x + 105, base_y), radius=18, fill=(52 + i * 16, 132 + i * 8, 174 - i * 10))
    else:
        baseline, bw, gap, start = H - 250, 105, 55, 90
        for i, val in enumerate([.44, .66, .88, .76]):
            local = max(0, min(1, progress * 1.4 - i * .08))
            hh, x = int(520 * val * local), start + i * (bw + gap)
            d.rounded_rectangle((x, baseline - hh, x + bw, baseline), radius=22, fill=(54 + i * 18, 142, 190 - i * 14))
    hook = (meta.get("hook") or meta.get("title") or "Dinero claro").strip()
    title_f = _font(50, True)
    y = 90
    for line in _wrap(d, hook, title_f, W - 100):
        box = d.textbbox((0, 0), line, font=title_f)
        x = (W - (box[2] - box[0])) // 2
        d.text((x, y), line, font=title_f, fill=(245, 248, 252))
        y += 62


def _procedural(channel: dict, meta: dict, out: Path) -> None:
    """Local fallback for testing only. Production is configured to use Veo."""
    duration = channel["scenes_per_short"] * channel["scene_seconds"]
    frames, seed = duration * FPS, _seed(meta)
    plant = "botanical" in channel.get("visual_mode", "")
    base = _gradient((150, 211, 229), (229, 242, 210)) if plant else _gradient((17, 27, 40), (9, 16, 27))
    silent = out.with_name("visual_only.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(silent)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(frames):
            p = n / max(1, frames - 1)
            frame = base.copy()
            if plant:
                draw_plant(frame, p, seed, n, meta, W, H)
            else:
                _finance(frame, p, meta)
            if not proc.stdin:
                raise RuntimeError("ffmpeg cerro la entrada antes de tiempo")
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg procedural renderer fallo")
    apply_audio(silent, out, channel, meta, duration, seed)


def _veo(channel: dict, meta: dict, workdir: Path, final: Path) -> None:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    files = []
    botanical = "botanical" in channel.get("visual_mode", "")

    for i, scene in enumerate(meta["scenes"]):
        if botanical:
            style = (
                "Photorealistic live-action macro nature documentary footage. Real botanical anatomy, real moist soil, "
                "natural sunlight, realistic lens depth of field. Continuous biological time-lapse of the SAME real plant. "
                "It must look like genuine camera footage, not a drawing, not animation, not cartoon, not stylized CGI, not plastic. "
                "Show seed germination, roots, sprout, leaves and mature plant continuously within the 8-second shot. "
            )
        else:
            style = (
                "Photorealistic live-action financial and small-business B-roll, natural lighting, believable hands and objects, "
                "realistic camera movement and documentary/commercial photography. No cartoon, no illustration, no obvious CGI. "
            )

        prompt = (
            f"Vertical 9:16 YouTube Short scene {i + 1}/{channel['scenes_per_short']}. "
            f"{style}{scene['visual_prompt']} Maintain continuity with adjacent scenes. "
            "Visual footage only: no speech, no narration, no dialogue, no lyrics. No logos, watermarks or embedded subtitles."
        )
        op = client.models.generate_videos(
            model=VIDEO_MODEL,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                duration_seconds=channel["scene_seconds"],
                resolution=VIDEO_RESOLUTION,
                number_of_videos=1,
            ),
        )
        while not op.done:
            time.sleep(10)
            op = client.operations.get(op)
        if not op.response or not op.response.generated_videos:
            raise RuntimeError(f"Veo no devolvio video para escena {i + 1}")

        generated = op.response.generated_videos[0]
        client.files.download(file=generated.video)
        scene_file = workdir / f"scene_{i + 1}.mp4"
        generated.video.save(str(scene_file))
        files.append(scene_file)

    manifest = workdir / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in files), encoding="utf-8")
    visual = workdir / "veo_visual_only.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(manifest),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-an", "-c:v", "libx264", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(visual),
        ],
        check=True,
    )
    duration = channel["scenes_per_short"] * channel["scene_seconds"]
    apply_audio(visual, final, channel, meta, duration, _seed(meta))


def generate_short(channel: dict, metadata: dict, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    final = workdir / "short.mp4"
    if VIDEO_PROVIDER == "procedural":
        _procedural(channel, metadata, final)
    elif VIDEO_PROVIDER == "veo":
        _veo(channel, metadata, workdir, final)
    else:
        raise ValueError(f"VIDEO_PROVIDER no soportado: {VIDEO_PROVIDER}")
    return final
