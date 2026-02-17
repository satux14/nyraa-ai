# NYRAA AI – Skin Service (CoreML / GPU Path)

This folder is reserved for a future GPU-accelerated skin analysis service running **natively on macOS** (outside Docker) on the Mac mini.

## Goal

- Provide the same HTTP contract as the Dockerized `skin-service`:
  - `POST /analyze-skin` with an uploaded image.
  - Response JSON:
    - `skin_type`
    - `acne_level`

## Recommended Implementation Approach

1. Train or fine-tune a better skin/acne classifier (TensorFlow/PyTorch).
2. Export the trained model to CoreML using `coremltools`.
3. Implement a small HTTP server on macOS, for example:
   - A Swift server using Vapor, or
   - A Python FastAPI app using `coremltools` / `tensorflow-metal`.
4. Run the service on `localhost:8202` and configure the API Gateway environment variable:

   ```bash
   SKIN_SERVICE_URL=http://host.docker.internal:8202/analyze-skin
   ```

This allows the Dockerized API Gateway to offload heavy skin analysis to the GPU-accelerated service while keeping all other services in Docker.

