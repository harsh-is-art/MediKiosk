"""
OCR Provider — Swappable Optical Character Recognition factory.

Usage:
    from kiosk.utils.ocr import get_ocr_provider
    provider = get_ocr_provider()
    result = provider.extract_text('/path/to/image.jpg')
"""


# Django & Application Imports

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .base import OCRProvider


# OCR Provider Factory

def get_ocr_provider() -> OCRProvider:
    """
    Factory: returns the configured OCR provider instance.
    """

    # Retrieve Configured OCR Provider

    provider_name = getattr(settings, 'OCR_PROVIDER', 'google')

    # Google Cloud Vision OCR Provider

    if provider_name == 'google':
        try:
            from .google_ocr import GoogleOCRProvider
            return GoogleOCRProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "Google Cloud Vision OCR selected but 'google-cloud-vision' is not installed.\n"
                "Install it with: pip install google-cloud-vision"
            )

    # Tesseract OCR Provider

    elif provider_name == 'tesseract':
        try:
            from .tesseract import TesseractOCRProvider
            return TesseractOCRProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "Tesseract OCR selected but 'pytesseract' is not installed.\n"
                "Install it with: pip install pytesseract\n"
                "Also install Tesseract system binary: https://github.com/tesseract-ocr/tesseract"
            )

    # EasyOCR Provider

    elif provider_name == 'easyocr':
        try:
            from .easyocr_provider import EasyOCRProvider
            return EasyOCRProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "EasyOCR selected but 'easyocr' is not installed.\n"
                "Install it with: pip install easyocr"
            )

    # Qwen-VL + PaddleOCR Local Engine Provider

    elif provider_name == 'qwen_paddle':
        try:
            from .qwen_paddle_engine import QwenPaddleOCRProvider
            return QwenPaddleOCRProvider()
        except ImportError:
            raise ImproperlyConfigured(
                "Qwen-VL + PaddleOCR selected but required packages are missing.\n"
                "Install with: pip install paddleocr transformers qwen-vl-utils"
            )

    # Invalid OCR Provider Confi.

    else:
        raise ImproperlyConfigured(
            f"Unknown OCR_PROVIDER: '{provider_name}'. "
            f"Choose from: google, tesseract, easyocr, qwen_paddle"
        )