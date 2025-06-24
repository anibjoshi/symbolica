"""Validation and configuration types for symbolic reasoning."""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Error found during rule or fact validation.
    
    Represents issues discovered when validating rules,
    facts, or other symbolic reasoning components.
    """
    rule_id: str
    error_type: str
    message: str
    field: Optional[str] = None
    severity: str = "error"  # error, warning, info
    
    def __str__(self) -> str:
        """Get string representation of the validation error."""
        if self.field:
            return f"Rule {self.rule_id}, field {self.field}: {self.message}"
        return f"Rule {self.rule_id}: {self.message}"
    
    def __repr__(self) -> str:
        """Get detailed representation of the validation error."""
        return (f"ValidationError(rule_id='{self.rule_id}', "
                f"error_type='{self.error_type}', "
                f"message='{self.message}', "
                f"field={self.field}, "
                f"severity='{self.severity}')")
    
    @property
    def is_error(self) -> bool:
        """Check if this is an error-level validation issue."""
        return self.severity == "error"
    
    @property
    def is_warning(self) -> bool:
        """Check if this is a warning-level validation issue."""
        return self.severity == "warning"
    
    @property
    def is_info(self) -> bool:
        """Check if this is an info-level validation issue."""
        return self.severity == "info"


class BackendType(str, Enum):
    """Supported backend types for rule engines.
    
    Defines the different storage and execution backends
    that can be used for rule engine implementations.
    """
    MEMORY = "memory"
    GRAPH = "graph"
    DISTRIBUTED = "distributed"
    DATABASE = "database"
    REDIS = "redis"
    
    @property
    def is_local(self) -> bool:
        """Check if this backend runs locally."""
        return self in {BackendType.MEMORY, BackendType.GRAPH}
    
    @property
    def is_distributed(self) -> bool:
        """Check if this backend supports distribution."""
        return self in {BackendType.DISTRIBUTED, BackendType.DATABASE, BackendType.REDIS}
    
    @property
    def supports_persistence(self) -> bool:
        """Check if this backend supports persistent storage."""
        return self in {BackendType.DATABASE, BackendType.REDIS}


class LogLevel(str, Enum):
    """Logging levels for symbolic reasoning operations.
    
    Standard logging levels for controlling verbosity
    of rule engine and inference operations.
    """
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    
    @property
    def numeric_level(self) -> int:
        """Get numeric representation of log level."""
        levels = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50
        }
        return levels[self]
    
    def __lt__(self, other) -> bool:
        """Compare log levels by severity."""
        if not isinstance(other, LogLevel):
            return NotImplemented
        return self.numeric_level < other.numeric_level


class OptimizationLevel(str, Enum):
    """Optimization levels for rule engine performance.
    
    Different levels of optimization that can be applied
    to rule engines for various performance/accuracy tradeoffs.
    """
    NONE = "none"
    BASIC = "basic"
    INDEXED = "indexed"
    CACHED = "cached"
    FULL = "full"
    AUTO = "auto"
    
    @property
    def includes_indexing(self) -> bool:
        """Check if this level includes rule indexing."""
        return self in {
            OptimizationLevel.INDEXED,
            OptimizationLevel.CACHED,
            OptimizationLevel.FULL
        }
    
    @property
    def includes_caching(self) -> bool:
        """Check if this level includes condition caching."""
        return self in {
            OptimizationLevel.CACHED,
            OptimizationLevel.FULL
        }
    
    @property
    def includes_short_circuit(self) -> bool:
        """Check if this level includes short-circuit evaluation."""
        return self in {
            OptimizationLevel.BASIC,
            OptimizationLevel.INDEXED,
            OptimizationLevel.CACHED,
            OptimizationLevel.FULL
        }


class ConflictResolution(str, Enum):
    """Strategies for resolving conflicts between rules.
    
    Different approaches to handle situations where
    multiple rules might produce conflicting conclusions.
    """
    PRIORITY = "priority"  # Higher priority rules win
    FIRST_MATCH = "first_match"  # First matching rule wins
    CONFIDENCE = "confidence"  # Higher confidence wins
    DISABLE_CONFLICTS = "disable_conflicts"  # Disable conflicting rules
    MERGE_CONCLUSIONS = "merge_conclusions"  # Attempt to merge conclusions
    RAISE_ERROR = "raise_error"  # Raise error on conflicts 