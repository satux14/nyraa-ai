"""
Face detection and region extraction using MediaPipe FaceMesh.
Produces face crop and landmark indices for under-eye and cheek regions.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import cv2
import numpy as np
import mediapipe as mp


# MediaPipe FaceMesh region indices (468 landmarks)
UNDER_EYE_LEFT = [243, 112, 26, 23, 24, 110, 25, 31, 228, 229, 230, 231, 232, 233]
UNDER_EYE_RIGHT = [359, 463, 253, 260, 259, 257, 258, 286, 414, 413, 412, 411, 410]
CHEEK_LEFT = [93, 234]
CHEEK_RIGHT = [454, 323]
# Upper lip / chin for facial hair density
UPPER_LIP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
LOWER_FACE = [152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]


@dataclass
class FaceRegions:
    face_detected: bool
    landmarks: List[Dict[str, float]]
    face_crop: Optional[np.ndarray]
    crop_bounds: Optional[Dict[str, int]]  # x_min, y_min, x_max, y_max in original image
    image_shape: tuple  # (h, w)


def _landmarks_to_bbox(
    landmarks: List[Dict[str, float]], h: int, w: int, padding: float = 0.12
) -> tuple:
    xs = [lm["x"] * w for lm in landmarks]
    ys = [lm["y"] * h for lm in landmarks]
    x_min = max(0, int(min(xs) - padding * w))
    x_max = min(w, int(max(xs) + padding * w))
    y_min = max(0, int(min(ys) - padding * h))
    y_max = min(h, int(max(ys) + padding * h))
    return x_min, y_min, x_max, y_max


def extract_face_regions(image: np.ndarray) -> FaceRegions:
    """
    Run MediaPipe FaceMesh on image; return face crop and normalized landmarks.
    Landmarks are in image coordinates (pixel) for the cropped face if crop is used,
    but we store original-image normalized (x, y) for consistency with other services.
    """
    if image is None or image.size == 0:
        return FaceRegions(
            face_detected=False,
            landmarks=[],
            face_crop=None,
            crop_bounds=None,
            image_shape=image.shape[:2] if image is not None else (0, 0),
        )

    h, w = image.shape[:2]
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_face = mp.solutions.face_mesh
    face_mesh = mp_face.FaceMesh(static_image_mode=True, max_num_faces=1)
    results = face_mesh.process(rgb)
    face_mesh.close()

    if not results.multi_face_landmarks:
        return FaceRegions(
            face_detected=False,
            landmarks=[],
            face_crop=None,
            crop_bounds=None,
            image_shape=(h, w),
        )

    landmarks = []
    for lm in results.multi_face_landmarks[0].landmark:
        landmarks.append({"x": float(lm.x), "y": float(lm.y)})

    x_min, y_min, x_max, y_max = _landmarks_to_bbox(landmarks, h, w)
    if x_max <= x_min or y_max <= y_min:
        return FaceRegions(
            face_detected=True,
            landmarks=landmarks,
            face_crop=image,
            crop_bounds={"x_min": 0, "y_min": 0, "x_max": w, "y_max": h},
            image_shape=(h, w),
        )

    face_crop = image[y_min:y_max, x_min:x_max].copy()
    return FaceRegions(
        face_detected=True,
        landmarks=landmarks,
        face_crop=face_crop,
        crop_bounds={"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max},
        image_shape=(h, w),
    )


def get_region_mask(
    image: np.ndarray,
    landmarks: List[Dict[str, float]],
    indices: List[int],
    expand_px: int = 8,
) -> np.ndarray:
    """Return a boolean mask for the region defined by landmark indices (in original image coords)."""
    h, w = image.shape[:2]
    xs = [landmarks[i]["x"] * w for i in indices if i < len(landmarks)]
    ys = [landmarks[i]["y"] * h for i in indices if i < len(landmarks)]
    if not xs:
        return np.zeros((h, w), dtype=np.uint8)
    x_min = max(0, int(min(xs)) - expand_px)
    x_max = min(w, int(max(xs)) + expand_px)
    y_min = max(0, int(min(ys)) - expand_px)
    y_max = min(h, int(max(ys)) + expand_px)
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y_min:y_max, x_min:x_max] = 1
    return mask


def get_region_mean_luminance(image: np.ndarray, landmarks: List[Dict[str, float]], indices: List[int]) -> float:
    """Mean luminance (LAB L) in the region; 0 if invalid."""
    h, w = image.shape[:2]
    xs = [landmarks[i]["x"] * w for i in indices if i < len(landmarks)]
    ys = [landmarks[i]["y"] * h for i in indices if i < len(landmarks)]
    if not xs:
        return 0.0
    x_min = max(0, int(min(xs)) - 5)
    x_max = min(w, int(max(xs)) + 5)
    y_min = max(0, int(min(ys)) - 5)
    y_max = min(h, int(max(ys)) + 5)
    if x_max <= x_min or y_max <= y_min:
        return 0.0
    crop = image[y_min:y_max, x_min:x_max]
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    return float(np.mean(lab[:, :, 0]))
