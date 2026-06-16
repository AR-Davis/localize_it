# Classifier Models

Trained models for localize_it query classification and style matching.

## Files

- `query_classifier.pkl` — Naive Bayes classifier for query type (WAKE_REQUEST, LEARNING, TECHNICAL, etc.)
- `style_index.pkl` — TF-IDF index for framework/context similarity matching
- `metadata.json` — Training metadata and categories

## Training Data

- 64 labeled examples from shadow analysis
- 4 explicit captures (frameworks/contexts)
- Source: 22,324 messages analyzed

## Categories

- WAKE_REQUEST — Session start, orientation
- LEARNING — Research, information seeking
- TECHNICAL — Setup, configuration, building
- PROJECT_SPECIFIC — Context-dependent work
- SOCIAL — Greetings, casual conversation
- META — System questions ("Can you...")
- DIRECTIVE — Commands
- VERIFICATION — Confirmations
- OTHER — Uncategorized

## Usage

```bash
# Classify a query
python3 src/inference/predict.py "your query here"

# Find matching frameworks
python3 src/inference/predict.py "your query" --framework

# Interactive mode
python3 src/inference/predict.py
```

## Accuracy

Current accuracy: ~38% with limited training data. 
Will improve as more explicit captures are added.

## Retraining

```bash
python3 src/train/train_classifier.py
```
