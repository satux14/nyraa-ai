from fastapi import FastAPI, UploadFile, File, HTTPException
import numpy as np
import cv2
import mediapipe as mp

app = FastAPI(title="NYRAA AI Face Service", version="1.0.0")

mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(static_image_mode=True)


def read_image(file_bytes: bytes) -> np.ndarray:
    np_arr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return image


@app.post("/detect-face")
async def detect_face(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    image = read_image(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image")

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return {"face_detected": False, "landmarks": []}

    landmarks = []
    for lm in results.multi_face_landmarks[0].landmark:
        landmarks.append({"x": float(lm.x), "y": float(lm.y)})

    return {"face_detected": True, "landmarks": landmarks}

