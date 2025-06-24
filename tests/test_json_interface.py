"""Tests for JSON interface functionality - critical for LLM integration."""

import pytest
import json
from symbolica import FactStore, RuleEngine, Inference
from symbolica.parsers.yaml_parser import YAMLRuleParser
from symbolica.core.types import Fact


class TestJSONInterface:
    """Test JSON input/output functionality for LLM agents."""
    
    def test_factstore_from_json_dict(self):
        """Test creating FactStore from dictionary."""
        data = {
            "claim_amount": 75000,
            "policy_active": True,
            "claim_type": "theft",
            "prior_claims_count": 3
        }
        
        facts = FactStore.from_json(data)
        
        assert len(facts) == 4
        assert facts.get("claim_amount")[0].value == 75000
        assert facts.get("policy_active")[0].value is True
        assert facts.get("claim_type")[0].value == "theft"
        assert facts.get("prior_claims_count")[0].value == 3
    
    def test_factstore_from_json_string(self):
        """Test creating FactStore from JSON string."""
        json_string = '{"amount": 1000, "status": "active", "count": 5}'
        
        facts = FactStore.from_json(json_string)
        
        assert len(facts) == 3
        assert facts.get("amount")[0].value == 1000
        assert facts.get("status")[0].value == "active"
        assert facts.get("count")[0].value == 5
    
    def test_factstore_from_nested_json(self):
        """Test creating FactStore from nested JSON objects."""
        data = {
            "claim": {
                "amount": 50000,
                "type": "auto"
            },
            "policy": {
                "number": "POL123",
                "active": True
            },
            "customer": {
                "age": 35,
                "location": "CA"
            }
        }
        
        facts = FactStore.from_json(data)
        
        # Check nested facts are created with dot notation
        assert facts.get("claim.amount")[0].value == 50000
        assert facts.get("claim.type")[0].value == "auto"
        assert facts.get("policy.number")[0].value == "POL123"
        assert facts.get("policy.active")[0].value is True
        assert facts.get("customer.age")[0].value == 35
        assert facts.get("customer.location")[0].value == "CA"
    
    def test_factstore_from_json_with_arrays(self):
        """Test creating FactStore from JSON with arrays."""
        data = {
            "tags": ["high-risk", "premium"],
            "prior_claims": [
                {"amount": 1000, "year": 2022},
                {"amount": 2000, "year": 2023}
            ],
            "scores": [85, 92, 78]
        }
        
        facts = FactStore.from_json(data)
        
        # Check array elements are indexed
        assert facts.get("tags[0]")[0].value == "high-risk"
        assert facts.get("tags[1]")[0].value == "premium"
        assert facts.get("tags.length")[0].value == 2
        
        # Check nested objects in arrays
        assert facts.get("prior_claims[0].amount")[0].value == 1000
        assert facts.get("prior_claims[0].year")[0].value == 2022
        assert facts.get("prior_claims[1].amount")[0].value == 2000
        assert facts.get("prior_claims.length")[0].value == 2
        
        # Check simple arrays
        assert facts.get("scores[0]")[0].value == 85
        assert facts.get("scores[1]")[0].value == 92
        assert facts.get("scores[2]")[0].value == 78
        assert facts.get("scores.length")[0].value == 3
    
    def test_factstore_load_json_method(self):
        """Test load_json method for adding to existing FactStore."""
        facts = FactStore()
        facts.add("existing_key", "existing_value")
        
        new_data = {"new_key": "new_value", "count": 42}
        facts.load_json(new_data)
        
        assert len(facts) == 3
        assert facts.get("existing_key")[0].value == "existing_value"
        assert facts.get("new_key")[0].value == "new_value"
        assert facts.get("count")[0].value == 42
    
    def test_inference_result_to_dict(self):
        """Test InferenceResult to_dict() method."""
        # Create simple facts and rules for testing
        facts = FactStore.from_json({"claim_amount": 75000})
        
        # Create a simple rule programmatically
        from symbolica.core.types import Rule, Condition, Conclusion, OperatorType
        rule = Rule(
            id="test_rule",
            conditions=[
                Condition(field="claim_amount", operator=OperatorType.GT, value=50000)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="high_value", value=True),
                    confidence=1.0,
                    rule_id="test_rule"
                )
            ],
            metadata={"name": "High Value Test Rule"}
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Test to_dict output
        output = result.to_dict()
        
        assert "success" in output
        assert "conclusions" in output
        assert "unique_conclusions" in output
        assert "reasoning_trace" in output
        assert "performance" in output
        
        # Check reasoning trace structure
        trace = output["reasoning_trace"]
        assert "summary" in trace
        assert "detailed_explanation" in trace
        assert "steps" in trace
        assert "total_steps" in trace
        
        # Check performance metrics
        perf = output["performance"]
        assert "total_execution_time_ms" in perf
        assert "rules_fired" in perf
        assert "conclusions_drawn" in perf
    
    def test_inference_result_to_json(self):
        """Test InferenceResult to_json() method."""
        facts = FactStore.from_json({"value": 100})
        
        from symbolica.core.types import Rule, Condition, Conclusion, OperatorType
        rule = Rule(
            id="json_test_rule",
            conditions=[
                Condition(field="value", operator=OperatorType.GT, value=50)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="result", value="passed"),
                    confidence=0.9,
                    rule_id="json_test_rule"
                )
            ]
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Test JSON serialization
        json_output = result.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)
        assert "success" in parsed
        assert "conclusions" in parsed
        
        # Test without trace
        json_no_trace = result.to_json(include_trace=False)
        parsed_no_trace = json.loads(json_no_trace)
        assert "trace" not in parsed_no_trace
    
    def test_reasoning_trace_json_output(self):
        """Test detailed reasoning trace in JSON output."""
        facts = FactStore.from_json({
            "temperature": 95,
            "humidity": 80,
            "pressure": 1013
        })
        
        from symbolica.core.types import Rule, Condition, Conclusion, OperatorType
        rule = Rule(
            id="weather_rule",
            conditions=[
                Condition(field="temperature", operator=OperatorType.GT, value=90),
                Condition(field="humidity", operator=OperatorType.GT, value=70)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="weather_alert", value="high_heat_humidity"),
                    confidence=0.95,
                    rule_id="weather_rule",
                    metadata={"priority": "high", "action": "alert_issued"}
                )
            ],
            metadata={"name": "High Heat & Humidity Alert"}
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        output = result.to_dict()
        
        # Check detailed reasoning trace
        steps = output["reasoning_trace"]["steps"]
        assert len(steps) > 0
        
        step = steps[0]
        assert "step_number" in step
        assert "rule_applied" in step
        assert "condition_evaluations" in step
        assert "reasoning_explanation" in step
        
        # Check condition evaluations
        evaluations = step["condition_evaluations"]
        assert len(evaluations) == 2  # Two conditions
        
        for eval in evaluations:
            assert "condition_text" in eval
            assert "fact_matched" in eval
            assert "operator" in eval
            assert "expected_value" in eval
            assert "actual_value" in eval
            assert "result" in eval
            assert "explanation" in eval
    
    def test_json_error_handling(self):
        """Test error handling for invalid JSON."""
        # Test invalid JSON string
        with pytest.raises(json.JSONDecodeError):
            FactStore.from_json('{"invalid": json}')
        
        # Test None input
        with pytest.raises((TypeError, AttributeError)):
            FactStore.from_json(None)
    
    def test_complex_real_world_scenario(self):
        """Test complex real-world JSON scenario."""
        insurance_claim = {
            "claim": {
                "id": "CLM-2024-001",
                "amount": 85000,
                "type": "theft",
                "date_filed": "2024-01-15",
                "location": {
                    "city": "Los Angeles",
                    "state": "CA",
                    "risk_level": "high"
                }
            },
            "policy": {
                "number": "POL-123456",
                "start_date": "2024-01-01",
                "premium": 2400,
                "deductible": 1000,
                "active": True
            },
            "customer": {
                "id": "CUST-789",
                "age": 34,
                "credit_score": 720,
                "prior_claims": [
                    {"date": "2022-03-15", "amount": 5000, "type": "auto"},
                    {"date": "2023-07-20", "amount": 12000, "type": "home"}
                ],
                "risk_factors": ["young_driver", "urban_area"]
            },
            "supporting_documents": {
                "police_report": False,
                "photos": True,
                "witness_statements": 2,
                "receipts": ["receipt1.pdf", "receipt2.pdf"]
            }
        }
        
        facts = FactStore.from_json(insurance_claim)
        
        # Verify complex nested structure is properly converted
        assert facts.get("claim.amount")[0].value == 85000
        assert facts.get("claim.location.risk_level")[0].value == "high"
        assert facts.get("policy.active")[0].value is True
        assert facts.get("customer.prior_claims[0].amount")[0].value == 5000
        assert facts.get("customer.prior_claims[1].type")[0].value == "home"
        assert facts.get("customer.risk_factors[0]")[0].value == "young_driver"
        assert facts.get("supporting_documents.police_report")[0].value is False
        assert facts.get("supporting_documents.receipts[0]")[0].value == "receipt1.pdf"
        
        # Check array lengths
        assert facts.get("customer.prior_claims.length")[0].value == 2
        assert facts.get("customer.risk_factors.length")[0].value == 2
        assert facts.get("supporting_documents.receipts.length")[0].value == 2
        
        # Verify total fact count
        assert len(facts) > 20  # Should have many facts from nested structure 