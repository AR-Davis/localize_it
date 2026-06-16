#!/usr/bin/env python3
"""
PREDICT — Run inference with trained localize_it classifiers
Part of LOCALIZE_IT: Personal AI Sovereignty

Usage:
  predict.py "query text here"
  predict.py --framework "query text"  # Find matching framework
  predict.py --style "query text"        # Get style suggestions
"""

import json
import pickle
import argparse
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_DIR = Path.home() / "Projects" / "localize_it"
MODEL_DIR = PROJECT_DIR / "models"


def load_models():
    """Load trained classifiers."""
    with open(MODEL_DIR / "query_classifier.pkl", 'rb') as f:
        query_classifier = pickle.load(f)
    
    with open(MODEL_DIR / "style_index.pkl", 'rb') as f:
        style_index = pickle.load(f)
    
    with open(MODEL_DIR / "metadata.json") as f:
        metadata = json.load(f)
    
    return query_classifier, style_index, metadata


def classify_query(query: str, classifier) -> Dict:
    """Classify a query into category."""
    prediction = classifier.predict([query])[0]
    probabilities = classifier.predict_proba([query])[0]
    
    # Get top 3 categories
    top_indices = probabilities.argsort()[-3:][::-1]
    top_categories = [
        {
            'category': classifier.classes_[i],
            'confidence': float(probabilities[i])
        }
        for i in top_indices
    ]
    
    return {
        'primary': prediction,
        'top_3': top_categories,
        'confidence': float(probabilities[classifier.classes_.tolist().index(prediction)])
    }


def find_similar_frameworks(query: str, style_index, top_k: int = 3) -> List[Dict]:
    """Find most similar frameworks/contexts for a query."""
    from sklearn.metrics.pairwise import cosine_similarity
    
    # Transform query
    query_vec = style_index['vectorizer'].transform([query])
    
    # Calculate similarities
    similarities = cosine_similarity(query_vec, style_index['vectors'])[0]
    
    # Get top k
    top_indices = similarities.argsort()[-top_k:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1:  # Minimum threshold
            results.append({
                'text': style_index['entries'][idx][:100],
                'metadata': style_index['metadata'][idx],
                'similarity': float(similarities[idx])
            })
    
    return results


def suggest_style(query: str, classification: Dict) -> Dict:
    """Suggest style based on query classification."""
    suggestions = {
        'format': 'default',
        'guidelines': []
    }
    
    category = classification['primary']
    
    if category == 'WAKE_REQUEST':
        suggestions['format'] = 'structured_summary'
        suggestions['guidelines'] = [
            'Start with session status overview',
            'List active tasks/deadlines',
            'Use emoji headers for quick scanning'
        ]
    
    elif category == 'TECHNICAL':
        suggestions['format'] = 'technical_documentation'
        suggestions['guidelines'] = [
            'Include code blocks with syntax highlighting',
            'Provide step-by-step commands',
            'Add troubleshooting section'
        ]
    
    elif category == 'LEARNING':
        suggestions['format'] = 'structured_research'
        suggestions['guidelines'] = [
            'Lead with key findings',
            'Use tables for comparisons',
            'Cite sources where applicable'
        ]
    
    elif category == 'PROJECT_SPECIFIC':
        suggestions['format'] = 'project_context'
        suggestions['guidelines'] = [
            'Reference existing project conventions',
            'Link to related contexts/frameworks',
            'Show command examples from conventions'
        ]
    
    else:
        # Default to user's 89% structured preference
        suggestions['format'] = 'highly_structured'
        suggestions['guidelines'] = [
            'Lead with bullet points before narrative',
            'Use tables for comparisons',
            'Keep sections discrete with clear headers'
        ]
    
    return suggestions


def main():
    parser = argparse.ArgumentParser(description="Classify queries with localize_it models")
    parser.add_argument("query", nargs="?", help="Query text to classify")
    parser.add_argument("--framework", "-f", action="store_true",
                       help="Find matching frameworks")
    parser.add_argument("--style", "-s", action="store_true",
                       help="Get style suggestions")
    parser.add_argument("--top-k", "-k", type=int, default=3,
                       help="Number of results to return")
    
    args = parser.parse_args()
    
    if not args.query:
        # Interactive mode
        print("LOCALIZE_IT Query Classifier")
        print("Enter queries to classify (Ctrl+D to exit):")
        while True:
            try:
                query = input("\n> ").strip()
                if query:
                    args.query = query
                    process_query(args)
            except EOFError:
                break
            except KeyboardInterrupt:
                break
    else:
        process_query(args)


def process_query(args):
    """Process a single query."""
    # Load models
    query_classifier, style_index, metadata = load_models()
    
    # Classify
    classification = classify_query(args.query, query_classifier)
    
    # Output
    print(f"\nQuery: {args.query}")
    print(f"Category: {classification['primary']} ({classification['confidence']:.2f})")
    print("\nTop 3 categories:")
    for cat in classification['top_3']:
        print(f"  {cat['category']}: {cat['confidence']:.2f}")
    
    # Style suggestions
    style = suggest_style(args.query, classification)
    print(f"\nSuggested format: {style['format']}")
    print("Guidelines:")
    for g in style['guidelines']:
        print(f"  • {g}")
    
    # Framework matching
    if args.framework or classification['primary'] == 'PROJECT_SPECIFIC':
        similar = find_similar_frameworks(args.query, style_index, args.top_k)
        if similar:
            print(f"\nSimilar frameworks/contexts:")
            for i, match in enumerate(similar, 1):
                print(f"  {i}. {match['metadata']['name']} ({match['metadata']['type']}, {match['similarity']:.2f})")
                print(f"     {match['text'][:60]}...")


if __name__ == "__main__":
    main()
