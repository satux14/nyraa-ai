from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional


class RecommendationRequest(BaseModel):
    skin_type: str
    acne_level: str
    face_shape: str
    dark_circle_score: Optional[str] = None


app = FastAPI(title="Nyraa Recommendation Service", version="1.0.0")


@app.post("/recommend")
async def recommend(payload: RecommendationRequest):
    services: List[str] = []
    products: List[str] = []

    skin = payload.skin_type
    acne = payload.acne_level
    shape = payload.face_shape

    if skin == "Oily" and acne in ["Moderate", "High"]:
        services.append("Acne Control Facial")
        products.append("Salicylic Cleanser")

    if skin == "Dry":
        services.append("Hydrating Facial")
        products.append("Vitamin C Serum")

    if shape == "Round":
        services.append("Layer Cut")
    elif shape == "Square":
        services.append("Soft Curl Styling")

    return {
        "recommended_services": services,
        "recommended_products": products,
    }

