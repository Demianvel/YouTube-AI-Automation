"""Offline validator for Dios Brain, Voz de Luz voice config, render quality and the orchestrator.

No network and no Google/YouTube libraries needed (stdlib + repo code only).
Run: PYTHONPATH=. python scripts/validate_dios_brain.py
"""
from __future__ import annotations

import copy
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import dios_premium_editorial_v7 as v7  # noqa: E402
from app import render_quality, spiritual_tts  # noqa: E402
from app.dios_brain import analyst, core, cta, editor, writer  # noqa: E402
from app.dios_brain.pillars import PILLARS, classify_theme  # noqa: E402
from app.dios_brain.themes import EXTRA_THEMES  # noqa: E402

ALL_THEMES = tuple(v7.THEMES) + EXTRA_THEMES


def _base(theme: dict) -> dict:
    return {
        "title": "Titulo previo", "topic": f"{theme['family']} | {theme['reference']}",
        "bible_reference": theme["reference"], "description": "desc",
        "target_short_seconds": 60, "contains_synthetic_media": True,
        "scenes": [{"narration": "x", "visual_prompt": "Jesus"} for _ in range(6)],
        "_brain_theme": dict(theme),
    }


def test_every_theme_packages_cleanly() -> None:
    for wpm in ("110", "126"):
        os.environ["DIOS_NARRATION_WPM"] = wpm
        budget = writer.word_budget(60)
        for index, theme in enumerate(ALL_THEMES):
            for variant in range(2):
                meta = core._package(_base(theme), theme, classify_theme(theme), [], 1000 + index, variant, {})
                ok, reasons = editor.review(meta, [], budget)
                assert ok, (theme["reference"], wpm, reasons, meta["title"])
                assert len(meta["title"]) <= 70, meta["title"]
                assert meta["title"].startswith(PILLARS[meta["brain_pillar"]]["keyword"]), meta["title"]
                assert "#Shorts" in meta["hashtags"] and 3 <= len(meta["hashtags"]) <= 5
                lines = meta["description"].splitlines()
                assert lines[0].startswith(PILLARS[meta["brain_pillar"]]["keyword"])
                assert "No es la voz literal de Dios" in meta["description"]
                words = meta["brain_word_count"]
                assert budget[1] - 15 <= words <= budget[0] + 3, (theme["reference"], words, budget)
                assert meta["cta_spoken"] in meta["scenes"][-1]["narration"]
    os.environ.pop("DIOS_NARRATION_WPM", None)


def test_editor_rejects_policy_risks() -> None:
    theme = ALL_THEMES[0]
    good = core._package(_base(theme), theme, classify_theme(theme), [], 7, 0, {})
    bad_phrases = (
        "Dios te dice que hoy todo cambia.", "Compartilo o tendrás mala suerte.",
        "Esta oración te cura el cáncer.", "Dios te hará rico esta semana.",
        "El 12 de diciembre va a pasar el milagro.", "Si no compartís, perdés la bendición.",
    )
    for phrase in bad_phrases:
        meta = copy.deepcopy(good)
        meta["scenes"][2]["narration"] = phrase
        ok, reasons = editor.review(meta, [], writer.word_budget(60))
        assert not ok and reasons, phrase
    long_title = copy.deepcopy(good)
    long_title["title"] = "x" * 80
    assert not editor.review(long_title, [])[0]
    repeated = copy.deepcopy(good)
    history = [{"status": "uploaded", "title": good["title"], "video_id": "a"}]
    assert not editor.review(repeated, history)[0]


def test_fallbacks() -> None:
    original = {"title": "Una palabra de paz | Salmo 23", "bible_reference": "Referencia inexistente 99:99", "scenes": [{"narration": "Dios acompaña tu camino hoy."}]}
    out = core.apply_brain_packaging(copy.deepcopy(original), [], themes=())
    assert out["brain_status"] == "fallback_error", out.get("brain_status")
    assert out["title"] == original["title"]
    risky = dict(original, description="Dios te dice: compartí o mala suerte")
    try:
        core.apply_brain_packaging(risky, [], themes=())
    except RuntimeError as exc:
        assert "BLOQUEADO ANTI-SPAM" in str(exc)
    else:
        raise AssertionError("policy risk in fallback metadata was not blocked")
    os.environ["DIOS_BRAIN_ENABLED"] = "false"
    try:
        assert core.apply_brain_packaging({"title": "t"}, [])["brain_status"] == "disabled"
    finally:
        os.environ.pop("DIOS_BRAIN_ENABLED", None)


def test_rotation_simulation() -> None:
    history: list[dict] = []
    pillars: list[str] = []
    ctas: list[str] = []
    base_time = datetime.now(timezone.utc) - timedelta(days=3)
    for run in range(14):
        os.environ["GITHUB_RUN_ID"] = str(50_000 + run)
        result = core.brain_choose_theme(v7, history)
        assert result is not None, run
        theme, _ = result
        meta = _base(theme)
        meta["brain_pillar"] = classify_theme(theme)
        out = core.apply_brain_packaging(meta, history, themes=v7.THEMES)
        assert out["brain_status"] == "applied", out.get("brain_editor_reasons")
        pillars.append(out["brain_pillar"])
        ctas.append(out["brain_cta_id"])
        history.append({
            "status": "uploaded", "channel": "dioshablahoyia", "video_id": f"v{run}",
            "created_at": (base_time + timedelta(hours=run)).isoformat(),
            "title": out["title"], "topic": out["topic"], "bible_reference": theme["reference"],
            "narration_preview": " ".join(s["narration"] for s in out["scenes"]).lower()[:1200],
            **analyst.record_fields(out),
        })
    os.environ.pop("GITHUB_RUN_ID", None)
    assert all(a != b for a, b in zip(pillars, pillars[1:])), pillars
    assert len(set(pillars)) >= 5, pillars
    for i in range(2, len(ctas)):
        assert ctas[i] not in ctas[i - 2:i], ctas
    refs = [row["bible_reference"] for row in history]
    assert len(set(refs)) == len(refs), refs


