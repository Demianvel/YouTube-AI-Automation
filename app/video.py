from __future__ import annotations

import hashlib
import math
import os
import random
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "procedural").lower().strip()
VIDEO_MODEL = os.getenv("GEMINI_VIDEO_MODEL", "veo-3.1-generate-preview")
VIDEO_RESOLUTION = os.getenv("VIDEO_RESOLUTION", "720p")
W, H, FPS = 720, 1280, 12


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


def _plant(frame, progress: float, seed: int, frame_no: int):
    d = ImageDraw.Draw(frame)
    soil = int(H * 0.58)
    d.rectangle((0, soil, W, H), fill=(82, 55, 35))
    rng = random.Random(seed + frame_no // 5)
    for _ in range(45):
        x, y, r = rng.randrange(W), rng.randrange(soil, H), rng.randrange(1, 5)
        d.ellipse((x-r, y-r, x+r, y+r), fill=(104, 74, 47))
    cx, sy = W // 2, soil + 70
    scale = max(.25, 1 - progress * .8)
    sw, sh = int(72 * scale), int(42 * scale)
    d.ellipse((cx-sw, sy-sh, cx+sw, sy+sh), fill=(129, 82, 45), outline=(80, 45, 25), width=5)
    if progress > .08:
        rp = min(1, (progress - .08) / .30)
        pts = [(cx + int(math.sin(i/29*7+1.4)*16*i/29), sy + int(280*rp*i/29)) for i in range(30)]
        d.line(pts, fill=(225, 215, 165), width=10)
    if progress <= .20:
        return
    sp = min(1, (progress - .20) / .60)
    stem_h = int(620 * sp)
    top = soil - stem_h
    d.line((cx, soil+30, cx, top), fill=(57, 126, 57), width=18)
    count = 2 + int(sp * 8)
    for i in range(count):
        frac = (i + 1) / (count + 1)
        y = int(soil - stem_h * frac)
        side = -1 if i % 2 == 0 else 1
        lx = cx + side * int(80 + 25 * math.sin(i))
        d.ellipse((lx-85, y-48, lx+85, y+48), fill=(54, 151, 69), outline=(33, 103, 45), width=5)
        d.line((cx, y, lx, y), fill=(57, 126, 57), width=8)
    if sp > .78:
        fp = (sp - .78) / .22
        r, fy = int(20 + 65 * fp), max(110, top-20)
        for p in range(7):
            a = p * 2 * math.pi / 7
            px, py = cx + int(math.cos(a)*r*.9), fy + int(math.sin(a)*r*.9)
            pr = max(8, int(r*.55))
            d.ellipse((px-pr, py-pr, px+pr, py+pr), fill=(245, 194, 62))
        d.ellipse((cx-r//2, fy-r//2, cx+r//2, fy+r//2), fill=(107, 69, 39))


def _finance(frame, progress: float, meta: dict):
    d = ImageDraw.Draw(frame)
    for y in range(180, H, 120):
        d.line((55, y, W-55, y), fill=(42, 55, 72), width=2)
    baseline, bw, gap, start = H-250, 105, 55, 90
    for i, val in enumerate([.44, .66, .88, .76]):
        local = max(0, min(1, progress*1.4-i*.08))
        hh, x = int(520*val*local), start+i*(bw+gap)
        d.rounded_rectangle((x, baseline-hh, x+bw, baseline), radius=22, fill=(54+i*18, 142, 190-i*14))
    pts = []
    for i in range(5):
        local = max(0, min(1, progress*1.25-i*.05))
        x, yt = 70+i*145, 720-i*105+int(math.sin(i*1.8)*50)
        pts.append((x, int(720+(yt-720)*local)))
    for i in range(1, len(pts)):
        if progress > i*.08:
            d.line((pts[i-1], pts[i]), fill=(255, 212, 90), width=10)
    hook = (meta.get("hook") or meta.get("title") or "Dinero claro").strip()
    narration = [s.get("narration", "").strip() for s in meta.get("scenes", []) if s.get("narration")]
    idx = min(len(narration)-1, int(progress*len(narration))) if narration else -1
    title_f, body_f = _font(50, True), _font(36)
    y = 95
    for line in _wrap(d, hook, title_f, W-100):
        box = d.textbbox((0, 0), line, font=title_f)
        x = (W-(box[2]-box[0]))//2
        d.text((x, y), line, font=title_f, fill=(245, 248, 252))
        y += 62
    if idx >= 0:
        lines = _wrap(d, narration[idx], body_f, W-120)
        by = 860
        d.rounded_rectangle((45, by-25, W-45, by+58*len(lines)+35), radius=28, fill=(14, 22, 32))
        for line in lines:
            d.text((70, by), line, font=body_f, fill=(235, 240, 245))
            by += 55


def _audio(video: Path, out: Path, channel: dict, meta: dict, duration: int):
    text = " ... ".join(s.get("narration", "").strip() for s in meta.get("scenes", []) if s.get("narration", "").strip())
    wav = out.with_name("narration.wav")
    speaker = "espeak-ng" if subprocess.run(["bash", "-lc", "command -v espeak-ng"], capture_output=True).returncode == 0 else "espeak"
    has_voice = False
    if text:
        try:
            subprocess.run([speaker, "-v", "es", "-s", "145", "-w", str(wav), text], check=True)
            has_voice = wav.exists()
        except Exception:
            pass
    noise = "brown" if channel["handle"].lower().startswith("@brotavida") else "pink"
    if has_voice:
        cmd = ["ffmpeg","-y","-loglevel","error","-i",str(video),"-i",str(wav),"-f","lavfi","-i",f"anoisesrc=color={noise}:amplitude=0.012:d={duration}",
               "-filter_complex",f"[1:a]apad=pad_dur={duration}[a1];[2:a]volume=.22[a2];[a1][a2]amix=inputs=2:duration=longest[a]",
               "-map","0:v:0","-map","[a]","-t",str(duration),"-c:v","copy","-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)]
    else:
        cmd = ["ffmpeg","-y","-loglevel","error","-i",str(video),"-f","lavfi","-i",f"anoisesrc=color={noise}:amplitude=0.012:d={duration}",
               "-map","0:v:0","-map","1:a:0","-t",str(duration),"-c:v","copy","-c:a","aac","-b:a","128k","-movflags","+faststart",str(out)]
    subprocess.run(cmd, check=True)


def _procedural(channel: dict, meta: dict, out: Path):
    duration = channel["scenes_per_short"] * channel["scene_seconds"]
    frames, seed = duration * FPS, _seed(meta)
    plant = channel["handle"].lower().startswith("@brotavida")
    base = _gradient((152, 211, 229), (230, 242, 210)) if plant else _gradient((17, 27, 40), (9, 16, 27))
    silent = out.with_name("visual_only.mp4")
    cmd = ["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an",
           "-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p","-movflags","+faststart",str(silent)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for n in range(frames):
            p = n / max(1, frames-1)
            frame = base.copy()
            _plant(frame, p, seed, n) if plant else _finance(frame, p, meta)
            proc.stdin.write(frame.tobytes())
    finally:
        if proc.stdin:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg procedural renderer fallo")
    _audio(silent, out, channel, meta, duration)


def _veo(channel: dict, meta: dict, workdir: Path, final: Path):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    files = []
    for i, scene in enumerate(meta["scenes"]):
        narration = (scene.get("narration") or "").strip()
        audio = f'Native audio. Calm Argentine Spanish narrator says exactly: "{narration}".' if narration else "Native ambient audio only."
        prompt = f"Vertical YouTube Short scene {i+1}/{channel['scenes_per_short']}. {scene['visual_prompt']} {audio} No logos, watermarks or on-screen text."
        op = client.models.generate_videos(model=VIDEO_MODEL, prompt=prompt, config=types.GenerateVideosConfig(
            aspect_ratio="9:16", duration_seconds=channel["scene_seconds"], resolution=VIDEO_RESOLUTION, number_of_videos=1))
        while not op.done:
            time.sleep(10)
            op = client.operations.get(op)
        if not op.response or not op.response.generated_videos:
            raise RuntimeError(f"Veo no devolvio video para escena {i+1}")
        g = op.response.generated_videos[0]
        client.files.download(file=g.video)
        f = workdir / f"scene_{i+1}.mp4"
        g.video.save(str(f))
        files.append(f)
    manifest = workdir / "concat.txt"
    manifest.write_text("\n".join(f"file '{p.resolve()}'" for p in files), encoding="utf-8")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(manifest),"-vf",
                    "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
                    "-c:v","libx264","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-movflags","+faststart",str(final)], check=True)


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
