"""YAML parser for rules and facts with support for if/then syntax."""

import yaml
import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime

from ..core.types import Rule, Fact, Condition, Conclusion, OperatorType, ValidationError


class YAMLRuleParser:
    """Parser for YAML rule definitions supporting multiple formats."""
    
    def __init__(self):
        """Initialize the YAML rule parser."""
        self.validation_errors: List[ValidationError] = []
        
        # Mapping of string operators to OperatorType
        self.operator_mapping = {
            '>': OperatorType.GT,
            '<': OperatorType.LT,
            '>=': OperatorType.GTE,
            '<=': OperatorType.LTE,
            '==': OperatorType.EQ,
            '!=': OperatorType.NE,
            'contains': OperatorType.CONTAINS,
            'in': OperatorType.IN,
            'exists': OperatorType.EXISTS
        }
    
    def parse_rules_from_folder(self, folder_path: str) -> List[Rule]:
        """Parse all rule files from a folder.
        
        Args:
            folder_path: Path to folder containing rule YAML files
            
        Returns:
            List of parsed Rule objects
        """
        self.validation_errors.clear()
        rules = []
        
        folder = Path(folder_path)
        if not folder.exists():
            self.validation_errors.append(ValidationError(
                rule_id="folder_error",
                error_type="folder_not_found",
                message=f"Folder not found: {folder_path}"
            ))
            return []
        
        # Find all YAML files in the folder
        yaml_files = list(folder.glob("*.yaml")) + list(folder.glob("*.yml"))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    content = f.read()
                
                parsed_rules = self.parse_rules(content, source_file=str(yaml_file))
                rules.extend(parsed_rules)
                
            except Exception as e:
                self.validation_errors.append(ValidationError(
                    rule_id=f"file_{yaml_file.name}",
                    error_type="file_parse_error",
                    message=f"Error parsing file {yaml_file}: {str(e)}"
                ))
        
        return rules
    
    def parse_rule_file(self, file_path: str) -> List[Rule]:
        """Parse rules from a single YAML file.
        
        Args:
            file_path: Path to the YAML file to parse
            
        Returns:
            List of parsed Rule objects
        """
        self.validation_errors.clear()
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            return self.parse_rules(content, source_file=file_path)
            
        except FileNotFoundError:
            self.validation_errors.append(ValidationError(
                rule_id="file_error",
                error_type="file_not_found",
                message=f"File not found: {file_path}"
            ))
            return []
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id="file_error",
                error_type="file_read_error",
                message=f"Error reading file {file_path}: {str(e)}"
            ))
            return []
    
    def parse_rules(self, yaml_data: Union[str, Dict[str, Any]], source_file: Optional[str] = None) -> List[Rule]:
        """Parse rules from YAML data supporting multiple formats.
        
        Supports both standard format and if/then format:
        
        Standard format:
        ```yaml
        rules:
          - id: "rule1"
            conditions: [...]
            conclusions: [...]
        ```
        
        If/then format:
        ```yaml
        rule:
          name: "rule1"
          if:
            all: [...]
            any: [...]
          then:
            field: value
        ```
        
        Args:
            yaml_data: YAML string or dictionary containing rule definitions
            source_file: Optional source file name for error reporting
            
        Returns:
            List of parsed Rule objects
        """
        self.validation_errors.clear()
        
        if isinstance(yaml_data, str):
            try:
                data = yaml.safe_load(yaml_data)
            except yaml.YAMLError as e:
                self.validation_errors.append(ValidationError(
                    rule_id="parse_error",
                    error_type="yaml_parse_error",
                    message=f"Invalid YAML: {str(e)}"
                ))
                return []
        else:
            data = yaml_data
        
        if not isinstance(data, dict):
            self.validation_errors.append(ValidationError(
                rule_id="format_error",
                error_type="invalid_format",
                message="YAML must contain a dictionary"
            ))
            return []
        
        rules = []
        
        # Handle if/then format (single rule)
        if "rule" in data and "if" in data["rule"]:
            rule = self._parse_if_then_rule(data["rule"], source_file, 0)
            if rule:
                rules.append(rule)
        
        # Handle standard multiple rules format
        elif "rules" in data:
            for i, rule_data in enumerate(data["rules"]):
                if "if" in rule_data:
                    rule = self._parse_if_then_rule(rule_data, source_file, i)
                else:
                    rule = self._parse_standard_rule(rule_data, i)
                if rule:
                    rules.append(rule)
        
        # Handle standard single rule format
        elif "rule" in data:
            rule = self._parse_standard_rule(data["rule"], 0)
            if rule:
                rules.append(rule)
        
        else:
            self.validation_errors.append(ValidationError(
                rule_id="format_error",
                error_type="missing_rules",
                message="YAML must contain 'rules' or 'rule' key"
            ))
        
        return rules

    def _parse_if_then_rule(self, rule_data: Dict[str, Any], source_file: Optional[str] = None, index: int = 0) -> Optional[Rule]:
        """Parse a rule in if/then format."""
        rule_name = rule_data.get("name", f"rule_{index}")
        rule_id = f"{Path(source_file).stem}_{rule_name}" if source_file else rule_name
        
        try:
            # Parse the 'if' section to create conditions
            if_section = rule_data.get("if", {})
            conditions = self._parse_if_section(if_section, rule_id)
            
            if not conditions:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="empty_conditions",
                    message="Rule has no valid conditions"
                ))
                return None
            
            # Parse the 'then' section to create conclusions
            then_section = rule_data.get("then", {})
            conclusions = self._parse_then_section(then_section, rule_id)
            
            if not conclusions:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="empty_conclusions",
                    message="Rule has no valid conclusions"
                ))
                return None
            
            # Extract metadata from rule_data (all fields except the structural ones)
            rule_metadata = {
                "name": rule_name,
                "source_file": source_file or "unknown", 
                "format": "if_then"
            }
            
            # Add any additional fields from the rule as metadata
            excluded_fields = {"name", "if", "then", "priority", "enabled", "metadata"}
            for key, value in rule_data.items():
                if key not in excluded_fields:
                    rule_metadata[key] = value
            
            # Add explicit metadata if present
            if "metadata" in rule_data:
                rule_metadata.update(rule_data["metadata"])
            
            # Create the rule
            rule = Rule(
                id=rule_id,
                conditions=conditions,
                conclusions=conclusions,
                priority=rule_data.get("priority", 0),
                enabled=rule_data.get("enabled", True),
                metadata=rule_metadata
            )
            
            return rule
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="parse_error",
                message=f"Error parsing if/then rule: {str(e)}"
            ))
            return None

    def _parse_standard_rule(self, rule_data: Dict[str, Any], index: int) -> Optional[Rule]:
        """Parse a rule in standard format."""
        rule_id = rule_data.get("id", f"rule_{index}")
        
        try:
            # Parse conditions
            conditions = []
            for cond_data in rule_data.get("conditions", []):
                condition = self._parse_condition(cond_data, rule_id)
                if condition:
                    conditions.append(condition)
            
            # Parse conclusions
            conclusions = []
            for concl_data in rule_data.get("conclusions", []):
                conclusion = self._parse_conclusion(concl_data, rule_id)
                if conclusion:
                    conclusions.append(conclusion)
            
            if not conditions:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="empty_conditions",
                    message="Rule has no valid conditions"
                ))
                return None
            
            if not conclusions:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="empty_conclusions", 
                    message="Rule has no valid conclusions"
                ))
                return None
            
            rule = Rule(
                id=rule_id,
                conditions=conditions,
                conclusions=conclusions,
                priority=rule_data.get("priority", 0),
                metadata={
                    "format": "standard",
                    **rule_data.get("metadata", {})
                },
                enabled=rule_data.get("enabled", True)
            )
            
            return rule
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="parse_error",
                message=f"Error parsing standard rule: {str(e)}"
            ))
            return None

    def _parse_if_section(self, if_section: Dict[str, Any], rule_id: str) -> List[Condition]:
        """Parse the 'if' section with all/any logic."""
        conditions = []
        
        # Handle 'all' conditions (AND logic)
        if "all" in if_section:
            all_conditions = if_section["all"]
            for condition_str in all_conditions:
                condition = self._parse_condition_string(condition_str, rule_id)
                if condition:
                    # Mark as 'all' type for logical grouping
                    condition.metadata["logic_type"] = "all"
                    conditions.append(condition)
        
        # Handle 'any' conditions (OR logic) 
        if "any" in if_section:
            any_conditions = if_section["any"]
            for condition_str in any_conditions:
                condition = self._parse_condition_string(condition_str, rule_id)
                if condition:
                    # Mark as 'any' type for logical grouping
                    condition.metadata["logic_type"] = "any"
                    conditions.append(condition)
        
        # Handle direct conditions (for backward compatibility)
        for key, value in if_section.items():
            if key not in ["all", "any"]:
                condition = Condition(
                    field=key,
                    operator=OperatorType.EQ,
                    value=value,
                    metadata={"logic_type": "direct"}
                )
                conditions.append(condition)
        
        return conditions

    def _parse_condition_string(self, condition_str: str, rule_id: str) -> Optional[Condition]:
        """Parse a condition string like 'cpu_utilization > 90'."""
        try:
            # Remove outer quotes if present
            condition_str = condition_str.strip()
            while ((condition_str.startswith('"') and condition_str.endswith('"')) or 
                   (condition_str.startswith("'") and condition_str.endswith("'"))):
                condition_str = condition_str[1:-1]
            
            # Try to match different operator patterns
            for op_str, op_type in self.operator_mapping.items():
                if op_str in condition_str:
                    parts = condition_str.split(op_str, 1)
                    if len(parts) == 2:
                        field = parts[0].strip()
                        value_str = parts[1].strip()
                        
                        # Try to convert value to appropriate type
                        value = self._convert_value(value_str)
                        
                        return Condition(
                            field=field,
                            operator=op_type,
                            value=value,
                            metadata={"original_condition": condition_str}
                        )
            
            # If no operator found, treat as existence check
            return Condition(
                field=condition_str,
                operator=OperatorType.EXISTS,
                value=True,
                metadata={"original_condition": condition_str}
            )
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="condition_parse_error",
                message=f"Error parsing condition '{condition_str}': {str(e)}"
            ))
            return None

    def _parse_condition(self, cond_data: Dict[str, Any], rule_id: str) -> Optional[Condition]:
        """Parse a single condition from dictionary data (standard format)."""
        try:
            field = cond_data.get("field")
            operator_str = cond_data.get("operator")
            value = cond_data.get("value")
            
            if not all([field, operator_str, value is not None]):
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="incomplete_condition",
                    message="Condition missing required fields: field, operator, value"
                ))
                return None
            
            # Convert operator string to OperatorType
            try:
                operator = OperatorType(operator_str)
            except ValueError:
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="invalid_operator",
                    message=f"Unknown operator: {operator_str}"
                ))
                return None
            
            condition = Condition(
                field=field,
                operator=operator,
                value=value,
                metadata=cond_data.get("metadata", {})
            )
            
            return condition
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="condition_parse_error",
                message=f"Error parsing condition: {str(e)}"
            ))
            return None

    def _convert_value(self, value_str: str) -> Any:
        """Convert string value to appropriate Python type."""
        value_str = value_str.strip()
        
        # Remove quotes if present (handle nested quotes)
        while ((value_str.startswith('"') and value_str.endswith('"')) or 
               (value_str.startswith("'") and value_str.endswith("'"))):
            value_str = value_str[1:-1]
        
        # Try integer
        try:
            return int(value_str)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value_str)
        except ValueError:
            pass
        
        # Try boolean
        if value_str.lower() in ['true', 'false']:
            return value_str.lower() == 'true'
        
        # Handle list format for 'in' operator
        if value_str.startswith('[') and value_str.endswith(']'):
            try:
                # Parse as list
                import ast
                return ast.literal_eval(value_str)
            except (ValueError, SyntaxError):
                pass
        
        return value_str

    def _parse_then_section(self, then_section: Dict[str, Any], rule_id: str) -> List[Conclusion]:
        """Parse the 'then' section to create conclusions."""
        if not then_section:
            return []
        
        conclusions = []
        
        # For each key-value pair in the then section, create a conclusion
        for key, value in then_section.items():
            # Extract confidence if specified, otherwise default to 1.0
            confidence = 1.0
            metadata = {}
            
            # Special handling for known fields
            if key == "confidence":
                continue  # Skip, will be handled separately
            elif key == "metadata":
                continue  # Skip, will be handled separately
            
            # If this is the confidence field, use it for all conclusions
            if "confidence" in then_section:
                confidence = then_section["confidence"]
            
            # Include other fields as metadata
            metadata = {k: v for k, v in then_section.items() 
                       if k not in [key, "confidence"]}
            
            # Create a fact for this conclusion
            fact = Fact(
                key=key,
                value=value,
                metadata=metadata,
                confidence=confidence
            )
            
            # Create the conclusion
            conclusion = Conclusion(
                fact=fact,
                confidence=confidence,
                rule_id=rule_id,
                metadata=metadata
            )
            
            conclusions.append(conclusion)
        
        return conclusions

    def _parse_conclusion(self, concl_data: Dict[str, Any], rule_id: str) -> Optional[Conclusion]:
        """Parse a single conclusion from dictionary data (standard format)."""
        try:
            field = concl_data.get("field")
            value = concl_data.get("value")
            confidence = concl_data.get("confidence", 1.0)
            
            if not all([field, value is not None]):
                self.validation_errors.append(ValidationError(
                    rule_id=rule_id,
                    error_type="incomplete_conclusion",
                    message="Conclusion missing required fields: field, value"
                ))
                return None
            
            # Create fact for the conclusion
            fact = Fact(
                key=field,
                value=value,
                metadata=concl_data.get("metadata", {}),
                confidence=confidence
            )
            
            conclusion = Conclusion(
                fact=fact,
                confidence=confidence,
                rule_id=rule_id,
                metadata=concl_data.get("metadata", {})
            )
            
            return conclusion
            
        except Exception as e:
            self.validation_errors.append(ValidationError(
                rule_id=rule_id,
                error_type="conclusion_parse_error",
                message=f"Error parsing conclusion: {str(e)}"
            ))
            return None
    
    def serialize_rules(self, rules: List[Rule]) -> str:
        """Serialize rules to YAML string.
        
        Args:
            rules: List of Rule objects to serialize
            
        Returns:
            YAML string representation of the rules
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
                        "field": concl.fact.key,
                        "value": concl.fact.value,
                        "confidence": concl.confidence,
                        "metadata": concl.metadata
                    }
                    for concl in rule.conclusions
                ]
            }
            rules_data.append(rule_data)
        
        return yaml.dump({"rules": rules_data}, default_flow_style=False, sort_keys=False)
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get validation errors from the last parse operation."""
        return self.validation_errors.copy()


