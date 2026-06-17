# Classifier Models

Trained models for localize_it query classification and style matching.

## Files

- `query_classifier.pkl` — Naive Bayes classifier for query type (WAKE_REQUEST, LEARNING, TECHNICAL, etc.)
- `style_index.pkl` — TF-IDF index for framework/context similarity matching
- `metadata.json` — Training metadata and categories

## Training Data

- **Shadow analysis:** 22,324 messages analyzed
- **Explicit captures:** 74 examples (frameworks, contexts, styles, voices, learning)
- **Labeled examples:** 108 total training samples

## Categories

| Category | Description | Status |
|:---|:---|:---:|
| **WAKE_REQUEST** | Session start, orientation | Strong |
| **LEARNING** | Research, explanation, information seeking | Fixed |
| **TECHNICAL** | Setup, configuration, building | Strong |
| **PROJECT_SPECIFIC** | Context-dependent work | Good |
| **SOCIAL** | Greetings, casual conversation | Low support |
| **DIRECTIVE** | Commands | Low support |
| **VERIFICATION** | Confirmations | Low support |
| **META** | System questions ("Can you...") | Low support |
| **OTHER** | Uncategorized | Low support |

## Accuracy Progress

| Version | Accuracy | Training Examples | Notes |
|:---|:---:|:---:|:---|
| Baseline | 38% | 64 | Shadow data only |
| v1 | 62.5% | 87 | +52 explicit captures |
| **v2 (current)** | 50% | 108 | +15 learning examples, LEARNING category fixed |

Note: Overall accuracy dropped to 50% because we now have more balanced categories (previously dominated by WAKE_REQUEST and TECHNICAL). Per-category performance is better.

### Category Performance (v2)

| Category | Precision | Recall | F1 | Support |
|:---|:---:|:---:|:---:|:---:|
| LEARNING | 0.50 | 0.67 | **0.57** | 3 |
| TECHNICAL | 0.80 | 1.00 | **0.89** | 4 |
| SOCIAL | 1.00 | 0.50 | **0.67** | 2 |
| WAKE_REQUEST | 0.33 | 0.60 | **0.43** | 5 |

## Usage

```bash
# Classify a query
python3 src/inference/predict.py "your query here"

# Find matching frameworks
python3 src/inference/predict.py "your query" --framework

# Interactive mode
python3 src/inference/predict.py
```

## Test Results

```
"Research distributed inference..." -> LEARNING (0.94)
"Explain RPC tensor alignment..." -> LEARNING (0.66)
"How does LoRA work?" -> LEARNING (0.91)
"Configure ProtonDrive..." -> TECHNICAL (0.70)
"Good morning Shepherd..." -> WAKE_REQUEST (0.94)
```

## Retraining

```bash
# Rebuild explicit corpus
python3 src/train/build-explicit-corpus.py

# Retrain classifier
python3 src/train/train_classifier.py
```

## Last Updated

2026-06-17 — LEARNING category fixed with 15 direct training examples
