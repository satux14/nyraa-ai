from fastapi import FastAPI, UploadFile, File, HTTPException
import numpy as np
import cv2
import tensorflow as tf

app = FastAPI(title="Nyraa Skin Service", version="1.0.0")

model = tf.keras.applications.MobileNetV2(
    weights="imagenet",
    include_top=False,
    pooling="avg",
)


def read_image(file_bytes: bytes) -> np.ndarray:
    np_arr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return image


def preprocess(image: np.ndarray) -> np.ndarray:
    image_resized = cv2.resize(image, (224, 224))
    image_resized = tf.keras.applications.mobilenet_v2.preprocess_input(
        image_resized.astype(np.float32)
    )
    return np.expand_dims(image_resized, axis=0)


@app.post("/analyze-skin")
async def analyze_skin(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    image = read_image(contents)
    if image is None:
        raise HTTPException(status_code=400, detail="Unable to decode image")

    img_batch = preprocess(image)
    _ = model.predict(img_batch)

    brightness = float(np.mean(image))
    acne_score = float(np.std(image) / 50.0)

    if brightness > 150:
        skin_type = "Dry"
    elif brightness < 100:
        skin_type = "Oily"
    else:
        skin_type = "Combination"

    if acne_score > 2:
        acne_level = "High"
    elif acne_score > 1:
        acne_level = "Moderate"
    else:
        acne_level = "Low"

    return {
        "skin_type": skin_type,
        "acne_level": acne_level,
    }