class YAMLFactParser:
    """Parser for facts in YAML format."""
    
    def __init__(self):
        """Initialize the YAML fact parser."""
        self.validation_errors: List[ValidationError] = []
    
    def parse_facts(self, yaml_data: Union[str, Dict[str, Any]]) -> List[Fact]:
        """Parse facts from YAML data.
        
        Args:
            yaml_data: YAML string or dictionary containing fact definitions
            
        Returns:
            List of parsed Fact objects
        """
        self.validation_errors.clear()
        
        if isinstance(yaml_data, str):
            try:
                data = yaml.safe_load(yaml_data)
            except yaml.YAMLError as e:
                self.validation_errors.append(ValidationError(
                    rule_id="parse_error",
                    error_type="yaml_parse_error",
                    message=f"Invalid YAML: {str(e)}"
                ))
                return []
        else:
            data = yaml_data
        
        facts = []
        
        if isinstance(data, dict):
            if "facts" in data:
                # Structured format with facts section
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
                    if isinstance(value, dict) and "value" in value:
                        # Extended format with metadata
                        fact = Fact(
                            key=key,
                            value=value["value"],
                            metadata=value.get("metadata", {}),
                            confidence=value.get("confidence", 1.0)
                        )
                    else:
                        # Simple value
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
                    if isinstance(timestamp_str, datetime):
                        timestamp = timestamp_str
                    else:
                        timestamp = datetime.fromisoformat(str(timestamp_str))
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
        """Serialize facts to YAML string.
        
        Args:
            facts: List of Fact objects to serialize
            
        Returns:
            YAML string representation of the facts
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
        
        return yaml.dump({"facts": facts_data}, default_flow_style=False, sort_keys=False)
    
    def get_validation_errors(self) -> List[ValidationError]:
        """Get validation errors from the last parse operation."""
        return self.validation_errors.copy()


# Helper functions for working with rules in any domain
def create_facts_from_metrics(metrics: Dict[str, Any]) -> List[Fact]:
    """Create facts from a metrics dictionary.
    
    Args:
        metrics: Dictionary of metric name -> value
        
    Returns:
        List of Fact objects
    """
    facts = []
    for key, value in metrics.items():
        fact = Fact(
            key=key,
            value=value,
            metadata={"source": "metrics", "type": "measurement"}
        )
        facts.append(fact)
    return facts


def load_rules_from_folder(folder_path: str) -> tuple[List[Rule], List[ValidationError]]:
    """Load rules from a folder using the YAML parser.
    
    Args:
        folder_path: Path to folder containing rule YAML files
        
    Returns:
        Tuple of (rules, validation_errors)
    """
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(folder_path)
    errors = parser.get_validation_errors()
    return rules, errors


# Example YAML formats
EXAMPLE_RULES_YAML = """
rules:
  - id: server_down_alert
    priority: 10
    enabled: true
    metadata:
      category: infrastructure
      severity: high
    conditions:
      - field: status
        operator: "=="
        value: down
      - field: entity_type
        operator: "=="
        value: server
    conclusions:
      - key: alert_severity
        value: high
        confidence: 0.9
        metadata:
          reason: "Server down condition met"

  - id: network_issue_rule
    priority: 5
    conditions:
      # Alternative object syntax for conditions
      status:
        operator: "=="
        value: unreachable
      type: network_device
    conclusions:
      - key: network_alert
        value: true
        confidence: 0.8
"""

EXAMPLE_FACTS_YAML = """
facts:
  - key: server_1_status
    value: down
    metadata:
      location: datacenter_1
      last_ping: "2024-01-01T10:00:00Z"
    confidence: 1.0
    timestamp: "2024-01-01T10:00:00Z"
  
  - key: server_1_type
    value: web_server
    metadata:
      role: frontend
    confidence: 1.0

# Alternative simple format
# server_2_status: up
# server_2_type: database
""" 