"""Bridge components for integrating with LLM frameworks."""

from .llm_bridge import LLMBridge

try:
    from .langraph_hooks import SymbolicaNode
except ImportError:
    SymbolicaNode = None

try:
    from .semantic_kernel_hooks import SymbolicaPlugin
except ImportError:
    SymbolicaPlugin = None

__all__ = [
    "LLMBridge",
    "SymbolicaNode",
    "SymbolicaPlugin",
] 