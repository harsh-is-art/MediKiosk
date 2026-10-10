"""Sarvam AI Text-to-Speech provider — Speech synthesis for Indian languages."""


# Python & Django Imports

import os
import logging
import requests
from django.conf import settings


# Logger Confi.

logger = logging.getLogger(__name__)


# Sarvam AI TTS Language Mapping

SARVAM_TTS_LANG_MAP = {
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

# Speaker mappings per language
SARVAM_SPEAKERS = {
    'hi-IN': 'shruti',
    'en-IN': 'shruti',
    'ta-IN': 'shruti',
    'bn-IN': 'shruti',
    'mr-IN': 'shruti',
}


# Sarvam AI Text-to-Speech Provider

class SarvamTTSProvider:
    """
    Wraps Sarvam AI TTS REST API (bulbul:v1) for Indian language speech synthesis.
    """

    def synthesize(self, text: str, language_code: str = 'en', speaker: str = None) -> dict:
        """
        Synthesizes text into audio using Sarvam AI Text-to-Speech API.

        Args:
            text: Text string to convert to speech.
            language_code: BCP-47 or standard language code (e.g., 'en', 'hi', 'ta').
            speaker: Optional speaker voice name (defaults to 'meera').

        Returns:
            dict containing:
                - audio_base64: Base64-encoded WAV audio string
                - language: target language code
                - provider: 'sarvam_tts'
        """

        if not text or not text.strip():
            raise ValueError("Text content is required for text-to-speech synthesis.")

        api_key = getattr(settings, 'SARVAM_API_KEY', '') or os.getenv('SARVAM_API_KEY', '')
        model = getattr(settings, 'SARVAM_TTS_MODEL', 'bulbul:v3') or 'bulbul:v3'

        if not api_key:
            logger.warning("SARVAM_API_KEY not configured. Generating fallback audio payload.")
            return {
                'audio_base64': _generate_fallback_wav_b64(text),
                'language': language_code,
                'provider': 'sarvam_tts_fallback',
            }

        sarvam_lang = SARVAM_TTS_LANG_MAP.get(
            language_code,
            f"{language_code}-IN" if '-' not in language_code else language_code
        )

        selected_speaker = speaker or SARVAM_SPEAKERS.get(sarvam_lang, 'shruti')

        url = "https://api.sarvam.ai/text-to-speech"
        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }

        model_setting = getattr(settings, 'SARVAM_TTS_MODEL', 'bulbul:v3') or 'bulbul:v3'

        if "v3" in model_setting:
            payload = {
                "inputs": [text.strip()],
                "target_language_code": sarvam_lang,
                "speaker": selected_speaker,
                "pace": 1.0,
                "speech_sample_rate": 24000,
                "model": "bulbul:v3",
            }
        else:
            payload = {
                "inputs": [text.strip()],
                "target_language_code": sarvam_lang,
                "speaker": selected_speaker,
                "pitch": 0,
                "pace": 1.0,
                "loudness": 1.5,
                "speech_sample_rate": 16000,
                "enable_preprocessing": True,
                "model": model_setting,
            }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code != 200:
                logger.error(f"Sarvam API status {response.status_code} response: {response.text}")
            response.raise_for_status()

            res_json = response.json()
            audios = res_json.get('audios', [])

            if not audios:
                raise ValueError("Sarvam TTS API returned empty audio list.")

            return {
                'audio_base64': audios[0],
                'language': sarvam_lang,
                'provider': 'sarvam_tts',
            }

        except Exception as e:
            logger.error(f"Sarvam TTS API error: {e}. Falling back to silent audio buffer.")
            return {
                'audio_base64': _generate_fallback_wav_b64(text),
                'language': language_code,
                'provider': 'sarvam_tts_fallback',
            }


def _generate_fallback_wav_b64(text: str) -> str:
    """Generates a clean silent PCM WAV audio stream for TTS fallback."""
    import io, wave, struct, base64
    sample_rate = 16000
    duration = 0.5  # Brief silent audio clip
    num_samples = int(sample_rate * duration)

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        frames = [struct.pack('<h', 0) for _ in range(num_samples)]
        wf.writeframes(b''.join(frames))

    return base64.b64encode(buf.getvalue()).decode('utf-8')
