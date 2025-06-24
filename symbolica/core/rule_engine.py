"""
Symbolica RuleEngine v1 - Simplified, unified engine for all workloads.

This single engine works well for both small and large rule sets by including
smart optimizations (indexing, caching) by default without complexity.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

from .types import Rule, Fact, Conclusion, ValidationError, ReasoningTrace, InferenceStep
from .fact_store import FactStore


class RuleEngine:
    """
    Unified RuleEngine for Symbolica v1.
    
    Features:
    - Works efficiently for both small and large rule sets
    - Rule indexing for fast fact-driven evaluation  
    - Condition evaluation caching
    - Comprehensive validation
    - Detailed tracing and explanations
    - Simple, clean API
    """
    
    def __init__(self, rules: Optional[List[Rule]] = None):
        """Initialize the rule engine.
        
        Args:
            rules: Initial rules to add
        """
        # Core storage
        self.rules: List[Rule] = []
        self._rule_dict: Dict[str, Rule] = {}
        
        # Optimization: Rule indexing (maps fact names to rule IDs)
        self._fact_to_rules: Dict[str, Set[str]] = defaultdict(set)
        
        # Optimization: Condition evaluation cache
        self._condition_cache: Dict[str, bool] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Statistics
        self.stats = {
            "total_evaluations": 0,
            "total_rules_fired": 0,
            "total_rules_skipped": 0,
            "total_execution_time_ms": 0
        }
        
        # Add initial rules
        if rules:
            for rule in rules:
                self.add_rule(rule)
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the engine."""
        # Basic validation
        if not rule.id:
            raise ValueError("Rule must have an ID")
        if not rule.conditions:
            raise ValueError("Rule must have conditions")
        if not rule.conclusions:
            raise ValueError("Rule must have conclusions")
        
        # Replace if exists
        if rule.id in self._rule_dict:
            self.remove_rule(rule.id)
        
        self.rules.append(rule)
        self._rule_dict[rule.id] = rule
        
        # Update index
        for condition in rule.conditions:
            if condition.field:
                self._fact_to_rules[condition.field].add(rule.id)
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        if rule_id not in self._rule_dict:
            return False
        
        rule = self._rule_dict[rule_id]
        
        # Remove from rules list
        self.rules = [r for r in self.rules if r.id != rule_id]
        del self._rule_dict[rule_id]
        
        # Update index
        for condition in rule.conditions:
            if condition.field:
                self._fact_to_rules[condition.field].discard(rule_id)
        
        return True
    
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self._rule_dict.get(rule_id)
    
    def list_rules(self, enabled_only: bool = True) -> List[Rule]:
        """List all rules."""
        if enabled_only:
            return [rule for rule in self.rules if rule.enabled]
        return self.rules.copy()
    
    def evaluate(self, facts: FactStore, max_iterations: int = 100) -> List[Conclusion]:
        """Evaluate rules against facts to draw conclusions."""
        start_time = time.time()
        
        # Clear cache for new evaluation
        self._condition_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        
        conclusions: List[Conclusion] = []
        all_facts = facts.get_all_facts()
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            new_conclusions = []
            
            # Get fact names for optimization
            fact_names = {fact.key for fact in all_facts}
            
            # Find relevant rules using index (optimization)
            relevant_rule_ids = set()
            for fact_name in fact_names:
                relevant_rule_ids.update(self._fact_to_rules.get(fact_name, set()))
            
            # Get enabled rules sorted by priority
            relevant_rules = [self._rule_dict[rule_id] for rule_id in relevant_rule_ids 
                            if rule_id in self._rule_dict and self._rule_dict[rule_id].enabled]
            relevant_rules.sort(key=lambda r: (-r.priority, r.id))
            
            # Track skipped rules
            self.stats["total_rules_skipped"] += len(self.rules) - len(relevant_rules)
            
            # Evaluate relevant rules
            for rule in relevant_rules:
                if self._can_fire_optimized(rule, all_facts):
                    rule_conclusions = self._evaluate_single_rule(rule, all_facts)
                    new_conclusions.extend(rule_conclusions)
                    self.stats["total_rules_fired"] += 1
                    
                    # Add new facts from conclusions
                    for conclusion in rule_conclusions:
                        facts.add(
                            conclusion.fact.key,
                            conclusion.fact.value,
                            conclusion.fact.metadata
                        )
                        all_facts.append(conclusion.fact)
            
            if not new_conclusions:
                break
            
            conclusions.extend(new_conclusions)
        
        # Update statistics
        execution_time_ms = (time.time() - start_time) * 1000
        self.stats["total_evaluations"] += 1
        self.stats["total_execution_time_ms"] += execution_time_ms
        
        return conclusions
    
    def evaluate_with_trace(self, facts: FactStore, 
                           max_iterations: int = 100) -> Tuple[List[Conclusion], ReasoningTrace]:
        """Evaluate rules with detailed reasoning trace."""
        trace = ReasoningTrace(steps=[], final_conclusions=[])
        conclusions: List[Conclusion] = []
        all_facts = facts.get_all_facts()
        iteration = 0
        step_number = 0
        
        self._condition_cache.clear()
        
        while iteration < max_iterations:
            iteration += 1
            iteration_conclusions = []
            
            # Get relevant rules (same optimization as evaluate)
            fact_names = {fact.key for fact in all_facts}
            relevant_rule_ids = set()
            for fact_name in fact_names:
                relevant_rule_ids.update(self._fact_to_rules.get(fact_name, set()))
            
            relevant_rules = [self._rule_dict[rule_id] for rule_id in relevant_rule_ids 
                            if rule_id in self._rule_dict and self._rule_dict[rule_id].enabled]
            relevant_rules.sort(key=lambda r: (-r.priority, r.id))
            
            for rule in relevant_rules:
                start_time = time.time()
                
                if self._can_fire_optimized(rule, all_facts):
                    rule_conclusions = self._evaluate_single_rule(rule, all_facts)
                    
                    if rule_conclusions:
                        step_number += 1
                        execution_time = (time.time() - start_time) * 1000
                        
                        # Find matching facts for trace
                        matching_facts = []
                        for condition in rule.conditions:
                            for fact in all_facts:
                                if condition.field == fact.key and condition.evaluate(fact):
                                    matching_facts.append(fact)
                                    break
                        
                        step = InferenceStep(
                            step_number=step_number,
                            rule_applied=rule,
                            facts_matched=matching_facts,
                            conclusions_drawn=rule_conclusions,
                            execution_time_ms=execution_time
                        )
                        
                        trace.add_step(step)
                        iteration_conclusions.extend(rule_conclusions)
                        
                        # Add new facts
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
    
    def validate_rules(self) -> List[ValidationError]:
        """Validate all rules in the engine."""
        errors = []
        
        # Check for duplicate IDs
        seen_ids = set()
        for rule in self.rules:
            if rule.id in seen_ids:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="duplicate_id",
                    message="Duplicate rule ID"
                ))
            seen_ids.add(rule.id)
            
            # Basic validation
            if not rule.conditions:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="missing_conditions",
                    message="Rule must have conditions"
                ))
            
            if not rule.conclusions:
                errors.append(ValidationError(
                    rule_id=rule.id,
                    error_type="missing_conclusions",
                    message="Rule must have conclusions"
                ))
        
        return errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        enabled_rules = [r for r in self.rules if r.enabled]
        total_cache_ops = self._cache_hits + self._cache_misses
        
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len(enabled_rules),
            "total_evaluations": self.stats["total_evaluations"],
            "total_rules_fired": self.stats["total_rules_fired"],
            "total_rules_skipped": self.stats["total_rules_skipped"],
            "total_execution_time_ms": self.stats["total_execution_time_ms"],
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": self._cache_hits / total_cache_ops if total_cache_ops > 0 else 0,
            "avg_execution_time_ms": self.stats["total_execution_time_ms"] / self.stats["total_evaluations"] if self.stats["total_evaluations"] > 0 else 0,
            "skip_rate": self.stats["total_rules_skipped"] / (self.stats["total_rules_fired"] + self.stats["total_rules_skipped"]) if (self.stats["total_rules_fired"] + self.stats["total_rules_skipped"]) > 0 else 0,
            "optimization_features": ["rule_indexing", "condition_caching", "fact_driven_evaluation"]
        }
    
    def clear(self) -> None:
        """Clear all rules from the engine."""
        self.rules.clear()
        self._rule_dict.clear()
        self._fact_to_rules.clear()
        self._condition_cache.clear()
    
    def _can_fire_optimized(self, rule: Rule, facts: List[Fact]) -> bool:
        """Check if rule can fire with caching optimization."""
        if not rule.enabled:
            return False
        
        # Group conditions by logic type
        all_conditions = []
        any_conditions = []
        
        for condition in rule.conditions:
            logic_type = condition.metadata.get("logic_type", "all")
            if logic_type == "all":
                all_conditions.append(condition)
            else:
                any_conditions.append(condition)
        
        # Evaluate ALL conditions (short-circuit on failure)
        if all_conditions:
            for condition in all_conditions:
                condition_matched = False
                for fact in facts:
                    if condition.field == fact.key:
                        # Check cache first (optimization)
                        cache_key = f"{condition.field}|{condition.operator.value}|{condition.value}|{fact.value}"
                        if cache_key in self._condition_cache:
                            result = self._condition_cache[cache_key]
                            self._cache_hits += 1
                        else:
                            result = condition.evaluate(fact)
                            self._condition_cache[cache_key] = result
                            self._cache_misses += 1
                        
                        if result:
                            condition_matched = True
                            break
                
                if not condition_matched:
                    return False  # Short-circuit
        
        # Evaluate ANY conditions (short-circuit on success)
        if any_conditions:
            any_matched = False
            for condition in any_conditions:
                for fact in facts:
                    if condition.field == fact.key:
                        cache_key = f"{condition.field}|{condition.operator.value}|{condition.value}|{fact.value}"
                        if cache_key in self._condition_cache:
                            result = self._condition_cache[cache_key]
                            self._cache_hits += 1
                        else:
                            result = condition.evaluate(fact)
                            self._condition_cache[cache_key] = result
                            self._cache_misses += 1
                        
                        if result:
                            any_matched = True
                            break
                if any_matched:
                    break
            
            if not any_matched:
                return False
        
        return True
    
    def _evaluate_single_rule(self, rule: Rule, facts: List[Fact]) -> List[Conclusion]:
        """Evaluate a single rule against facts."""
        matching_fact_sets = []
        
        for condition in rule.conditions:
            matching_facts = []
            for fact in facts:
                if fact.key == condition.field and condition.evaluate(fact):
                    matching_facts.append(fact)
            matching_fact_sets.append(matching_facts)
        
        if not all(matching_fact_sets):
            return []
        
        # Generate combinations and create conclusions
        import itertools
        fact_combinations = list(itertools.product(*matching_fact_sets))
        
        conclusions = []
        for fact_combo in fact_combinations:
            for conclusion_template in rule.conclusions:
                min_confidence = min(fact.confidence for fact in fact_combo)
                conclusion_confidence = min(conclusion_template.confidence, min_confidence)
                
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
    
    # Convenience methods
    def count_rules(self, enabled_only: bool = True) -> int:
        return len(self.list_rules(enabled_only))
    
    def has_rule(self, rule_id: str) -> bool:
        return rule_id in self._rule_dict
    
    def __len__(self) -> int:
        return len(self.rules)
    
    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._rule_dict
