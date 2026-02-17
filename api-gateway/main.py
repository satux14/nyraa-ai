import io
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
import jwt
from fastapi import FastAPI, Request, UploadFile, File, Form, Body, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse, FileResponse
import asyncpg
import numpy as np
import cv2
from sqlalchemy import create_engine

from srs_audit import init_audit
from srs_audit.fastapi import AuditMiddleware, metrics_route


FACE_SERVICE_URL = os.getenv("FACE_SERVICE_URL", "http://face-service:8001/detect-face")
SKIN_SERVICE_URL = os.getenv("SKIN_SERVICE_URL", "http://skin-service:8002/analyze-skin")
SHAPE_SERVICE_URL = os.getenv("SHAPE_SERVICE_URL", "http://shape-service:8003/detect-shape")
RECOMMENDATION_SERVICE_URL = os.getenv(
    "RECOMMENDATION_SERVICE_URL",
    "http://recommendation-service:8004/recommend",
)
SKIN_CONSULTING_SERVICE_URL = os.getenv(
    "SKIN_CONSULTING_SERVICE_URL",
    "http://skin-consulting-service:8005",
)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "nyraa_ai")
DB_USER = os.getenv("DB_USER", "nyraa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nyraa123")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
IST = ZoneInfo("Asia/Kolkata")

audit_db_engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
audit_logger = init_audit(service_name="nyraa-ai", db_engine=audit_db_engine, version="1.0.0")

app = FastAPI(title="NYRAA AI API Gateway", version="1.0.0")

app.add_middleware(
    AuditMiddleware,
    service_name="nyraa-ai",
    db_engine=audit_db_engine,
    version="1.0.0",
)
app.include_router(metrics_route)

security = HTTPBearer(auto_error=False)

db_pool: asyncpg.pool.Pool | None = None


