import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import httpx

# In Docker Compose, set API_GATEWAY_URL=http://api-gateway:8000. When running web-ui on host, use http://localhost:9000.
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:9000")
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="NYRAA AI Web UI", version="1.0.0")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...), customer_name: str = Form(None), authorization: str = Header(None)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    filename = file.filename or "image.jpg"
    content_type = file.content_type or "image/jpeg"

    timeout = httpx.Timeout(60.0, connect=10.0)
    headers = {"Authorization": authorization}
    data = {}
    if customer_name is not None and customer_name.strip():
        data["customer_name"] = customer_name.strip()
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(
                f"{API_GATEWAY_URL}/analyze",
                files={"file": (filename, contents, content_type)},
                data=data,
                headers=headers,
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


@app.post("/api/login")
async def login(request: Request):
    """Proxy to gateway /login. Body: { role: 'guest' } or { username, password }."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(f"{API_GATEWAY_URL}/login", json=body)
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


@app.get("/api/uploads/{path:path}")
async def serve_upload(path: str):
    """Proxy to gateway /uploads/<path> to serve saved analysis images."""
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{API_GATEWAY_URL}/uploads/{path}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Gateway error: {e}")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Image not found")
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))


@app.get("/api/admin/analyses")
async def admin_analyses(authorization: str = Header(None)):
    """Proxy to gateway GET /admin/analyses. Requires Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(
                f"{API_GATEWAY_URL}/admin/analyses",
                headers={"Authorization": authorization},
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


@app.post("/api/admin/analyses/delete")
async def admin_delete_analyses(request: Request, authorization: str = Header(None)):
    """Proxy to gateway POST /admin/analyses/delete. Requires Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON body required")
    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(
                f"{API_GATEWAY_URL}/admin/analyses/delete",
                json=body,
                headers={"Authorization": authorization},
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


@app.post("/api/consult")
async def consult(file: UploadFile = File(...), authorization: str = Header(None)):
    """Proxy to API gateway /consult (skin-consulting-service)."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    filename = file.filename or "image.jpg"
    content_type = file.content_type or "image/jpeg"

    timeout = httpx.Timeout(60.0, connect=10.0)
    headers = {"Authorization": authorization}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(
                f"{API_GATEWAY_URL}/consult",
                files={"file": (filename, contents, content_type)},
                headers=headers,
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
