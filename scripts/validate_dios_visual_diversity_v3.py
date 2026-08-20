from __future__ import annotations

import json
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from app.dios_visual_integrity import validate_short_visuals
from app.spiritual_visual_motion import MOTION_PROFILE_NAMES, motion_profile
from app.visual_variety_v3 import attach_visual_pack_v3

ROOT = Path(__file__).resolve().parents[1]


def _sample_meta() -> dict:
    return {
        "topic": "esperanza y confianza en Dios",
        "title": "Dios sigue obrando aun cuando no lo ves",
        "bible_reference": "Isaías 41:10",
        "scenes": [{"visual_prompt": "placeholder"} for _ in range(6)],
    }


def _previous() -> list[dict]:
    return [
        {
            "channel": "dioshablahoyia",
            "visual_pack": [
                {"family": "norway", "scene": "Tromso winter fjord beneath vivid green and violet aurora borealis reflected on still water"},
                {"family": "jesus_and_prayer", "scene": "recurring synthetic Jesus praying alone beside an old olive tree with a peaceful natural expression"},
            ],
        },
        {
            "channel": "dioshablahoyia",
            "visual_pack": [
                {"family": "creation_and_nature", "scene": "clear river winding through a green valley with distant mountains and realistic moving clouds"},
                {"family": "symbols_of_faith", "scene": "simple wooden cross on a grassy hill above a sea of clouds"},
            ],
        },
    ]


def test_semantic_pack() -> None:
    meta = attach_visual_pack_v3(_sample_meta(), _previous())
    pack = meta["visual_pack"]
    families = [row["family"] for row in pack]
    scenes = [row["scene"].lower().strip() for row in pack]
    assert len(pack) == 6
    assert len(set(families)) == 6, families
    assert len(set(scenes)) == 6, scenes
    assert meta["visual_brand_anchor_forced"] is False
    assert meta["visual_no_repeat_window"] >= 40
    assert meta["visual_engine_version"].endswith("v3")


def _image(path: Path, invert: bool = False) -> None:
    image = Image.new("RGB", (1080, 1920), (25, 35, 60) if not invert else (220, 210, 180))
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 200, 980, 1720), fill=(160, 110, 70) if not invert else (40, 90, 140))
    draw.ellipse((260, 460, 820, 1020), fill=(235, 210, 175) if not invert else (30, 45, 70))
    image.save(path, "JPEG", quality=92)


def test_same_base_source_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        _image(workdir / "spiritual_generated_1.jpg", False)
        _image(workdir / "spiritual_generated_2.jpg", True)
        metadata = {
            "generated_visual_provider": [
                "local_project_jesus_reference/reference:jesus_reference_a.jpg/variant_01_of_30",
                "local_project_jesus_reference/reference:jesus_reference_a.jpg/variant_17_of_30",
            ]
        }
        try:
            validate_short_visuals(workdir, [], metadata)
        except RuntimeError as exc:
            assert "misma fuente base" in str(exc) or "mas de una escena" in str(exc)
        else:
            raise AssertionError("El guard permitio dos variantes de la misma foto base.")


def test_motion_profiles() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        labels = set()
        for index in range(12):
            path = root / f"img_{index}.jpg"
            _image(path, invert=index % 2 == 1)
            # Make the source digest different even when the basic drawing repeats.
            with path.open("ab") as fh:
                fh.write(f"seed-{index}".encode("utf-8"))
            profile, label = motion_profile(path, index=index, salt="validation")
            assert 0 <= profile < len(MOTION_PROFILE_NAMES)
            labels.add(label)
        assert len(labels) >= 5, labels


def test_wiring() -> None:
    fast = (ROOT / "scripts" / "publish_dios_fast.py").read_text(encoding="utf-8")
    emergency = (ROOT / "scripts" / "publish_dios_fast_local_emergency.py").read_text(encoding="utf-8")
    long = (ROOT / "scripts" / "publish_dios_long_fresh.py").read_text(encoding="utf-8")
    assert "attach_visual_pack_v3" in fast
    assert "render_still_motion" in fast
    assert "_fresh_free_media" in emergency
    assert "_local_first_download" not in emergency
    assert "apply_long_visual_diversity" in long
    assert "_fresh_long_motion" in long


def main() -> None:
    test_semantic_pack()
    test_same_base_source_blocked()
    test_motion_profiles()
    test_wiring()
    print(json.dumps({
        "status": "ok",
        "semantic_unique_families": 6,
        "same_base_source_blocked": True,
        "motion_profiles_available": len(MOTION_PROFILE_NAMES),
        "short_and_long_wiring": True,
    }))


if __name__ == "__main__":
    main()
