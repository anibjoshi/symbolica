"""JSON parser for rules and facts."""

import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from ..core.types import Rule, Fact, Condition, Conclusion, OperatorType, ValidationError


class JSONRuleParser:
    """Parser for rules in JSON format."""
    
    def __init__(self):
        """Initialize the JSON rule parser."""
        self.validation_errors: List[ValidationError] = []
    
    def parse_rules(self, json_data: Union[str, Dict[str, Any]]) -> List[Rule]:
        """Parse rules from JSON data.
        
        Args:
            json_data: JSON string or dictionary containing rule definitions
            
        Returns:
            List of parsed Rule objects
        """
        self.validation_errors.clear()
        
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                self.validation_errors.append(ValidationError(
                    rule_id="parse_error",
                    error_type="json_decode_error",
                    message=f"Invalid JSON: {str(e)}"
                ))
                return []
        else:
            data = json_data
        
        if not isinstance(data, dict):
            self.validation_errors.append(ValidationError(
                rule_id="parse_error",
                error_type="invalid_format",
                message="Root element must be a dictionary"
            ))
            return []
        
        rules_data = data.get("rules", [])
        if not isinstance(rules_data, list):
            self.validation_errors.append(ValidationError(
                rule_id="parse_error",
                error_type="invalid_format",
                message="'rules' must be a list"
            ))
            return []
        
        rules = []
        for i, rule_data in enumerate(rules_data):
            rule = self._parse_single_rule(rule_data, i)
            if rule:
                rules.append(rule)
        
        return rules
    
    def _parse_single_rule(self, rule_data: Dict[str, Any], index: int) -> Optional[Rule]:
        """Parse a single rule from dictionary data."""
        rule_id = rule_data.get("id", f"rule_{index}")
        
        try:
            # Parse conditions
            conditions = []
            conditions_data = rule_data.get("conditions", [])
            
            for j, cond_data in enumerate(conditions_data):
                condition = self._parse_condition(cond_data, rule_id, j)
                if condition:
                    conditions.append(condition)
            
            # Parse conclusions
            conclusions = []
            conclusions_data = rule_data.get("conclusions", [])
            
            for k, concl_data in enumerate(conclusions_data):
                conclusion = self._parse_conclusion(concl_data, rule_id, k)
                if conclusion:
                    conclusions.append(conclusion)
            
            # Create rule
            rule = Rule(
                id=rule_id,
                conditions=conditions,
                conclusions=conclusions,
                priority=rule_data.get("priority", 0),
                metadata=rule_data.get("metadata", {}),
                enabled=rule_data.get("enabled", True)
            )
            
            return rule
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="parse_error",
                message=f"Error parsing rule: {str(e)}"
            ))
            return None
    
    def _parse_condition(self, cond_data: Dict[str, Any], rule_id: str, index: int) -> Optional[Condition]:
        """Parse a condition from dictionary data."""
        try:
            field = cond_data.get("field")
            operator_str = cond_data.get("operator")
            value = cond_data.get("value")
            
            if not field:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="missing_field",
                    message=f"Condition {index} missing 'field'",
                    field=f"conditions[{index}].field"
                ))
                return None
            
            if not operator_str:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="missing_operator",
                    message=f"Condition {index} missing 'operator'",
                    field=f"conditions[{index}].operator"
                ))
                return None
            
            try:
                operator = OperatorType(operator_str)
            except ValueError:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="invalid_operator",
                    message=f"Condition {index} has invalid operator: {operator_str}",
                    field=f"conditions[{index}].operator"
                ))
                return None
            
            return Condition(
                field=field,
                operator=operator,
                value=value,
                metadata=cond_data.get("metadata", {})
            )
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="condition_parse_error",
                message=f"Error parsing condition {index}: {str(e)}",
                field=f"conditions[{index}]"
            ))
            return None
    
    def _parse_conclusion(self, concl_data: Dict[str, Any], rule_id: str, index: int) -> Optional[Conclusion]:
        """Parse a conclusion from dictionary data."""
        try:
            fact_data = concl_data.get("fact", {})
            
            # Handle legacy format where fact fields are at the top level
            if "fact_key" in concl_data:
                fact_key = concl_data["fact_key"]
                fact_value = concl_data["fact_value"]
                fact_metadata = concl_data.get("fact_metadata", {})
            else:
                fact_key = fact_data.get("key")
                fact_value = fact_data.get("value")
                fact_metadata = fact_data.get("metadata", {})
            
            if not fact_key:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="missing_fact_key",
                    message=f"Conclusion {index} missing fact key",
                    field=f"conclusions[{index}].fact.key"
                ))
                return None
            
            fact = Fact(
                key=fact_key,
                value=fact_value,
                metadata=fact_metadata,
                confidence=fact_data.get("confidence", 1.0)
            )
            
            conclusion = Conclusion(
                fact=fact,
                confidence=concl_data.get("confidence", 1.0),
                rule_id=rule_id,
                metadata=concl_data.get("metadata", {})
            )
            
            return conclusion
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="conclusion_parse_error",
                message=f"Error parsing conclusion {index}: {str(e)}",
                field=f"conclusions[{index}]"
            ))
            return None
    
    def serialize_rules(self, rules: List[Rule]) -> str:
        """Serialize rules to JSON string.
        
        Args:
            rules: List of Rule objects to serialize
            
        Returns:
            JSON string representation of the rules
        """
        rules_data = []
        
        for rule in rules:
            rule_data = {
                "id": rule.id,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "metadata": rule.metadata,
                "conditions": [
                    {
                        "field": cond.field,
                        "operator": cond.operator.value,
                        "value": cond.value,
                        "metadata": cond.metadata
                    }
                    for cond in rule.conditions
                ],
                "conclusions": [
                    {
                        "fact": {
                            "key": concl.fact.key,
                            "value": concl.fact.value,
                            "metadata": concl.fact.metadata,
                            "confidence": concl.fact.confidence
                        },
                        "confidence": concl.confidence,
                        "metadata": concl.metadata
                    }
                    for concl in rule.conclusions
                ]
            }
            rules_data.append(rule_data)
        
        return json.dumps({"rules": rules_data}, indent=2, default=str)
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get validation errors from the last parse operation."""
        return self.validation_errors.copy()


class JSONFactParser:
    """Parser for facts in JSON format."""
    
    def __init__(self):
        """Initialize the JSON fact parser."""
        self.validation_errors: List[ValidationError] = []
    
    def parse_facts(self, json_data: Union[str, Dict[str, Any]]) -> List[Fact]:
        """Parse facts from JSON data.
        
        Args:
            json_data: JSON string or dictionary containing fact definitions
            
        Returns:
            List of parsed Fact objects
        """
        self.validation_errors.clear()
        
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                self.validation_errors.append(ValidationError(
                    rule_id="parse_error",
                    error_type="json_decode_error",
                    message=f"Invalid JSON: {str(e)}"
                ))
                return []
        else:
            data = json_data
        
        facts = []
        
        if isinstance(data, dict):
            if "facts" in data:
                # Structured format with facts array
                facts_data = data["facts"]
                if isinstance(facts_data, list):
                    for i, fact_data in enumerate(facts_data):
                        fact = self._parse_single_fact(fact_data, i)
                        if fact:
                            facts.append(fact)
                elif isinstance(facts_data, dict):
                    # Simple key-value format
                    for key, value in facts_data.items():
                        fact = Fact(key=key, value=value)
                        facts.append(fact)
            else:
                # Treat entire dict as key-value facts
                for key, value in data.items():
                    fact = Fact(key=key, value=value)
                    facts.append(fact)
        elif isinstance(data, list):
            # List of fact objects
            for i, fact_data in enumerate(data):
                fact = self._parse_single_fact(fact_data, i)
                if fact:
                    facts.append(fact)
        
        return facts
    
    def _parse_single_fact(self, fact_data: Dict[str, Any], index: int) -> Optional[Fact]:
        """Parse a single fact from dictionary data."""
        try:
            key = fact_data.get("key")
            value = fact_data.get("value")
            
            if not key:
                self.validation_errors.append(ValidationError(
                    rule_id=f"fact_{index}",
                    error_type="missing_key",
                    message=f"Fact {index} missing 'key'"
                ))
                return None
            
            metadata = fact_data.get("metadata", {})
            confidence = fact_data.get("confidence", 1.0)
            
            # Parse timestamp if provided
            timestamp_str = fact_data.get("timestamp")
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    # Use current time if timestamp parsing fails
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            return Fact(
                key=key,
                value=value,
                metadata=metadata,
                timestamp=timestamp,
                confidence=confidence
            )
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=f"fact_{index}",
                error_type="fact_parse_error",
                message=f"Error parsing fact {index}: {str(e)}"
            ))
            return None
    
    def serialize_facts(self, facts: List[Fact]) -> str:
        """Serialize facts to JSON string.
        
        Args:
            facts: List of Fact objects to serialize
            
        Returns:
            JSON string representation of the facts
        """
        facts_data = []
        
        for fact in facts:
            fact_data = {
                "key": fact.key,
                "value": fact.value,
                "metadata": fact.metadata,
                "timestamp": fact.timestamp.isoformat(),
                "confidence": fact.confidence
            }
            facts_data.append(fact_data)
        
        return json.dumps({"facts": facts_data}, indent=2, default=str)
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get validation errors from the last parse operation."""
        return self.validation_errors.copy()


# Example JSON formats
EXAMPLE_RULES_JSON = {
    "rules": [
        {
            "id": "server_down_alert",
            "priority": 10,
            "enabled": True,
            "metadata": {"category": "infrastructure", "severity": "high"},
            "conditions": [
                {"field": "status", "operator": "==", "value": "down"},
                {"field": "entity_type", "operator": "==", "value": "server"}
            ],
            "conclusions": [
                {
                    "fact": {
                        "key": "alert_severity",
                        "value": "high",
                        "metadata": {"auto_generated": True},
                        "confidence": 0.9
                    },
                    "confidence": 0.9,
                    "metadata": {"reason": "Server down condition met"}
                }
            ]
        }
    ]
}

EXAMPLE_FACTS_JSON = {
    "facts": [
        {
            "key": "server_1_status",
            "value": "down",
            "metadata": {"location": "datacenter_1", "last_ping": "2024-01-01T10:00:00Z"},
            "confidence": 1.0,
            "timestamp": "2024-01-01T10:00:00Z"
        },
        {
            "key": "server_1_type",
            "value": "web_server",
            "metadata": {"role": "frontend"},
            "confidence": 1.0
        }
    ]
} 