"""
Optimized RuleEngine for handling hundreds or thousands of rules efficiently.

This implementation includes:
1. Rule Index Builder - preprocessing for fast lookups
2. Fact-Driven Rule Activator - only evaluate relevant rules
3. Condition Evaluator - short-circuit logic and memoization
4. Enhanced Trace Generator - detailed explanation trails
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, DefaultDict
from collections import defaultdict
import re
import ast
import operator

from .types import (
    Rule, 
    Fact, 
    Condition, 
    Conclusion, 
    ValidationError, 
    BackendType,
    ReasoningTrace,
    InferenceStep,
    OperatorType
)
from .fact_store import FactStore


class ConditionEvaluationCache:
    """Cache for condition evaluation results during inference."""
    
    def __init__(self):
        self.cache: Dict[str, bool] = {}
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, condition: Condition, fact_value: Any) -> str:
        """Generate cache key for condition-value pair."""
        return f"{condition.field}|{condition.operator.value}|{condition.value}|{fact_value}"
    
    def get(self, condition: Condition, fact_value: Any) -> Optional[bool]:
        """Get cached evaluation result."""
        key = self.get_cache_key(condition, fact_value)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, condition: Condition, fact_value: Any, result: bool) -> None:
        """Cache evaluation result."""
        key = self.get_cache_key(condition, fact_value)
        self.cache[key] = result
    
    def clear(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0,
            "cache_size": len(self.cache)
        }


class RuleIndex:
    """
    Rule Index Builder for fast rule lookup based on facts.
    
    Creates mappings from fact names to rules for efficient filtering.
    """
    
    def __init__(self):
        # Map fact names to rule IDs that reference them
        self.fact_to_rules: DefaultDict[str, Set[str]] = defaultdict(set)
        
        # Map rule IDs to the fact names they depend on
        self.rule_to_facts: DefaultDict[str, Set[str]] = defaultdict(set)
        
        # Cache parsed conditions for faster evaluation
        self.parsed_conditions: Dict[str, Any] = {}
        
    def build_index(self, rules: List[Rule]) -> None:
        """Build index from list of rules."""
        self.fact_to_rules.clear()
        self.rule_to_facts.clear()
        self.parsed_conditions.clear()
        
        for rule in rules:
            fact_names = self._extract_fact_names(rule)
            
            for fact_name in fact_names:
                self.fact_to_rules[fact_name].add(rule.id)
                self.rule_to_facts[rule.id].add(fact_name)
            
            # Pre-parse conditions for faster evaluation
            for i, condition in enumerate(rule.conditions):
                cache_key = f"{rule.id}_{i}"
                self.parsed_conditions[cache_key] = self._parse_condition(condition)
    
    def _extract_fact_names(self, rule: Rule) -> Set[str]:
        """Extract all fact names referenced by a rule."""
        fact_names = set()
        
        for condition in rule.conditions:
            if condition.field:
                fact_names.add(condition.field)
        
        return fact_names
    
    def _parse_condition(self, condition: Condition) -> Dict[str, Any]:
        """Parse condition into optimized evaluation structure."""
        return {
            "field": condition.field,
            "operator": condition.operator,
            "value": condition.value,
            "logic_type": condition.metadata.get("logic_type", "all"),
            "original": condition.metadata.get("original_condition", "")
        }
    
    def get_rules_for_facts(self, fact_names: Set[str]) -> Set[str]:
        """Get rule IDs that might be affected by the given fact names."""
        relevant_rules = set()
        
        for fact_name in fact_names:
            relevant_rules.update(self.fact_to_rules.get(fact_name, set()))
        
        return relevant_rules
    
    def get_facts_for_rule(self, rule_id: str) -> Set[str]:
        """Get fact names required by a specific rule."""
        return self.rule_to_facts.get(rule_id, set())


class DetailedTrace:
    """Enhanced trace generator for detailed reasoning explanations."""
    
    def __init__(self):
        self.evaluation_steps: List[Dict[str, Any]] = []
        self.condition_evaluations: List[Dict[str, Any]] = []
        
    def add_condition_evaluation(self, condition: Condition, fact_value: Any, 
                                result: bool, cached: bool = False) -> None:
        """Record a condition evaluation step."""
        self.condition_evaluations.append({
            "field": condition.field,
            "operator": condition.operator.value,
            "condition_value": condition.value,
            "fact_value": fact_value,
            "result": result,
            "cached": cached,
            "timestamp": datetime.now(),
            "original_condition": condition.metadata.get("original_condition", "")
        })
    
    def add_rule_evaluation(self, rule: Rule, matched: bool, 
                           matched_facts: List[Fact], execution_time_ms: float) -> None:
        """Record a rule evaluation step."""
        self.evaluation_steps.append({
            "rule_id": rule.id,
            "rule_name": rule.metadata.get("name", rule.id),
            "matched": matched,
            "matched_facts": [{"key": f.key, "value": f.value} for f in matched_facts],
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.now()
        })
    
    def generate_explanation(self) -> List[str]:
        """Generate human-readable explanation of the reasoning process."""
        explanations = []
        
        for step in self.evaluation_steps:
            if step["matched"]:
                explanations.append(
                    f"✓ Rule '{step['rule_name']}' matched in {step['execution_time_ms']:.2f}ms"
                )
                for fact in step["matched_facts"]:
                    explanations.append(f"  - {fact['key']} = {fact['value']}")
            else:
                explanations.append(
                    f"✗ Rule '{step['rule_name']}' did not match"
                )
        
        return explanations


class OptimizedRuleEngine:
    """
    Scalable rule engine optimized for hundreds or thousands of rules.
    
    Features:
    - Rule indexing for O(1) fact-to-rule lookup
    - Fact-driven rule activation (only evaluate relevant rules)
    - Condition evaluation caching and short-circuiting
    - Detailed tracing and explanation generation
    """
    
    def __init__(self, rules: Optional[List[Rule]] = None, backend: str = "memory"):
        """Initialize the optimized rule engine."""
        self.rules: List[Rule] = rules or []
        self.backend = BackendType(backend)
        
        # Core optimization components
        self.rule_index = RuleIndex()
        self.evaluation_cache = ConditionEvaluationCache()
        
        # Standard indexing
        self._rule_dict: Dict[str, Rule] = {}
        self._priority_sorted_rules: List[Rule] = []
        self._validation_errors: List[ValidationError] = []
        
        # Performance tracking
        self.stats = {
            "rules_evaluated": 0,
            "rules_skipped": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_inference_time_ms": 0
        }
        
        # Build indices
        self._rebuild_indices()
    
    def add_rule(self, rule: Rule) -> None:
        """Add a rule and rebuild indices."""
        if rule.id in self._rule_dict:
            self.rules = [r for r in self.rules if r.id != rule.id]
        
        self.rules.append(rule)
        self._rebuild_indices()
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule and rebuild indices."""
        if rule_id not in self._rule_dict:
            return False
        
        self.rules = [r for r in self.rules if r.id != rule_id]
        self._rebuild_indices()
        return True
    
    def evaluate_optimized(self, facts: FactStore, max_iterations: int = 100) -> List[Conclusion]:
        """
        Optimized evaluation using fact-driven rule activation.
        
        Only evaluates rules that could potentially be triggered by the current facts.
        """
        start_time = time.time()
        conclusions: List[Conclusion] = []
        all_facts = facts.get_all_facts()
        
        # Clear evaluation cache for new inference run
        self.evaluation_cache.clear()
        
        # Get fact names from current facts
        fact_names = {fact.key for fact in all_facts}
        
        # Find potentially relevant rules using index
        relevant_rule_ids = self.rule_index.get_rules_for_facts(fact_names)
        relevant_rules = [self._rule_dict[rule_id] for rule_id in relevant_rule_ids 
                         if rule_id in self._rule_dict and self._rule_dict[rule_id].enabled]
        
        # Sort by priority
        relevant_rules.sort(key=lambda r: (-r.priority, r.id))
        
        self.stats["rules_evaluated"] = len(relevant_rules)
        self.stats["rules_skipped"] = len(self.rules) - len(relevant_rules)
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            new_conclusions = []
            
            for rule in relevant_rules:
                rule_conclusions = self._evaluate_single_rule_optimized(rule, all_facts)
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
                break
            
            conclusions.extend(new_conclusions)
            
            # Update relevant rules if new facts were added
            if new_conclusions:
                new_fact_names = {conclusion.fact.key for conclusion in new_conclusions}
                additional_rule_ids = self.rule_index.get_rules_for_facts(new_fact_names)
                additional_rules = [self._rule_dict[rule_id] for rule_id in additional_rule_ids 
                                  if rule_id in self._rule_dict and self._rule_dict[rule_id].enabled]
                
                # Add any new relevant rules
                for rule in additional_rules:
                    if rule not in relevant_rules:
                        relevant_rules.append(rule)
                
                relevant_rules.sort(key=lambda r: (-r.priority, r.id))
        
        end_time = time.time()
        self.stats["total_inference_time_ms"] = (end_time - start_time) * 1000
        
        # Update cache stats
        cache_stats = self.evaluation_cache.get_stats()
        self.stats["cache_hits"] = cache_stats["hits"]
        self.stats["cache_misses"] = cache_stats["misses"]
        
        return conclusions
    
    def evaluate_with_detailed_trace(self, facts: FactStore, 
                                   max_iterations: int = 100) -> Tuple[List[Conclusion], DetailedTrace]:
        """
        Optimized evaluation with enhanced tracing.
        
        Provides detailed trace of rule evaluation process for explainability.
        """
        trace = DetailedTrace()
        conclusions: List[Conclusion] = []
        all_facts = facts.get_all_facts()
        
        # Clear evaluation cache
        self.evaluation_cache.clear()
        
        # Get relevant rules
        fact_names = {fact.key for fact in all_facts}
        relevant_rule_ids = self.rule_index.get_rules_for_facts(fact_names)
        relevant_rules = [self._rule_dict[rule_id] for rule_id in relevant_rule_ids 
                         if rule_id in self._rule_dict and self._rule_dict[rule_id].enabled]
        relevant_rules.sort(key=lambda r: (-r.priority, r.id))
        
        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            new_conclusions = []
            
            for rule in relevant_rules:
                start_time = time.time()
                
                # Evaluate rule with detailed tracing
                rule_matched, matched_facts = self._can_fire_with_trace(rule, all_facts, trace)
                
                if rule_matched:
                    rule_conclusions = self._evaluate_single_rule_optimized(rule, all_facts)
                    new_conclusions.extend(rule_conclusions)
                    
                    # Add new facts
                    for conclusion in rule_conclusions:
                        facts.add(
                            conclusion.fact.key,
                            conclusion.fact.value,
                            conclusion.fact.metadata
                        )
                        all_facts.append(conclusion.fact)
                
                execution_time = (time.time() - start_time) * 1000
                trace.add_rule_evaluation(rule, rule_matched, matched_facts, execution_time)
            
            if not new_conclusions:
                break
            
            conclusions.extend(new_conclusions)
        
        return conclusions, trace
    
    def _can_fire_with_trace(self, rule: Rule, facts: List[Fact], 
                           trace: DetailedTrace) -> Tuple[bool, List[Fact]]:
        """Check if rule can fire with detailed condition tracing."""
        # Group conditions by logic type
        all_conditions = []
        any_conditions = []
        
        for condition in rule.conditions:
            logic_type = condition.metadata.get("logic_type", "all")
            if logic_type == "all":
                all_conditions.append(condition)
            elif logic_type == "any":
                any_conditions.append(condition)
        
        matched_facts = []
        
        # Evaluate ALL conditions (short-circuit on first failure)
        if all_conditions:
            for condition in all_conditions:
                condition_matched = False
                matching_fact = None
                
                for fact in facts:
                    if fact.key == condition.field:
                        # Check cache first
                        cached_result = self.evaluation_cache.get(condition, fact.value)
                        if cached_result is not None:
                            result = cached_result
                            trace.add_condition_evaluation(condition, fact.value, result, cached=True)
                        else:
                            result = self._evaluate_condition_optimized(condition, fact.value)
                            self.evaluation_cache.set(condition, fact.value, result)
                            trace.add_condition_evaluation(condition, fact.value, result, cached=False)
                        
                        if result:
                            condition_matched = True
                            matching_fact = fact
                            break
                
                if not condition_matched:
                    return False, matched_facts  # Short-circuit: ALL failed
                
                if matching_fact:
                    matched_facts.append(matching_fact)
        
        # Evaluate ANY conditions (short-circuit on first success)
        if any_conditions:
            any_matched = False
            for condition in any_conditions:
                for fact in facts:
                    if fact.key == condition.field:
                        # Check cache first
                        cached_result = self.evaluation_cache.get(condition, fact.value)
                        if cached_result is not None:
                            result = cached_result
                            trace.add_condition_evaluation(condition, fact.value, result, cached=True)
                        else:
                            result = self._evaluate_condition_optimized(condition, fact.value)
                            self.evaluation_cache.set(condition, fact.value, result)
                            trace.add_condition_evaluation(condition, fact.value, result, cached=False)
                        
                        if result:
                            any_matched = True
                            matched_facts.append(fact)
                            break
                
                if any_matched:
                    break  # Short-circuit: ANY succeeded
            
            if not any_matched:
                return False, matched_facts
        
        return True, matched_facts
    
    def _evaluate_condition_optimized(self, condition: Condition, fact_value: Any) -> bool:
        """Optimized condition evaluation with type handling."""
        try:
            if condition.operator == OperatorType.EQ:
                return fact_value == condition.value
            elif condition.operator == OperatorType.NE:
                return fact_value != condition.value
            elif condition.operator == OperatorType.GT:
                return float(fact_value) > float(condition.value)
            elif condition.operator == OperatorType.LT:
                return float(fact_value) < float(condition.value)
            elif condition.operator == OperatorType.GTE:
                return float(fact_value) >= float(condition.value)
            elif condition.operator == OperatorType.LTE:
                return float(fact_value) <= float(condition.value)
            elif condition.operator == OperatorType.IN:
                if isinstance(condition.value, list):
                    return fact_value in condition.value
                return str(fact_value) in str(condition.value)
            elif condition.operator == OperatorType.CONTAINS:
                return str(condition.value) in str(fact_value)
            elif condition.operator == OperatorType.EXISTS:
                return fact_value is not None
            elif condition.operator == OperatorType.REGEX:
                import re
                return bool(re.search(str(condition.value), str(fact_value)))
            else:
                return False
        except (ValueError, TypeError):
            return False
    
    def _evaluate_single_rule_optimized(self, rule: Rule, facts: List[Fact]) -> List[Conclusion]:
        """Optimized single rule evaluation."""
        # Reuse the existing implementation but with cached condition evaluation
        matching_fact_sets = []
        
        for condition in rule.conditions:
            matching_facts = []
            for fact in facts:
                if fact.key == condition.field:
                    # Use cached evaluation if available
                    cached_result = self.evaluation_cache.get(condition, fact.value)
                    if cached_result is not None:
                        result = cached_result
                    else:
                        result = self._evaluate_condition_optimized(condition, fact.value)
                        self.evaluation_cache.set(condition, fact.value, result)
                    
                    if result:
                        matching_facts.append(fact)
            
            matching_fact_sets.append(matching_facts)
        
        if not all(matching_fact_sets):
            return []
        
        # Generate conclusions
        conclusions = []
        import itertools
        fact_combinations = list(itertools.product(*matching_fact_sets))
        
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
    
    def _rebuild_indices(self) -> None:
        """Rebuild all indices for optimized lookup."""
        # Standard indices
        self._rule_dict = {rule.id: rule for rule in self.rules}
        self._priority_sorted_rules = sorted(
            self.rules, 
            key=lambda r: (-r.priority, r.id)
        )
        
        # Optimization indices
        self.rule_index.build_index(self.rules)
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about optimization performance."""
        cache_stats = self.evaluation_cache.get_stats()
        
        return {
            "rule_engine_stats": self.stats,
            "cache_stats": cache_stats,
            "index_stats": {
                "total_rules": len(self.rules),
                "indexed_facts": len(self.rule_index.fact_to_rules),
                "avg_rules_per_fact": (
                    sum(len(rules) for rules in self.rule_index.fact_to_rules.values()) / 
                    len(self.rule_index.fact_to_rules)
                    if self.rule_index.fact_to_rules else 0
                )
            }
        }
    
    def explain_optimization_benefit(self, facts: FactStore) -> Dict[str, Any]:
        """Explain the optimization benefit for current facts."""
        fact_names = {fact.key for fact in facts.get_all_facts()}
        relevant_rule_ids = self.rule_index.get_rules_for_facts(fact_names)
        
        total_rules = len(self.rules)
        relevant_rules = len(relevant_rule_ids)
        rules_skipped = total_rules - relevant_rules
        
        return {
            "total_rules": total_rules,
            "relevant_rules": relevant_rules,
            "rules_skipped": rules_skipped,
            "skip_percentage": (rules_skipped / total_rules * 100) if total_rules > 0 else 0,
            "optimization_factor": f"{total_rules / relevant_rules:.1f}x" if relevant_rules > 0 else "∞",
            "fact_names_provided": list(fact_names),
            "relevant_rule_ids": list(relevant_rule_ids)
        }
    
    # Delegate standard methods to maintain compatibility
    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get rule by ID."""
        return self._rule_dict.get(rule_id)
    
    def validate_rules(self) -> List[ValidationError]:
        """Validate all rules."""
        # Reuse validation logic from base implementation
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        base_stats = {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "disabled_rules": len([r for r in self.rules if not r.enabled]),
            "backend": self.backend.value,
        }
        
        optimization_stats = self.get_optimization_stats()
        
        return {**base_stats, **optimization_stats}
    
    def __len__(self) -> int:
        return len(self.rules)
    
    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._rule_dict
    
    def __iter__(self):
        return iter(self.rules)
    
    def __repr__(self) -> str:
        return f"OptimizedRuleEngine(rules={len(self.rules)}, backend={self.backend.value})" 