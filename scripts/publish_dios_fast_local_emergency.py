from __future__ import annotations

"""Compatibility shim for old recovery workflows.

This path used to switch Dios Habla Hoy to a local voice and procedural visuals.
That behavior is permanently retired. Any workflow that still invokes this file
now delegates to the locked Voz de Luz / Algenib + realistic reference publisher.
"""

from scripts.publish_dios_locked import main


if __name__ == "__main__":
    main()
