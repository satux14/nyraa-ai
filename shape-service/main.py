from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import numpy as np


class Landmark(BaseModel):
    x: float
    y: float


class ShapeRequest(BaseModel):
    landmarks: List[Landmark]


app = FastAPI(title="NYRAA AI Shape Service", version="1.0.0")


@app.post("/detect-shape")
async def detect_shape(payload: ShapeRequest):
    landmarks = payload.landmarks
    required = [454, 234, 152, 10, 21, 251, 93, 323]
    if len(landmarks) <= max(required):
        raise HTTPException(status_code=400, detail="Insufficient landmarks provided")

    points = np.array([[lm.x, lm.y] for lm in landmarks], dtype=np.float32)

    jaw_left = points[234]
    jaw_right = points[454]
    forehead_top = points[10]
    chin = points[152]
    forehead_left = points[21]
    forehead_right = points[251]
    cheek_left = points[93]
    cheek_right = points[323]

    jaw_width = float(np.linalg.norm(jaw_right - jaw_left))
    face_height = float(np.linalg.norm(chin - forehead_top))
    forehead_width = float(np.linalg.norm(forehead_right - forehead_left))
    cheek_width = float(np.linalg.norm(cheek_right - cheek_left))

    if jaw_width == 0.0:
        raise HTTPException(status_code=400, detail="Invalid landmark geometry")

    ratio = face_height / jaw_width

    if ratio > 1.65:
        face_shape = "Oblong"
    elif ratio < 1.2:
        face_shape = "Round"
    elif cheek_width > forehead_width and cheek_width > jaw_width:
        face_shape = "Diamond"
    elif forehead_width > jaw_width * 1.08:
        face_shape = "Heart"
    elif ratio > 1.5:
        face_shape = "Oval"
    else:
        face_shape = "Square"

    return {"face_shape": face_shape}

