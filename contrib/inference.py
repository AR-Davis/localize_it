#!/usr/bin/env python3
"""
Pupper Inference Router — Smart backend selection for Mycelium integration
Part of The Kennel: Personal AI Sovereignty

Automatically selects between Mycelium (distributed) and Ollama (local)
with graceful fallback and health checking.

Usage:
    from inference import SmartInferenceRouter
    
    router = SmartInferenceRouter()
    response = router.generate("What do you see ahead?")
"""

import requests
import json
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import subprocess

class BackendType(Enum):
    MYCELIUM = "mycelium"
    OLLAMA = "ollama"
    FALLBACK = "fallback"

@dataclass
class BackendHealth:
    type: BackendType
    available: bool
    latency_ms: Optional[int]
    nodes: Optional[List[str]]
    preferred_model: str
    details: Optional[Dict] = None

class InferenceBackend:
    """Abstract base for inference backends."""
    
    def generate(self, prompt: str, context: str = "", system: str = "") -> str:
        raise NotImplementedError
    
    def health(self) -> BackendHealth:
        raise NotImplementedError

class MyceliumBackend(InferenceBackend):
    """
    Distributed inference via The Mycelium.
    
    Routes through Three Ravens:
    - huginn: Fast, local (prefer for quick queries)
    - muninn: Deep, remote (prefer for complex reasoning)
    - skald: Precise, deterministic (prefer for verification)
    """
    
    DEFAULT_ENDPOINT = "http://localhost:11435"
    
    def __init__(self, endpoint: str = None, raven: str = "huginn"):
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.raven = raven  # huginn/muninn/skald
        
    def health(self) -> BackendHealth:
        """Check Mycelium health via /api/status"""
        try:
            response = requests.get(
                f"{self.endpoint}/api/status",
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                nodes = data.get("nodes", [])
                node_names = [n.get("name") for n in nodes if n.get("status") == "healthy"]
                
                # Calculate average latency from healthy nodes
                latencies = []
                for n in nodes:
                    lat = n.get("latency", "0s")
                    if lat.endswith("ms"):
                        latencies.append(int(lat[:-2]))
                    elif lat != "0s":
                        latencies.append(0)
                avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0
                
                return BackendHealth(
                    type=BackendType.MYCELIUM,
                    available=True,
                    latency_ms=avg_latency,
                    nodes=node_names,
                    preferred_model=f"mycelium/{self.raven}",
                    details=data
                )
            else:
                return BackendHealth(
                    type=BackendType.MYCELIUM,
                    available=False,
                    latency_ms=None,
                    nodes=None,
                    preferred_model="unavailable"
                )
        except Exception as e:
            return BackendHealth(
                type=BackendType.MYCELIUM,
                available=False,
                latency_ms=None,
                nodes=None,
                preferred_model="unavailable",
                details={"error": str(e)}
            )
    
    def generate(self, prompt: str, context: str = "", system: str = "") -> str:
        """Generate response via Mycelium with Three Ravens routing."""
        headers = {"X-Mycelium-Target": self.raven}
        
        # Build messages for chat endpoint
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if context:
            messages.append({"role": "user", "content": context})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "llama3.2:1b",  # Base model
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.endpoint}/api/chat",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except requests.exceptions.Timeout:
            raise RuntimeError("Mycelium timeout — consider fallback")
        except Exception as e:
            raise RuntimeError(f"Mycelium error: {e}")
    
    def set_raven(self, raven: str):
        """Change Three Ravens routing preference."""
        if raven in ["huginn", "muninn", "skald"]:
            self.raven = raven

class OllamaBackend(InferenceBackend):
    """Local Ollama inference — fallback when Mycelium unavailable."""
    
    DEFAULT_ENDPOINT = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2:1b"
    
    def __init__(self, endpoint: str = None, model: str = None):
        self.endpoint = endpoint or self.DEFAULT_ENDPOINT
        self.model = model or self.DEFAULT_MODEL
        
    def health(self) -> BackendHealth:
        """Check Ollama health via /api/tags"""
        try:
            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                return BackendHealth(
                    type=BackendType.OLLAMA,
                    available=True,
                    latency_ms=0,  # Local
                    nodes=["localhost"],
                    preferred_model=self.model,
                    details={"available_models": models}
                )
            else:
                return BackendHealth(
                    type=BackendType.OLLAMA,
                    available=False,
                    latency_ms=None,
                    nodes=None,
                    preferred_model="unavailable"
                )
        except Exception as e:
            return BackendHealth(
                type=BackendType.OLLAMA,
                available=False,
                latency_ms=None,
                nodes=None,
                preferred_model="unavailable",
                details={"error": str(e)}
            )
    
    def generate(self, prompt: str, context: str = "", system: str = "") -> str:
        """Generate response via local Ollama."""
        # Build full prompt with context and system
        full_prompt = ""
        if system:
            full_prompt += f"{system}\n\n"
        if context:
            full_prompt += f"Context: {context}\n\n"
        full_prompt += prompt
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.endpoint}/api/generate",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")

