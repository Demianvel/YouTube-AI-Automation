from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
REF_DIR = ROOT / "assets" / "dioshablahoyia" / "reference"
DEFAULT_OUT = ROOT / "models" / "dios_sovereign" / "training" / "jesus_identity"
REFERENCES = (
    "jesus_reference_a.jpg",
    "jesus_reference_b.jpg",
    "jesus_reference_c.jpg",
)
IDENTITY_TOKEN = "dhhjesus"


def _variant(source: Image.Image, seed: int, size: int) -> Image.Image:
    rng = random.Random(seed)
    image = source.convert("RGB")

    # Identity-safe augmentation: moderate crop, tiny rotation and restrained
    # photographic grade. No geometric face warping or horizontal flip.
    zoom = rng.uniform(1.00, 1.13)
    target = int(size * zoom)
    frame = ImageOps.fit(
        image,
        (target, target),
        method=Image.Resampling.LANCZOS,
        centering=(rng.uniform(0.45, 0.55), rng.uniform(0.43, 0.56)),
    )
    left = max(0, (frame.width - size) // 2 + rng.randint(-18, 18))
    top = max(0, (frame.height - size) // 2 + rng.randint(-18, 18))
    frame = frame.crop((left, top, left + size, top + size))

    angle = rng.uniform(-1.5, 1.5)
    frame = frame.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
    frame = ImageEnhance.Brightness(frame).enhance(rng.uniform(0.96, 1.04))
    frame = ImageEnhance.Contrast(frame).enhance(rng.uniform(0.97, 1.07))
    frame = ImageEnhance.Color(frame).enhance(rng.uniform(0.96, 1.06))
    if rng.random() < 0.35:
        frame = frame.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.1, 0.45)))
    return frame


def build(out_dir: Path, variants_per_reference: int, size: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    refs = [REF_DIR / name for name in REFERENCES]
    missing = [str(path) for path in refs if not path.exists()]
    if missing:
        raise SystemExit("Faltan referencias: " + ", ".join(missing))

    rows: list[dict] = []
    for ref_index, ref_path in enumerate(refs):
        with Image.open(ref_path) as opened:
            base = ImageOps.exif_transpose(opened).convert("RGB")
            for variant_index in range(variants_per_reference):
                seed_text = f"{ref_path.name}|{variant_index}|dhh-sovereign-v1"
                seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:12], 16)
                image = _variant(base, seed, size)
                name = f"{ref_path.stem}_{variant_index:03d}.jpg"
                destination = out_dir / name
                image.save(destination, format="JPEG", quality=95, subsampling=0, optimize=True)
                caption = (
                    f"{IDENTITY_TOKEN}, artistic photorealistic adult Jesus, realistic human face, "
                    "shoulder-length dark brown hair, groomed beard, compassionate expression, "
                    "natural skin texture, cream linen robe, premium live-action biblical cinema"
                )
                rows.append(
                    {
                        "file_name": name,
                        "text": caption,
                        "source_reference": ref_path.name,
                        "seed": seed,
                    }
                )

    metadata = out_dir / "metadata.jsonl"
    metadata.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "engine": "dhh-sovereign-v1",
        "identity_token": IDENTITY_TOKEN,
        "references": list(REFERENCES),
        "variants_per_reference": variants_per_reference,
        "image_count": len(rows),
        "size": size,
        "identity_safe_augmentation": True,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--variants-per-reference", type=int, default=48)
    parser.add_argument("--size", type=int, default=1024)
    args = parser.parse_args()
    variants = max(16, min(160, args.variants_per_reference))
    size = max(512, min(1536, args.size))
    manifest = build(Path(args.out), variants, size)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
