# NYRAA AI – Analysis Capabilities & How to Maximise Customer Benefit

## 1. What the Services Do Today

### Face Service (MediaPipe FaceMesh)
- **Current:** Detects one face and returns **468 normalized landmarks** (eyes, nose, lips, jaw, forehead, etc.).
- **Used for:** Face shape (via Shape Service) and as input for any region-based analysis.
- **Limitation:** Single face only; no expression or age estimate.

### Skin Service (MobileNetV2 + heuristics)
- **Current:**
  - **Skin type:** Oily / Dry / Combination, from **average image brightness** (bright → Dry, dark → Oily).
  - **Acne level:** Low / Moderate / High, from **pixel variance** (texture proxy).
- **Limitation:** Rules are heuristic, not trained on real skin labels. No face-region focus (whole image used). No pigmentation, dark circles, or wrinkles.

### Shape Service (landmark geometry)
- **Current:** Uses 4 landmarks (forehead, chin, jaw left/right) to compute **height/width ratio** and classifies:
  - **Oval** (ratio > 1.5), **Round** (ratio < 1.2), **Square** (else).
- **Limitation:** Only three shapes; no oblong/heart/diamond. No cheek or nose metrics.

### Recommendation Service (rules)
- **Current:** Maps skin type + acne + face shape to:
  - **Services:** e.g. Acne Control Facial, Hydrating Facial, Layer Cut, Soft Curl Styling.
  - **Products:** e.g. Salicylic Cleanser, Vitamin C Serum.
- **Limitation:** Fixed rules; not personalised by severity or preferences. No dark-circle or other signals.

---

## 2. Advanced Analyses the Stack Can Support (With Small Extensions)

These fit the current architecture and give customers more value.

| Area | Advanced analysis | How (high level) | Customer benefit |
|------|--------------------|------------------|-------------------|
| **Skin** | **Dark circles** | Crop under-eye from landmarks, compare brightness to cheek; return Low/Moderate/High | Clear “tiredness” / under-eye score and product suggestions |
| **Skin** | **Pigmentation / spots** | Use face landmarks to crop forehead/cheeks; variance or a small spot detector | “Evenness” or “pigmentation” score and targeted treatments |
| **Skin** | **Skin type from face region** | Crop face (or T-zone) using landmarks, run current logic on crop | More accurate skin type (avoids hair/background) |
| **Skin** | **Roughness / texture** | Local variance or frequency analysis on cheek/forehead crop | “Smoothness” or “texture” score for product choice |
| **Shape** | **More shapes** | Add cheek width, nose length, etc.; classify Oblong, Heart, Diamond | Better haircut and styling recommendations |
| **Shape** | **Symmetry** | Compare left/right landmark distances | “Symmetry” score (informational or for treatment focus) |
| **Recommendations** | **Dark circle / pigmentation rules** | Add inputs: dark_circle_score, pigmentation_score; extend rules | More relevant serums and treatments |
| **Recommendations** | **Salon-specific menu** | Load services/products from DB or config per salon | Recommendations match actual menu and pricing |
| **Recommendations** | **Severity-weighted** | Use acne_level + skin_type strength to suggest “priority” or “gentle” options | Safer and more relevant plans |

---

## 3. Improvements for Maximum Customer Benefit

### Quick wins (no new models)

1. **Crop to face for skin**
   - Use Face Service landmarks to crop a face (or T-zone) rectangle before Skin Service.
   - **Benefit:** Skin type and acne level less affected by background, hair, and lighting.

2. **Dark circle score**
   - New small step (in Skin Service or a tiny “DarkCircle” service): under-eye crop from landmarks → average brightness vs cheek → Low/Moderate/High.
   - **Benefit:** Clear, explainable “under-eye” result and product suggestions (e.g. caffeine serum, brightening).

3. **More face shapes**
   - Add Oblong, Heart, Diamond using extra landmarks (e.g. cheek, nose) and thresholds.
   - **Benefit:** Better match to real face shapes and styling advice.

4. **Richer recommendation rules**
   - Add rules for Combination + acne, Normal + “boost glow”, and for dark_circle_score / pigmentation when you add them.
   - **Benefit:** More personalised and complete suggestions.

5. **Salon-configurable recommendations**
   - Store “service → conditions” and “product → conditions” in DB or config; Recommendation Service reads them.
   - **Benefit:** Each salon sees only their services/products and pricing.

### Medium-term (better accuracy)

6. **Trained skin model**
   - Replace brightness/variance heuristics with a small CNN (or fine-tuned MobileNet) trained on labelled skin type / acne / dark circles.
   - **Benefit:** More reliable skin type and acne level; possible pigmentation/evenness score.

7. **GPU / CoreML skin service**
   - Run the skin (and later dark-circle) model on Mac mini GPU or CoreML.
   - **Benefit:** Faster, scalable analysis for multiple customers.

8. **Under-eye and T-zone regions in UI**
   - Show overlays (e.g. under-eye, T-zone, cheeks) and which regions drove which scores.
   - **Benefit:** Trust and clarity (“this is why we said oily / dark circles”).

### Longer-term (fuller experience)

9. **Before/after and history**
   - Store analysis results by customer/session; show simple before/after or “last time vs now”.
   - **Benefit:** Progress tracking and retention.

10. **Multi-language and accessibility**
    - Localise UI and recommendations (e.g. Tamil, Hindi); ensure contrast and screen-reader support.
    - **Benefit:** Inclusive for all salon customers.

11. **Consent and privacy**
    - Optional “save photo” vs “analyse only”; clear retention policy; delete after N days if no consent.
    - **Benefit:** Trust and compliance.

---

## 4. Suggested Priority Order

| Priority | Item | Why |
|----------|------|-----|
| 1 | **Crop to face for skin** | Better accuracy with minimal code; no new model. |
| 2 | **Dark circle score + rules** | High perceived value; uses existing landmarks. |
| 3 | **More face shapes** | Better styling relevance. |
| 4 | **Salon-configurable recommendations** | Directly ties AI to your menu and pricing. |
| 5 | **Trained skin model** | Big step up in reliability and optional extra signals (e.g. pigmentation). |
| 6 | **Region overlays in UI** | Builds trust and explains “what we analysed”. |

---

## 5. Summary

- **Today:** The system gives **face detection**, **heuristic skin type and acne level**, **three face shapes**, and **rule-based services/products**. It is best used as a **conversation starter** and **guidance**, not as a medical or definitive diagnosis.
- **Advanced analyses** that fit the current stack: **dark circles**, **face-only skin analysis**, **pigmentation/evenness**, **texture**, **more shapes**, **symmetry**, and **configurable, severity-aware recommendations**.
- **Maximum customer benefit** comes from: (1) more accurate skin analysis (face crop + optional trained model), (2) visible “extra” scores (dark circles, shapes, regions), and (3) recommendations that match each salon’s actual menu and customer preferences.

Implementing **face cropping for skin**, **dark circle score**, and **salon-configurable rules** first will deliver the largest gain for effort.
