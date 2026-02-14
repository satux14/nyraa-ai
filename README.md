# Nyraa AI – Face & Skin Analysis (Microservices)

This project implements the Nyraa AI Face & Skin Analysis system as a set of Python/FastAPI microservices orchestrated with Docker Compose.

## Services

- `api-gateway` – Orchestrates all calls, exposes `POST /analyze` on port 9000.
- `web-ui` – Frontend for uploading a face image and viewing results on port 9001.
- `face-service` – MediaPipe FaceMesh; returns 468 facial landmarks.
- `skin-service` – TensorFlow MobileNetV2-based skin analysis.
- `shape-service` – Landmark geometry-based face shape detection.
- `recommendation-service` – Rule-based mapping from analysis to salon services and products.
- `db` – PostgreSQL 15 for analysis logs.

## Running Locally (CPU-only, Mac mini or dev machine)

1. Install Docker Desktop.
2. From the `nyraa-ai` directory, build and start:

   ```bash
   docker compose up --build
   ```

3. **Web UI:** Open **http://localhost:9001** to upload a face image and see results.
4. **API docs:** Open **http://localhost:9000/docs** to use the `/analyze` endpoint directly.

All inter-service communication happens on the internal `nyraa-network` bridge. Only the API Gateway is exposed externally.

