"""RuleEngine implementation for evaluating rules against facts."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .types import (
    Rule, 
    Fact, 
    Condition, 
    Conclusion, 
    ValidationError, 
    BackendType,
    ReasoningTrace,
    InferenceStep
)
from .fact_store import FactStore


class RuleEngine:
    """Evaluates rules against facts using configurable backends."""
    
    def __init__(self, rules: Optional[List[Rule]] = None, backend: str = "memory"):
        """Initialize the rule engine.
        
        Args:
            rules: Optional list of initial rules
            backend: Backend type ("memory", "graph", "distributed")
        """
        self.rules: List[Rule] = rules or []
        self.backend = BackendType(backend)
        self._rule_index: Dict[str, Rule] = {}
        self._priority_sorted_rules: List[Rule] = []
        self._validation_errors: List[ValidationError] = []
        
        # Build initial indices
        self._rebuild_indices()
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine.
        
        Args:
            rule: The rule to add
        """
        if rule.id in self._rule_index:
            # Replace existing rule
            old_rule = self._rule_index[rule.id]
            self.rules = [r for r in self.rules if r.id != rule.id]
        
        self.rules.append(rule)
        self._rebuild_indices()
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID.
        
        Args:
            rule_id: The ID of the rule to remove
            
        Returns:
            True if rule was found and removed, False otherwise
        """
        if rule_id not in self._rule_index:
            return False
            
        self.rules = [r for r in self.rules if r.id != rule_id]
        self._rebuild_indices()
        return True
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID.
        
        Args:
            rule_id: The rule ID
            
        Returns:
            The rule if found, None otherwise
        """
        return self._rule_index.get(rule_id)
    
    def evaluate(self, facts: FactStore, max_iterations: int = 100) -> List[Conclusion]:
        """Evaluate all rules against the fact store.
        
        Args:
            facts: The fact store to evaluate against
            max_iterations: Maximum number of inference iterations
            
        Returns:
            List of conclusions drawn from rule evaluation
        """
        conclusions: List[Conclusion] = []
        all_facts = facts.get_all_facts()
        iteration = 0
        
        # Track which rules have fired to avoid infinite loops
        fired_rules: Set[str] = set()
        
        while iteration < max_iterations:
            iteration += 1
            new_conclusions = []
            
            # Evaluate rules in priority order
            for rule in self._priority_sorted_rules:
                if not rule.enabled:
                    continue
                    
                # Check if rule can fire
                if rule.can_fire(all_facts):
                    rule_conclusions = self._evaluate_single_rule(rule, all_facts)
                    new_conclusions.extend(rule_conclusions)
                    
                    # Add new facts from conclusions
                    for conclusion in rule_conclusions:
                        facts.add(
                            conclusion.fact.key,
                            conclusion.fact.value,
                            conclusion.fact.metadata
                        )
                        all_facts.append(conclusion.fact)
            
            if not new_conclusions:
                # No new conclusions, stop inference
                break
                
            conclusions.extend(new_conclusions)
        
        return conclusions
    
    def _evaluate_single_rule(self, rule: Rule, facts: List[Fact]) -> List[Conclusion]:
        """Evaluate a single rule against facts.
        
        Args:
            rule: The rule to evaluate
            facts: List of available facts
            
        Returns:
            List of conclusions from this rule
        """
        # Find facts that match all conditions
        matching_fact_sets = rule.get_matching_facts(facts)
        
        if not all(matching_fact_sets):
            return []
        
        # Generate all combinations of matching facts
        import itertools
        fact_combinations = list(itertools.product(*matching_fact_sets))
        
        conclusions = []
        for fact_combo in fact_combinations:
            # Create conclusions for this combination
            for conclusion_template in rule.conclusions:
                # Calculate confidence based on supporting facts
                min_confidence = min(fact.confidence for fact in fact_combo)
                conclusion_confidence = min(
                    conclusion_template.confidence,
                    min_confidence
                )
                
                conclusion = Conclusion(
                    fact=Fact(
                        key=conclusion_template.fact.key,
                        value=conclusion_template.fact.value,
                        metadata=conclusion_template.fact.metadata.copy(),
                        confidence=conclusion_confidence
                    ),
                    confidence=conclusion_confidence,
                    rule_id=rule.id,
                    supporting_facts=list(fact_combo),
                    metadata=conclusion_template.metadata.copy()
                )
                
                conclusions.append(conclusion)
        
        return conclusions
    
    def evaluate_with_trace(self, facts: FactStore, max_iterations: int = 100) -> Tuple[List[Conclusion], ReasoningTrace]:
        """Evaluate rules with detailed reasoning trace.
        
        Args:
            facts: The fact store to evaluate against
            max_iterations: Maximum number of inference iterations
            
        Returns:
            Tuple of (conclusions, reasoning_trace)
        """
        trace = ReasoningTrace(steps=[], final_conclusions=[])
        conclusions: List[Conclusion] = []
        all_facts = facts.get_all_facts()
        iteration = 0
        step_number = 0
        
        while iteration < max_iterations:
            iteration += 1
            iteration_conclusions = []
            
            for rule in self._priority_sorted_rules:
                if not rule.enabled:
                    continue
                
                start_time = time.time()
                
                if rule.can_fire(all_facts):
                    rule_conclusions = self._evaluate_single_rule(rule, all_facts)
                    
                    if rule_conclusions:
                        step_number += 1
                        
                        # Find the specific facts that matched
                        matching_facts = []
                        for condition in rule.conditions:
                            condition_matches = [f for f in all_facts if condition.evaluate(f)]
                            matching_facts.extend(condition_matches)
                        
                        # Remove duplicates while preserving order
                        seen = set()
                        unique_matching_facts = []
                        for fact in matching_facts:
                            fact_id = (fact.key, fact.timestamp)
                            if fact_id not in seen:
                                seen.add(fact_id)
                                unique_matching_facts.append(fact)
                        
                        execution_time = (time.time() - start_time) * 1000
                        
                        step = InferenceStep(
                            step_number=step_number,
                            rule_applied=rule,
                            facts_matched=unique_matching_facts,
                            conclusions_drawn=rule_conclusions,
                            execution_time_ms=execution_time
                        )
                        
                        trace.add_step(step)
                        iteration_conclusions.extend(rule_conclusions)
                        
                        # Add new facts from conclusions
                        for conclusion in rule_conclusions:
                            facts.add(
                                conclusion.fact.key,
                                conclusion.fact.value,
                                conclusion.fact.metadata
                            )
                            all_facts.append(conclusion.fact)
            
            if not iteration_conclusions:
                break
                
            conclusions.extend(iteration_conclusions)
        
        trace.finalize(conclusions)
        return conclusions, trace
    
    def explain(self, conclusion: Conclusion, facts: FactStore) -> ReasoningTrace:
        """Generate explanation for how a conclusion was reached.
        
        Args:
            conclusion: The conclusion to explain
            facts: The fact store used for inference
            
        Returns:
            Reasoning trace showing how the conclusion was derived
        """
        # This is a simplified explanation - in practice, we'd need to
        # track the full inference graph
        trace = ReasoningTrace(steps=[], final_conclusions=[conclusion])
        
        # Find the rule that generated this conclusion
        rule = self.get_rule(conclusion.rule_id)
        if not rule:
            return trace
        
        # Create a step showing this rule application
        step = InferenceStep(
            step_number=1,
            rule_applied=rule,
            facts_matched=conclusion.supporting_facts,
            conclusions_drawn=[conclusion]
        )
        
        trace.add_step(step)
        trace.finalize([conclusion])
        return trace
    
    def validate_rules(self) -> List[ValidationError]:
        """Validate all rules in the engine.
        
        Returns:
            List of validation errors found
        """
        errors = []
        
        for rule in self.rules:
            # Check for duplicate rule IDs
            if sum(1 for r in self.rules if r.id == rule.id) > 1:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="duplicate_id",
                    message="Duplicate rule ID found"
                ))
            
            # Check for empty conditions
            if not rule.conditions:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="empty_conditions",
                    message="Rule has no conditions"
                ))
            
            # Check for empty conclusions
            if not rule.conclusions:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="empty_conclusions", 
                    message="Rule has no conclusions"
                ))
            
            # Validate individual conditions
            for i, condition in enumerate(rule.conditions):
                if not condition.field:
                    errors.append(ValidationError(
                        rule_id=rule.id,
                        error_type="invalid_condition",
                        message=f"Condition {i} has empty field",
                        field=f"conditions[{i}].field"
                    ))
                
                if condition.value is None and condition.operator.value != "exists":
                    errors.append(ValidationError(
                        rule_id=rule.id,
                        error_type="invalid_condition",
                        message=f"Condition {i} has null value for non-exists operator",
                        field=f"conditions[{i}].value"
                    ))
            
            # Validate conclusions
            for i, conclusion in enumerate(rule.conclusions):
                if not conclusion.fact.key:
                    errors.append(ValidationError(
                        rule_id=rule.id,
                        error_type="invalid_conclusion",
                        message=f"Conclusion {i} has empty fact key",
                        field=f"conclusions[{i}].fact.key"
                    ))
                
                if not (0 <= conclusion.confidence <= 1):
                    errors.append(ValidationError(
                        rule_id=rule.id,
                        error_type="invalid_confidence",
                        message=f"Conclusion {i} has invalid confidence value",
                        field=f"conclusions[{i}].confidence"
                    ))
        
        self._validation_errors = errors
        return errors
    
    def get_conflicting_rules(self) -> List[Tuple[Rule, Rule, str]]:
        """Find rules that might conflict with each other.
        
        Returns:
            List of tuples containing (rule1, rule2, conflict_reason)
        """
        conflicts = []
        
        for i, rule1 in enumerate(self.rules):
            for rule2 in self.rules[i+1:]:
                # Check if rules have same priority but different conclusions for same fact
                if rule1.priority == rule2.priority:
                    rule1_conclusion_keys = {c.fact.key for c in rule1.conclusions}
                    rule2_conclusion_keys = {c.fact.key for c in rule2.conclusions}
                    
                    common_keys = rule1_conclusion_keys & rule2_conclusion_keys
                    if common_keys:
                        # Check if conclusions actually conflict (different values)
                        for key in common_keys:
                            rule1_values = {c.fact.value for c in rule1.conclusions if c.fact.key == key}
                            rule2_values = {c.fact.value for c in rule2.conclusions if c.fact.key == key}
                            
                            if rule1_values & rule2_values == set():  # No common values
                                conflicts.append((
                                    rule1, 
                                    rule2, 
                                    f"Conflicting conclusions for fact '{key}'"
                                ))
        
        return conflicts
    
    def resolve_conflicts(self, strategy: str = "priority") -> None:
        """Resolve rule conflicts using the specified strategy.
        
        Args:
            strategy: Conflict resolution strategy ("priority", "disable", "merge")
        """
        conflicts = self.get_conflicting_rules()
        
        if strategy == "priority":
            # Higher priority rules override lower priority ones
            # This is handled automatically in rule ordering
            pass
        elif strategy == "disable":
            # Disable conflicting rules with lower priority
            for rule1, rule2, reason in conflicts:
                if rule1.priority > rule2.priority:
                    rule2.enabled = False
                elif rule2.priority > rule1.priority:
                    rule1.enabled = False
                # If equal priority, disable both
                else:
                    rule1.enabled = False
                    rule2.enabled = False
        elif strategy == "merge":
            # This would require more complex logic to merge rule conditions
            # For now, just log that merging is not implemented
            pass
    
    def _rebuild_indices(self) -> None:
        """Rebuild internal indices for fast lookup."""
        self._rule_index = {rule.id: rule for rule in self.rules}
        self._priority_sorted_rules = sorted(
            self.rules, 
            key=lambda r: (-r.priority, r.id)  # Higher priority first, then by ID
        )
    
    def get_applicable_rules(self, facts: List[Fact]) -> List[Rule]:
        """Get rules that can fire given the current facts.
        
        Args:
            facts: Available facts
            
        Returns:
            List of rules that can fire
        """
        applicable = []
        for rule in self._priority_sorted_rules:
            if rule.enabled and rule.can_fire(facts):
                applicable.append(rule)
        return applicable
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the rule engine.
        
        Returns:
            Dictionary containing various statistics
        """
        enabled_rules = [r for r in self.rules if r.enabled]
        disabled_rules = [r for r in self.rules if not r.enabled]
        
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len(enabled_rules),
            "disabled_rules": len(disabled_rules),
            "validation_errors": len(self._validation_errors),
            "backend": self.backend.value,
            "priority_distribution": {
                priority: len([r for r in self.rules if r.priority == priority])
                for priority in set(r.priority for r in self.rules)
            }
        }
    
    def __len__(self) -> int:
        """Get the number of rules."""
        return len(self.rules)
    
    def __contains__(self, rule_id: str) -> bool:
        """Check if a rule exists."""
        return rule_id in self._rule_index
    
    def __iter__(self):
        """Iterate over rules."""
        return iter(self.rules)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"RuleEngine(rules={len(self.rules)}, backend={self.backend.value})" 