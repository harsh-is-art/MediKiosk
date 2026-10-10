"""Tesseract OCR provider — fully offline."""


# Python Logging & Local Application Imports

import logging
from .base import OCRProvider, OCRResult


# Logger Confi.

logger = logging.getLogger(__name__)


# Tesseract OCR Provider

class TesseractOCRProvider(OCRProvider):
    """
    Wraps pytesseract for offline OCR.
    """

    # Tesseract Initialization

    def __init__(self):
        """
        Initializes the pytesseract OCR library.
        """

        import pytesseract

        self.pytesseract = pytesseract

    # Text Extraction

    def extract_text(self, image_path: str) -> OCRResult:
        """
        Extracts text from an image using Tesseract OCR.
        """

        # Image Processing Import

        from PIL import Image

        # Open Image File

        img = Image.open(image_path)

        # Run OCR With Confidence Data

        data = self.pytesseract.image_to_data(
            img,
            lang='eng+hin',
            output_type=self.pytesseract.Output.DICT
        )

        # Build OCR Text & Calculate Confidence

        words = []
        confidences = []

        for i, word in enumerate(data['text']):
            if word.strip():
                words.append(word)

                conf = data['conf'][i]

                if conf != -1:
                    confidences.append(conf)

        # Process OCR Output

        raw_text = ' '.join(words)

        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0

        # Return OCR Result

        return OCRResult(
            raw_text=raw_text,
            confidence=round(avg_confidence, 3),
            language='en',
            provider_name='tesseract'
        )