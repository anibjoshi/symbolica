#!/usr/bin/env python3
"""
Custom Functions Example
========================

Demonstrates the new custom function capability in Symbolica.
"""

from symbolica import Engine, facts

# Example rules using custom functions
custom_function_rules = """
rules:
  - id: "risk_assessment"
    priority: 100
    condition: "risk_score(credit_score) == 'low' and income_tier(annual_income) != 'low'"
    actions:
      approved: true
      rate: 0.035
      limit: 50000
    tags: ["low_risk", "approval"]
  
  - id: "medium_risk_approval"
    priority: 90
    condition: "risk_score(credit_score) == 'medium' and debt_ratio(monthly_debt, monthly_income) < 0.4"
    actions:
      approved: true
      rate: 0.065
      limit: 25000
    tags: ["medium_risk", "approval"]
  
  - id: "high_risk_rejection"
    priority: 80
    condition: "risk_score(credit_score) == 'high' or debt_ratio(monthly_debt, monthly_income) >= 0.4"
    actions:
      approved: false
      reason: "High risk profile"
    tags: ["high_risk", "rejection"]
    
  - id: "premium_customer_bonus"
    priority: 70
    condition: "approved == true and customer_score(years_with_bank, total_deposits) > 8.5"
    actions:
      premium_rate: true
      bonus_limit: 10000
    tags: ["premium", "bonus"]
"""

def demo_custom_functions():
    """Demonstrate custom function registration and usage."""
    print("=== Custom Functions Demo ===")
    
    # Create engine
    engine = Engine.from_yaml(custom_function_rules)
    
    # Register custom functions
    engine.register_function("risk_score", lambda score: 
        "low" if score > 750 else "high" if score < 600 else "medium")
    
    engine.register_function("income_tier", lambda income:
        "high" if income > 100000 else "low" if income < 40000 else "medium")
    
    engine.register_function("debt_ratio", lambda debt, income:
        debt / income if income > 0 else 1.0)
    
    engine.register_function("customer_score", lambda years, deposits:
        min(10.0, (years * 2) + (deposits / 100000)))
    
    # List all available functions
    print("Available functions:")
    for name, description in engine.list_functions().items():
        print(f"  {name}: {description}")
    
    print("\nTest cases:")
    
    # Test case 1: Low risk customer
    print("\n1. Low risk customer:")
    customer1 = facts(
        credit_score=780,
        annual_income=85000,
        monthly_debt=1200,
        monthly_income=7000,
        years_with_bank=5,
        total_deposits=250000
    )
    
    result1 = engine.reason(customer1)
    print(f"Facts: {customer1.data}")
    print(f"Verdict: {result1.verdict}")
    print(f"Rules fired: {result1.fired_rules}")
    print(f"Reasoning: {result1.reasoning}")
    
    # Test case 2: Medium risk customer
    print("\n2. Medium risk customer:")
    customer2 = facts(
        credit_score=680,
        annual_income=55000,
        monthly_debt=1500,
        monthly_income=4500,
        years_with_bank=2,
        total_deposits=50000
    )
    
    result2 = engine.reason(customer2)
    print(f"Facts: {customer2.data}")
    print(f"Verdict: {result2.verdict}")
    print(f"Rules fired: {result2.fired_rules}")
    print(f"Reasoning: {result2.reasoning}")
    
    # Test case 3: High risk customer
    print("\n3. High risk customer:")
    customer3 = facts(
        credit_score=580,
        annual_income=35000,
        monthly_debt=2000,
        monthly_income=2900,
        years_with_bank=1,
        total_deposits=5000
    )
    
    result3 = engine.reason(customer3)
    print(f"Facts: {customer3.data}")
    print(f"Verdict: {result3.verdict}")
    print(f"Rules fired: {result3.fired_rules}")
    print(f"Reasoning: {result3.reasoning}")


def demo_function_error_handling():
    """Demonstrate error handling in custom functions."""
    print("\n=== Custom Function Error Handling ===")
    
    engine = Engine.from_yaml("""
rules:
  - id: "test_error"
    condition: "error_func(value) > 0"
    actions:
      result: true
""")
    
    # Register a function that might error
    engine.register_function("error_func", lambda x: 10 / x)
    
    # Test with valid input
    print("1. Valid input (x=2):")
    try:
        result = engine.reason(facts(value=2))
        print(f"Result: {result.verdict}")
        print(f"Rules fired: {result.fired_rules}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with input that causes error
    print("\n2. Invalid input (x=0, division by zero):")
    try:
        result = engine.reason(facts(value=0))
        print(f"Result: {result.verdict}")
        print(f"Rules fired: {result.fired_rules}")
    except Exception as e:
        print(f"Error handled gracefully: {e}")


def demo_complex_functions():
    """Demonstrate more complex custom functions."""
    print("\n=== Complex Custom Functions ===")
    
    engine = Engine.from_yaml("""
rules:
  - id: "fraud_detection"
    condition: "fraud_probability(transaction_amount, avg_amount, location_risk) > 0.7"
    actions:
      fraud_alert: true
      hold_transaction: true
    
  - id: "vip_treatment"
    condition: "customer_lifetime_value(years, avg_monthly_spend) > 50000"
    actions:
      vip_status: true
      priority_support: true
""")
    
    # Register complex functions
    def fraud_probability(amount, avg_amount, location_risk):
        """Calculate fraud probability based on multiple factors."""
        amount_deviation = abs(amount - avg_amount) / avg_amount if avg_amount > 0 else 1.0
        amount_factor = min(1.0, amount_deviation)
        return (amount_factor * 0.6) + (location_risk * 0.4)
    
    def customer_lifetime_value(years, monthly_spend):
        """Calculate customer lifetime value."""
        return years * monthly_spend * 12 * 0.85  # 85% retention factor
    
    engine.register_function("fraud_probability", fraud_probability)
    engine.register_function("customer_lifetime_value", customer_lifetime_value)
    
    # Test fraud detection
    print("Fraud detection test:")
    transaction = facts(
        transaction_amount=15000,
        avg_amount=500,
        location_risk=0.8,
        years=3,
        avg_monthly_spend=800
    )
    
    result = engine.reason(transaction)
    print(f"Transaction: {transaction.data}")
    print(f"Decision: {result.verdict}")
    print(f"Rules fired: {result.fired_rules}")


if __name__ == "__main__":
    demo_custom_functions()
    demo_function_error_handling()
    demo_complex_functions()
    
    print("\n=== Custom Functions Demo Complete ===")
    print("✓ Function registration and usage")
    print("✓ Error handling in custom functions")
    print("✓ Complex multi-parameter functions")
    print("✓ Integration with rule reasoning") 