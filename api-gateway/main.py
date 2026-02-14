import os
from typing import Any, Dict

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import asyncpg


FACE_SERVICE_URL = os.getenv("FACE_SERVICE_URL", "http://face-service:8001/detect-face")
SKIN_SERVICE_URL = os.getenv("SKIN_SERVICE_URL", "http://skin-service:8002/analyze-skin")
SHAPE_SERVICE_URL = os.getenv("SHAPE_SERVICE_URL", "http://shape-service:8003/detect-shape")
RECOMMENDATION_SERVICE_URL = os.getenv(
    "RECOMMENDATION_SERVICE_URL",
    "http://recommendation-service:8004/recommend",
)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "nyraa_ai")
DB_USER = os.getenv("DB_USER", "nyraa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nyraa123")


app = FastAPI(title="Nyraa API Gateway", version="1.0.0")

db_pool: asyncpg.pool.Pool | None = None


@app.get("/")
async def root():
    return {
        "service": "Nyraa AI API Gateway",
        "docs": "/docs",
        "analyze": "POST /analyze (upload face image)",
        "web_ui": "http://localhost:9001",
    }


@app.on_event("startup")
async def on_startup() -> None:
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=1,
        max_size=5,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global db_pool
    if db_pool:
        await db_pool.close()


async def call_service(
    url: str,
    method: str = "POST",
    files: Dict[str, Any] | None = None,
    json: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    timeout = httpx.Timeout(20.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method.upper() == "POST":
                resp = await client.post(url, files=files, json=json)
            else:
                resp = await client.get(url, params=json)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Error contacting service at {url}: {exc}",
            )

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Service error from {url}: {resp.text}",
        )

    return resp.json()


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    filename = getattr(file, "filename", "image.jpg") or "image.jpg"
    content_type = file.content_type or "image/jpeg"

    file_tuple = (filename, contents, content_type)

    face_task = call_service(
        FACE_SERVICE_URL,
        files={"file": file_tuple},
    )
    skin_task = call_service(
        SKIN_SERVICE_URL,
        files={"file": file_tuple},
    )

    face, skin = await face_task, await skin_task

    if not face.get("face_detected"):
        raise HTTPException(
            status_code=422,
            detail="We couldn't detect a face in this image. Please use a clear, front-facing photo with your face clearly visible and good lighting.",
        )

    landmarks = face.get("landmarks")
    if not landmarks:
        raise HTTPException(status_code=422, detail="Face landmarks not available")

    shape = await call_service(
        SHAPE_SERVICE_URL,
        json={"landmarks": landmarks},
    )

    combined = {
        "skin_type": skin.get("skin_type"),
        "acne_level": skin.get("acne_level"),
        "face_shape": shape.get("face_shape"),
    }

    rec = await call_service(
        RECOMMENDATION_SERVICE_URL,
        json=combined,
    )

    response = {
        "skin": skin,
        "shape": shape,
        "recommendation": rec,
        "landmarks": landmarks,
    }

    if db_pool is not None:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analysis_logs (skin_type, acne_level, face_shape,
                                              recommended_services, recommended_products)
                    VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
                    """,
                    combined["skin_type"],
                    combined["acne_level"],
                    combined["face_shape"],
                    JSONResponse(content=rec["recommended_services"]).body.decode(),
                    JSONResponse(content=rec["recommended_products"]).body.decode(),
                )
        except Exception:
            # Logging can be added here; failures to log should not break the API.
            pass

    return response

