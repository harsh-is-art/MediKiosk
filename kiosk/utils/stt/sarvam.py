"""Sarvam AI ASR provider — Speech-to-text for Indian languages."""


# Python & Django Imports

import os
import logging
import requests
from django.conf import settings
from .base import STTProvider, TranscriptionResult


# Logger Confi.

logger = logging.getLogger(__name__)


# Sarvam AI Language Mapping

SARVAM_LANG_MAP = {
    'en': 'en-IN',
    'hi': 'hi-IN',
    'ta': 'ta-IN',
    'bn': 'bn-IN',
    'mr': 'mr-IN',
    'te': 'te-IN',
    'kn': 'kn-IN',
    'ml': 'ml-IN',
    'gu': 'gu-IN',
    'pa': 'pa-IN',
    'od': 'or-IN',
}


# Sarvam AI Speech-to-Text Provider

class SarvamSTTProvider(STTProvider):
    """
    Wraps Sarvam AI STT REST API (saaras:v3 / saaras:v1) for Indian language speech recognition.
    """

    # Speech-to-Text Transcription

    def transcribe(self, audio_path: str, language_code: str = 'en') -> TranscriptionResult:
        """
        Transcribes an audio file using Sarvam AI Speech-to-Text API.
        """

        # Retrieve Sarvam Confi.

        api_key = getattr(settings, 'SARVAM_API_KEY', '') or os.getenv('SARVAM_API_KEY', '')
        model = getattr(settings, 'SARVAM_STT_MODEL', 'saaras:v3') or 'saaras:v3'

        # Validate Sarvam API Key

        if not api_key:
            raise ValueError("SARVAM_API_KEY not configured. Please set it in your .env file.")

        # Map Application Language to Sarvam Language Code

        sarvam_lang = SARVAM_LANG_MAP.get(language_code, f"{language_code}-IN" if '-' not in language_code else language_code)

        # Prepare Sarvam API Request

        url = "https://api.sarvam.ai/speech-to-text"
        headers = {
            "api-subscription-key": api_key,
        }

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            try:
                from sarvamai import SarvamAI
                client = SarvamAI(api_subscription_key=api_key)
                with open(audio_path, 'rb') as f:
                    res = client.speech_to_text.transcribe(
                        file=f,
                        model=model,
                        mode="transcribe"
                    )
                
                transcript = getattr(res, 'transcript', None)
                if transcript is None and isinstance(res, dict):
                    transcript = res.get('transcript', '')
                elif transcript is None:
                    transcript = str(res)

                return TranscriptionResult(
                    text=transcript,
                    confidence=0.98,
                    language=language_code,
                    provider_name='sarvamai_sdk'
                )
            except Exception as sdk_err:
                logger.warning(f"SarvamAI SDK transcribe failed ({sdk_err}), falling back to REST API.")
                with open(audio_path, 'rb') as audio_file:
                    files = {
                        'file': (os.path.basename(audio_path), audio_file, 'audio/wav')
                    }
                    data = {
                        'model': model,
                        'language_code': sarvam_lang,
                        'with_timestamps': 'false',
                    }

                    response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                    response.raise_for_status()

                    res_json = response.json()
                    transcript = res_json.get('transcript', '')

                    return TranscriptionResult(
                        text=transcript,
                        confidence=0.95,
                        language=language_code,
                        provider_name='sarvam_asr'
                    )

        except Exception as e:
            logger.error(f"Sarvam STT API error ({e}). Returning fallback transcription result.")
            return TranscriptionResult(
                text="",
                confidence=0.0,
                language=language_code,
                provider_name='sarvam_asr_fallback'
            )

    # Real-Time Streaming WebSocket Client Helper

    def get_streaming_client(
        self,
        language_code: str = 'en',
        mode: str = 'transcribe',
        model: str = 'saaras:v4'
    ):
        """
        Instantiates a SarvamStreamingSTTClient for real-time WebSocket transcription.
        """
        from .sarvam_streaming import SarvamStreamingSTTClient
        return SarvamStreamingSTTClient(
            model=model,
            mode=mode,
            language_code=language_code
        )

