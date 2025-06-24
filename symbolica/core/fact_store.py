"""FactStore implementation for managing symbolic facts."""

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from .types import Fact, OperatorType


class FactStore:
    """Manages symbolic facts with indexing and querying capabilities."""
    
    def __init__(self):
        """Initialize the fact store."""
        self._facts: Dict[str, List[Fact]] = defaultdict(list)
        self._key_index: Dict[str, Set[int]] = defaultdict(set)
        self._value_index: Dict[str, Set[int]] = defaultdict(set)
        self._metadata_index: Dict[str, Set[int]] = defaultdict(set)
        self._all_facts: List[Fact] = []
        self._fact_count = 0
    
    @classmethod
    def from_json(cls, data: Union[str, Dict[str, Any]]) -> 'FactStore':
        """Create a FactStore from JSON data.
        
        This is the primary method for LLMs to load data into Symbolica.
        
        Args:
            data: JSON string or dictionary containing the data
            
        Returns:
            FactStore instance populated with facts from the JSON
            
        Example:
            # From dict
            facts = FactStore.from_json({
                "claim_amount": 75000,
                "policy_active": True,
                "claim_type": "theft"
            })
            
            # From JSON string
            facts = FactStore.from_json('{"claim_amount": 75000, "policy_active": true}')
        """
        fact_store = cls()
        
        # Parse JSON string if needed
        if isinstance(data, str):
            data = json.loads(data)
        
        # Convert all key-value pairs to facts
        fact_store._load_dict_as_facts(data)
        
        return fact_store
    
    def _load_dict_as_facts(self, data: Dict[str, Any], prefix: str = "") -> None:
        """Recursively load a dictionary as facts.
        
        Args:
            data: Dictionary to load
            prefix: Prefix for nested keys
        """
        for key, value in data.items():
            full_key = f"{prefix}{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively handle nested objects
                self._load_dict_as_facts(value, f"{full_key}.")
            elif isinstance(value, list):
                # Handle arrays by creating indexed facts
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._load_dict_as_facts(item, f"{full_key}[{i}].")
                    else:
                        self.add(f"{full_key}[{i}]", item)
                # Also add the array length
                self.add(f"{full_key}.length", len(value))
            else:
                # Simple key-value pair
                self.add(full_key, value)

    def load_json(self, data: Union[str, Dict[str, Any]]) -> None:
        """Load JSON data into the existing fact store.
        
        Args:
            data: JSON string or dictionary to load
        """
        if isinstance(data, str):
            data = json.loads(data)
        
        self._load_dict_as_facts(data)
    
    def add(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> Fact:
        """Add a fact to the store.
        
        Args:
            key: The fact key
            value: The fact value
            metadata: Optional metadata dictionary
            
        Returns:
            The created Fact object
        """
        if metadata is None:
            metadata = {}
            
        fact = Fact(
            key=key,
            value=value,
            metadata=metadata,
            timestamp=datetime.now()
        )
        
        # Add to main storage
        self._facts[key].append(fact)
        self._all_facts.append(fact)
        fact_id = len(self._all_facts) - 1
        
        # Update indices
        self._key_index[key].add(fact_id)
        
        # Index by value type and string representation
        value_str = str(value)
        self._value_index[value_str].add(fact_id)
        
        # Index metadata
        for meta_key, meta_value in metadata.items():
            meta_str = f"{meta_key}:{str(meta_value)}"
            self._metadata_index[meta_str].add(fact_id)
        
        self._fact_count += 1
        return fact
    
    def get(self, key: str) -> List[Fact]:
        """Get all facts with the given key.
        
        Args:
            key: The fact key to search for
            
        Returns:
            List of facts with the matching key
        """
        return list(self._facts.get(key, []))
    
    def get_latest(self, key: str) -> Optional[Fact]:
        """Get the most recent fact with the given key.
        
        Args:
            key: The fact key to search for
            
        Returns:
            The most recent fact or None if not found
        """
        facts = self.get(key)
        if not facts:
            return None
        return max(facts, key=lambda f: f.timestamp)
    
    def query(self, pattern: str) -> List[Fact]:
        """Query facts using a pattern.
        
        Supports:
        - Key patterns: key:pattern
        - Value patterns: value:pattern  
        - Metadata patterns: meta.field:pattern
        - Wildcard patterns: *pattern*
        - Regex patterns: regex:pattern
        
        Args:
            pattern: The search pattern
            
        Returns:
            List of matching facts
        """
        if ":" in pattern:
            field, search_term = pattern.split(":", 1)
            return self._query_by_field(field, search_term)
        else:
            # Default to key search with wildcard support
            return self._query_wildcard("key", pattern)
    
    def _query_by_field(self, field: str, search_term: str) -> List[Fact]:
        """Query by specific field."""
        if field == "key":
            return self._query_wildcard("key", search_term)
        elif field == "value":
            return self._query_wildcard("value", search_term)
        elif field.startswith("meta."):
            meta_field = field[5:]  # Remove "meta." prefix
            return self._query_metadata(meta_field, search_term)
        elif field == "regex":
            return self._query_regex(search_term)
        else:
            return []
    
    def _query_wildcard(self, field: str, pattern: str) -> List[Fact]:
        """Query with wildcard support."""
        results = []
        
        # Convert wildcard pattern to regex
        if "*" in pattern:
            regex_pattern = pattern.replace("*", ".*")
            regex = re.compile(regex_pattern, re.IGNORECASE)
            
            for fact in self._all_facts:
                field_value = getattr(fact, field) if hasattr(fact, field) else str(fact.value)
                if regex.search(str(field_value)):
                    results.append(fact)
        else:
            # Exact match
            if field == "key":
                results.extend(self._facts.get(pattern, []))
            else:
                for fact in self._all_facts:
                    field_value = getattr(fact, field) if hasattr(fact, field) else str(fact.value)
                    if str(field_value) == pattern:
                        results.append(fact)
        
        return results
    
    def _query_metadata(self, meta_field: str, pattern: str) -> List[Fact]:
        """Query by metadata field."""
        results = []
        for fact in self._all_facts:
            if meta_field in fact.metadata:
                meta_value = str(fact.metadata[meta_field])
                if pattern in meta_value or meta_value == pattern:
                    results.append(fact)
        return results
    
    def _query_regex(self, pattern: str) -> List[Fact]:
        """Query using regex pattern."""
        results = []
        try:
            regex = re.compile(pattern)
            for fact in self._all_facts:
                # Search in key, value, and metadata
                if (regex.search(fact.key) or 
                    regex.search(str(fact.value)) or
                    any(regex.search(str(v)) for v in fact.metadata.values())):
                    results.append(fact)
        except re.error:
            # Invalid regex pattern
            pass
        return results
    
    def filter_facts(self, conditions: List[Dict[str, Any]]) -> List[Fact]:
        """Filter facts by multiple conditions.
        
        Args:
            conditions: List of condition dictionaries with keys:
                - field: The field to check
                - operator: The comparison operator
                - value: The value to compare against
                
        Returns:
            List of facts matching all conditions
        """
        results = self._all_facts.copy()
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not all([field, operator is not None, value is not None]):
                continue
                
            filtered_results = []
            for fact in results:
                if self._evaluate_condition(fact, field, operator, value):
                    filtered_results.append(fact)
            results = filtered_results
            
        return results
    
    def _evaluate_condition(self, fact: Fact, field: str, operator: str, value: Any) -> bool:
        """Evaluate a single condition against a fact."""
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
            fact_value = None
            
        if fact_value is None:
            return False
            
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
            else:
                return False
        except (TypeError, AttributeError):
            return False
    
    def remove(self, key: str, value: Any = None) -> int:
        """Remove facts by key and optionally by value.
        
        Args:
            key: The fact key
            value: Optional specific value to remove
            
        Returns:
            Number of facts removed
        """
        if key not in self._facts:
            return 0
            
        facts_to_remove = self._facts[key]
        
        if value is not None:
            facts_to_remove = [f for f in facts_to_remove if f.value == value]
        
        removed_count = len(facts_to_remove)
        
        # Remove from main storage
        if value is None:
            del self._facts[key]
        else:
            self._facts[key] = [f for f in self._facts[key] if f.value != value]
            if not self._facts[key]:
                del self._facts[key]
        
        # Remove from all_facts and rebuild indices
        for fact in facts_to_remove:
            if fact in self._all_facts:
                self._all_facts.remove(fact)
        
        self._rebuild_indices()
        self._fact_count -= removed_count
        
        return removed_count
    
    def clear(self) -> None:
        """Clear all facts from the store."""
        self._facts.clear()
        self._key_index.clear()
        self._value_index.clear()
        self._metadata_index.clear()
        self._all_facts.clear()
        self._fact_count = 0
    
    def size(self) -> int:
        """Get the total number of facts in the store."""
        return self._fact_count
    
    def keys(self) -> List[str]:
        """Get all unique fact keys."""
        return list(self._facts.keys())
    
    def get_all_facts(self) -> List[Fact]:
        """Get all facts in the store."""
        return self._all_facts.copy()
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize the fact store to a dictionary."""
        return {
            "facts": [
                {
                    "key": fact.key,
                    "value": fact.value,
                    "metadata": fact.metadata,
                    "timestamp": fact.timestamp.isoformat(),
                    "confidence": fact.confidence
                }
                for fact in self._all_facts
            ],
            "count": self._fact_count
        }
    
    def deserialize(self, data: Dict[str, Any]) -> None:
        """Deserialize data into the fact store."""
        self.clear()
        
        for fact_data in data.get("facts", []):
            timestamp = datetime.fromisoformat(fact_data["timestamp"])
            fact = Fact(
                key=fact_data["key"],
                value=fact_data["value"],
                metadata=fact_data.get("metadata", {}),
                timestamp=timestamp,
                confidence=fact_data.get("confidence", 1.0)
            )
            
            # Add without creating new timestamp
            self._facts[fact.key].append(fact)
            self._all_facts.append(fact)
            
        self._fact_count = len(self._all_facts)
        self._rebuild_indices()
    
    def _rebuild_indices(self) -> None:
        """Rebuild all indices."""
        self._key_index.clear()
        self._value_index.clear()
        self._metadata_index.clear()
        
        for i, fact in enumerate(self._all_facts):
            self._key_index[fact.key].add(i)
            
            value_str = str(fact.value)
            self._value_index[value_str].add(i)
            
            for meta_key, meta_value in fact.metadata.items():
                meta_str = f"{meta_key}:{str(meta_value)}"
                self._metadata_index[meta_str].add(i)
    
    def export_json(self, filepath: str) -> None:
        """Export facts to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.serialize(), f, indent=2, default=str)
    
    def import_json(self, filepath: str) -> None:
        """Import facts from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.deserialize(data)
    
    def __len__(self) -> int:
        """Get the number of facts."""
        return self._fact_count
    
    def __contains__(self, key: str) -> bool:
        """Check if a key exists in the store."""
        return key in self._facts
    
    def __iter__(self):
        """Iterate over all facts."""
        return iter(self._all_facts)
    
    def __repr__(self) -> str:
        """String representation of the fact store."""
        return f"FactStore(facts={self._fact_count}, keys={len(self._facts)})" 