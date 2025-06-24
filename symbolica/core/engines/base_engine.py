"""Abstract base class for rule engines."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from ..types import Rule, Conclusion, ValidationError
from ..fact_store import FactStore


class BaseRuleEngine(ABC):
    """Abstract base class for all rule engines.
    
    Defines the common interface that all rule engines must implement,
    ensuring consistency across different engine implementations.
    """
    
    @abstractmethod
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine.
        
        Args:
            rule: The rule to add
            
        Raises:
            ValidationError: If the rule is invalid
        """
        pass
    
    @abstractmethod
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        pass
    
    @abstractmethod
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID.
        
        Args:
            rule_id: ID of the rule to retrieve
            
        Returns:
            The rule if found, None otherwise
        """
        pass
    
    @abstractmethod
    def list_rules(self, enabled_only: bool = True) -> List[Rule]:
        """List all rules in the engine.
        
        Args:
            enabled_only: If True, only return enabled rules
            
        Returns:
            List of rules
        """
        pass
    
    @abstractmethod
    def evaluate(self, facts: FactStore) -> List[Conclusion]:
        """Evaluate rules against facts to draw conclusions.
        
        Args:
            facts: The fact store to evaluate against
            
        Returns:
            List of conclusions drawn from rule evaluation
        """
        pass
    
    @abstractmethod
    def validate_rules(self) -> List[ValidationError]:
        """Validate all rules in the engine.
        
        Returns:
            List of validation errors found
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics and performance metrics.
        
        Returns:
            Dictionary containing engine statistics
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all rules from the engine."""
        pass
    
    # Optional methods with default implementations
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule.
        
        Args:
            rule_id: ID of the rule to enable
            
        Returns:
            True if rule was enabled, False if not found
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule.
        
        Args:
            rule_id: ID of the rule to disable
            
        Returns:
            True if rule was disabled, False if not found
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False
    
    def get_enabled_rules(self) -> List[Rule]:
        """Get all enabled rules.
        
        Returns:
            List of enabled rules
        """
        return [rule for rule in self.list_rules(enabled_only=False) if rule.enabled]
    
    def get_disabled_rules(self) -> List[Rule]:
        """Get all disabled rules.
        
        Returns:
            List of disabled rules
        """
        return [rule for rule in self.list_rules(enabled_only=False) if not rule.enabled]
    
    def count_rules(self, enabled_only: bool = True) -> int:
        """Count rules in the engine.
        
        Args:
            enabled_only: If True, only count enabled rules
            
        Returns:
            Number of rules
        """
        return len(self.list_rules(enabled_only=enabled_only))
    
    def has_rule(self, rule_id: str) -> bool:
        """Check if a rule exists in the engine.
        
        Args:
            rule_id: ID of the rule to check
            
        Returns:
            True if rule exists
        """
        return self.get_rule(rule_id) is not None 