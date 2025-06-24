"""End-to-end integration tests for Symbolica."""

import pytest
import json
from pathlib import Path
from symbolica import FactStore, RuleEngine, Inference
from symbolica.parsers.yaml_parser import YAMLRuleParser


class TestInsuranceClaimsIntegration:
    """Test complete insurance claims processing workflow."""
    
    def test_high_value_claim_processing(self):
        """Test processing a high-value insurance claim end-to-end."""
        # Create high-value claim data
        claim_data = {
            "claim_amount": 85000,
            "policy_active": True,
            "days_since_policy_start": 14,
            "police_report_filed": False
        }
        
        # Process through Symbolica
        facts = FactStore.from_json(claim_data)
        
        # Create simple test rule
        from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType
        rule = Rule(
            id="high_value_test",
            conditions=[
                Condition(field="claim_amount", operator=OperatorType.GT, value=50000)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="requires_review", value=True),
                    confidence=1.0,
                    rule_id="high_value_test"
                )
            ]
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Verify results
        assert result.success
        assert len(result.conclusions) > 0
        
        # Check reasoning trace
        assert result.trace is not None
        assert len(result.trace.steps) > 0
        
        # Verify JSON output structure
        output = result.to_dict()
        assert "success" in output
        assert "conclusions" in output
        assert "reasoning_trace" in output
        assert "performance" in output
    
    def test_legitimate_claim_processing(self):
        """Test processing a legitimate claim that should pass all checks."""
        parser = YAMLRuleParser()
        rules_folder = Path(__file__).parent.parent.parent / "examples" / "insurance-claims"
        
        if not rules_folder.exists():
            pytest.skip("Insurance claims rules not available")
        
        rules = parser.parse_rules_from_folder(str(rules_folder))
        
        # Create legitimate claim data
        legitimate_claim = {
            "claim_amount": 15000,
            "policy_start_date": "2022-01-01", 
            "claim_date": "2024-03-15",
            "days_since_policy_start": 800,
            "claim_type": "auto_accident",
            "police_report_filed": True,
            "policy_active": True,
            "prior_claims_count": 0,
            "invoice_id": "INV-2024-NEW-001",
            "prior_claimed_invoice_ids": [],
            "beneficiary_info_complete": True,
            "pre_existing_condition": False
        }
        
        facts = FactStore.from_json(legitimate_claim)
        engine = RuleEngine(rules)
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Should have fewer or no red flags
        output = result.to_dict()
        
        # Check if any concerning issues were detected
        concerning_conclusions = [
            c for c in result.conclusions 
            if c.metadata.get("tags") and 
            any("reject" in str(tag).lower() for tag in c.metadata["tags"])
        ]
        
        # Legitimate claim should have fewer concerning issues
        assert len(concerning_conclusions) == 0 or len(concerning_conclusions) < len(result.conclusions)
    
    def test_complex_nested_json_processing(self):
        """Test processing complex nested JSON claim data."""
        parser = YAMLRuleParser()
        rules_folder = Path(__file__).parent.parent.parent / "examples" / "insurance-claims"
        
        if not rules_folder.exists():
            pytest.skip("Insurance claims rules not available")
        
        rules = parser.parse_rules_from_folder(str(rules_folder))
        
        # Complex nested claim structure
        complex_claim = {
            "claim": {
                "id": "CLM-2024-001",
                "amount": 75000,
                "type": "property_damage",
                "filed_date": "2024-02-15",
                "location": {
                    "address": "123 Main St",
                    "city": "Los Angeles", 
                    "state": "CA",
                    "risk_level": "high",
                    "crime_rate": "above_average"
                }
            },
            "policy": {
                "number": "POL-456789",
                "start_date": "2024-01-01",
                "status": "active",
                "premium": 2400,
                "deductible": 1000,
                "coverage": {
                    "property": True,
                    "liability": True,
                    "comprehensive": False
                }
            },
            "customer": {
                "id": "CUST-123",
                "age": 29,
                "credit_score": 680,
                "employment": {
                    "status": "employed",
                    "income": 65000,
                    "years": 3
                },
                "claims_history": [
                    {"date": "2022-05-10", "amount": 8000, "type": "auto"},
                    {"date": "2023-09-15", "amount": 3500, "type": "property"}
                ]
            },
            "incident": {
                "date": "2024-02-10",
                "time": "14:30",
                "weather": "clear",
                "police_report": False,
                "witnesses": 1,
                "photos_taken": True,
                "damage_assessment": {
                    "structural": "moderate",
                    "cosmetic": "minor",
                    "estimated_repair_cost": 72000
                }
            }
        }
        
        # Calculate derived fields that rules might check
        days_since_policy = 45  # Feb 15 - Jan 1
        complex_claim["days_since_policy_start"] = days_since_policy
        complex_claim["claim_amount"] = complex_claim["claim"]["amount"]
        complex_claim["police_report_filed"] = complex_claim["incident"]["police_report"]
        complex_claim["policy_active"] = complex_claim["policy"]["status"] == "active"
        complex_claim["prior_claims_count"] = len(complex_claim["customer"]["claims_history"])
        
        facts = FactStore.from_json(complex_claim)
        engine = RuleEngine(rules)
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Verify complex structure was processed
        assert len(facts) > 20  # Should have many facts from nested structure
        
        # Verify nested facts are accessible
        nested_facts = facts.query("claim.*")
        assert len(nested_facts) > 0
        
        location_facts = facts.query("policy.*")
        assert len(location_facts) > 0
        
        # Verify inference worked on complex data
        output = result.to_dict()
        assert "reasoning_trace" in output
        
        if result.conclusions:
            # Check that reasoning trace explains the nested data access
            trace_steps = output["reasoning_trace"]["steps"]
            assert len(trace_steps) > 0


