# NYRAA AI Skin Consulting Service

Lightweight skin consultation microservice: face detection (MediaPipe), 6 skin metrics (0–100), confidence scoring, service recommendations, and before/after simulation. CPU-only; no heavy CNN.

## Endpoints

- **POST /consult-staff** – Upload image; returns `skin_scores`, `confidence_score`, `manual_review_required`, `top_3_services`, `suggested_roadmap`, `improvement_projection`.
- **POST /consult-customer** – Upload image; returns `before_image_base64`, `after_image_base64`, `top_recommended_service`, `disclaimer`.
- **GET /health** – Health check.

## Metrics (0–100)

Brightness, pigmentation density, redness, texture roughness, dark circle index, facial hair density. Confidence reduced for blur, uneven lighting, partial face, or small skin region; if &lt; 60 then `manual_review_required: true`.

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8005
```

Or via Docker Compose from repo root: `docker compose up --build` (service on port 8005).
