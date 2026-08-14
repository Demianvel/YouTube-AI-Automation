from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _enabled() -> bool:
    return os.getenv("SPIRITUAL_LIPSYNC_ENABLED", "true").lower().strip() == "true"


def _musetalk_dir() -> Path | None:
    raw = os.getenv("MUSETALK_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    return path if path.exists() else None


def available() -> bool:
    """MuseTalk is used only when a prepared CUDA/GPU runner is available."""
    if not _enabled():
        return False
    root = _musetalk_dir()
    if root is None:
        return False
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _latest_mp4(root: Path) -> Path | None:
    files = [p for p in root.rglob("*.mp4") if p.is_file() and p.stat().st_size > 50_000]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def apply_musetalk_lipsync(video: Path, audio: Path, out: Path) -> str:
    """Apply official MuseTalk v1.5 to a generated synthetic human video.

    The source video already contains head/hand/body motion from the video model;
    MuseTalk changes the facial mouth region to follow the real narration audio.
    A CUDA runner with a prepared official MuseTalk checkout and weights is required.
    """
    if not available():
        raise RuntimeError("MuseTalk no esta disponible: se requiere MUSETALK_DIR preparado y un runner con CUDA/GPU.")

    root = _musetalk_dir()
    assert root is not None
    work = out.parent / "musetalk_work"
    work.mkdir(parents=True, exist_ok=True)
    source25 = work / "source_25fps.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", "fps=25", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", str(source25),
    ], check=True)

    config = work / "dioshablahoyia_musetalk.yaml"
    config.write_text(
        "task_0:\n"
        f"  video_path: \"{source25.resolve()}\"\n"
        f"  audio_path: \"{audio.resolve()}\"\n",
        encoding="utf-8",
    )

    result_dir = work / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    version = os.getenv("MUSETALK_VERSION", "v15").strip() or "v15"
    if version == "v1":
        unet_model = root / "models" / "musetalk" / "pytorch_model.bin"
        unet_config = root / "models" / "musetalk" / "musetalk.json"
    else:
        version = "v15"
        unet_model = root / "models" / "musetalkV15" / "unet.pth"
        unet_config = root / "models" / "musetalkV15" / "musetalk.json"

    if not unet_model.exists() or not unet_config.exists():
        raise RuntimeError("Faltan los pesos oficiales de MuseTalk en MUSETALK_DIR/models.")

    bbox_shift = os.getenv("MUSETALK_BBOX_SHIFT", "0").strip() or "0"
    cmd = [
        sys.executable,
        "-m", "scripts.inference",
        "--inference_config", str(config),
        "--result_dir", str(result_dir),
        "--unet_model_path", str(unet_model),
        "--unet_config", str(unet_config),
        "--version", version,
        "--bbox_shift", bbox_shift,
    ]
    ffmpeg_path = os.getenv("MUSETALK_FFMPEG_PATH", "").strip()
    if ffmpeg_path:
        cmd.extend(["--ffmpeg_path", ffmpeg_path])

    timeout = int(os.getenv("MUSETALK_TIMEOUT_SECONDS", "3600"))
    subprocess.run(cmd, cwd=str(root), check=True, timeout=timeout)
    generated = _latest_mp4(result_dir)
    if generated is None:
        raise RuntimeError("MuseTalk termino sin producir un MP4 valido.")

    normalized = work / "lipsynced_30fps.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(generated),
        "-vf", "fps=30", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(normalized),
    ], check=True)
    shutil.copy2(normalized, out)
    if not out.exists() or out.stat().st_size < 50_000:
        raise RuntimeError("MuseTalk no produjo un video de lip-sync valido.")
    return "MuseTalk v1.5 audio-driven lip-sync"
