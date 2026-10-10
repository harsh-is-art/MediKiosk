"""Bhashini ASR provider — Government of India speech-to-text."""


# Python & Django Imports

import base64
import logging
import requests
from django.conf import settings
from .base import STTProvider, TranscriptionResult


# Logger Confi.

logger = logging.getLogger(__name__)


# Bhashini Language Mapping

BHASHINI_LANG_MAP = {
    'en': 'en',
    'hi': 'hi',
    'ta': 'ta',
    'bn': 'bn',
    'mr': 'mr',
}


# Bhashini Speech-to-Text Provider

class BhashiniSTTProvider(STTProvider):
    """
    Wraps Bhashini ASR API for Indian language speech recognition.
    """

    # Speech-to-Text Transcription

    def transcribe(self, audio_path: str, language_code: str = 'en') -> TranscriptionResult:
        """
        Transcribes an audio file using the Bhashini ASR API.
        """

        # Retrieve Bhashini Confi.

        api_key = getattr(settings, 'BHASHINI_API_KEY', '')
        user_id = getattr(settings, 'BHASHINI_USER_ID', '')

        # Validate Bhashini API Key

        if not api_key:
            raise ValueError("BHASHINI_API_KEY not configured. Set it in your .env file.")

        # Map Application Language to Bhashini Language

        bhashini_lang = BHASHINI_LANG_MAP.get(language_code, language_code)

        # Read & Encode Audio File

        with open(audio_path, 'rb') as f:
            audio_content = base64.b64encode(f.read()).decode('utf-8')

        # Step 1: Get Bhashini Pipeline Confi.

        config_url = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

        config_payload = {
            "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": bhashini_lang}}}],
            "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"}
        }

        # Bhashini API Request Processing

        try:
            config_resp = requests.post(
                config_url,
                json=config_payload,
                headers={
                    "Content-Type": "application/json",
                    "userID": user_id,
                    "ulcaApiKey": api_key,
                },
                timeout=15,
            )

            # Validate Pipeline Confi. Response

            config_resp.raise_for_status()
            config_data = config_resp.json()

            # Extract Pipeline Inference Confi.

            callback_url = config_data.get("pipelineInferenceAPIEndPoint", {}).get("callbackUrl", "")
            inference_key = config_data.get("pipelineInferenceAPIEndPoint", {}).get("inferenceApiKey", {}).get("value", "")
            service_id = config_data.get("pipelineResponseConfig", [{}])[0].get("config", [{}])[0].get("serviceId", "")

            # Step 2: Prepare ASR Inference Payload

            infer_payload = {
                "pipelineTasks": [{
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": bhashini_lang},
                        "serviceId": service_id,
                        "audioFormat": "wav",
                        "samplingRate": 16000,
                    }
                }],
                "inputData": {"audio": [{"audioContent": audio_content}]}
            }

            # Send ASR Inference Request

            infer_resp = requests.post(
                callback_url,
                json=infer_payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": inference_key,
                },
                timeout=30,
            )

            # Validate ASR Inference Response

            infer_resp.raise_for_status()
            infer_data = infer_resp.json()

            # Extract Transcribed Text

            text = infer_data.get("pipelineResponse", [{}])[0].get("output", [{}])[0].get("source", "")

            # Return Transcription Result

            return TranscriptionResult(
                text=text,
                confidence=0.85,  # Bhashini doesn't return confidence scores
                language=language_code,
                provider_name='bhashini_asr'
            )

        # Handle Bhashini API Errors

        except Exception as e:
            logger.error(f"Bhashini ASR error: {e}")
            raise