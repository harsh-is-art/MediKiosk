"""
Qwen-VL + PaddleOCR local medical slip recognition engine.
Optimized for CUDA (NVIDIA RTX 4060 8GB VRAM).
"""

import os
import cv2
import uuid
import logging
import numpy as np
from PIL import Image
from django.conf import settings
from .base import OCRProvider, OCRResult
from .preprocessing.document_crop import detect_document_corners
from .preprocessing.perspective import four_point_transform
from .preprocessing.image_clean import preprocess_document_image

logger = logging.getLogger(__name__)

# Configurable confidence threshold
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.90'))


class QwenPaddleEngine:
    """
    Local GPU engine combining PaddleOCR (document & text layout detection)
    and Qwen-VL (handwriting recognition) for medical prescriptions.
    """
    _paddle_instance = None
    _qwen_model = None
    _qwen_tokenizer = None

    @classmethod
    def get_paddle(cls):
        if cls._paddle_instance is None:
            try:
                from paddleocr import PaddleOCR
                cls._paddle_instance = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True, show_log=False)
                logger.info("PaddleOCR engine initialized with CUDA/GPU acceleration.")
            except Exception as e:
                logger.warning(f"PaddleOCR GPU initialization warning: {e}. Falling back to standard processing.")
                cls._paddle_instance = False
        return cls._paddle_instance if cls._paddle_instance is not False else None

    @classmethod
    def get_qwen(cls):
        if cls._qwen_model is None:
            try:
                import torch
                from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

                model_name = os.getenv('QWEN_VL_MODEL', 'Qwen/Qwen2-VL-2B-Instruct')
                logger.info(f"Loading local Qwen-VL model '{model_name}' on CUDA...")

                device = "cuda" if torch.cuda.is_available() else "cpu"
                dtype = torch.float16 if device == "cuda" else torch.float32

                cls._qwen_processor = AutoProcessor.from_pretrained(model_name)
                cls._qwen_model = Qwen2VLForConditionalGeneration.from_pretrained(
                    model_name, torch_dtype=dtype, device_map="auto"
                )
                logger.info("Qwen-VL model loaded successfully.")
            except Exception as e:
                logger.warning(f"Qwen-VL local model loading warning: {e}. Utilizing hybrid OCR reader fallback.")
                cls._qwen_model = False
        return cls._qwen_model if cls._qwen_model is not False else None

    def process_image(self, image_path: str):
        """
        Executes document cropping, perspective warping, preprocessing,
        text detection, and local Qwen-VL handwriting extraction.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Input image path does not exist: {image_path}")

        # 1. Read input image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not decode image at path: {image_path}")

        # 2. Document boundary detection & perspective correction
        pts = detect_document_corners(image)
        if pts is not None:
            cropped = four_point_transform(image, pts)
            logger.info("Successfully detected document boundaries and applied 4-point perspective warp.")
        else:
            cropped = image
            logger.info("Document boundaries obscured; utilizing full bounding frame.")

        # 3. Preprocess cropped slip (CLAHE + unsharp sharpening)
        cleaned_image = preprocess_document_image(cropped)

        # 4. Save cropped image to media directory
        media_subfolder = os.path.join(settings.MEDIA_ROOT, 'cropped_slips')
        os.makedirs(media_subfolder, exist_ok=True)

        crop_filename = f"slip_{uuid.uuid4().hex[:10]}.png"
        crop_save_path = os.path.join(media_subfolder, crop_filename)
        cv2.imwrite(crop_save_path, cleaned_image if cleaned_image is not None else cropped)

        crop_relative_url = f"/media/cropped_slips/{crop_filename}"

        # 5. PaddleOCR text region detection & layout
        paddle_ocr = self.get_paddle()
        paddle_boxes = []
        paddle_scores = []
        raw_paddle_texts = []

        if paddle_ocr:
            try:
                result = paddle_ocr.ocr(crop_save_path, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        bbox, (text, score) = line
                        paddle_boxes.append(bbox)
                        paddle_scores.append(score)
                        raw_paddle_texts.append(text)
            except Exception as pe:
                logger.warning(f"PaddleOCR execution warning: {pe}")

        # Calculate average PaddleOCR score
        avg_paddle_score = float(np.mean(paddle_scores)) if paddle_scores else 0.75

        # 6. Qwen-VL Local Handwriting Recognition
        extracted_text = ""
        qwen_model = self.get_qwen()

        if qwen_model and hasattr(self, '_qwen_processor'):
            try:
                import torch
                from qwen_vl_utils import process_vision_info

                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": crop_save_path},
                            {"type": "text", "text": "Transcribe all handwritten medical prescription text from this document accurately. Do not invent or diagnose."},
                        ],
                    }
                ]

                text_input = self._qwen_processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                image_inputs, video_inputs = process_vision_info(messages)
                inputs = self._qwen_processor(
                    text=[text_input],
                    images=image_inputs,
                    videos=video_inputs,
                    padding=True,
                    return_tensors="pt",
                )
                inputs = inputs.to("cuda" if torch.cuda.is_available() else "cpu")

                generated_ids = qwen_model.generate(**inputs, max_new_tokens=256)
                generated_ids_trimmed = [
                    out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
                ]
                extracted_text = self._qwen_processor.batch_decode(
                    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0]
            except Exception as qe:
                logger.warning(f"Qwen-VL generation fallback: {qe}")
                extracted_text = "\n".join(raw_paddle_texts)
        else:
            extracted_text = "\n".join(raw_paddle_texts)

        # 7. Confidence Score Calculation
        # Combine PaddleOCR region detection confidence & text density heuristics
        text_len = len(extracted_text.strip())
        if text_len > 15 and avg_paddle_score > 0.80:
            confidence = min(0.96, avg_paddle_score + 0.05)
        elif text_len > 5:
            confidence = round(avg_paddle_score, 2)
        else:
            confidence = 0.60

        # 8. Threshold Check (>= 0.90 vs < 0.90)
        if confidence >= CONFIDENCE_THRESHOLD and extracted_text.strip():
            return {
                "success": True,
                "confidence": confidence,
                "status": "accepted",
                "text": extracted_text.strip(),
                "cropped_image": None,
                "cropped_image_path": crop_save_path,
            }
        else:
            return {
                "success": True,
                "confidence": confidence,
                "status": "manual_review",
                "text": None,
                "cropped_image": crop_relative_url,
                "cropped_image_path": crop_save_path,
            }


class QwenPaddleOCRProvider(OCRProvider):
    """
    Adapter integrating QwenPaddleEngine into MediKiosk provider framework.
    """

    def __init__(self):
        self.engine = QwenPaddleEngine()

    def extract_text(self, image_path: str) -> OCRResult:
        res = self.engine.process_image(image_path)
        raw_text = res.get('text') or "Low confidence document scan — Manual verification required."
        return OCRResult(
            raw_text=raw_text,
            confidence=res.get('confidence', 0.80),
            language='en',
            provider_name='qwen_paddle_local'
        )
