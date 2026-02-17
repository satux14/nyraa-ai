import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI
from pydantic import BaseModel


class RecommendationRequest(BaseModel):
    skin_type: str
    acne_level: str
    face_shape: str
    dark_circle_score: Optional[str] = None


app = FastAPI(title="NYRAA AI Recommendation Service", version="1.0.0")

CONFIG_PATH = os.getenv("RECOMMENDATIONS_CONFIG", "/app/config/recommendations.json")
_rules: List[Dict[str, Any]] = []


def _load_rules() -> List[Dict[str, Any]]:
    path = Path(CONFIG_PATH)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("rules", [])
    except Exception:
        return []


def _rule_matches(conditions: Dict[str, Any], payload: RecommendationRequest) -> bool:
    payload_dict = {
        "skin_type": payload.skin_type,
        "acne_level": payload.acne_level,
        "face_shape": payload.face_shape,
        "dark_circle_score": payload.dark_circle_score or "Low",
    }
    for key, value in conditions.items():
        if key not in payload_dict:
            continue
        actual = payload_dict[key]
        if isinstance(value, list):
            if actual not in value:
                return False
        else:
            if actual != value:
                return False
    return True


def _recommend_from_rules(payload: RecommendationRequest) -> Tuple[List[str], List[str]]:
    services: List[str] = []
    products: List[str] = []
    seen_s: set = set()
    seen_p: set = set()
    for rule in _rules:
        cond = rule.get("conditions", {})
        if not _rule_matches(cond, payload):
            continue
        for s in rule.get("services", []):
            if s and s not in seen_s:
                services.append(s)
                seen_s.add(s)
        for p in rule.get("products", []):
            if p and p not in seen_p:
                products.append(p)
                seen_p.add(p)
    return services, products


def _recommend_fallback(payload: RecommendationRequest) -> Tuple[List[str], List[str]]:
    services: List[str] = []
    products: List[str] = []
    skin = payload.skin_type
    acne = payload.acne_level
    shape = payload.face_shape
    dark_circle = payload.dark_circle_score or "Low"

    if skin == "Oily" and acne in ["Moderate", "High"]:
        services.append("Acne Control Facial")
        products.append("Salicylic Cleanser")
    if skin == "Dry":
        services.append("Hydrating Facial")
        products.append("Vitamin C Serum")
    if dark_circle in ["Moderate", "High"]:
        services.append("Under-Eye Brightening Treatment")
        products.append("Caffeine Eye Serum")
    if shape == "Round":
        services.append("Layer Cut")
    elif shape == "Square":
        services.append("Soft Curl Styling")
    elif shape == "Oblong":
        services.append("Soft Layers / Side-Swept Styling")
    elif shape == "Heart":
        services.append("Chin-Length or Layered Cut")
    elif shape == "Diamond":
        services.append("Styles to Add Width at Forehead or Chin")

    return services, products


@app.on_event("startup")
def startup():
    global _rules
    _rules = _load_rules()


@app.post("/recommend")
async def recommend(payload: RecommendationRequest):
    if _rules:
        services, products = _recommend_from_rules(payload)
    else:
        services, products = _recommend_fallback(payload)

    return {
        "recommended_services": services,
        "recommended_products": products,
    }
