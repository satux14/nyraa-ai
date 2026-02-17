# Nyraa Smart Skin Consultation Engine – Implementation Prompt

## 🎯 Project Goal

Build a microservice called:

Nyraa Smart Skin Consultation Engine

The system must:

- Perform deep but lightweight skin analysis
- Score multiple skin metrics (0–100 scale)
- Recommend salon services (De-Tan, Fruit Facial, Gold/Diamond, Acne Treatment, Threading, Waxing)
- Simulate realistic service impact
- Simulate product improvement over time
- Include AI confidence scoring
- Be optimized for Mac Mini (CPU-friendly)
- No heavy CNN models

---

## 🏗 Architecture

Folder structure:

skin-service/
- main.py
- face_region_extractor.py
- skin_scoring.py
- recommendation_engine.py
- simulation_engine.py
- confidence_engine.py
- requirements.txt

Expose using FastAPI.

---

## 🧠 Required Skin Metrics (0–100)

Implement using OpenCV + NumPy.

### 1. Brightness Index
Convert to LAB.
Mean of L channel.

### 2. Pigmentation Density
Detect dark clusters:
% of pixels below threshold relative to mean L.

### 3. Redness Score
HSV red pixel ratio:
Hue range 0–15 and 160–180.

### 4. Texture Roughness
Laplacian variance.

### 5. Dark Circle Index
Under-eye brightness vs cheek brightness difference.

### 6. Facial Hair Density
Edge density + dark cluster detection.

Normalize all metrics to 0–100.

---

## 🧠 AI Confidence System

Reduce confidence if:

- Lighting uneven
- Image blur high
- Face partially detected
- Skin region too small

Return:

{
  confidence_score: 78
}

If < 60:
Return flag:
manual_review_required: true

---

## 💆 Service Recommendation Rules

IF Pigmentation > 45 → Recommend De-Tan Facial  
IF Brightness < 60 AND dryness mild → Fruit Facial  
IF Event Mode = Bridal → Gold/Diamond Facial  
IF Redness > 50 → Acne Treatment  
IF Hair Density high → Threading/Waxing  

Each recommendation must include:

- Reason
- Expected visible effect
- Estimated improvement %

---

## ✨ Service Impact Simulation (Immediate)

### De-Tan
- Reduce pigmentation 20–30%
- Improve tone uniformity

### Fruit Facial
- Add glow
- Mild hydration smoothing

### Gold/Diamond Facial
- Brightness boost
- Slight reflectivity enhancement

### Threading
- Clean brow edges
- Remove upper lip shadow

Preserve natural texture.
No over-whitening.

---

## 🧴 Product Time Simulation

Support:

- 7 days → 15% correction
- 30 days → 30% correction
- 60 days → max 50%

Apply:

- Controlled pigmentation lightening
- Controlled redness reduction
- Edge-preserving smoothing
- Subtle glow layer

Never exceed 50% correction.

---

## 📊 Internal Staff Mode Output

Return:

{
  skin_scores,
  confidence_score,
  top_3_services,
  suggested_roadmap,
  improvement_projection
}

---

## 👩 Customer Mode Output

Return simplified:

- Before image
- After simulated image
- Top recommended service
- Disclaimer:
  "This visualization is a digital simulation. Results may vary."

---

## ⚡ Performance Requirements

- CPU-based processing
- Execution under 2 seconds
- Async FastAPI
- Docker-ready
- Modular structure

---

## 🔐 Ethical Limits

Hard-limit:

- Max 50% visual correction
- No skin whitening beyond natural tone
- No “cure” claims
- Always include disclaimer

---

## 📦 Expected Output from Code AI

Generate:

- Full modular FastAPI project
- Skin scoring implementation
- Service recommendation engine
- Simulation engine
- Confidence engine
- Error handling
- Logging
- Setup instructions