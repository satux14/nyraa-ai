"""
NYRAA AI Skin Consulting Service.
POST /consult-staff: full analysis (scores, confidence, top_3_services, roadmap, projection).
POST /consult-customer: before/after base64, top service, disclaimer.
"""
import logging
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException

from face_region_extractor import extract_face_regions
from skin_scoring import compute_skin_scores, SkinScores
from confidence_engine import compute_confidence
from recommendation_engine import (
    get_top_3_services,
    get_suggested_roadmap,
    get_improvement_projection,
)
from simulation_engine import get_before_after_base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NYRAA AI Skin Consulting Service",
    version="1.0.0",
    description="Deep skin analysis, recommendations, and simulation for staff and customer.",
)


def _decode_image(contents: bytes) -> np.ndarray:
    arr = np.frombuffer(contents, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


@app.post("/consult-staff")
async def consult_staff(file: UploadFile = File(...)):
    """
    Staff mode: skin_scores, confidence_score, manual_review_required,
    top_3_services, suggested_roadmap, improvement_projection.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    image = _decode_image(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image")

    regions = extract_face_regions(image)
    if not regions.face_detected:
        return {
            "face_detected": False,
            "skin_scores": None,
            "confidence_score": 0.0,
            "manual_review_required": True,
            "top_3_services": [],
            "suggested_roadmap": [],
            "improvement_projection": {},
        }

    scores = compute_skin_scores(image, regions)
    confidence = compute_confidence(image, regions)
    top_3 = get_top_3_services(scores)
    roadmap = get_suggested_roadmap(scores)
    projection = get_improvement_projection(scores)

    return {
        "face_detected": True,
        "skin_scores": scores.to_dict(),
        "confidence_score": confidence.confidence_score,
        "manual_review_required": confidence.manual_review_required,
        "top_3_services": top_3,
        "suggested_roadmap": roadmap,
        "improvement_projection": projection,
    }


@app.post("/consult-customer")
async def consult_customer(file: UploadFile = File(...)):
    """
    Customer mode: before image (base64), after simulated image (base64),
    top recommended service, disclaimer.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    image = _decode_image(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image")

    regions = extract_face_regions(image)
    if not regions.face_detected:
        return {
            "face_detected": False,
            "before_image_base64": "",
            "after_image_base64": "",
            "top_recommended_service": None,
            "disclaimer": "This visualization is a digital simulation. Results may vary.",
        }

    scores = compute_skin_scores(image, regions)
    top_3 = get_top_3_services(scores)
    top_service = top_3[0]["service"] if top_3 else "Fruit Facial"

    before_b64, after_b64 = get_before_after_base64(
        regions.face_crop,
        top_service,
        use_product_simulation=False,
    )

    return {
        "face_detected": True,
        "before_image_base64": before_b64,
        "after_image_base64": after_b64,
        "top_recommended_service": top_service,
        "disclaimer": "This visualization is a digital simulation. Results may vary.",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "skin-consulting"}
