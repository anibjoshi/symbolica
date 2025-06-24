"""
Symbolica: Symbolic reasoning engine for LLM agents.

Symbolica provides a powerful symbolic reasoning framework that enables LLM agents
to perform structured logical inference with natural language explanations.
"""

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

from .core.fact_store import FactStore
from .core.rule_engine import RuleEngine
from .core.inference import Inference
from .core.types import (
    Fact,
    Rule,
    Condition,
    Conclusion,
    InferenceResult,
    ReasoningTrace,
    InferenceStep,
    ValidationError,
)
from .bridges.llm_bridge import LLMBridge

__all__ = [
    "__version__",
    "FactStore",
    "RuleEngine", 
    "Inference",
    "LLMBridge",
    "Fact",
    "Rule",
    "Condition",
    "Conclusion",
    "InferenceResult",
    "ReasoningTrace",
    "InferenceStep",
    "ValidationError",
] 