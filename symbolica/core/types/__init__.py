"""Modular types for symbolic reasoning.

This module provides all the core data types used throughout
the Symbolica symbolic reasoning system, organized into
focused sub-modules for better maintainability.
"""

# Import base types
from .base_types import (
    Fact,
    Condition,
    Rule,
    Conclusion
)

# Import operator types  
from .operator_types import (
    OperatorType,
    apply_operator,
    validate_operator_compatibility
)

# Import inference types
from .inference_types import (
    InferenceStep,
    ReasoningTrace,
    InferenceResult
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
    "Condition", 
    "Rule",
    "Conclusion",
    
    # Operator types
    "OperatorType",
    "apply_operator",
    "validate_operator_compatibility",
    
    # Inference types
    "InferenceStep",
    "ReasoningTrace", 
    "InferenceResult",
    
    # Validation types
    "ValidationError",
    "BackendType",
    "LogLevel",
    "OptimizationLevel",
    "ConflictResolution"
] 