class SmartInferenceRouter:
    """
    Automatically selects best available inference backend.
    
    Usage:
        router = SmartInferenceRouter(prefer_mycelium=True)
        
        # Get status on wake
        print(router.status_report())
        
        # Generate with automatic backend selection
        response = router.generate("What do you see?")
        
        # Or specify raven for Mycelium
        router.set_raven("muninn")  # Deep thinking
        response = router.generate("Complex analysis...")
    """
    
    def __init__(self, prefer_mycelium: bool = True, raven: str = "huginn"):
        self.prefer_mycelium = prefer_mycelium
        self.raven = raven
        
        # Initialize backends
        self.mycelium = MyceliumBackend(raven=raven)
        self.ollama = OllamaBackend()
        
        self.current_backend: Optional[InferenceBackend] = None
        self.last_error: Optional[str] = None
        
        # Health check on init
        self._refresh_backends()
    
    def _refresh_backends(self):
        """Refresh backend health status."""
        self.mycelium_health = self.mycelium.health()
        self.ollama_health = self.ollama.health()
    
    def select_backend(self, force_refresh: bool = False) -> InferenceBackend:
        """
        Select best available backend.
        
        Priority:
        1. Mycelium (if prefer_mycelium and healthy)
        2. Ollama (local fallback)
        3. Raise error (no backend available)
        """
        if force_refresh:
            self._refresh_backends()
        
        # Try Mycelium first if preferred
        if self.prefer_mycelium and self.mycelium_health.available:
            self.current_backend = self.mycelium
            return self.mycelium
        
        # Fall back to Ollama
        if self.ollama_health.available:
            self.current_backend = self.ollama
            return self.ollama
        
        # Neither available
        raise RuntimeError(
            "No inference backend available. "
            "Mycelium: {} | Ollama: {}".format(
                "unhealthy" if self.prefer_mycelium else "skipped",
                "unhealthy" if not self.ollama_health.available else "unknown"
            )
        )
    
    def generate(self, prompt: str, context: str = "", system: str = "") -> str:
        """
        Generate response using best available backend.
        
        Handles mid-session failover if backend becomes unavailable.
        """
        try:
            backend = self.select_backend()
            return backend.generate(prompt, context, system)
            
        except RuntimeError as e:
            # Backend failed — try failover
            self.last_error = str(e)
            
            if self.current_backend == self.mycelium:
                # Try Ollama fallback
                if self.ollama_health.available:
                    self.current_backend = self.ollama
                    return self.ollama.generate(prompt, context, system)
            
            # No fallback available
            raise
    
    def set_raven(self, raven: str):
        """Change Three Ravens routing preference."""
        self.raven = raven
        self.mycelium.set_raven(raven)
    
    def status_report(self) -> str:
        """Generate status report for user (Pupper wake message)."""
        self._refresh_backends()
        
        lines = ["*woof* I'm here! Checking Mycelium..."]
        
        # Mycelium status
        if self.mycelium_health.available:
            lines.append(f"  ✓ Connected ({self.mycelium_health.latency_ms}ms)")
            if self.mycelium_health.nodes:
                lines.append(f"  Nodes: {', '.join(self.mycelium_health.nodes)}")
            lines.append(f"  Raven: {self.raven} (huginn=fast, muninn=deep, skald=precise)")
            lines.append("  Using distributed inference.")
        else:
            lines.append("  ✗ Mycelium unavailable")
        
        # Ollama status
        if self.ollama_health.available:
            if not self.mycelium_health.available:
                lines.append(f"  Falling back to local Ollama ({self.ollama_health.preferred_model})")
            else:
                lines.append(f"  Local Ollama ready (fallback)")
        else:
            lines.append("  ✗ Ollama unavailable — limited capabilities")
        
        return "\n".join(lines)
    
    def get_health(self) -> Dict:
        """Get detailed health status for all backends."""
        self._refresh_backends()
        return {
            "mycelium": {
                "available": self.mycelium_health.available,
                "latency_ms": self.mycelium_health.latency_ms,
                "nodes": self.mycelium_health.nodes,
                "raven": self.raven
            },
            "ollama": {
                "available": self.ollama_health.available,
                "model": self.ollama_health.preferred_model
            },
            "current_backend": self.current_backend.__class__.__name__ if self.current_backend else None
        }


# Convenience function for direct use
def generate_with_fallback(prompt: str, prefer_mycelium: bool = True) -> str:
    """One-shot generation with automatic backend selection."""
    router = SmartInferenceRouter(prefer_mycelium=prefer_mycelium)
    return router.generate(prompt)


if __name__ == "__main__":
    # Test the router
    print("Testing SmartInferenceRouter...")
    print("=" * 60)
    
    router = SmartInferenceRouter()
    
    # Status report
    print("\n" + router.status_report())
    
    # Health details
    print("\nDetailed health:")
    print(json.dumps(router.get_health(), indent=2))
