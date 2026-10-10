"""
STT Provider — Swappable Speech-to-Text factory.

Usage:
    from kiosk.utils.stt import get_stt_provider
    provider = get_stt_provider()
    result = provider.transcribe('/path/to/audio.wav', 'en')
"""


# Django & Application Imports

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .base import STTProvider


# STT Provider Factory

def get_stt_provider() -> STTProvider:
    """
    Factory: returns the configured STT provider instance.
    """

    # Retrieve Configured STT Provider

    provider_name = getattr(settings, 'STT_PROVIDER', 'google')

    # Google Cloud Speech-to-Text Provider

    if provider_name == 'google':
        try:
            from .google_stt import GoogleSTTProvider
            return GoogleSTTProvider()
        except (ImproperlyConfigured, Exception) as e:
            import logging
            logging.getLogger(__name__).warning(f"Google Cloud STT initialization failed ({e}). Falling back to Sarvam AI STT.")
            try:
                from .sarvam import SarvamSTTProvider
                return SarvamSTTProvider()
            except Exception:
                raise e

    # Bhashini Speech-to-Text Provider

    elif provider_name == 'bhashini':
        try:
            from .bhashini import BhashiniSTTProvider
            return BhashiniSTTProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "Bhashini STT selected but 'requests' is not installed.\n"
                "Install it with: pip install requests"
            )

    # Sarvam AI Speech-to-Text Provider

    elif provider_name == 'sarvam':
        try:
            from .sarvam import SarvamSTTProvider
            return SarvamSTTProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "Sarvam AI STT selected but 'requests' is not installed.\n"
                "Install it with: pip install requests"
            )

    # Local Whisper Speech-to-Text Provider

    elif provider_name == 'whisper_local':
        try:
            from .whisper import WhisperSTTProvider
            return WhisperSTTProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "Local Whisper STT selected but 'openai-whisper' is not installed.\n"
                "Install it with: pip install openai-whisper"
            )

    # Invalid STT Provider Confi.

    else:
        raise ImproperlyConfigured(
            f"Unknown STT_PROVIDER: '{provider_name}'. "
            f"Choose from: google, sarvam, bhashini, whisper_local"
        )