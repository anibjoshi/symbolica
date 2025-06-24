"""Tests for rule parsers functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from symbolica.parsers.yaml_parser import YAMLRuleParser
from symbolica.core.types import Rule, OperatorType


class TestYAMLParser:
    """Test YAML rule parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = YAMLRuleParser()
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_simple_rule_file(self):
        """Test parsing a simple YAML rule file."""
        rule_content = """
rule:
  name: "simple test rule"
  if:
    all:
      - "value > 100"
  then:
    diagnosis: true
    tags:
      - "high_value"
"""
        
        rule_file = Path(self.temp_dir) / "simple_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        assert rule.metadata.get("name") == "simple test rule"
        assert len(rule.conditions) == 1
        assert rule.conditions[0].field == "value"
        assert rule.conditions[0].operator == OperatorType.GT
        assert rule.conditions[0].value == 100
    
    def test_parse_multiple_conditions(self):
        """Test parsing rules with multiple conditions."""
        rule_content = """
rule:
  name: "multi condition rule"
  if:
    all:
      - "temperature > 90"
      - "humidity > 80"
      - "pressure < 1000"
  then:
    diagnosis: true
    tags:
      - "weather_alert"
"""
        
        rule_file = Path(self.temp_dir) / "multi_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        assert len(rule.conditions) == 3
        
        # Check each condition
        temp_condition = next(c for c in rule.conditions if c.field == "temperature")
        assert temp_condition.operator == OperatorType.GT
        assert temp_condition.value == 90
        
        humidity_condition = next(c for c in rule.conditions if c.field == "humidity")
        assert humidity_condition.operator == OperatorType.GT
        assert humidity_condition.value == 80
        
        pressure_condition = next(c for c in rule.conditions if c.field == "pressure")
        assert pressure_condition.operator == OperatorType.LT
        assert pressure_condition.value == 1000
    
    def test_parse_any_logic_conditions(self):
        """Test parsing rules with ANY logic conditions."""
        rule_content = """
rule:
  name: "any logic rule"
  if:
    any:
      - "priority == 'high'"
      - "urgent == true"
      - "emergency_type == 'fire'"
  then:
    diagnosis: true
    tags:
      - "immediate_response"
"""
        
        rule_file = Path(self.temp_dir) / "any_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        assert len(rule.conditions) == 3
        
        # All conditions should have "any" logic type
        for condition in rule.conditions:
            assert condition.metadata.get("logic_type") == "any"
    
    def test_parse_mixed_logic_conditions(self):
        """Test parsing rules with both ALL and ANY conditions."""
        rule_content = """
rule:
  name: "mixed logic rule"
  if:
    all:
      - "amount > 50000"
      - "account_active == true"
    any:
      - "customer_type == 'premium'"
      - "loyalty_years >= 5"
  then:
    diagnosis: true
    tags:
      - "special_processing"
"""
        
        rule_file = Path(self.temp_dir) / "mixed_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        assert len(rule.conditions) == 4
        
        # Check that logic types are set correctly
        all_conditions = [c for c in rule.conditions if c.metadata.get("logic_type") == "all"]
        any_conditions = [c for c in rule.conditions if c.metadata.get("logic_type") == "any"]
        
        assert len(all_conditions) == 2
        assert len(any_conditions) == 2
    
    def test_parse_rules_from_folder(self):
        """Test parsing multiple rules from a folder."""
        # Create multiple rule files
        rule1_content = """
rule:
  name: "rule one"
  if:
    all:
      - "value1 > 10"
  then:
    diagnosis: true
    tags: ["tag1"]
"""
        
        rule2_content = """
rule:
  name: "rule two"
  if:
    all:
      - "value2 < 20"
  then:
    diagnosis: false
    tags: ["tag2"]
"""
        
        (Path(self.temp_dir) / "rule1.yaml").write_text(rule1_content)
        (Path(self.temp_dir) / "rule2.yaml").write_text(rule2_content)
        
        rules = self.parser.parse_rules_from_folder(self.temp_dir)
        
        assert len(rules) == 2
        rule_names = [rule.metadata.get("name") for rule in rules]
        assert "rule one" in rule_names
        assert "rule two" in rule_names
    
    def test_parse_string_conditions(self):
        """Test parsing various string-based conditions."""
        rule_content = """
rule:
  name: "string conditions test"
  if:
    all:
      - "status == 'active'"
      - "category in ['premium', 'gold', 'platinum']"
      - "description contains 'urgent'"
  then:
    diagnosis: true
    tags: ["string_test"]
"""
        
        rule_file = Path(self.temp_dir) / "string_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        assert len(rule.conditions) == 3
        
        # Check string equality condition
        status_condition = next(c for c in rule.conditions if c.field == "status")
        assert status_condition.operator == OperatorType.EQ
        assert status_condition.value == "active"
        
        # Check membership condition
        category_condition = next(c for c in rule.conditions if c.field == "category")
        assert category_condition.operator == OperatorType.IN
        assert category_condition.value == ["premium", "gold", "platinum"]
        
        # Check contains condition
        desc_condition = next(c for c in rule.conditions if c.field == "description")
        assert desc_condition.operator == OperatorType.CONTAINS
        assert desc_condition.value == "urgent"
    
    def test_parse_boolean_conditions(self):
        """Test parsing boolean conditions."""
        rule_content = """
rule:
  name: "boolean test"
  if:
    all:
      - "is_active == true"
      - "is_deleted == false"
  then:
    diagnosis: true
    tags: ["boolean_test"]
"""
        
        rule_file = Path(self.temp_dir) / "bool_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        
        active_condition = next(c for c in rule.conditions if c.field == "is_active")
        assert active_condition.value is True
        
        deleted_condition = next(c for c in rule.conditions if c.field == "is_deleted")
        assert deleted_condition.value is False
    
    def test_error_handling_invalid_yaml(self):
        """Test error handling for invalid YAML."""
        invalid_content = """
rule:
  name: "invalid yaml
  if:
    all:
      - "value > 100"
  then:
    diagnosis: true
"""
        
        rule_file = Path(self.temp_dir) / "invalid.yaml"
        rule_file.write_text(invalid_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        # Should return empty list for invalid YAML
        assert len(rules) == 0
        
        # Check for validation errors
        errors = self.parser.get_validation_errors()
        assert len(errors) > 0
    
    def test_error_handling_missing_file(self):
        """Test error handling for missing files."""
        rules = self.parser.parse_rule_file("non_existent_file.yaml")
        
        assert len(rules) == 0
        errors = self.parser.get_validation_errors()
        assert len(errors) > 0
    
    def test_complex_rule_metadata(self):
        """Test parsing rules with complex metadata."""
        rule_content = """
rule:
  name: "complex metadata rule"
  priority: 10
  enabled: true
  description: "A rule with rich metadata"
  category: "security"
  version: "1.2.3"
  if:
    all:
      - "security_score < 50"
  then:
    diagnosis: true
    confidence: 0.85
    tags:
      - "security_risk"
      - "immediate_review"
    metadata:
      severity: "high"
      department: "security"
      auto_resolve: false
"""
        
        rule_file = Path(self.temp_dir) / "metadata_rule.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        
        # Check rule metadata
        assert rule.metadata.get("name") == "complex metadata rule"
        assert rule.metadata.get("description") == "A rule with rich metadata"
        assert rule.metadata.get("category") == "security"
        assert rule.metadata.get("version") == "1.2.3"
        assert rule.priority == 10
        assert rule.enabled is True
        
        # Check conclusion metadata
        assert len(rule.conclusions) > 0
        conclusion = rule.conclusions[0]
        assert conclusion.confidence == 0.85
        assert "security_risk" in conclusion.metadata.get("tags", [])
    
    def test_rule_id_generation(self):
        """Test automatic rule ID generation."""
        rule_content = """
rule:
  name: "auto id test rule"
  if:
    all:
      - "value > 0"
  then:
    diagnosis: true
"""
        
        rule_file = Path(self.temp_dir) / "auto-id-test.yaml"
        rule_file.write_text(rule_content)
        
        rules = self.parser.parse_rule_file(str(rule_file))
        
        assert len(rules) == 1
        rule = rules[0]
        
        # Rule ID should be generated from filename and rule name
        expected_id = "auto-id-test_auto id test rule"
        assert rule.id == expected_id
    
    def test_ignore_non_yaml_files(self):
        """Test that non-YAML files are ignored."""
        # Create YAML file
        yaml_content = """
rule:
  name: "yaml rule"
  if:
    all:
      - "value > 0"
  then:
    diagnosis: true
"""
        (Path(self.temp_dir) / "valid.yaml").write_text(yaml_content)
        
        # Create non-YAML files
        (Path(self.temp_dir) / "readme.txt").write_text("This is not a rule file")
        (Path(self.temp_dir) / "config.json").write_text('{"not": "a rule"}')
        (Path(self.temp_dir) / "script.py").write_text("print('hello')")
        
        rules = self.parser.parse_rules_from_folder(self.temp_dir)
        
        # Should only parse the YAML file
        assert len(rules) == 1
        assert rules[0].metadata.get("name") == "yaml rule" 