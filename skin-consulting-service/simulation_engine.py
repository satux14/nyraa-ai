"""
Service and product impact simulation on face image. Max 50% visual correction;
no over-whitening. Returns before/after as base64.
"""
import base64
from typing import Tuple

import cv2
import numpy as np


MAX_CORRECTION = 0.5  # 50% cap


def _to_base64(image: np.ndarray, fmt: str = ".jpg") -> str:
    """Encode BGR image to base64 JPEG."""
    if image is None or image.size == 0:
        return ""
    ok, buf = cv2.imencode(fmt, image)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("utf-8")


def _cap_correction(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """Limit per-pixel change so overall correction does not exceed 50%. Never darken on average."""
    before = np.clip(before.astype(np.float32), 0, 255)
    after = np.clip(after.astype(np.float32), 0, 255)
    delta = after - before
    # Scale delta so max average absolute change is 50% of 255
    max_avg_delta = MAX_CORRECTION * 255.0 * 0.5
    avg_abs = np.mean(np.abs(delta))
    if avg_abs > 1e-6 and avg_abs > max_avg_delta:
        scale = max_avg_delta / avg_abs
        delta = delta * scale
    result = before + delta
    # Safeguard: if result is darker on average than before, add a constant lift so we don't show a darker "after"
    mean_before = np.mean(before)
    mean_result = np.mean(result)
    if mean_result < mean_before - 0.5:
        lift = mean_before - mean_result
        result = np.clip(result + lift, 0, 255)
    return np.clip(result, 0, 255).astype(np.uint8)


def _no_over_whiten(lab: np.ndarray, max_l: float = 95.0) -> np.ndarray:
    """Cap L channel to avoid over-whitening."""
    lab = lab.astype(np.float32)
    lab[:, :, 0] = np.minimum(lab[:, :, 0], max_l)
    return np.clip(lab, 0, 255).astype(np.uint8)


def _simulate_de_tan(img: np.ndarray) -> np.ndarray:
    """Reduce pigmentation 20-30%, improve tone uniformity. Keep or lift brightness."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    l, a, b = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]
    mean_l = np.mean(l)
    mask_dark = (l < mean_l).astype(np.float32)
    l = l + mask_dark * (mean_l - l) * 0.25
    # Small global L lift so result is never darker
    l = np.minimum(255.0, l + 2.5)
    a = a * 0.92 + 128 * 0.08
    b = b * 0.92 + 128 * 0.08
    lab[:, :, 0], lab[:, :, 1], lab[:, :, 2] = l, a, b
    lab = _no_over_whiten(lab.astype(np.uint8))
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def _simulate_fruit_facial(img: np.ndarray) -> np.ndarray:
    """Add glow, mild hydration smoothing. Smooth only A,B so L stays bright."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    # Brighten L and cap (no smoothing of L – smoothing was making after darker)
    l_ch = np.minimum(255.0, lab[:, :, 0] * 1.06 + 3)
    l_ch = np.minimum(l_ch, 95.0)
    # Smooth only A and B for even tone; leave L as brightened (bilateral needs 3 channels)
    a_ch = lab[:, :, 1].astype(np.uint8)
    b_ch = lab[:, :, 2].astype(np.uint8)
    ab_smooth = cv2.bilateralFilter(cv2.merge([a_ch, b_ch, a_ch]), 5, 30, 30)
    a_smooth = ab_smooth[:, :, 0].astype(np.float32)
    b_smooth = ab_smooth[:, :, 1].astype(np.float32)
    lab_out = np.stack([l_ch, a_smooth, b_smooth], axis=2)
    lab_out = np.clip(lab_out, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab_out, cv2.COLOR_LAB2BGR)


def _simulate_gold_diamond(img: np.ndarray) -> np.ndarray:
    """Brightness boost, slight reflectivity."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:, :, 0] = np.minimum(255.0, lab[:, :, 0] * 1.08 + 3)
    lab = _no_over_whiten(lab.astype(np.uint8))
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def _simulate_threading(img: np.ndarray) -> np.ndarray:
    """Soften edges; add slight L lift so result is not darker."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab_uint8 = np.clip(lab, 0, 255).astype(np.uint8)
    smooth = cv2.bilateralFilter(lab_uint8, 3, 25, 25).astype(np.float32)
    # Ensure we don't darken: slight L lift
    smooth[:, :, 0] = np.minimum(255.0, smooth[:, :, 0] * 1.02 + 1.5)
    smooth = np.clip(smooth, 0, 255).astype(np.uint8)
    return cv2.cvtColor(smooth, cv2.COLOR_LAB2BGR)


def _simulate_acne_treatment(img: np.ndarray) -> np.ndarray:
    """Reduce redness slightly; small L lift so skin doesn't look darker."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:, :, 1] = lab[:, :, 1] * 0.88 + 128 * 0.12
    # Slight brightness so less-red doesn't read as darker
    lab[:, :, 0] = np.minimum(255.0, lab[:, :, 0] * 1.03 + 2)
    lab = np.clip(lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def simulate_service_impact(face_crop: np.ndarray, service_name: str) -> np.ndarray:
    """Apply one service simulation; return capped result."""
    if face_crop is None or face_crop.size == 0:
        return face_crop
    name = (service_name or "").lower()
    if "de-tan" in name or "detan" in name:
        after = _simulate_de_tan(face_crop)
    elif "fruit" in name:
        after = _simulate_fruit_facial(face_crop)
    elif "gold" in name or "diamond" in name:
        after = _simulate_gold_diamond(face_crop)
    elif "thread" in name or "wax" in name:
        after = _simulate_threading(face_crop)
    elif "acne" in name:
        after = _simulate_acne_treatment(face_crop)
    else:
        after = _simulate_fruit_facial(face_crop)
    return _cap_correction(face_crop, after)


def _product_correction_factor(days: int) -> float:
    """7 -> 0.15, 30 -> 0.30, 60 -> 0.50; cap 0.50."""
    if days <= 7:
        return 0.15
    if days <= 30:
        return 0.30
    return 0.50


def simulate_product_impact(face_crop: np.ndarray, days: int = 30) -> np.ndarray:
    """Controlled pigmentation lightening, redness reduction, edge-preserving smoothing, subtle glow. Cap 50%."""
    if face_crop is None or face_crop.size == 0:
        return face_crop
    f = _product_correction_factor(days)
    lab = cv2.cvtColor(face_crop, cv2.COLOR_BGR2LAB).astype(np.float32)
    # Mild L lift
    lab[:, :, 0] = lab[:, :, 0] + (128 - lab[:, :, 0]) * f * 0.4
    lab[:, :, 1] = lab[:, :, 1] * (1 - f * 0.3) + 128 * (f * 0.3)
    lab = _no_over_whiten(lab.astype(np.uint8))
    smooth = cv2.bilateralFilter(lab, 5, 40, 40)
    after = cv2.cvtColor(smooth, cv2.COLOR_LAB2BGR)
    return _cap_correction(face_crop, after)


def get_before_after_base64(
    face_crop: np.ndarray,
    top_service_name: str,
    use_product_simulation: bool = False,
    product_days: int = 30,
) -> Tuple[str, str]:
    """
    Return (before_base64, after_base64). After = service impact; if use_product_simulation
    then apply product time simulation on top (capped at 50% total).
    """
    before_b64 = _to_base64(face_crop) if face_crop is not None and face_crop.size > 0 else ""
    if face_crop is None or face_crop.size == 0:
        return before_b64, ""

    after = simulate_service_impact(face_crop, top_service_name)
    if use_product_simulation:
        after = simulate_product_impact(after, product_days)
    after_b64 = _to_base64(after)
    return before_b64, after_b64
