"""OCR Provider base class — all providers implement this interface."""


# Python Standard Library Imports

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


# OCR Result Data Definition

@dataclass
class OCRResult:
    """
    Result from optical character recognition.
    """

    # OCR Result Fields

    raw_text: str
    confidence: float
    language: str
    provider_name: str


# OCR Provider Abstract Base Class

class OCRProvider(ABC):
    """
    Abstract base class for OCR providers.
    """

    # Text Extraction Interface

    @abstractmethod
    def extract_text(self, image_path: str) -> OCRResult:
        """
        Extract text from an image file.

        Args:
            image_path: Path to image file (JPG, PNG, etc.)

        Returns:
            OCRResult with raw text, confidence, language, and provider name
        """

        pass