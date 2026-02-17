"""
Confidence scoring for skin analysis. Reduces score for uneven lighting, blur,
partial face, or small skin region. Returns manual_review_required if < 60.
"""
from dataclasses import dataclass
from typing import List, Dict

import cv2
import numpy as np

from face_region_extractor import FaceRegions


@dataclass
class ConfidenceResult:
    confidence_score: float
    manual_review_required: bool


def _blur_score(face_crop: np.ndarray) -> float:
    """Laplacian variance as sharpness; low = blur. Return 0-1 (1 = sharp)."""
    if face_crop is None or face_crop.size == 0:
        return 0.0
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    var = np.var(lap)
    # Typical: < 100 blurry, 100-500 ok, > 500 sharp
    return float(np.clip((var - 50) / 450.0, 0.0, 1.0))


def _lighting_uniformity(face_crop: np.ndarray) -> float:
    """Split face in quadrants; compare mean L. High variance = uneven. Return 0-1 (1 = even)."""
    if face_crop is None or face_crop.size == 0:
        return 0.0
    h, w = face_crop.shape[:2]
    if h < 20 or w < 20:
        return 0.0
    lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
    l_ch = lab[:, :, 0]
    mid_y, mid_x = h // 2, w // 2
    q1 = np.mean(l_ch[:mid_y, :mid_x])
    q2 = np.mean(l_ch[:mid_y, mid_x:])
    q3 = np.mean(l_ch[mid_y:, :mid_x])
    q4 = np.mean(l_ch[mid_y:, mid_x:])
    std = np.std([q1, q2, q3, q4])
    # std 0 = perfect, > 15 = quite uneven
    return float(np.clip(1.0 - std / 20.0, 0.0, 1.0))


def _face_completeness(regions: FaceRegions) -> float:
    """Heuristic: enough landmarks and reasonable crop size. 0-1."""
    if not regions.face_detected or not regions.landmarks:
        return 0.0
    n_landmarks = len(regions.landmarks)
    if n_landmarks < 400:
        return 0.5  # partial
    if regions.face_crop is None:
        return 0.7
    h, w = regions.face_crop.shape[:2]
    pixels = h * w
    # Very small crop = face far or partial
    if pixels < 4000:
        return 0.4
    if pixels < 15000:
        return 0.8
    return 1.0


def _skin_region_size(regions: FaceRegions) -> float:
    """Crop area relative to typical; 0-1."""
    if regions.face_crop is None or regions.face_crop.size == 0:
        return 0.0
    h, w = regions.face_crop.shape[:2]
    area = h * w
    # 50x50 = 2500 min, 300x300 = 90k good
    return float(np.clip((area - 2500) / 87500.0, 0.0, 1.0))


def compute_confidence(image: np.ndarray, regions: FaceRegions) -> ConfidenceResult:
    """
    Combine blur, lighting uniformity, face completeness, and region size
    into a 0-100 confidence score. If < 60, set manual_review_required.
    """
    if not regions.face_detected:
        return ConfidenceResult(confidence_score=0.0, manual_review_required=True)

    face_crop = regions.face_crop
    blur = _blur_score(face_crop) if face_crop is not None else 0.0
    lighting = _lighting_uniformity(face_crop) if face_crop is not None else 0.0
    completeness = _face_completeness(regions)
    size = _skin_region_size(regions) if face_crop is not None else 0.0

    # Weighted average
    score = 100.0 * (0.25 * blur + 0.25 * lighting + 0.25 * completeness + 0.25 * size)
    score = round(min(100.0, max(0.0, score)), 1)
    return ConfidenceResult(
        confidence_score=score,
        manual_review_required=score < 60.0,
    )
