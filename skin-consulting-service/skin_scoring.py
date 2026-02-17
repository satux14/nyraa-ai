"""
Skin metrics (0-100) using OpenCV + NumPy.
Uses face crop for most metrics; full image + landmarks for under-eye vs cheek.
"""
from dataclasses import dataclass
from typing import List, Dict

import cv2
import numpy as np

from face_region_extractor import (
    FaceRegions,
    UNDER_EYE_LEFT,
    UNDER_EYE_RIGHT,
    CHEEK_LEFT,
    CHEEK_RIGHT,
    UPPER_LIP,
    LOWER_FACE,
    get_region_mean_luminance,
)


@dataclass
class SkinScores:
    brightness: float
    pigmentation_density: float
    redness: float
    texture_roughness: float
    dark_circle_index: float
    facial_hair_density: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "brightness": round(self.brightness, 1),
            "pigmentation_density": round(self.pigmentation_density, 1),
            "redness": round(self.redness, 1),
            "texture_roughness": round(self.texture_roughness, 1),
            "dark_circle_index": round(self.dark_circle_index, 1),
            "facial_hair_density": round(self.facial_hair_density, 1),
        }


def _normalize_0_100(value: float, low: float, high: float) -> float:
    """Clip and map [low, high] -> [0, 100]."""
    if high <= low:
        return 50.0
    x = np.clip(value, low, high)
    return float(100.0 * (x - low) / (high - low))


def _brightness_index(face_crop: np.ndarray) -> float:
    """LAB L channel mean -> 0-100 (typical L range ~20-90)."""
    lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
    l_mean = np.mean(lab[:, :, 0])
    return _normalize_0_100(l_mean, 20.0, 90.0)


def _pigmentation_density(face_crop: np.ndarray) -> float:
    """Dark clusters: % of pixels below threshold relative to mean L -> 0-100."""
    lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    l_mean = np.mean(l_channel)
    # Pixels darker than mean - 15 count as "dark cluster"
    threshold = max(0, l_mean - 15)
    below = np.sum(l_channel < threshold)
    total = l_channel.size
    if total == 0:
        return 0.0
    ratio = below / total
    # 0-40% dark -> 0-100 scale (higher = more pigmentation)
    return _normalize_0_100(ratio * 100.0, 0.0, 40.0)


def _redness_score(face_crop: np.ndarray) -> float:
    """HSV: red hue ratio (0-15 and 160-180) -> 0-100."""
    hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    # Red in OpenCV hue: 0-10 and 170-180 (half scale 0-180)
    red_mask = ((h <= 10) | (h >= 170)).astype(np.float32)
    ratio = np.mean(red_mask)
    return _normalize_0_100(ratio * 100.0, 5.0, 35.0)


def _texture_roughness(face_crop: np.ndarray) -> float:
    """Laplacian variance -> 0-100 (higher = rougher)."""
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    var = np.var(lap)
    # Typical range ~50-2000
    return _normalize_0_100(var, 50.0, 2000.0)


def _dark_circle_index(image: np.ndarray, landmarks: List[Dict[str, float]]) -> float:
    """Under-eye vs cheek luminance difference -> 0-100 (higher = more dark circles)."""
    under_l = (
        get_region_mean_luminance(image, landmarks, UNDER_EYE_LEFT)
        + get_region_mean_luminance(image, landmarks, UNDER_EYE_RIGHT)
    ) / 2.0
    cheek_l = (
        get_region_mean_luminance(image, landmarks, CHEEK_LEFT)
        + get_region_mean_luminance(image, landmarks, CHEEK_RIGHT)
    ) / 2.0
    if cheek_l <= 0:
        return 0.0
    ratio = under_l / cheek_l
    # ratio 1.0 = no dark circle; 0.7 = moderate; 0.5 = high -> map to 0-100
    # So 100 when ratio low (bad), 0 when ratio high (good)
    return _normalize_0_100(1.0 - ratio, 0.0, 0.5)


def _facial_hair_density(image: np.ndarray, landmarks: List[Dict[str, float]]) -> float:
    """Edge density + dark clusters in lower face / upper lip -> 0-100."""
    h, w = image.shape[:2]
    indices = list(set(UPPER_LIP + LOWER_FACE))
    xs = [landmarks[i]["x"] * w for i in indices if i < len(landmarks)]
    ys = [landmarks[i]["y"] * h for i in indices if i < len(landmarks)]
    if not xs:
        return 0.0
    x_min = max(0, int(min(xs)) - 10)
    x_max = min(w, int(max(xs)) + 10)
    y_min = max(0, int(min(ys)) - 10)
    y_max = min(h, int(max(ys)) + 10)
    if x_max <= x_min or y_max <= y_min:
        return 0.0
    crop = image[y_min:y_max, x_min:x_max]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.mean(edges > 0) * 100.0
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    l_channel = lab[:, :, 0]
    dark_ratio = np.mean(l_channel < np.percentile(l_channel, 25))
    combined = 0.5 * _normalize_0_100(edge_density, 2.0, 15.0) + 0.5 * _normalize_0_100(dark_ratio * 100.0, 10.0, 40.0)
    return min(100.0, combined)


def compute_skin_scores(image: np.ndarray, regions: FaceRegions) -> SkinScores:
    """
    Compute all 6 metrics. Uses face_crop for brightness, pigmentation, redness, texture;
    full image + landmarks for dark_circle and facial_hair.
    """
    if not regions.face_detected or regions.face_crop is None or regions.face_crop.size == 0:
        return SkinScores(
            brightness=50.0,
            pigmentation_density=50.0,
            redness=50.0,
            texture_roughness=50.0,
            dark_circle_index=50.0,
            facial_hair_density=50.0,
        )

    face_crop = regions.face_crop
    landmarks = regions.landmarks

    brightness = _brightness_index(face_crop)
    pigmentation_density = _pigmentation_density(face_crop)
    redness = _redness_score(face_crop)
    texture_roughness = _texture_roughness(face_crop)

    # These need full image + landmarks (in original image coords)
    dark_circle_index = _dark_circle_index(image, landmarks) if landmarks else 50.0
    facial_hair_density = _facial_hair_density(image, landmarks) if landmarks else 50.0

    return SkinScores(
        brightness=brightness,
        pigmentation_density=pigmentation_density,
        redness=redness,
        texture_roughness=texture_roughness,
        dark_circle_index=dark_circle_index,
        facial_hair_density=facial_hair_density,
    )
