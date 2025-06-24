"""Tests for RuleEngine functionality and tracing."""

import pytest
from symbolica import FactStore, RuleEngine, Inference
from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType, ValidationError


class TestRuleEngine:
    """Test RuleEngine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.facts = FactStore()
        self.engine = RuleEngine()
    
    def test_add_rule(self):
        """Test adding rules to the engine."""
        rule = Rule(
            id="test_rule",
            conditions=[
                Condition(field="status", operator=OperatorType.EQ, value="active")
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="result", value="passed"),
                    confidence=1.0,
                    rule_id="test_rule"
                )
            ]
        )
        
        self.engine.add_rule(rule)
        
        assert len(self.engine) == 1
        assert self.engine.has_rule("test_rule")
        assert "test_rule" in self.engine
    
    def test_remove_rule(self):
        """Test removing rules from the engine."""
        rule = Rule(
            id="remove_test",
            conditions=[Condition(field="test", operator=OperatorType.EQ, value="value")],
            conclusions=[Conclusion(fact=Fact(key="test", value="result"), confidence=1.0, rule_id="remove_test")]
        )
        
        self.engine.add_rule(rule)
        assert self.engine.has_rule("remove_test")
        
        removed = self.engine.remove_rule("remove_test")
        assert removed is True
        assert not self.engine.has_rule("remove_test")
        
        # Test removing non-existent rule
        removed = self.engine.remove_rule("non_existent")
        assert removed is False
    
    def test_simple_rule_evaluation(self):
        """Test basic rule evaluation."""
        # Add facts
        self.facts.add("temperature", 85)
        self.facts.add("humidity", 70)
        
        # Create rule
        rule = Rule(
            id="heat_warning",
            conditions=[
                Condition(field="temperature", operator=OperatorType.GT, value=80)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="warning", value="high_temperature"),
                    confidence=0.9,
                    rule_id="heat_warning"
                )
            ]
        )
        
        self.engine.add_rule(rule)
        conclusions = self.engine.evaluate(self.facts)
        
        assert len(conclusions) == 1
        assert conclusions[0].fact.key == "warning"
        assert conclusions[0].fact.value == "high_temperature"
        assert conclusions[0].confidence == 0.9
    
    def test_multiple_conditions_all_logic(self):
        """Test rule with multiple conditions (ALL logic)."""
        self.facts.add("age", 25)
        self.facts.add("income", 75000)
        self.facts.add("credit_score", 750)
        
        rule = Rule(
            id="loan_approval",
            conditions=[
                Condition(field="age", operator=OperatorType.GTE, value=21),
                Condition(field="income", operator=OperatorType.GT, value=50000),
                Condition(field="credit_score", operator=OperatorType.GTE, value=700)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="loan_approved", value=True),
                    confidence=0.95,
                    rule_id="loan_approval"
                )
            ]
        )
        
        self.engine.add_rule(rule)
        conclusions = self.engine.evaluate(self.facts)
        
        assert len(conclusions) == 1
        assert conclusions[0].fact.value is True
    
    def test_multiple_conditions_any_logic(self):
        """Test rule with ANY logic conditions."""
        self.facts.add("emergency_type", "fire")
        self.facts.add("priority", "low")
        
        rule = Rule(
            id="emergency_response",
            conditions=[
                Condition(
                    field="emergency_type", 
                    operator=OperatorType.EQ, 
                    value="fire",
                    metadata={"logic_type": "any"}
                ),
                Condition(
                    field="emergency_type", 
                    operator=OperatorType.EQ, 
                    value="flood",
                    metadata={"logic_type": "any"}
                ),
                Condition(
                    field="priority", 
                    operator=OperatorType.EQ, 
                    value="high",
                    metadata={"logic_type": "any"}
                )
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="response_required", value=True),
                    confidence=1.0,
                    rule_id="emergency_response"
                )
            ]
        )
        
        self.engine.add_rule(rule)
        conclusions = self.engine.evaluate(self.facts)
        
        assert len(conclusions) == 1
        assert conclusions[0].fact.value is True
    
    def test_rule_priority_ordering(self):
        """Test that rules are evaluated in priority order."""
        self.facts.add("value", 100)
        
        # Low priority rule
        rule1 = Rule(
            id="low_priority",
            priority=1,
            conditions=[Condition(field="value", operator=OperatorType.GT, value=50)],
            conclusions=[
                Conclusion(
                    fact=Fact(key="priority_test", value="low"),
                    confidence=1.0,
                    rule_id="low_priority"
                )
            ]
        )
        
        # High priority rule
        rule2 = Rule(
            id="high_priority",
            priority=10,
            conditions=[Condition(field="value", operator=OperatorType.GT, value=50)],
            conclusions=[
                Conclusion(
                    fact=Fact(key="priority_test", value="high"),
                    confidence=1.0,
                    rule_id="high_priority"
                )
            ]
        )
        
        # Add in reverse priority order
        self.engine.add_rule(rule1)
        self.engine.add_rule(rule2)
        
        conclusions = self.engine.evaluate(self.facts)
        
        # Higher priority rule should fire first
        assert len(conclusions) >= 1
        # Due to duplicate prevention, we should get unique conclusions
        conclusion_values = [c.fact.value for c in conclusions]
        assert "high" in conclusion_values
    
    def test_rule_validation(self):
        """Test rule validation functionality."""
        # Valid rule
        valid_rule = Rule(
            id="valid",
            conditions=[Condition(field="test", operator=OperatorType.EQ, value="value")],
            conclusions=[Conclusion(fact=Fact(key="result", value="ok"), confidence=1.0, rule_id="valid")]
        )
        
        self.engine.add_rule(valid_rule)
        errors = self.engine.validate_rules()
        assert len(errors) == 0
        
        # Add duplicate rule
        duplicate_rule = Rule(
            id="valid",  # Same ID
            conditions=[Condition(field="test2", operator=OperatorType.EQ, value="value2")],
            conclusions=[Conclusion(fact=Fact(key="result2", value="ok2"), confidence=1.0, rule_id="valid")]
        )
        
        self.engine.add_rule(duplicate_rule)  # Will replace the first one
        errors = self.engine.validate_rules()
        assert len(errors) == 0  # No duplicates after replacement
    
    def test_engine_statistics(self):
        """Test engine statistics and performance metrics."""
        rule = Rule(
            id="stats_test",
            conditions=[Condition(field="value", operator=OperatorType.GT, value=0)],
            conclusions=[Conclusion(fact=Fact(key="result", value="positive"), confidence=1.0, rule_id="stats_test")]
        )
        
        self.engine.add_rule(rule)
        self.facts.add("value", 10)
        
        # Run evaluation to generate statistics
        self.engine.evaluate(self.facts)
        
        stats = self.engine.get_statistics()
        
        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert "total_evaluations" in stats
        assert "total_rules_fired" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "optimization_features" in stats
        
        assert stats["total_rules"] == 1
        assert stats["enabled_rules"] == 1
        assert stats["total_evaluations"] >= 1
    
    def test_disabled_rules(self):
        """Test that disabled rules are not evaluated."""
        self.facts.add("test", "value")
        
        rule = Rule(
            id="disabled_rule",
            conditions=[Condition(field="test", operator=OperatorType.EQ, value="value")],
            conclusions=[Conclusion(fact=Fact(key="result", value="fired"), confidence=1.0, rule_id="disabled_rule")],
            enabled=False
        )
        
        self.engine.add_rule(rule)
        conclusions = self.engine.evaluate(self.facts)
        
        assert len(conclusions) == 0
    
    def test_clear_engine(self):
        """Test clearing all rules from the engine."""
        rule = Rule(
            id="clear_test",
            conditions=[Condition(field="test", operator=OperatorType.EQ, value="value")],
            conclusions=[Conclusion(fact=Fact(key="result", value="ok"), confidence=1.0, rule_id="clear_test")]
        )
        
        self.engine.add_rule(rule)
        assert len(self.engine) == 1
        
        self.engine.clear()
        assert len(self.engine) == 0
        assert not self.engine.has_rule("clear_test")


class TestInferenceTracing:
    """Test detailed inference tracing functionality."""
    
    def test_inference_with_trace(self):
        """Test inference with detailed tracing."""
        facts = FactStore()
        facts.add("temperature", 95)
        facts.add("humidity", 85)
        
        rule = Rule(
            id="heat_alert",
            conditions=[
                Condition(field="temperature", operator=OperatorType.GT, value=90),
                Condition(field="humidity", operator=OperatorType.GT, value=80)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="alert", value="extreme_heat"),
                    confidence=0.95,
                    rule_id="heat_alert"
                )
            ],
            metadata={"name": "Extreme Heat Alert"}
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Check that tracing occurred
        assert result.trace is not None
        assert len(result.trace.steps) > 0
        
        step = result.trace.steps[0]
        assert step.rule_applied.id == "heat_alert"
        assert len(step.condition_evaluations) == 2
        assert step.reasoning_explanation != ""
        
        # Check condition evaluations
        temp_eval = next(e for e in step.condition_evaluations if "temperature" in e.condition_text)
        assert temp_eval.result is True
        assert temp_eval.actual_value == 95
        assert temp_eval.expected_value == 90
        assert "SATISFIED" in temp_eval.explanation
        
        humidity_eval = next(e for e in step.condition_evaluations if "humidity" in e.condition_text)
        assert humidity_eval.result is True
        assert humidity_eval.actual_value == 85
        assert humidity_eval.expected_value == 80
        assert "SATISFIED" in humidity_eval.explanation
    
    def test_reasoning_explanation_generation(self):
        """Test automatic reasoning explanation generation."""
        facts = FactStore()
        facts.add("score", 850)
        
        rule = Rule(
            id="credit_excellent",
            conditions=[
                Condition(field="score", operator=OperatorType.GTE, value=800)
            ],
            conclusions=[
                Conclusion(
                    fact=Fact(key="credit_rating", value="excellent"),
                    confidence=1.0,
                    rule_id="credit_excellent",
                    metadata={"benefits": ["low_interest", "high_limit"]}
                )
            ],
            metadata={"name": "Excellent Credit Score"}
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        step = result.trace.steps[0]
        explanation = step.get_explanation()
        
        assert "Applied rule: 'Excellent Credit Score'" in explanation
        assert "✓ score (850) is greater than or equal to 800 - SATISFIED" in explanation
        assert "Therefore concluded:" in explanation
        assert "credit_rating = excellent" in explanation
    
    def test_trace_performance_metrics(self):
        """Test trace performance metrics."""
        facts = FactStore()
        facts.add("value1", 10)
        facts.add("value2", 20)
        
        rule1 = Rule(
            id="rule1",
            conditions=[Condition(field="value1", operator=OperatorType.GT, value=5)],
            conclusions=[Conclusion(fact=Fact(key="result1", value="ok"), confidence=1.0, rule_id="rule1")]
        )
        
        rule2 = Rule(
            id="rule2", 
            conditions=[Condition(field="value2", operator=OperatorType.GT, value=15)],
            conclusions=[Conclusion(fact=Fact(key="result2", value="ok"), confidence=1.0, rule_id="rule2")]
        )
        
        engine = RuleEngine([rule1, rule2])
        inference = Inference(engine)
        result = inference.run(facts)
        
        trace = result.trace
        
        assert trace.total_rules_fired >= 2
        assert trace.total_conclusions_drawn >= 2
        assert trace.average_step_time_ms >= 0
        assert trace.total_execution_time_ms > 0
        
        # Check rule usage stats
        usage_stats = trace.get_rule_usage_stats()
        assert "rule1" in usage_stats
        assert "rule2" in usage_stats
    
    def test_trace_json_serialization(self):
        """Test trace JSON serialization."""
        facts = FactStore()
        facts.add("amount", 1000)
        
        rule = Rule(
            id="amount_check",
            conditions=[Condition(field="amount", operator=OperatorType.GT, value=500)],
            conclusions=[Conclusion(fact=Fact(key="status", value="high"), confidence=0.8, rule_id="amount_check")]
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Test trace to_dict
        trace_dict = result.trace.to_dict()
        assert "steps" in trace_dict
        assert "final_conclusions" in trace_dict
        assert "reasoning_summary" in trace_dict
        
        # Test trace to_json
        trace_json = result.trace.to_json()
        import json
        parsed = json.loads(trace_json)
        assert isinstance(parsed, dict)
        assert "steps" in parsed
    
    def test_duplicate_rule_prevention(self):
        """Test that duplicate rule firing is prevented."""
        facts = FactStore()
        facts.add("value", 100)
        
        # Rule that could potentially fire multiple times
        rule = Rule(
            id="duplicate_test",
            conditions=[Condition(field="value", operator=OperatorType.GT, value=50)],
            conclusions=[Conclusion(fact=Fact(key="result", value="fired"), confidence=1.0, rule_id="duplicate_test")]
        )
        
        engine = RuleEngine([rule])
        inference = Inference(engine)
        result = inference.run(facts, max_iterations=10)
        
        # Should not fire the same rule multiple times for the same facts
        unique_conclusions = result.unique_conclusions
        assert len(unique_conclusions) == 1
        
        # Check that duplicate prevention is working
        stats = engine.get_statistics()
        assert "duplicate_prevention" in stats["optimization_features"]


class TestComplexRuleScenarios:
    """Test complex rule scenarios and edge cases."""
    
    def test_chained_rule_inference(self):
        """Test rules that trigger other rules in sequence."""
        facts = FactStore()
        facts.add("initial_value", 10)
        
        # Rule 1: Transform initial value
        rule1 = Rule(
            id="transform_rule",
            conditions=[Condition(field="initial_value", operator=OperatorType.GT, value=5)],
            conclusions=[Conclusion(fact=Fact(key="transformed_value", value=20), confidence=1.0, rule_id="transform_rule")]
        )
        
        # Rule 2: Use transformed value
        rule2 = Rule(
            id="final_rule",
            conditions=[Condition(field="transformed_value", operator=OperatorType.GT, value=15)],
            conclusions=[Conclusion(fact=Fact(key="final_result", value="success"), confidence=1.0, rule_id="final_rule")]
        )
        
        engine = RuleEngine([rule1, rule2])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Should have conclusions from both rules
        conclusion_keys = [c.fact.key for c in result.conclusions]
        assert "transformed_value" in conclusion_keys
        assert "final_result" in conclusion_keys
        
        # Check trace shows both steps
        assert len(result.trace.steps) >= 2
    
    def test_conflicting_rules_resolution(self):
        """Test handling of potentially conflicting rules."""
        facts = FactStore()
        facts.add("score", 75)
        
        # Rule 1: Score > 70 = good
        rule1 = Rule(
            id="good_score",
            priority=5,
            conditions=[Condition(field="score", operator=OperatorType.GT, value=70)],
            conclusions=[Conclusion(fact=Fact(key="rating", value="good"), confidence=0.8, rule_id="good_score")]
        )
        
        # Rule 2: Score < 80 = fair
        rule2 = Rule(
            id="fair_score", 
            priority=3,
            conditions=[Condition(field="score", operator=OperatorType.LT, value=80)],
            conclusions=[Conclusion(fact=Fact(key="rating", value="fair"), confidence=0.7, rule_id="fair_score")]
        )
        
        engine = RuleEngine([rule1, rule2])
        inference = Inference(engine)
        result = inference.run(facts)
        
        # Higher priority rule should fire first
        conclusions = result.conclusions
        assert len(conclusions) >= 1
        
        # Check that both rules can fire (they're not truly conflicting, just different conclusions)
        rating_values = [c.fact.value for c in conclusions if c.fact.key == "rating"]
        assert len(rating_values) >= 1 