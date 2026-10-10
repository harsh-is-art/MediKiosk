"""
Document boundary detection for medical prescriptions/slips using OpenCV contours.
"""

import cv2
import numpy as np


def detect_document_corners(image: np.ndarray):
    """
    Detects the 4 corner points of a medical document/slip inside a photo.
    Returns np.ndarray of shape (4, 2) or None if 4-corner boundary is not found.
    """
    if image is None:
        return None

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Edge detection
    edged = cv2.Canny(blurred, 50, 200)

    # Find contours
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    screen_cnt = None

    for c in contours[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)

        # Check if contour has 4 points and covers at least 15% of image area
        if len(approx) == 4 and cv2.contourArea(c) > (width * height * 0.15):
            screen_cnt = approx
            break

    if screen_cnt is not None:
        return screen_cnt.reshape(4, 2)

    return None