def _create_token(role: str) -> str:
    payload = {"role": role, "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(credentials: Optional[HTTPAuthorizationCredentials]) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    return _decode_token(credentials)


async def get_admin_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
    payload = _decode_token(credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return payload


@app.get("/")
async def root():
    return {
        "service": "NYRAA AI API Gateway",
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
    # Ensure analysis_logs has required columns (for existing DBs created before auth).
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS dark_circle_score TEXT")
            await conn.execute("ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS user_type TEXT")
            await conn.execute("ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS customer_name TEXT")
            await conn.execute("ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS image_path TEXT")
            await conn.execute("ALTER TABLE analysis_logs ADD COLUMN IF NOT EXISTS analysis_result JSONB")
            await conn.execute("UPDATE analysis_logs SET user_type = 'guest' WHERE user_type IS NULL")
    except Exception as e:
        import logging
        logging.getLogger("uvicorn.error").warning("analysis_logs migration skipped: %s", e)
    if UPLOAD_DIR:
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
        except Exception as e:
            import logging
            logging.getLogger("uvicorn.error").warning("Could not create UPLOAD_DIR %s: %s", UPLOAD_DIR, e)


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
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    timeout = httpx.Timeout(20.0, connect=5.0)
    headers = {}
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            if method.upper() == "POST":
                resp = await client.post(url, files=files, json=json, headers=headers)
            else:
                resp = await client.get(url, params=json, headers=headers)
        except httpx.RequestError as exc:
            audit_logger.track_error("service_call_failed", details={"url": url, "error": str(exc)})
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


def _decode_image(contents: bytes):
    arr = np.frombuffer(contents, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _crop_face_region(image: np.ndarray, landmarks: List[Dict[str, float]], padding: float = 0.1) -> np.ndarray:
    h, w = image.shape[:2]
    xs = [lm["x"] * w for lm in landmarks]
    ys = [lm["y"] * h for lm in landmarks]
    x_min = max(0, int(min(xs) - padding * w))
    x_max = min(w, int(max(xs) + padding * w))
    y_min = max(0, int(min(ys) - padding * h))
    y_max = min(h, int(max(ys) + padding * h))
    if x_max <= x_min or y_max <= y_min:
        return image
    return image[y_min:y_max, x_min:x_max]


def _region_mean_brightness(image: np.ndarray, landmarks: List[Dict[str, float]], indices: List[int]) -> float:
    h, w = image.shape[:2]
    xs = [landmarks[i]["x"] * w for i in indices if i < len(landmarks)]
    ys = [landmarks[i]["y"] * h for i in indices if i < len(landmarks)]
    if not xs:
        return 0.0
    x_min = max(0, int(min(xs)) - 5)
    x_max = min(w, int(max(xs)) + 5)
    y_min = max(0, int(min(ys)) - 5)
    y_max = min(h, int(max(ys)) + 5)
    if x_max <= x_min or y_max <= y_min:
        return 0.0
    crop = image[y_min:y_max, x_min:x_max]
    return float(np.mean(crop))


def _compute_dark_circle_score(image: np.ndarray, landmarks: List[Dict[str, float]]) -> str:
    # MediaPipe: under-eye left ~ 243, 112, 26, 23, 24, 110, 25, 31, 228, 229, 230, 231, 232, 233
    under_eye_left = [243, 112, 26, 23, 24, 110, 25, 31, 228, 229, 230, 231, 232, 233]
    # under-eye right ~ 359, 463, 253, 260, 259, 257, 258, 286, 414, 413, 412, 411, 410
    under_eye_right = [359, 463, 253, 260, 259, 257, 258, 286, 414, 413, 412, 411, 410]
    # cheek left 93, 234; cheek right 454, 323
    cheek_left = [93, 234]
    cheek_right = [454, 323]
    under_eye_bright = (
        _region_mean_brightness(image, landmarks, under_eye_left)
        + _region_mean_brightness(image, landmarks, under_eye_right)
    ) / 2.0
    cheek_bright = (
        _region_mean_brightness(image, landmarks, cheek_left)
        + _region_mean_brightness(image, landmarks, cheek_right)
    ) / 2.0
    if cheek_bright <= 0:
        return "Low"
    ratio = under_eye_bright / cheek_bright
    if ratio < 0.85:
        return "High"
    if ratio < 0.95:
        return "Moderate"
    return "Low"


@app.post("/login")
async def login(request: Request, body: Dict[str, Any] = Body(...)):
    role = body.get("role")
    if role == "guest":
        audit_logger.track_login(username="guest", success=True, request=request)
        return {"access_token": _create_token("guest"), "role": "guest"}
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required for admin")
    if username != ADMIN_USER or password != ADMIN_PASSWORD:
        audit_logger.track_login(username=username, success=False, request=request)
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    audit_logger.track_login(username=username, success=True, request=request)
    return {"access_token": _create_token("admin"), "role": "admin"}


@app.post("/analyze")
async def analyze(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    file: UploadFile = File(...),
    customer_name: Optional[str] = Form(None),
):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    correlation_id = getattr(request.state, "correlation_id", None)
    filename = getattr(file, "filename", "image.jpg") or "image.jpg"
    content_type = file.content_type or "image/jpeg"

    file_tuple = (filename, contents, content_type)

    face = await call_service(FACE_SERVICE_URL, files={"file": file_tuple}, correlation_id=correlation_id)

    if not face.get("face_detected"):
        raise HTTPException(
            status_code=422,
            detail="We couldn't detect a face in this image. Please use a clear, front-facing photo with your face clearly visible and good lighting.",
        )

    landmarks = face.get("landmarks")
    if not landmarks:
        raise HTTPException(status_code=422, detail="Face landmarks not available")

    image = _decode_image(contents)
    if image is not None:
        cropped = _crop_face_region(image, landmarks)
        _, buf = cv2.imencode(".jpg", cropped)
        cropped_bytes = buf.tobytes()
    else:
        cropped_bytes = contents
    cropped_tuple = ("face_crop.jpg", cropped_bytes, "image/jpeg")

    skin = await call_service(SKIN_SERVICE_URL, files={"file": cropped_tuple}, correlation_id=correlation_id)

    shape = await call_service(
        SHAPE_SERVICE_URL,
        json={"landmarks": landmarks},
        correlation_id=correlation_id,
    )

    dark_circle_score = "Low"
    if image is not None:
        dark_circle_score = _compute_dark_circle_score(image, landmarks)

    combined = {
        "skin_type": skin.get("skin_type"),
        "acne_level": skin.get("acne_level"),
        "face_shape": shape.get("face_shape"),
        "dark_circle_score": dark_circle_score,
    }

    skin_response = dict(skin)
    skin_response["dark_circle_score"] = dark_circle_score

    rec = await call_service(
        RECOMMENDATION_SERVICE_URL,
        json=combined,
        correlation_id=correlation_id,
    )

    response = {
        "skin": skin_response,
        "shape": shape,
        "recommendation": rec,
        "landmarks": landmarks,
    }

    staff_url = f"{SKIN_CONSULTING_SERVICE_URL.rstrip('/')}/consult-staff"
    try:
        staff = await call_service(staff_url, files={"file": file_tuple}, correlation_id=correlation_id)
        response["skin_consult"] = staff
    except Exception:
        response["skin_consult"] = {"face_detected": False}

    user_type = current_user.get("role", "guest")
    cust_name = None
    if user_type == "admin":
        cust_name = (customer_name or "GENERAL").strip() or "GENERAL"
    else:
        cust_name = None

    image_path = None
    if contents and UPLOAD_DIR:
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            ext = "jpg"
            image_path = f"{uuid.uuid4().hex}.{ext}"
            out_path = os.path.join(UPLOAD_DIR, image_path)
            with open(out_path, "wb") as f:
                f.write(contents)
        except Exception:
            image_path = None

    if db_pool is not None:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO analysis_logs (user_type, customer_name, skin_type, acne_level, face_shape, dark_circle_score,
                                              recommended_services, recommended_products, image_path, analysis_result)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10::jsonb)
                    """,
                    user_type,
                    cust_name,
                    combined["skin_type"],
                    combined["acne_level"],
                    combined["face_shape"],
                    combined.get("dark_circle_score"),
                    json.dumps(rec.get("recommended_services") or []),
                    json.dumps(rec.get("recommended_products") or []),
                    image_path,
                    json.dumps(response),
                )
        except Exception:
            pass

    audit_logger.audit(
        action="ANALYSIS_COMPLETED",
        resource_type="analysis",
        details={
            "user_type": user_type,
            "customer_name": cust_name,
            "skin_type": combined.get("skin_type"),
            "face_shape": combined.get("face_shape"),
        },
        request=request,
        correlation_id=correlation_id,
    )
    audit_logger.track_interaction("skin_analysis", request=request)

    return response


def _to_ist(dt) -> Optional[str]:
    """Format datetime as IST string for display. DB returns UTC."""
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    local = dt.astimezone(IST)
    return local.strftime("%Y-%m-%d %H:%M:%S IST")


@app.get("/uploads/{path:path}")
async def serve_upload(path: str):
    """Serve saved analysis image. path is filename only (e.g. uuid.jpg)."""
    if not path or ".." in path or "/" in path:
        raise HTTPException(status_code=400, detail="Invalid path")
    full = os.path.join(UPLOAD_DIR, path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(full, media_type="image/jpeg")


@app.get("/admin/analyses")
async def admin_analyses(request: Request, current_user: Dict[str, Any] = Depends(get_admin_user)):
    """Return all analysis logs (admin only). created_at in IST."""
    audit_logger.audit(action="ADMIN_VIEW_LOGS", resource_type="admin", request=request)
    if db_pool is None:
        return []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, created_at, user_type, customer_name, skin_type, acne_level, face_shape,
                       dark_circle_score, recommended_services, recommended_products, image_path, analysis_result
                FROM analysis_logs ORDER BY created_at DESC
                """
            )
        return [
            {
                "id": r["id"],
                "created_at": _to_ist(r["created_at"]),
                "user_type": r["user_type"],
                "customer_name": r["customer_name"],
                "skin_type": r["skin_type"],
                "acne_level": r["acne_level"],
                "face_shape": r["face_shape"],
                "dark_circle_score": r["dark_circle_score"],
                "recommended_services": r["recommended_services"],
                "recommended_products": r["recommended_products"],
                "image_path": r["image_path"],
                "analysis_result": r["analysis_result"],
            }
            for r in rows
        ]
    except Exception:
        return []


@app.post("/admin/analyses/delete")
async def admin_delete_analyses(
    request: Request,
    body: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """Delete analysis log rows by id (admin only). Removes DB rows and their image files."""
    ids = body.get("ids")
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=400, detail="ids array required")
    ids = [int(x) for x in ids if isinstance(x, (int, float)) and int(x) > 0]
    if not ids:
        return {"deleted": 0}
    if db_pool is None:
        return {"deleted": 0}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, image_path FROM analysis_logs WHERE id = ANY($1::bigint[])",
                ids,
            )
            for r in rows:
                if r["image_path"] and UPLOAD_DIR:
                    full = os.path.join(UPLOAD_DIR, r["image_path"])
                    if os.path.isfile(full):
                        try:
                            os.remove(full)
                        except Exception:
                            pass
            await conn.execute(
                "DELETE FROM analysis_logs WHERE id = ANY($1::bigint[])",
                ids,
            )
        audit_logger.audit(
            action="ANALYSIS_DELETED",
            resource_type="admin",
            details={"deleted_ids": ids},
            request=request,
        )
        return {"deleted": len(ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/audit/logs")
async def get_audit_logs_endpoint(
    current_user: Dict[str, Any] = Depends(get_admin_user),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """Query audit logs with optional filters (admin only)."""
    return audit_logger.get_audit_logs(
        action=action,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )


@app.get("/admin/audit/stats")
async def get_audit_stats_endpoint(
    current_user: Dict[str, Any] = Depends(get_admin_user),
    period: str = "today",
):
    """Get audit statistics for a period (admin only)."""
    return audit_logger.get_audit_stats(period=period)


@app.post("/consult")
async def consult(file: UploadFile = File(...), current_user: Dict[str, Any] = Depends(get_current_user)):
    """Forward to skin-consulting-service: staff + customer results."""
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    filename = getattr(file, "filename", "image.jpg") or "image.jpg"
    content_type = file.content_type or "image/jpeg"
    file_tuple = (filename, contents, content_type)

    staff_url = f"{SKIN_CONSULTING_SERVICE_URL.rstrip('/')}/consult-staff"
    customer_url = f"{SKIN_CONSULTING_SERVICE_URL.rstrip('/')}/consult-customer"

    try:
        staff = await call_service(staff_url, files={"file": file_tuple})
    except HTTPException:
        staff = {"face_detected": False, "detail": "Skin consulting staff call failed"}

    try:
        customer = await call_service(customer_url, files={"file": file_tuple})
    except HTTPException:
        customer = {"face_detected": False, "detail": "Skin consulting customer call failed"}

    return {"staff": staff, "customer": customer}

