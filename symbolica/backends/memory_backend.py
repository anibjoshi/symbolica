"""Memory backend for fast in-memory processing."""

from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from ..core.types import Fact, Rule, Conclusion
from ..core.fact_store import FactStore


class MemoryBackend:
    """High-performance in-memory backend for symbolic reasoning."""
    
    def __init__(self):
        """Initialize the memory backend."""
        self.fact_store = FactStore()
        self._fact_indices: Dict[str, Set[int]] = defaultdict(set)
        self._rule_cache: Dict[str, Any] = {}
        self._optimization_enabled = True
    
    def add_fact(self, fact: Fact) -> None:
        """Add a fact to the backend storage."""
        self.fact_store.add(fact.key, fact.value, fact.metadata)
        self._update_indices(fact)
    
    def get_facts(self, pattern: Optional[str] = None) -> List[Fact]:
        """Get facts matching a pattern."""
        if pattern:
            return self.fact_store.query(pattern)
        return self.fact_store.get_all_facts()
    
    def remove_fact(self, key: str, value: Any = None) -> int:
        """Remove facts by key and optionally value."""
        removed_count = self.fact_store.remove(key, value)
        self._rebuild_indices()
        return removed_count
    
    def clear_facts(self) -> None:
        """Clear all facts."""
        self.fact_store.clear()
        self._fact_indices.clear()
        self._rule_cache.clear()
    
    def find_matching_facts(self, field: str, operator: str, value: Any) -> List[Fact]:
        """Find facts matching specific criteria with optimized lookup."""
        if not self._optimization_enabled:
            return self._brute_force_search(field, operator, value)
        
        # Use indices for faster lookup when possible
        if operator == "==" and field == "key":
            return self.fact_store.get(str(value))
        elif operator == "==" and field == "value":
            return [f for f in self.fact_store.get_all_facts() if f.value == value]
        else:
            return self._brute_force_search(field, operator, value)
    
    def _brute_force_search(self, field: str, operator: str, value: Any) -> List[Fact]:
        """Fallback brute force search for complex conditions."""
        matching_facts = []
        all_facts = self.fact_store.get_all_facts()
        
        for fact in all_facts:
            if self._evaluate_condition(fact, field, operator, value):
                matching_facts.append(fact)
        
        return matching_facts
    
    def _evaluate_condition(self, fact: Fact, field: str, operator: str, value: Any) -> bool:
        """Evaluate a condition against a fact."""
        # Get the fact field value
        if field == "key":
            fact_value = fact.key
        elif field == "value":
            fact_value = fact.value
        elif field == "timestamp":
            fact_value = fact.timestamp
        elif field == "confidence":
            fact_value = fact.confidence
        elif field.startswith("metadata."):
            meta_key = field[9:]  # Remove "metadata." prefix
            fact_value = fact.metadata.get(meta_key)
        else:
            # Try to get from fact.value if it's a dict
            if isinstance(fact.value, dict):
                fact_value = fact.value.get(field)
            else:
                return False
        
        if fact_value is None:
            return operator == "exists" and value is True
        
        # Apply operator
        try:
            if operator == "==":
                return fact_value == value
            elif operator == "!=":
                return fact_value != value
            elif operator == ">":
                return fact_value > value
            elif operator == "<":
                return fact_value < value
            elif operator == ">=":
                return fact_value >= value
            elif operator == "<=":
                return fact_value <= value
            elif operator == "in":
                return fact_value in value
            elif operator == "contains":
                return value in fact_value
            elif operator == "exists":
                return fact_value is not None
            elif operator == "regex":
                import re
                return bool(re.search(str(value), str(fact_value)))
            else:
                return False
        except (TypeError, AttributeError):
            return False
    
    def _update_indices(self, fact: Fact) -> None:
        """Update search indices for faster lookup."""
        fact_id = len(self.fact_store) - 1
        
        # Index by key
        self._fact_indices[f"key:{fact.key}"].add(fact_id)
        
        # Index by value
        self._fact_indices[f"value:{str(fact.value)}"].add(fact_id)
        
        # Index by metadata
        for meta_key, meta_value in fact.metadata.items():
            self._fact_indices[f"metadata.{meta_key}:{str(meta_value)}"].add(fact_id)
    
    def _rebuild_indices(self) -> None:
        """Rebuild all search indices."""
        self._fact_indices.clear()
        all_facts = self.fact_store.get_all_facts()
        
        for i, fact in enumerate(all_facts):
            # Index by key
            self._fact_indices[f"key:{fact.key}"].add(i)
            
            # Index by value
            self._fact_indices[f"value:{str(fact.value)}"].add(i)
            
            # Index by metadata
            for meta_key, meta_value in fact.metadata.items():
                self._fact_indices[f"metadata.{meta_key}:{str(meta_value)}"].add(i)
    
    def optimize_rules(self, rules: List[Rule]) -> List[Rule]:
        """Optimize rules for better performance."""
        if not self._optimization_enabled:
            return rules
        
        # Sort rules by selectivity (rules with more specific conditions first)
        optimized_rules = sorted(rules, key=self._calculate_rule_selectivity, reverse=True)
        
        # Cache compiled rule patterns
        for rule in optimized_rules:
            self._rule_cache[rule.id] = self._compile_rule(rule)
        
        return optimized_rules
    
    def _calculate_rule_selectivity(self, rule: Rule) -> float:
        """Calculate selectivity score for rule ordering."""
        selectivity = 0.0
        
        for condition in rule.conditions:
            # More specific operators get higher selectivity
            if condition.operator.value == "==":
                selectivity += 1.0
            elif condition.operator.value in ["!=", ">", "<", ">=", "<="]:
                selectivity += 0.8
            elif condition.operator.value in ["in", "contains"]:
                selectivity += 0.6
            elif condition.operator.value == "exists":
                selectivity += 0.4
            elif condition.operator.value == "regex":
                selectivity += 0.3
        
        # Rules with more conditions are generally more selective
        selectivity += len(rule.conditions) * 0.1
        
        return selectivity
    
    def _compile_rule(self, rule: Rule) -> Dict[str, Any]:
        """Compile rule into optimized format."""
        compiled = {
            "id": rule.id,
            "priority": rule.priority,
            "enabled": rule.enabled,
            "conditions": [],
            "conclusions": rule.conclusions
        }
        
        for condition in rule.conditions:
            compiled_condition = {
                "field": condition.field,
                "operator": condition.operator.value,
                "value": condition.value,
                "metadata": condition.metadata
            }
            compiled["conditions"].append(compiled_condition)
        
        return compiled
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get backend performance statistics."""
        return {
            "total_facts": len(self.fact_store),
            "unique_keys": len(self.fact_store.keys()),
            "index_entries": sum(len(indices) for indices in self._fact_indices.values()),
            "cached_rules": len(self._rule_cache),
            "optimization_enabled": self._optimization_enabled,
            "backend_type": "memory"
        }
    
    def enable_optimization(self, enabled: bool = True) -> None:
        """Enable or disable performance optimizations."""
        self._optimization_enabled = enabled
        if not enabled:
            self._rule_cache.clear()
    
    def get_fact_store(self) -> FactStore:
        """Get the underlying fact store."""
        return self.fact_store
    
    def clone(self) -> "MemoryBackend":
        """Create a copy of this backend."""
        new_backend = MemoryBackend()
        
        # Copy all facts
        for fact in self.fact_store.get_all_facts():
            new_backend.add_fact(fact)
        
        # Copy settings
        new_backend._optimization_enabled = self._optimization_enabled
        
        return new_backend
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MemoryBackend(facts={len(self.fact_store)}, optimized={self._optimization_enabled})" 