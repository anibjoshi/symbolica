"""Modular rule engine architecture for symbolic reasoning.

This module provides a clean, extensible engine architecture with
clear separation of concerns and strategy patterns for evaluation.
"""

# Import engine components
from .base_engine import BaseRuleEngine
from .rule_manager import RuleManager

# This will be populated as we create more engine modules
__all__ = [
    "BaseRuleEngine",
    "RuleManager",
] 