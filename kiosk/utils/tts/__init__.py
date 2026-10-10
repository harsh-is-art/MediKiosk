"""TTS Provider — Text-to-Speech factory."""

from .sarvam_tts import SarvamTTSProvider
try:
    from .chatterbox_tts import ChatterboxTTSProvider
except Exception as e:
    # If Chatterbox imports fail (e.g., missing dependencies), we fallback to Sarvam.
    ChatterboxTTSProvider = None


def get_tts_provider():
    """
    Factory: returns default TTS provider (Sarvam AI Speech Synthesis).
    """
    return SarvamTTSProvider()
