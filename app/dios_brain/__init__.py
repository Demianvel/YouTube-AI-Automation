"""Dios Brain: small editorial agents for Dios Habla Hoy IA Shorts.

Roles (each a module):
* strategist – picks pillar + biblical theme (rotation, history, analytics).
* writer     – hook-first script, SEO title/description/hashtags/tags.
* cta        – rotating soft calls to action (spoken + description).
* editor     – quality/policy gate (repetition, length, YouTube policies).
* analyst    – records variants and prefers winners (UCB1) when data exists.

Everything is fail-open: on any error the publisher keeps its existing behavior.
"""
from .core import BRAIN_VERSION, apply_brain_packaging, brain_choose_theme, enabled, record_fields

__all__ = ["BRAIN_VERSION", "apply_brain_packaging", "brain_choose_theme", "enabled", "record_fields"]
