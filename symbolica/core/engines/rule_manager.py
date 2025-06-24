"""Rule management component for handling rule CRUD operations."""

from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict

from ..types import Rule, Condition, Conclusion, ValidationError, ConflictResolution


class RuleManager:
    """Manages rule storage, validation, and conflict resolution.
    
    Provides centralized management of rules with validation,
    conflict detection, and dependency tracking.
    """
    
    def __init__(self, rules: Optional[List[Rule]] = None, 
                 conflict_resolution: ConflictResolution = ConflictResolution.PRIORITY):
        """Initialize the rule manager.
        
        Args:
            rules: Initial rules to add
            conflict_resolution: Strategy for resolving rule conflicts
        """
        self._rules: Dict[str, Rule] = {}
        self._conflict_resolution = conflict_resolution
        self._field_dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        if rules:
            for rule in rules:
                self.add_rule(rule)
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the manager.
        
        Args:
            rule: The rule to add
            
        Raises:
            ValueError: If rule validation fails
        """
        # Validate the rule first
        errors = self._validate_rule(rule)
        if any(error.is_error for error in errors):
            error_messages = [str(error) for error in errors if error.is_error]
            raise ValueError(f"Rule validation failed: {'; '.join(error_messages)}")
        
        # Check for conflicts
        conflicts = self._check_conflicts(rule)
        if conflicts:
            self._resolve_conflicts(rule, conflicts)
        
        # Add the rule
        self._rules[rule.id] = rule
        
        # Update field dependencies
        for field in rule.get_dependent_fields():
            self._field_dependencies[field].add(rule.id)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the manager.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        if rule_id not in self._rules:
            return False
        
        rule = self._rules[rule_id]
        
        # Remove from field dependencies
        for field in rule.get_dependent_fields():
            self._field_dependencies[field].discard(rule_id)
        
        # Remove the rule
        del self._rules[rule_id]
        return True
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID.
        
        Args:
            rule_id: ID of the rule to retrieve
            
        Returns:
            The rule if found, None otherwise
        """
        return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = True) -> List[Rule]:
        """List all rules.
        
        Args:
            enabled_only: If True, only return enabled rules
            
        Returns:
            List of rules
        """
        rules = list(self._rules.values())
        if enabled_only:
            rules = [rule for rule in rules if rule.enabled]
        return rules
    
    def get_rules_by_field(self, field_name: str) -> List[Rule]:
        """Get all rules that depend on a specific field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            List of rules that reference this field
        """
        rule_ids = self._field_dependencies.get(field_name, set())
        return [self._rules[rule_id] for rule_id in rule_ids if rule_id in self._rules]
    
    def get_rules_by_priority(self, ascending: bool = False) -> List[Rule]:
        """Get rules sorted by priority.
        
        Args:
            ascending: If True, sort in ascending order (lowest first)
            
        Returns:
            List of rules sorted by priority
        """
        rules = self.list_rules(enabled_only=True)
        return sorted(rules, key=lambda r: r.priority, reverse=not ascending)
    
    def validate_all_rules(self) -> List[ValidationError]:
        """Validate all rules in the manager.
        
        Returns:
            List of validation errors found
        """
        errors = []
        for rule in self._rules.values():
            errors.extend(self._validate_rule(rule))
        
        # Check for global conflicts
        global_conflicts = self._check_global_conflicts()
        errors.extend(global_conflicts)
        
        return errors
    
    def get_conflicts(self) -> List[Tuple[Rule, Rule, str]]:
        """Get all rule conflicts.
        
        Returns:
            List of tuples (rule1, rule2, conflict_description)
        """
        conflicts = []
        rules = list(self._rules.values())
        
        for i, rule1 in enumerate(rules):
            for rule2 in rules[i+1:]:
                conflict_desc = self._detect_conflict(rule1, rule2)
                if conflict_desc:
                    conflicts.append((rule1, rule2, conflict_desc))
        
        return conflicts
    
    def clear(self) -> None:
        """Clear all rules from the manager."""
        self._rules.clear()
        self._field_dependencies.clear()
    
    def count_rules(self, enabled_only: bool = True) -> int:
        """Count rules in the manager.
        
        Args:
            enabled_only: If True, only count enabled rules
            
        Returns:
            Number of rules
        """
        if enabled_only:
            return sum(1 for rule in self._rules.values() if rule.enabled)
        return len(self._rules)
    
    def get_statistics(self) -> Dict[str, any]:
        """Get rule manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        enabled_rules = [rule for rule in self._rules.values() if rule.enabled]
        disabled_rules = [rule for rule in self._rules.values() if not rule.enabled]
        
        return {
            "total_rules": len(self._rules),
            "enabled_rules": len(enabled_rules),
            "disabled_rules": len(disabled_rules),
            "fields_tracked": len(self._field_dependencies),
            "avg_conditions_per_rule": sum(len(rule.conditions) for rule in self._rules.values()) / len(self._rules) if self._rules else 0,
            "avg_conclusions_per_rule": sum(len(rule.conclusions) for rule in self._rules.values()) / len(self._rules) if self._rules else 0,
            "priority_distribution": self._get_priority_distribution(),
            "conflict_resolution_strategy": self._conflict_resolution.value
        }
    
    def _validate_rule(self, rule: Rule) -> List[ValidationError]:
        """Validate a single rule.
        
        Args:
            rule: The rule to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check basic rule structure
        if not rule.id:
            errors.append(ValidationError(
                rule_id=rule.id or "unknown",
                error_type="missing_id",
                message="Rule must have an ID"
            ))
        
        if not rule.conditions:
            errors.append(ValidationError(
                rule_id=rule.id,
                error_type="missing_conditions",
                message="Rule must have at least one condition"
            ))
        
        if not rule.conclusions:
            errors.append(ValidationError(
                rule_id=rule.id,
                error_type="missing_conclusions",
                message="Rule must have at least one conclusion"
            ))
        
        # Validate conditions
        for i, condition in enumerate(rule.conditions):
            if not condition.field:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="invalid_condition",
                    message=f"Condition {i} missing field name",
                    field=f"conditions[{i}].field"
                ))
            
            if condition.value is None and condition.operator.value != "exists":
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="invalid_condition",
                    message=f"Condition {i} missing value (except for 'exists' operator)",
                    field=f"conditions[{i}].value"
                ))
        
        # Validate conclusions
        for i, conclusion in enumerate(rule.conclusions):
            if not conclusion.fact:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="invalid_conclusion",
                    message=f"Conclusion {i} missing fact",
                    field=f"conclusions[{i}].fact"
                ))
            
            if not 0 <= conclusion.confidence <= 1:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="invalid_confidence",
                    message=f"Conclusion {i} confidence must be between 0 and 1",
                    field=f"conclusions[{i}].confidence"
                ))
        
        return errors
    
    def _check_conflicts(self, new_rule: Rule) -> List[Rule]:
        """Check for conflicts with a new rule.
        
        Args:
            new_rule: The rule to check for conflicts
            
        Returns:
            List of conflicting rules
        """
        conflicts = []
        for existing_rule in self._rules.values():
            if self._detect_conflict(new_rule, existing_rule):
                conflicts.append(existing_rule)
        return conflicts
    
    def _detect_conflict(self, rule1: Rule, rule2: Rule) -> Optional[str]:
        """Detect if two rules conflict.
        
        Args:
            rule1: First rule
            rule2: Second rule
            
        Returns:
            Conflict description if conflict exists, None otherwise
        """
        # Same ID conflict
        if rule1.id == rule2.id:
            return "Rules have the same ID"
        
        # Priority conflict (same priority might indicate conflict)
        if rule1.priority == rule2.priority and rule1.priority != 0:
            # Check if they could fire on the same facts
            fields1 = rule1.get_dependent_fields()
            fields2 = rule2.get_dependent_fields()
            if fields1.intersection(fields2):
                return f"Rules have same priority ({rule1.priority}) and overlap on fields"
        
        # Conclusion conflict (same fact key, different values)
        for c1 in rule1.conclusions:
            for c2 in rule2.conclusions:
                if (c1.fact.key == c2.fact.key and 
                    c1.fact.value != c2.fact.value):
                    return f"Rules produce conflicting values for fact '{c1.fact.key}'"
        
        return None
    
    def _resolve_conflicts(self, new_rule: Rule, conflicting_rules: List[Rule]) -> None:
        """Resolve conflicts between rules.
        
        Args:
            new_rule: The new rule being added
            conflicting_rules: List of conflicting existing rules
        """
        if self._conflict_resolution == ConflictResolution.PRIORITY:
            # Higher priority rules win
            for existing_rule in conflicting_rules:
                if new_rule.priority <= existing_rule.priority:
                    # New rule has lower/equal priority, disable it
                    new_rule.enabled = False
                    break
                else:
                    # New rule has higher priority, disable existing rule
                    existing_rule.enabled = False
        
        elif self._conflict_resolution == ConflictResolution.DISABLE_CONFLICTS:
            # Disable all conflicting rules
            for existing_rule in conflicting_rules:
                existing_rule.enabled = False
            new_rule.enabled = False
        
        elif self._conflict_resolution == ConflictResolution.RAISE_ERROR:
            # Raise an error for conflicts
            conflict_ids = [rule.id for rule in conflicting_rules]
            raise ValueError(f"Rule {new_rule.id} conflicts with existing rules: {conflict_ids}")
        
        # For other strategies, we'll implement them as needed
    
    def _check_global_conflicts(self) -> List[ValidationError]:
        """Check for global conflicts across all rules.
        
        Returns:
            List of validation errors for global conflicts
        """
        errors = []
        conflicts = self.get_conflicts()
        
        for rule1, rule2, description in conflicts:
            errors.append(ValidationError(
                rule_id=rule1.id,
                error_type="rule_conflict",
                message=f"Conflicts with rule {rule2.id}: {description}",
                severity="warning"
            ))
        
        return errors
    
    def _get_priority_distribution(self) -> Dict[int, int]:
        """Get distribution of rule priorities.
        
        Returns:
            Dictionary mapping priority values to counts
        """
        distribution = defaultdict(int)
        for rule in self._rules.values():
            distribution[rule.priority] += 1
        return dict(distribution) 