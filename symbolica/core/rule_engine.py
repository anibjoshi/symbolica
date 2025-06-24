"""
Symbolica RuleEngine v1 - Simplified, unified engine for all workloads.

This single engine works well for both small and large rule sets by including
smart optimizations (indexing, caching) by default without complexity.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict

from .types import Rule, Fact, Conclusion, ValidationError, ReasoningTrace, InferenceStep, ConditionEvaluation
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
        
        # Track which rule-fact combinations have already fired
        self._fired_combinations: Set[str] = set()
        
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
        self._fired_combinations.clear()
        
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
                can_fire, _ = self._can_fire_with_details(rule, all_facts)
                if can_fire:
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
        
        # Clear state for new evaluation
        self._condition_cache.clear()
        self._fired_combinations.clear()
        
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
                
                # Check if rule can fire and get detailed evaluation
                can_fire, condition_evaluations = self._can_fire_with_details(rule, all_facts)
                
                if can_fire:
                    rule_conclusions = self._evaluate_single_rule(rule, all_facts)
                    
                    if rule_conclusions:
                        step_number += 1
                        execution_time = (time.time() - start_time) * 1000
                        
                        # Find specific matching facts
                        matching_facts = []
                        for eval in condition_evaluations:
                            if eval.result:
                                matching_facts.append(eval.fact_matched)
                        
                        # Create detailed reasoning explanation
                        reasoning_explanation = self._create_reasoning_explanation(
                            rule, condition_evaluations, rule_conclusions
                        )
                        
                        step = InferenceStep(
                            step_number=step_number,
                            rule_applied=rule,
                            facts_matched=matching_facts,
                            conclusions_drawn=rule_conclusions,
                            condition_evaluations=condition_evaluations,
                            reasoning_explanation=reasoning_explanation,
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
    
    def _can_fire_with_details(self, rule: Rule, facts: List[Fact]) -> Tuple[bool, List[ConditionEvaluation]]:
        """Check if rule can fire and return detailed condition evaluations."""
        if not rule.enabled:
            return False, []
        
        condition_evaluations = []
        
        # Create a hash of this rule-fact combination to prevent duplicates
        fact_hash = hash(tuple(sorted((f.key, str(f.value)) for f in facts)))
        combination_key = f"{rule.id}:{fact_hash}"
        
        if combination_key in self._fired_combinations:
            return False, []
        
        # Group conditions by logic type
        all_conditions = []
        any_conditions = []
        
        for condition in rule.conditions:
            logic_type = condition.metadata.get("logic_type", "all")
            if logic_type == "all":
                all_conditions.append(condition)
            else:
                any_conditions.append(condition)
        
        # Evaluate ALL conditions
        all_satisfied = True
        if all_conditions:
            for condition in all_conditions:
                condition_satisfied = False
                matched_fact = None
                
                for fact in facts:
                    if condition.field == fact.key:
                        # Check cache first
                        cache_key = f"{condition.field}|{condition.operator.value}|{condition.value}|{fact.value}"
                        if cache_key in self._condition_cache:
                            result = self._condition_cache[cache_key]
                            self._cache_hits += 1
                        else:
                            result = condition.evaluate(fact)
                            self._condition_cache[cache_key] = result
                            self._cache_misses += 1
                        
                        # Create condition evaluation
                        evaluation = ConditionEvaluation(
                            condition_text=f"{condition.field} {condition.operator.value} {condition.value}",
                            fact_matched=fact,
                            operator=condition.operator.value,
                            expected_value=condition.value,
                            actual_value=fact.value,
                            result=result,
                            explanation=self._create_condition_explanation(condition, fact, result)
                        )
                        condition_evaluations.append(evaluation)
                        
                        if result:
                            condition_satisfied = True
                            matched_fact = fact
                            break
                
                if not condition_satisfied:
                    all_satisfied = False
                    break
        
        # Evaluate ANY conditions
        any_satisfied = True
        if any_conditions:
            any_satisfied = False
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
                        
                        evaluation = ConditionEvaluation(
                            condition_text=f"{condition.field} {condition.operator.value} {condition.value}",
                            fact_matched=fact,
                            operator=condition.operator.value,
                            expected_value=condition.value,
                            actual_value=fact.value,
                            result=result,
                            explanation=self._create_condition_explanation(condition, fact, result)
                        )
                        condition_evaluations.append(evaluation)
                        
                        if result:
                            any_satisfied = True
                            break
                if any_satisfied:
                    break
        
        can_fire = all_satisfied and any_satisfied
        
        # Mark this combination as fired if successful
        if can_fire:
            self._fired_combinations.add(combination_key)
        
        return can_fire, condition_evaluations
    
    def _create_condition_explanation(self, condition, fact: Fact, result: bool) -> str:
        """Create a human-readable explanation for a condition evaluation."""
        operator_explanations = {
            "==": "equals",
            "!=": "does not equal", 
            ">": "is greater than",
            "<": "is less than",
            ">=": "is greater than or equal to",
            "<=": "is less than or equal to",
            "in": "is in",
            "contains": "contains"
        }
        
        operator_text = operator_explanations.get(condition.operator.value, condition.operator.value)
        
        if result:
            return f"✓ {fact.key} ({fact.value}) {operator_text} {condition.value} - SATISFIED"
        else:
            return f"✗ {fact.key} ({fact.value}) {operator_text} {condition.value} - NOT SATISFIED"
    
    def _create_reasoning_explanation(self, rule: Rule, evaluations: List[ConditionEvaluation], 
                                    conclusions: List[Conclusion]) -> str:
        """Create a detailed reasoning explanation for a rule application."""
        rule_name = rule.metadata.get("name", rule.id)
        
        explanation_parts = [
            f"Applied rule: '{rule_name}'"
        ]
        
        # Explain condition evaluations
        satisfied_conditions = [e for e in evaluations if e.result]
        if satisfied_conditions:
            explanation_parts.append("Conditions satisfied:")
            for eval in satisfied_conditions:
                explanation_parts.append(f"  {eval.explanation}")
        
        # Explain conclusions
        if conclusions:
            explanation_parts.append("Therefore concluded:")
            for conclusion in conclusions:
                confidence_text = f" (confidence: {conclusion.confidence:.0%})" if conclusion.confidence < 1.0 else ""
                explanation_parts.append(f"  • {conclusion.fact.key} = {conclusion.fact.value}{confidence_text}")
                
                # Add metadata explanations
                if conclusion.metadata.get('tags'):
                    tags = conclusion.metadata['tags']
                    if isinstance(tags, list):
                        explanation_parts.append(f"    Actions required: {', '.join(tags)}")
                    else:
                        explanation_parts.append(f"    Action required: {tags}")
        
        return "\n".join(explanation_parts)
    
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
            "optimization_features": ["rule_indexing", "condition_caching", "fact_driven_evaluation", "duplicate_prevention"]
        }
    
    def clear(self) -> None:
        """Clear all rules from the engine."""
        self.rules.clear()
        self._rule_dict.clear()
        self._fact_to_rules.clear()
        self._condition_cache.clear()
        self._fired_combinations.clear()
    
    def _evaluate_single_rule(self, rule: Rule, facts: List[Fact]) -> List[Conclusion]:
        """Evaluate a single rule against facts."""
        matching_fact_sets = []
        
        for condition in rule.conditions:
            matching_facts = []
            for fact in facts:
                if fact.key == condition.field and condition.evaluate(fact):
                    matching_facts.append(fact)
            if matching_facts:
                matching_fact_sets.append(matching_facts[:1])  # Take only first match to prevent combinatorial explosion
        
        if not all(matching_fact_sets):
            return []
        
        # Generate combinations and create conclusions (simplified to prevent duplicates)
        import itertools
        fact_combinations = list(itertools.product(*matching_fact_sets))
        
        conclusions = []
        for fact_combo in fact_combinations[:1]:  # Take only first combination to prevent duplicates
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
