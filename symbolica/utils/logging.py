"""Logging utilities for Symbolica."""

import logging
import sys
from typing import Optional, Dict, Any
from datetime import datetime

from ..core.types import LogLevel


def setup_logger(
    name: str = "symbolica",
    level: LogLevel = LogLevel.INFO,
    format_string: Optional[str] = None,
    include_timestamp: bool = True,
    include_level: bool = True,
    include_name: bool = True
) -> logging.Logger:
    """Set up a logger for Symbolica components.
    
    Args:
        name: Logger name
        level: Logging level
        format_string: Custom format string
        include_timestamp: Include timestamp in logs
        include_level: Include log level in logs
        include_name: Include logger name in logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.value))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.value))
    
    # Create formatter
    if format_string is None:
        format_parts = []
        
        if include_timestamp:
            format_parts.append("%(asctime)s")
        
        if include_level:
            format_parts.append("%(levelname)s")
        
        if include_name:
            format_parts.append("%(name)s")
        
        format_parts.append("%(message)s")
        format_string = " - ".join(format_parts)
    
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger


def get_logger(name: str = "symbolica") -> logging.Logger:
    """Get an existing logger or create a default one.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set it up with defaults
    if not logger.handlers:
        setup_logger(name)
    
    return logger


class SymbolicaLogger:
    """Enhanced logger with Symbolica-specific functionality."""
    
    def __init__(self, name: str = "symbolica", level: LogLevel = LogLevel.INFO):
        """Initialize the Symbolica logger.
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = setup_logger(name, level)
        self.name = name
        self.level = level
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs) -> None:
        """Set context information to include in logs.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear all context information."""
        self._context.clear()
    
    def _format_message(self, message: str) -> str:
        """Format message with context information."""
        if not self._context:
            return message
        
        context_str = ", ".join(f"{k}={v}" for k, v in self._context.items())
        return f"{message} [{context_str}]"
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        if kwargs:
            self.set_context(**kwargs)
        self.logger.debug(self._format_message(message))
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        if kwargs:
            self.set_context(**kwargs)
        self.logger.info(self._format_message(message))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        if kwargs:
            self.set_context(**kwargs)
        self.logger.warning(self._format_message(message))
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        if kwargs:
            self.set_context(**kwargs)
        self.logger.error(self._format_message(message))
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        if kwargs:
            self.set_context(**kwargs)
        self.logger.critical(self._format_message(message))
    
    def log_inference_start(self, facts_count: int, rules_count: int) -> None:
        """Log the start of inference."""
        self.info(
            "Starting inference",
            facts_count=facts_count,
            rules_count=rules_count,
            timestamp=datetime.now().isoformat()
        )
    
    def log_inference_end(self, conclusions_count: int, execution_time_ms: float) -> None:
        """Log the end of inference."""
        self.info(
            "Inference completed",
            conclusions_count=conclusions_count,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now().isoformat()
        )
    
    def log_rule_fired(self, rule_id: str, facts_matched: int, conclusions_drawn: int) -> None:
        """Log when a rule fires."""
        self.debug(
            f"Rule fired: {rule_id}",
            rule_id=rule_id,
            facts_matched=facts_matched,
            conclusions_drawn=conclusions_drawn
        )
    
    def log_fact_added(self, key: str, value: Any) -> None:
        """Log when a fact is added."""
        self.debug(
            f"Fact added: {key} = {value}",
            fact_key=key,
            fact_value=str(value)
        )
    
    def log_validation_error(self, error_type: str, message: str, **details) -> None:
        """Log validation errors."""
        self.warning(
            f"Validation error: {message}",
            error_type=error_type,
            **details
        )
    
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        self.info("Performance metrics", **metrics)
    
    def set_level(self, level: LogLevel) -> None:
        """Change the logging level.
        
        Args:
            level: New logging level
        """
        self.level = level
        self.logger.setLevel(getattr(logging, level.value))
        for handler in self.logger.handlers:
            handler.setLevel(getattr(logging, level.value))
    
    def __repr__(self) -> str:
        """String representation."""
        return f"SymbolicaLogger(name={self.name}, level={self.level.value})"


# Global logger instance
_global_logger: Optional[SymbolicaLogger] = None


def get_global_logger() -> SymbolicaLogger:
    """Get the global Symbolica logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = SymbolicaLogger()
    return _global_logger


def set_global_log_level(level: LogLevel) -> None:
    """Set the global logging level."""
    logger = get_global_logger()
    logger.set_level(level) 