def test_analyst_bandit() -> None:
    assert analyst.choose_arm(list(cta.CTA_ORDER), [], "brain_cta_id") is None
    now = datetime.now(timezone.utc)
    rows = []
    for i in range(12):
        arm = "amen" if i % 2 else "guardar"
        rows.append({"video_id": f"x{i}", "brain_cta_id": arm, "status": "uploaded",
                     "created_at": (now - timedelta(days=2)).isoformat(), "vph": 9.0 if arm == "amen" else 1.0})
    chosen = analyst.choose_arm(["amen", "guardar"], rows, "brain_cta_id")
    assert chosen == "amen", chosen
    summary = analyst.summarize(rows)
    assert summary["brain_cta_id"]["amen"][0] == 6


def test_voice_config() -> None:
    for key in ("DIOS_TTS_VOICE", "GEMINI_TTS_VOICE", "DIOS_TTS_VOICE_FALLBACKS", "GEMINI_TTS_MODEL", "GEMINI_TTS_MODEL_FALLBACKS"):
        os.environ.pop(key, None)
    assert spiritual_tts.configured_gemini_voice() == "Algieba"
    assert spiritual_tts.gemini_voice_chain() == ["Algieba", "Schedar"]
    assert spiritual_tts.gemini_tts_models() == ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview"]
    assert spiritual_tts.is_configured_gemini_provider("gemini-3.8-flash-tts:Algieba:voz_de_luz_serena_original_v1:x:v5")
    assert spiritual_tts.is_configured_gemini_provider("gemini-3.8-flash-tts:Schedar:voz_de_luz_serena_original_v1:x:v5")
    assert not spiritual_tts.is_configured_gemini_provider("kokoro:em_alex")
    os.environ["DIOS_TTS_VOICE"] = "Achird"
    try:
        assert spiritual_tts.gemini_voice_chain()[0] == "Achird"
    finally:
        os.environ.pop("DIOS_TTS_VOICE", None)
    prompt = spiritual_tts._voice_prompt("Texto", "Algieba", "biblical_reflection")
    assert "Voz de Luz" in prompt and "NEVER the literal voice of God" in prompt
    assert "slow" in prompt.lower() and "serene" in prompt.lower()


def test_render_quality() -> None:
    os.environ.pop("DIOS_RENDER_4K", None)
    assert render_quality.short_size() == (1080, 1920)
    assert render_quality.x264_crf() == 18 and render_quality.audio_bitrate() == "192k"
    os.environ["DIOS_RENDER_4K"] = "true"
    try:
        assert render_quality.short_size() == (2160, 3840)
    finally:
        os.environ.pop("DIOS_RENDER_4K", None)


def test_orchestrator_and_wiring() -> None:
    import yaml  # noqa: PLC0415 - optional, validated only when PyYAML is present
    from scripts.dios_orchestrator import build_plan

    assert build_plan(confirmed=0, due=3)["to_publish"] == 2
    assert build_plan(confirmed=3, due=3)["to_publish"] == 0
    assert build_plan(confirmed=9, due=10)["to_publish"] == 1
    assert build_plan(confirmed=10, due=10, manual_count=2)["to_publish"] == 0
    assert build_plan(confirmed=4, due=0, manual_count=1)["to_publish"] == 1

    workflows = ROOT / ".github" / "workflows"
    orch = yaml.safe_load((workflows / "dios-orchestrator.yml").read_text(encoding="utf-8"))
    on = orch.get(True) or orch.get("on")
    crons = [item["cron"] for item in on["schedule"]]
    fires = sum(len(c.split()[1].split(",")) for c in crons)
    assert fires == 10, crons
    assert "count" in on["workflow_dispatch"]["inputs"]
    assert orch["concurrency"]["cancel-in-progress"] is False
    assert orch["jobs"]["orchestrate"]["timeout-minutes"] <= 60
    assert orch["jobs"]["orchestrate"]["env"]["DIOS_RENDER_4K"] == "false"

    allowed = {
        "dios-orchestrator.yml", "dioshablahoyia-comment-responder.yml", "dioshablahoyia-playlist-sync.yml",
        "analytics-monitor.yml", "dioshablahoyia-growth-engine.yml", "dioshablahoyia-market-monitor.yml",
        "dioshablahoyia-visual-optimizer.yml",
    }
    for path in workflows.glob("*.yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        trig = data.get(True) or data.get("on") or {}
        if isinstance(trig, dict) and "schedule" in trig:
            assert path.name in allowed, f"publicador programado inesperado: {path.name}"

    hybrid = (ROOT / "scripts" / "publish_dios_hybrid.py").read_text(encoding="utf-8")
    assert "apply_brain_packaging" in hybrid and "is_configured_gemini_provider" in hybrid
    assert ":algenib:" not in hybrid


def main() -> None:
    tests = [
        test_every_theme_packages_cleanly, test_editor_rejects_policy_risks, test_fallbacks,
        test_rotation_simulation, test_analyst_bandit, test_voice_config, test_render_quality,
    ]
    try:
        import yaml  # noqa: F401
        tests.append(test_orchestrator_and_wiring)
    except ImportError:
        print("PyYAML no instalado: se omite la validacion de workflows.")
    for test in tests:
        test()
        print(f"OK {test.__name__}", flush=True)
    print(json.dumps({"status": "ok", "themes": len(ALL_THEMES), "pillars": sorted(PILLARS)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
