"""Voice package: TTS + alert templating."""

from __future__ import annotations

from bas_har.voice.alerts import format_alert_message
from bas_har.voice.tts import ConfirmationSound, TtsEngine

__all__ = ["ConfirmationSound", "TtsEngine", "format_alert_message"]
