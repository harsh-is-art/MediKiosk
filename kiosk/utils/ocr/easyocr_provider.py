"""EasyOCR provider — offline, good multilingual support."""


# Python Logging & Local Application Imports

import logging
from .base import OCRProvider, OCRResult


# Logger Confi.

logger = logging.getLogger(__name__)


# EasyOCR Provider

class EasyOCRProvider(OCRProvider):
    """
    Wraps EasyOCR for offline multilingual OCR.
    """

    # EasyOCR Initialization

    def __init__(self, languages=None):
        """
        Initializes the EasyOCR reader with the configured languages.
        """

        import easyocr

        self.languages = languages or ['en', 'hi']

        logger.info(f"Initializing EasyOCR with languages: {self.languages}")

        self.reader = easyocr.Reader(self.languages, gpu=False)

    # Text Extraction

    def extract_text(self, image_path: str) -> OCRResult:
        """
        Extracts text from an image using EasyOCR.
        """

        results = self.reader.readtext(image_path)

        # OCR Text & Confidence Collection

        texts = []
        confidences = []

        for (bbox, text, confidence) in results:
            texts.append(text)
            confidences.append(confidence)

        # OCR Result Processing

        raw_text = ' '.join(texts)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Return OCR Result

        return OCRResult(
            raw_text=raw_text,
            confidence=round(avg_confidence, 3),
            language='multi',
            provider_name='easyocr'
        )