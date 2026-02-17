"""
Service recommendation rules from skin scores. Each recommendation includes
reason, expected effect, and estimated improvement %. Builds top_3_services and suggested_roadmap.
"""
from dataclasses import dataclass
from typing import List, Dict, Any

from skin_scoring import SkinScores


@dataclass
class ServiceRecommendation:
    service: str
    reason: str
    expected_effect: str
    estimated_improvement_pct: float


def _recommendations(scores: SkinScores) -> List[ServiceRecommendation]:
    out: List[ServiceRecommendation] = []

    if scores.pigmentation_density > 45:
        out.append(ServiceRecommendation(
            service="De-Tan Facial",
            reason=f"Pigmentation density score is {scores.pigmentation_density:.0f} (above 45).",
            expected_effect="Reduce tan and dark spots; improve tone uniformity.",
            estimated_improvement_pct=25.0,
        ))

    if scores.brightness < 60:
        out.append(ServiceRecommendation(
            service="Fruit Facial",
            reason=f"Brightness score is {scores.brightness:.0f} (below 60).",
            expected_effect="Add glow and mild hydration; smooth skin.",
            estimated_improvement_pct=20.0,
        ))

    if scores.redness > 50:
        out.append(ServiceRecommendation(
            service="Acne Treatment",
            reason=f"Redness score is {scores.redness:.0f} (above 50).",
            expected_effect="Calm redness and reduce acne-related inflammation.",
            estimated_improvement_pct=30.0,
        ))

    if scores.facial_hair_density > 55:
        out.append(ServiceRecommendation(
            service="Threading / Waxing",
            reason=f"Facial hair density score is {scores.facial_hair_density:.0f} (high).",
            expected_effect="Clean brow edges and upper lip; smoother finish.",
            estimated_improvement_pct=15.0,
        ))

    # Gold/Diamond: optional for dull skin (brightness low, not covered by fruit only once)
    if scores.brightness < 50 and not any(r.service == "Gold/Diamond Facial" for r in out):
        out.append(ServiceRecommendation(
            service="Gold/Diamond Facial",
            reason=f"Brightness score is {scores.brightness:.0f}; premium boost recommended.",
            expected_effect="Brightness boost and slight reflectivity enhancement.",
            estimated_improvement_pct=22.0,
        ))

    return out


def get_top_3_services(scores: SkinScores) -> List[Dict[str, Any]]:
    """Return up to 3 service recommendations with reason, effect, improvement %."""
    recs = _recommendations(scores)
    # Sort by estimated improvement descending, take 3
    recs.sort(key=lambda r: r.estimated_improvement_pct, reverse=True)
    top = recs[:3]
    return [
        {
            "service": r.service,
            "reason": r.reason,
            "expected_effect": r.expected_effect,
            "estimated_improvement_pct": round(r.estimated_improvement_pct, 1),
        }
        for r in top
    ]


def get_suggested_roadmap(scores: SkinScores) -> List[str]:
    """Ordered list of service names as a suggested sequence (e.g. De-Tan then Fruit)."""
    recs = _recommendations(scores)
    recs.sort(key=lambda r: r.estimated_improvement_pct, reverse=True)
    return [r.service for r in recs]


def get_improvement_projection(scores: SkinScores) -> Dict[str, float]:
    """Projected score changes after following recommendations (example ranges)."""
    recs = _recommendations(scores)
    proj = {
        "brightness": scores.brightness,
        "pigmentation_density": scores.pigmentation_density,
        "redness": scores.redness,
        "texture_roughness": scores.texture_roughness,
        "dark_circle_index": scores.dark_circle_index,
        "facial_hair_density": scores.facial_hair_density,
    }
    for r in recs:
        if "De-Tan" in r.service:
            proj["pigmentation_density"] = max(0, proj["pigmentation_density"] - 20)
        if "Fruit" in r.service:
            proj["brightness"] = min(100, proj["brightness"] + 15)
        if "Acne" in r.service:
            proj["redness"] = max(0, proj["redness"] - 25)
        if "Threading" in r.service or "Waxing" in r.service:
            proj["facial_hair_density"] = max(0, proj["facial_hair_density"] - 30)
        if "Gold" in r.service or "Diamond" in r.service:
            proj["brightness"] = min(100, proj["brightness"] + 10)
    return {k: round(v, 1) for k, v in proj.items()}
