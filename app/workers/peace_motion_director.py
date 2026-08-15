from __future__ import annotations

WORKER = {
    "id": "peace_motion_director",
    "name": "Director Paz Viva",
    "role": "direccion_audiovisual_lipsync_voz_movimiento",
    "owner": "performance_and_editing",
}


def performance_directive(spoken_line: str) -> str:
    return f"""
{WORKER['name']} is the professional performance and editing director.
The synthetic character speaks EXACTLY this Spanish line and nothing else: "{spoken_line}"

VOICE DIRECTION:
Adult male low warm baritone, deeply human, intimate, serene and compassionate. Neutral Latin-American Spanish. The voice must convey peace, love, hope, spiritual warmth and quiet strength. Natural breath, gentle pauses and emotionally present phrasing. Never robotic, never an announcer, never aggressive, never shouted, never exaggerated sermon delivery, never artificial cathedral echo.

FACE AND LIP SYNC:
Prioritize convincing audio-visual synchronization. Lip shapes, jaw opening, cheeks, chin, tongue visibility when appropriate and facial muscles must follow each phoneme naturally. No delayed mouth movement, no random lip motion, no frozen mouth while speech is audible. Preserve the same facial identity from first frame to last frame.

BODY PERFORMANCE:
Natural breathing, blinking, tiny eye refocusing, subtle head motion, realistic shoulder and torso weight shifts, one restrained open-hand gesture and a second gentle gesture only if it fits the sentence. Hands must have correct anatomy and five fingers. Gestures must begin and finish naturally with the spoken phrase, not loop mechanically.

EDITORIAL QUALITY:
One coherent cinematic performance. No sudden cuts during a spoken word, no duplicate character, no temporal face warping, no mannequin body, no jitter, no excessive slow motion. Natural ambience must remain below the voice. Any music must be original, extremely soft and emotionally supportive, never masking speech.
""".strip()


def apply_director_requirements(meta: dict) -> dict:
    meta["worker_motion_director"] = WORKER["name"]
    meta["worker_motion_director_id"] = WORKER["id"]
    meta["director_requires_lip_sync"] = True
    meta["director_requires_full_body_motion"] = True
    meta["director_requires_face_identity_stability"] = True
    meta["director_voice_emotion"] = "peace_love_hope_spiritual_warmth"
    meta["director_voice_style"] = "human_warm_low_baritone_latam"
    meta["director_professional_editing"] = True
    return meta
