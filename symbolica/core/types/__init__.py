"""Core types for Symbolica symbolic reasoning engine."""

# Import base types
from .base_types import (
    Fact,
    Rule,
    Condition,
    Conclusion,
    OperatorType
)

# Import inference types
from .inference_types import (
    InferenceStep,
    ReasoningTrace,
    InferenceResult,
    ConditionEvaluation
)

# Import validation types
from .validation_types import (
    ValidationError,
    BackendType,
    LogLevel,
    OptimizationLevel,
    ConflictResolution
)

# Define what gets exported when someone does "from symbolica.core.types import *"
__all__ = [
    # Base types
    "Fact",
    "Rule",
    "Condition", 
    "Conclusion",
    "OperatorType",
    
    # Inference types
    "InferenceStep",
    "ReasoningTrace", 
    "InferenceResult",
    "ConditionEvaluation",
    
    # Validation types
    "ValidationError",
    "BackendType",
    "LogLevel",
    "OptimizationLevel",
    "ConflictResolution"
] 