class TestCrossFrameworkCompatibility:
    """Test compatibility with different data formats and frameworks."""
    
    def test_langgraph_state_compatibility(self):
        """Test compatibility with LangGraph state format."""
        # Simulate LangGraph state structure
        langgraph_state = {
            "messages": [
                {"role": "user", "content": "Process my insurance claim"},
                {"role": "assistant", "content": "I'll help you process that claim"}
            ],
            "claim_data": {
                "amount": 45000,
                "type": "home_damage",
                "policy_active": True
            },
            "processing_step": "claim_evaluation",
            "user_id": "user_123"
        }
        
        # Extract just claim data for Symbolica
        facts = FactStore.from_json(langgraph_state["claim_data"])
        
        # Create simple rule for testing
        from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType
        rule = Rule(
            id="langgraph_test",
            conditions=[
                Condition(field="amount", operator=OperatorType.GT, value=40000)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="requires_review", value=True),
                    confidence=0.9,
                    rule_id="langgraph_test"
                )
            ]
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Convert back to LangGraph-compatible format
        symbolica_results = {
            "symbolica_conclusions": result.to_dict()["unique_conclusions"],
            "reasoning_summary": result.trace.get_reasoning_summary(),
            "processing_complete": True
        }
        
        # Verify format is JSON-serializable (LangGraph requirement)
        json_output = json.dumps(symbolica_results)
        parsed_back = json.loads(json_output)
        assert isinstance(parsed_back, dict)
        assert "symbolica_conclusions" in parsed_back
    



class TestPerformanceIntegration:
    """Test performance characteristics of the full system."""
    
    def test_large_fact_set_processing(self):
        """Test processing with a large number of facts."""
        # Create large fact set
        large_data = {}
        for i in range(1000):
            large_data[f"metric_{i}"] = i * 10
            large_data[f"status_{i}"] = "active" if i % 2 == 0 else "inactive"
            large_data[f"score_{i}"] = i * 0.1
        
        facts = FactStore.from_json(large_data)
        assert len(facts) == 3000  # 3 facts per iteration
        
        # Create rules that will match some facts
        from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType
        rules = []
        for i in range(10):
            rule = Rule(
                id=f"perf_rule_{i}",
                conditions=[
                    Condition(field=f"metric_{i*100}", operator=OperatorType.GT, value=500)
                ],
                conclusions=[
                    Conclusion(
                        fact=Fact(key=f"result_{i}", value="matched"),
                        confidence=1.0,
                        rule_id=f"perf_rule_{i}"
                    )
                ]
            )
            rules.append(rule)
        
        engine = RuleEngine(rules)
        inference = Inference(engine)
        
        # Time the execution
        import time
        start_time = time.time()
        result = inference.run(facts)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert execution_time < 5.0  # 5 seconds max
        assert result.success
        
        # Check optimization is working
        stats = engine.get_statistics()
        assert stats["cache_hit_rate"] >= 0  # Should be using cache
        assert "duplicate_prevention" in stats["optimization_features"]
    
    def test_complex_rule_interaction(self):
        """Test complex scenarios with multiple interacting rules."""
        # Create facts that will trigger a chain of rules
        claim_data = {
            "base_amount": 100000,
            "location_risk": "high", 
            "customer_tier": "premium",
            "policy_age_years": 0.5,
            "has_security_system": False,
            "claim_complexity": "complex"
        }
        
        facts = FactStore.from_json(claim_data)
        
        # Create interacting rules
        from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType
        
        rules = [
            # Rule 1: High amount increases risk
            Rule(
                id="high_amount_risk",
                conditions=[
                    Condition(field="base_amount", operator=OperatorType.GT, value=75000)
                ],
                conclusions=[
                    Conclusion(
                        fact=Fact(key="risk_level", value="elevated"),
                        confidence=0.8,
                        rule_id="high_amount_risk"
                    )
                ]
            ),
            # Rule 2: Location + risk = higher scrutiny
            Rule(
                id="location_risk_combo",
                conditions=[
                    Condition(field="location_risk", operator=OperatorType.EQ, value="high"),
                    Condition(field="risk_level", operator=OperatorType.EQ, value="elevated")
                ],
                conclusions=[
                    Conclusion(
                        fact=Fact(key="scrutiny_level", value="maximum"),
                        confidence=0.9,
                        rule_id="location_risk_combo"
                    )
                ]
            ),
            # Rule 3: Premium customer gets different handling
            Rule(
                id="premium_handling",
                conditions=[
                    Condition(field="customer_tier", operator=OperatorType.EQ, value="premium"),
                    Condition(field="scrutiny_level", operator=OperatorType.EQ, value="maximum")
                ],
                conclusions=[
                    Conclusion(
                        fact=Fact(key="handling_type", value="white_glove_review"),
                        confidence=1.0,
                        rule_id="premium_handling"
                    )
                ]
            )
        ]
        
        engine = RuleEngine(rules)
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Should have conclusions from multiple rule interactions
        assert len(result.conclusions) >= 3
        
        # Check the chain of reasoning
        conclusion_keys = [c.fact.key for c in result.conclusions]
        assert "risk_level" in conclusion_keys
        assert "scrutiny_level" in conclusion_keys
        assert "handling_type" in conclusion_keys
        
        # Verify trace shows the chain
        assert len(result.trace.steps) >= 3
        
        # Check reasoning explains the interactions
        detailed_explanation = result.trace.get_detailed_explanation()
        assert "elevated" in detailed_explanation
        assert "maximum" in detailed_explanation
        assert "white_glove_review" in detailed_explanation 