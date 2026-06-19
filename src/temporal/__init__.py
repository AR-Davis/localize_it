"""
TEMPORAL — Time-aware capture classification for localize_it

Auto-tags captures with temporal state (past/present/future) based on keyword detection.
Enables time-aware retrieval: "what am I building?" → prioritize 'present' captures.

Part of localize_it: Personal AI Sovereignty
"""

from .classifier import TemporalClassifier, classify_capture, query_by_temporal

__all__ = ['TemporalClassifier', 'classify_capture', 'query_by_temporal']
