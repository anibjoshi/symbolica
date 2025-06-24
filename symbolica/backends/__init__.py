"""Backend implementations for different storage and processing strategies."""

from .memory_backend import MemoryBackend

try:
    from .graph_backend import GraphBackend
except ImportError:
    GraphBackend = None

__all__ = [
    "MemoryBackend",
    "GraphBackend",
] 