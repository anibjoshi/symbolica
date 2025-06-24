"""Operator types and evaluation logic for symbolic reasoning."""

from enum import Enum
from typing import Any
import re


class OperatorType(str, Enum):
    """Supported comparison operators for condition evaluation."""
    EQ = "=="
    NE = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    IN = "in"
    CONTAINS = "contains"
    REGEX = "regex"
    EXISTS = "exists"


def apply_operator(fact_value: Any, operator: OperatorType, condition_value: Any) -> bool:
    """Apply the operator to compare values.
    
    Args:
        fact_value: The value from the fact
        operator: The comparison operator to apply
        condition_value: The value from the condition
        
    Returns:
        Boolean result of the comparison
        
    Raises:
        TypeError: If values are incompatible for comparison
    """
    try:
        if operator == OperatorType.EQ:
            return fact_value == condition_value
        elif operator == OperatorType.NE:
            return fact_value != condition_value
        elif operator == OperatorType.GT:
            return fact_value > condition_value
        elif operator == OperatorType.LT:
            return fact_value < condition_value
        elif operator == OperatorType.GTE:
            return fact_value >= condition_value
        elif operator == OperatorType.LTE:
            return fact_value <= condition_value
        elif operator == OperatorType.IN:
            return fact_value in condition_value
        elif operator == OperatorType.CONTAINS:
            return condition_value in fact_value
        elif operator == OperatorType.EXISTS:
            return fact_value is not None
        elif operator == OperatorType.REGEX:
            return bool(re.search(str(condition_value), str(fact_value)))
        else:
            return False
    except (TypeError, AttributeError):
        return False


def validate_operator_compatibility(fact_value: Any, operator: OperatorType, condition_value: Any) -> bool:
    """Check if values are compatible with the operator.
    
    Args:
        fact_value: The value from the fact
        operator: The comparison operator
        condition_value: The value from the condition
        
    Returns:
        True if values are compatible with the operator
    """
    try:
        # Numeric operators require numeric values
        if operator in {OperatorType.GT, OperatorType.LT, OperatorType.GTE, OperatorType.LTE}:
            float(fact_value)
            float(condition_value)
            return True
        
        # IN operator requires condition_value to be iterable
        if operator == OperatorType.IN:
            iter(condition_value)
            return True
        
        # CONTAINS operator requires fact_value to be iterable
        if operator == OperatorType.CONTAINS:
            iter(fact_value)
            return True
        
        # EXISTS only needs to check fact_value
        if operator == OperatorType.EXISTS:
            return True
        
        # REGEX requires string-like values
        if operator == OperatorType.REGEX:
            str(fact_value)
            str(condition_value)
            return True
        
        # EQ and NE work with any values
        if operator in {OperatorType.EQ, OperatorType.NE}:
            return True
        
        return False
        
    except (TypeError, ValueError):
        return False 