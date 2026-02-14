import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Nyraa Web UI", version="1.0.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    filename = file.filename or "image.jpg"
    content_type = file.content_type or "image/jpeg"

    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(
                f"{API_GATEWAY_URL}/analyze",
                files={"file": (filename, contents, content_type)},
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"API Gateway error: {e}")

    if resp.status_code >= 400:
        detail = resp.text
        try:
            detail = resp.json().get("detail", detail)
        except Exception:
            pass
        raise HTTPException(status_code=resp.status_code, detail=detail)

    return resp.json()
