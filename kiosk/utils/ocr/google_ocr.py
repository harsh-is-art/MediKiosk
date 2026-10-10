"""Google Cloud Vision OCR provider."""


# Python & Django Imports

import os
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .base import OCRProvider, OCRResult


# Logger Confi.

logger = logging.getLogger(__name__)


# Google Cloud Vision OCR Provider

class GoogleOCRProvider(OCRProvider):
    """
    Wraps Google Cloud Vision API for OCR.
    """

    # Google Cloud Vision Initialization

    def __init__(self):
        """
        Initializes the Google Cloud Vision OCR client using
        the configured service account credentials.
        """

        cred_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '') or os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

        # Validate Google Cloud Credentials

        if not cred_path or not os.path.exists(cred_path):
            logger.error(f"Google Cloud credential file not found at: '{cred_path}'")

            raise ImproperlyConfigured(
                f"GOOGLE_APPLICATION_CREDENTIALS path is invalid or file does not exist: '{cred_path}'. "
                "Please configure a valid service account JSON file path in your .env file."
            )

        # Configure Google Application Credentials

        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = cred_path

        # Initialize Google Vision Client

        try:
            from google.cloud import vision

            self.client = vision.ImageAnnotatorClient()
            self.vision = vision

        except Exception as e:
            logger.error(f"Failed to initialize Google ImageAnnotatorClient: {e}")

            raise ImproperlyConfigured(f"Failed to initialize Google ImageAnnotatorClient: {e}")

    # Text Extraction

    def extract_text(self, image_path: str) -> OCRResult:
        """
        Extracts text from an image using Google Cloud Vision OCR.
        """

        # Read Image File

        with open(image_path, 'rb') as f:
            content = f.read()

        # Create Google Vision Image Object

        image = self.vision.Image(content=content)

        # Perform Document Text Detection

        response = self.client.document_text_detection(image=image)

        # Handle Google Vision API Errors

        if response.error.message:
            raise Exception(f"Google Vision API error: {response.error.message}")

        # Extract Full OCR Text

        full_text = response.full_text_annotation.text if response.full_text_annotation else ''

        # Calculate Average OCR Confidence

        confidence = 0.0

        if response.full_text_annotation and response.full_text_annotation.pages:
            confidences = []

            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    confidences.append(block.confidence)

            if confidences:
                confidence = sum(confidences) / len(confidences)

        # Detect OCR Language

        detected_lang = 'en'

        if response.full_text_annotation and response.full_text_annotation.pages:
            for page in response.full_text_annotation.pages:
                if page.property and page.property.detected_languages:
                    detected_lang = page.property.detected_languages[0].language_code

        # Return OCR Result

        return OCRResult(
            raw_text=full_text,
            confidence=round(confidence, 3),
            language=detected_lang,
            provider_name='google_cloud_vision'
        )