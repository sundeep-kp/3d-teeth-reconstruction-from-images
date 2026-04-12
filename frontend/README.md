# Frontend

Styled command-runner frontend for the TeethDreamer + NeUS pipeline.

## Quick Start

1. From repository root, activate your Python environment.
2. Install Node dependencies once:

```bash
npm install
```

3. Start backend and frontend together:

```bash
npm run dev
```

4. Open either page:

- Landing page: `http://127.0.0.1:3000/frontend/index.html`
- Runner page: `http://127.0.0.1:3000/frontend/runner.html`

The runner backend listens on `http://127.0.0.1:8787/run`.

## What This Frontend Includes

- New visual style and assets (layout, typography, gradients, cards, gallery)
- Separate pages:
  - `index.html`: informational landing page
  - `runner.html`: dedicated command-runner UI
- Landing page disease predictor:
  - Symptom checkbox form
  - Top disease and confidence score
  - Other probable diseases with lower confidences
  - Weighted danger rank (severity weighted higher than confidence)
- Runner features:
  - Runner setup fields
  - Command builder for Generate / Upper / Lower
  - Copy and Run buttons
  - Sequential `Run All`
  - Terminal-style execution log

## File Structure

- `index.html`: Landing page
- `runner.html`: Dedicated command runner page
- `static/styles.css`: Shared styling for both pages
- `static/app.js`: Shared script (tabs on landing, runner logic on runner page)

## Disease Predictor Usage

### How It Works

1. **Select Symptoms**: On the landing page, check the symptoms you observe. You can select any combination of the 26 available dental symptoms.

2. **Choose Model**: Select one of three trained models:
   - **Decision Tree (DT)**: Fastest, good for basic classification
   - **Naive Bayes (NB)**: Most accurate overall (93.2% test accuracy)
   - **K-Nearest Neighbors (KNN)**: Good balance of speed and accuracy (91.8% test accuracy)

3. **Get Prediction**: Click "Predict Disease" to submit symptoms to the backend.

4. **Review Results**:
   - **Top Disease**: The most likely dental condition with confidence score (0–1.0)
   - **Alternatives**: Other possible diseases ranked by probability
   - **Danger Rank**: A severity assessment based on the disease type and prediction confidence

### Understanding Danger Ranking

The danger score combines two factors:
- **Disease Severity** (70% weight): Inherent severity of the predicted condition
  - Critical: Diseases like Abscess, Impacted Tooth, Oral Cancer (5/5)
  - High: Dry Socket, Enamel Erosion, Periodontitis (3–4/5)
  - Moderate: Tartar, Bruxism, Caries (2/5)
  - Low: Halitosis, Dryness, Plaque (1/5)
- **Prediction Confidence** (30% weight): How confident the model is in its prediction

**Danger Labels**:
- 🟢 **Low** (0–2): Monitor; no urgent action needed
- 🟡 **Moderate** (2–4): Schedule appointment; common condition
- 🟠 **High** (4–5): Seek dental care soon; more serious condition
- 🔴 **Critical** (5+): Seek immediate professional help

### Example

**Symptoms selected:** tooth_pain, black_spots, bleeding_gums
**Model:** Naive Bayes
**Result:**
- Top disease: Gingivitis (confidence: 0.998)
- Danger rank: High (underlying inflammation warrants prompt dental visit)
- Alternatives: Dental Caries (0.002), Abscess (0.0001), ...

### API Details

**Endpoint:** `POST http://127.0.0.1:8787/predict-disease`

**Request:**
```json
{
  "symptoms": ["tooth_pain", "bleeding_gums"],
  "model": "nb"
}
```

**Response:**
```json
{
  "model": "nb",
  "selected_symptoms": ["bleeding_gums", "tooth_pain"],
  "top_disease": "Gingivitis",
  "confidence": 0.998,
  "danger": {
    "label": "High",
    "score": 4.2,
    "severity": 3,
    "confidence_component": 5.0
  },
  "alternatives": [
    {"disease": "Dental Caries", "confidence": 0.002, "severity": 2},
    {"disease": "Abscess", "confidence": 0.0001, "severity": 5}
  ],
  "all_symptoms": [...]
}
```

## Notes

- The command runner requires `runner.py` and does not depend on `/api/reconstruct` or `/api/detect-malfunction`.
- The disease predictor calls `POST /predict-disease` on `runner.py`.
- Trained models are exported to `dental-disease-aiml/models/` during dataset training.
- Keep default directories aligned with repository structure unless your data layout differs.

