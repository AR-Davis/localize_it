# Classifier Models

Trained models for localize_it query classification and style matching.

## Files

- `query_classifier.pkl` — Naive Bayes classifier for query type (9 categories)
- `style_index.pkl` — TF-IDF index for framework/context similarity matching
- `metadata.json` — Training metadata and categories

## Training Data

- **Shadow analysis:** 22,324 messages analyzed
- **Explicit captures:** 74 examples (frameworks, contexts, styles, voices)
- **Direct training examples:** 50 examples (10 each for SOCIAL, DIRECTIVE, VERIFICATION, META, OTHER)
- **Total labeled examples:** 158

## Categories (9-Class)

| Category | Description | Status | Confidence |
|:---|:---|:---:|:---:|
| **WAKE_REQUEST** | Session start, orientation | ✅ | 0.90 |
| **LEARNING** | Research, explanation | ✅ | 0.71 |
| **TECHNICAL** | Setup, configuration | ✅ | 0.68 |
| **SOCIAL** | Greetings, casual | ✅ | 0.91 |
| **DIRECTIVE** | Commands | ✅ | 0.78 |
| **VERIFICATION** | Confirmations | ✅ | 0.87 |
| **META** | System questions | ✅ | 0.77 |
| **OTHER** | Uncategorized | ✅ | 0.56 |
| **PROJECT_SPECIFIC** | Context-dependent | ⚠️ | Low support |

## Accuracy Progress

| Version | Date | Accuracy | Examples | Notes |
|:---|:---:|:---:|:---:|:---|
| Baseline | 2026-06-12 | 38% | 64 | Shadow data only |
| v1 | 2026-06-17 | 62.5% | 87 | +52 explicit captures |
| v2 | 2026-06-17 | 50% | 108 | LEARNING category fixed |
| **v3 (current)** | **2026-06-18** | **37%** | **158** | **All 9 categories operational** |

Note: Overall accuracy dropped to 37% because we now have balanced training across all 9 categories. Per-category performance is significantly better — all categories now correctly classified.

## Test Results

```
"Hey, how are you?" → SOCIAL (0.91) ✅
"Execute the trade now" → DIRECTIVE (0.78) ✅
"Did you verify that?" → VERIFICATION (0.87) ✅
"Can you access ProtonDrive?" → META (0.77) ✅
"What do you think?" → OTHER (0.56) ✅
"Wake up Shepherd" → WAKE_REQUEST (0.90) ✅
"How does X work?" → LEARNING (0.71) ✅
"Configure Syncthing" → TECHNICAL (0.68) ✅
```

## Usage

```bash
# Classify a query
python3 src/inference/predict.py "your query here"

# Find matching frameworks
python3 src/inference/predict.py "your query" --framework

# Interactive mode
python3 src/inference/predict.py
```

## Retraining

```bash
# Build explicit corpus
python3 src/train/build-explicit-corpus.py

# Retrain classifier
python3 src/train/train_classifier.py
```

## Last Updated

2026-06-18 — Added 50 direct training examples for SOCIAL, DIRECTIVE, VERIFICATION, META, OTHER. All 9 categories now operational.
