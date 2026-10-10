"""
STT Provider base class — all providers implement this interface.
"""


# Python Standard Library Imports

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


# Transcription Result Data Definition

@dataclass
class TranscriptionResult:
    """
    Result from a speech-to-text transcription.
    """

    # Transcription Result Fields

    text: str
    confidence: float
    language: str
    provider_name: str


# STT Provider Abstract Base Class

class STTProvider(ABC):
    """
    Abstract base class for speech-to-text providers.
    """

    # Speech-to-Text Transcription Interface

    @abstractmethod
    def transcribe(self, audio_path: str, language_code: str = 'en') -> TranscriptionResult:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to audio file (WAV 16kHz mono preferred)
            language_code: BCP-47 language code (e.g., 'en', 'hi', 'ta')

        Returns:
            TranscriptionResult with text, confidence, language, and provider name
        """

        pass