from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import numpy as np


class Landmark(BaseModel):
    x: float
    y: float


class ShapeRequest(BaseModel):
    landmarks: List[Landmark]


app = FastAPI(title="Nyraa Shape Service", version="1.0.0")


@app.post("/detect-shape")
async def detect_shape(payload: ShapeRequest):
    landmarks = payload.landmarks
    if len(landmarks) <= max(454, 234, 152, 10):
        raise HTTPException(status_code=400, detail="Insufficient landmarks provided")

    points = np.array([[lm.x, lm.y] for lm in landmarks], dtype=np.float32)

    jaw_left = points[234]
    jaw_right = points[454]
    forehead = points[10]
    chin = points[152]

    width = float(np.linalg.norm(jaw_right - jaw_left))
    height = float(np.linalg.norm(chin - forehead))

    if width == 0.0:
        raise HTTPException(status_code=400, detail="Invalid landmark geometry")

    ratio = height / width

    if ratio > 1.5:
        face_shape = "Oval"
    elif ratio < 1.2:
        face_shape = "Round"
    else:
        face_shape = "Square"

    return {"face_shape": face_shape}

