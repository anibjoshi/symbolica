"""Pytest configuration and fixtures for Symbolica tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from symbolica import FactStore, RuleEngine, Inference
from symbolica.core.types import Rule, Condition, Conclusion, Fact, OperatorType


@pytest.fixture
def fact_store():
    """Create a fresh FactStore for testing."""
    return FactStore()


@pytest.fixture
def rule_engine():
    """Create a fresh RuleEngine for testing."""
    return RuleEngine()


@pytest.fixture
def sample_facts():
    """Create sample facts for testing."""
    facts = FactStore()
    facts.add("temperature", 85)
    facts.add("humidity", 70)
    facts.add("pressure", 1013)
    facts.add("status", "active")
    facts.add("value", 100)
    return facts


@pytest.fixture
def sample_rule():
    """Create a sample rule for testing."""
    return Rule(
        id="test_rule",
        conditions=[
            Condition(field="temperature", operator=OperatorType.GT, value=80)
        ],
        conclusions=[
            Conclusion(
                fact=Fact(key="alert", value="high_temperature"),
                confidence=0.9,
                rule_id="test_rule"
            )
        ],
        metadata={"name": "Temperature Alert Rule"}
    )


@pytest.fixture
def temp_directory():
    """Create a temporary directory for file-based tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def insurance_claim_data():
    """Sample insurance claim data for testing."""
    return {
        "claim_amount": 75000,
        "policy_start_date": "2024-01-01",
        "claim_date": "2024-02-15",
        "days_since_policy_start": 45,
        "claim_type": "theft",
        "location": "urban_area",
        "police_report_filed": True,
        "policy_active": True,
        "prior_claims_count": 1,
        "customer_age": 35,
        "credit_score": 720
    }


@pytest.fixture
def complex_nested_data():
    """Complex nested data structure for testing."""
    return {
        "customer": {
            "personal": {
                "name": "John Doe",
                "age": 34,
                "location": {
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94102"
                }
            },
            "financial": {
                "income": 85000,
                "credit_score": 750,
                "accounts": [
                    {"type": "checking", "balance": 5000},
                    {"type": "savings", "balance": 25000}
                ]
            }
        },
        "application": {
            "type": "loan",
            "amount": 50000,
            "purpose": "home_improvement",
            "documents": ["income_statement", "credit_report"],
            "risk_factors": ["first_time_buyer", "self_employed"]
        }
    }


@pytest.fixture
def multi_condition_rule():
    """Rule with multiple conditions for testing."""
    return Rule(
        id="multi_condition_test",
        conditions=[
            Condition(field="claim_amount", operator=OperatorType.GT, value=50000),
            Condition(field="policy_active", operator=OperatorType.EQ, value=True),
            Condition(field="days_since_policy_start", operator=OperatorType.LT, value=30)
        ],
        conclusions=[
            Conclusion(
                fact=Fact(key="requires_investigation", value=True),
                confidence=0.85,
                rule_id="multi_condition_test",
                metadata={"priority": "high", "department": "fraud"}
            )
        ],
        metadata={"name": "Early High-Value Claim Investigation"}
    )


# Test markers for categorizing tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "json: mark test as testing JSON functionality"
    )
    config.addinivalue_line(
        "markers", "tracing: mark test as testing tracing functionality"
    )


# Custom assertions for Symbolica objects
class SymbolicaAssertions:
    """Custom assertions for Symbolica testing."""
    
    @staticmethod
    def assert_fact_exists(fact_store, key, value=None):
        """Assert that a fact with the given key exists."""
        facts = fact_store.get(key)
        assert len(facts) > 0, f"No facts found with key '{key}'"
        if value is not None:
            fact_values = [f.value for f in facts]
            assert value in fact_values, f"Value '{value}' not found in facts for key '{key}'"
    
    @staticmethod
    def assert_rule_fired(inference_result, rule_id):
        """Assert that a specific rule fired during inference."""
        fired_rules = [step.rule_applied.id for step in inference_result.trace.steps]
        assert rule_id in fired_rules, f"Rule '{rule_id}' did not fire"
    
    @staticmethod
    def assert_conclusion_exists(inference_result, key, value=None):
        """Assert that a specific conclusion was drawn."""
        conclusion_keys = [c.fact.key for c in inference_result.conclusions]
        assert key in conclusion_keys, f"No conclusion found with key '{key}'"
        if value is not None:
            conclusion_values = [c.fact.value for c in inference_result.conclusions if c.fact.key == key]
            assert value in conclusion_values, f"Value '{value}' not found in conclusions for key '{key}'"
    
    @staticmethod
    def assert_trace_has_steps(inference_result, min_steps=1):
        """Assert that the reasoning trace has at least the specified number of steps."""
        actual_steps = len(inference_result.trace.steps)
        assert actual_steps >= min_steps, f"Expected at least {min_steps} trace steps, got {actual_steps}"
    
    @staticmethod
    def assert_json_serializable(obj):
        """Assert that an object is JSON serializable."""
        import json
        try:
            json.dumps(obj, default=str)
        except (TypeError, ValueError) as e:
            pytest.fail(f"Object is not JSON serializable: {e}")


@pytest.fixture
def symbolica_assertions():
    """Provide custom Symbolica assertions."""
    return SymbolicaAssertions 