"""
Image enhancement and preprocessing for handwriting recognition.
"""

import cv2
import numpy as np


def preprocess_document_image(image: np.ndarray) -> np.ndarray:
    """
    Enhances medical prescription image contrast and legibility without destroying handwriting.
    """
    if image is None:
        return None

    # Convert to LAB color space to equalize lightness channel
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L-channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)

    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # Mild sharpening to clarify faint pencil/pen strokes
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(enhanced, -1, kernel)

    return sharpened
