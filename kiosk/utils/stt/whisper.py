"""Local Whisper STT provider — offline speech recognition."""


# Python Logging & Local Application Imports

import logging
from .base import STTProvider, TranscriptionResult


# Logger Confi.

logger = logging.getLogger(__name__)


# Whisper Language Mapping

WHISPER_LANG_MAP = {
    'en': 'english',
    'hi': 'hindi',
    'ta': 'tamil',
    'bn': 'bengali',
    'mr': 'marathi',
}


# Local Whisper Speech-to-Text Provider

class WhisperSTTProvider(STTProvider):
    """
    Wraps OpenAI Whisper for fully offline speech recognition.
    """

    # Whisper Model Initialization

    def __init__(self, model_size='base'):
        """
        Loads the configured Whisper model for local speech recognition.
        """

        import whisper

        logger.info(f"Loading Whisper model: {model_size}")

        self.model = whisper.load_model(model_size)

    # Speech-to-Text Transcription

    def transcribe(self, audio_path: str, language_code: str = 'en') -> TranscriptionResult:
        """
        Transcribes an audio file using the locally loaded Whisper model.
        """

        # Determine Whisper Language

        whisper_lang = WHISPER_LANG_MAP.get(language_code, 'english')

        # Run Whisper Transcription

        result = self.model.transcribe(
            audio_path,
            language=whisper_lang,
            fp16=False,  # Use FP32 for CPU compatibility
        )

        # Extract Transcribed Text

        text = result.get('text', '').strip()

        # Calculate Average Transcription Confidence

        # Whisper doesn't give per-utterance confidence, but segments have "no_speech_prob"

        segments = result.get('segments', [])

        avg_confidence = 1.0

        if segments:
            avg_no_speech = sum(s.get('no_speech_prob', 0) for s in segments) / len(segments)
            avg_confidence = max(0.0, 1.0 - avg_no_speech)

        # Return Transcription Result

        return TranscriptionResult(
            text=text,
            confidence=round(avg_confidence, 3),
            language=language_code,
            provider_name='whisper_local'
        )