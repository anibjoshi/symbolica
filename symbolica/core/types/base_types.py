"""Core base types for symbolic reasoning."""

from datetime import datetime
from typing import Any, Dict, List
from dataclasses import dataclass, field

from .operator_types import OperatorType, apply_operator


@dataclass
class Fact:
    """A symbolic fact with metadata and temporal information.
    
    Represents a piece of knowledge with an associated confidence level
    and metadata for context and provenance tracking.
    """
    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    
    def __post_init__(self):
        """Validate confidence is between 0 and 1."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
    
    def __hash__(self):
        """Make facts hashable for use in sets."""
        return hash((self.key, str(self.value), self.timestamp))


@dataclass
class Condition:
    """A condition that can be evaluated against facts.
    
    Represents a logical condition that tests whether a fact
    meets certain criteria using comparison operators.
    """
    field: str
    operator: OperatorType
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def evaluate(self, fact: Fact) -> bool:
        """Evaluate this condition against a fact.
        
        Args:
            fact: The fact to evaluate against
            
        Returns:
            True if the condition is satisfied by the fact
        """
        fact_value = self._extract_fact_value(fact)
        if fact_value is None:
            return False
        
        return apply_operator(fact_value, self.operator, self.value)
    
    def _extract_fact_value(self, fact: Fact) -> Any:
        """Extract the relevant value from a fact for evaluation.
        
        Args:
            fact: The fact to extract value from
            
        Returns:
            The value to use for comparison, or None if not found
        """
        # Direct field match
        if self.field == fact.key:
            return fact.value
        
        # Special meta-fields
        if self.field == "key":
            return fact.key
        elif self.field == "value":
            return fact.value
        elif self.field == "timestamp":
            return fact.timestamp
        elif self.field == "confidence":
            return fact.confidence
        
        # Try to get from fact attributes
        fact_value = getattr(fact, self.field, None)
        if fact_value is not None:
            return fact_value
        
        # Try to get from fact.value if it's a dict
        if isinstance(fact.value, dict):
            return fact.value.get(self.field)
        
        # Try to get from metadata
        if self.field in fact.metadata:
            return fact.metadata[self.field]
        
        return None


@dataclass
class Conclusion:
    """A conclusion drawn from rule evaluation.
    
    Represents a new fact that was inferred by applying a rule,
    along with its confidence and supporting evidence.
    """
    fact: Fact
    confidence: float
    rule_id: str
    supporting_facts: List[Fact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate confidence is between 0 and 1."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass
class Rule:
    """A symbolic rule with conditions and conclusions.
    
    Represents a logical rule that can be applied to facts
    to derive new conclusions when conditions are met.
    """
    id: str
    conditions: List[Condition]
    conclusions: List[Conclusion]
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def can_fire(self, facts: List[Fact]) -> bool:
        """Check if this rule can fire given the facts.
        
        Args:
            facts: List of available facts
            
        Returns:
            True if all conditions can be satisfied by the facts
        """
        if not self.enabled:
            return False
        
        # Group conditions by logic type
        all_conditions = []
        any_conditions = []
        
        for condition in self.conditions:
            logic_type = condition.metadata.get("logic_type", "all")
            if logic_type == "all":
                all_conditions.append(condition)
            elif logic_type == "any":
                any_conditions.append(condition)
            else:
                # Default to 'all' for backward compatibility
                all_conditions.append(condition)
        
        # All conditions must be satisfied
        if all_conditions:
            for condition in all_conditions:
                if not any(condition.evaluate(fact) for fact in facts):
                    return False
        
        # At least one of any conditions must be satisfied
        if any_conditions:
            any_satisfied = False
            for condition in any_conditions:
                if any(condition.evaluate(fact) for fact in facts):
                    any_satisfied = True
                    break
            if not any_satisfied:
                return False
        
        return True
    
    def get_matching_facts(self, facts: List[Fact]) -> List[List[Fact]]:
        """Get facts that match each condition.
        
        Args:
            facts: List of available facts
            
        Returns:
            List of fact lists, one for each condition
        """
        matches = []
        for condition in self.conditions:
            condition_matches = [fact for fact in facts if condition.evaluate(fact)]
            matches.append(condition_matches)
        return matches
    
    def get_dependent_fields(self) -> set[str]:
        """Get all field names this rule depends on.
        
        Returns:
            Set of field names referenced in conditions
        """
        return {condition.field for condition in self.conditions} 