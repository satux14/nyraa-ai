# Nyraa Hairstyle Preview Service – Implementation Prompt

## 🎯 Project Goal

Build a standalone microservice called:

Nyraa Hairstyle Preview Service

The system must:

- Detect face shape using MediaPipe
- Recommend Tamil Nadu appropriate hairstyles
- Apply selected hairstyle using Stable Diffusion 1.5 (img2img)
- Run entirely on Mac Mini (Apple Silicon, 16GB RAM)
- Use PyTorch MPS backend (NO CUDA, NO ControlNet, NO SDXL)
- Be lightweight, stable, and production-ready

---

## 🏗 Architecture

Folder structure:

hairstyle-service/
- main.py
- face_shape_detector.py
- hairstyle_recommender.py
- sd_pipeline.py
- tamil_hairstyles.json
- requirements.txt

Expose using FastAPI.

---

## 🧠 Face Shape Detection

Use MediaPipe FaceMesh.

Calculate:

- Jaw width (landmarks 234 & 454)
- Face height (landmarks 10 & 152)
- Cheekbone width
- Forehead width

Classify into:

- Oval
- Round
- Square
- Heart

Return:

{
  face_shape: "Oval",
  confidence: 82
}

Reduce confidence if:
- Poor lighting
- Partial face detection
- Blur detected

---

## 💇 Hairstyle Recommendation Logic

Load tamil_hairstyles.json:

Example structure:

[
  {
    "id": "tamil_bridal_jadai",
    "name": "Tamil Bridal Jadai",
    "face_shapes": ["Oval", "Round"],
    "category": "Bridal",
    "prompt": "Traditional Tamil bridal bun with jasmine flowers..."
  }
]

Return:

- Top 3 matching styles
- Reason
- Confidence %

---

## 🎨 Stable Diffusion Implementation

Use:

- runwayml/stable-diffusion-v1-5
- img2img pipeline only
- device = torch.device("mps")

Settings:

- Resolution: 512x512
- Steps: 25
- Guidance scale: 7
- Strength: 0.75
- torch.float16 if supported
- enable_attention_slicing()
- enable_vae_slicing()

No ControlNet.
No IP-Adapter.
No SDXL.

Load pipeline once globally at startup.

---

## 🎯 API Endpoints

POST /detect-face-shape  
Returns:
- face_shape
- confidence

POST /recommend-hairstyles  
Input:
- face_shape
- occasion (optional)

Returns:
- top_styles

POST /preview-hairstyle  
Input:
- image_base64
- hairstyle_id

Returns:
- styled_image_base64

---

## ⚡ Performance Constraints

- Memory under 10GB
- Single SD pipeline instance
- Limit concurrent generation
- Async FastAPI
- Proper error handling

---

## 🔐 Ethical Constraints

- Preserve identity
- Do not alter skin tone
- Avoid unrealistic transformations
- Add disclaimer for preview mode

---

## 📦 Expected Output from Code AI

Generate:

- Complete folder structure
- Full FastAPI implementation
- Stable Diffusion MPS pipeline
- Hairstyle JSON loader
- Error handling
- Logging
- Setup instructions