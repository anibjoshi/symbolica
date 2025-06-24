#!/usr/bin/env python3
"""
Income Tax Processing Example with Symbolica.

This example demonstrates how to:
- Load tax rules using the same universal if/then syntax
- Process taxpayer information 
- Determine tax credits, deductions, and eligibility
- Generate natural language explanations for tax decisions

Shows Symbolica's domain-agnostic capabilities across tax law.
"""

import os
from pathlib import Path
from symbolica import FactStore, RuleEngine, Inference, LLMBridge
from symbolica.parsers.yaml_parser import YAMLRuleParser


def create_facts_from_tax_data(tax_data: dict) -> FactStore:
    """Create facts from taxpayer data.
    
    Args:
        tax_data: Dictionary of tax information
        
    Returns:
        FactStore containing the facts
    """
    facts = FactStore()
    for key, value in tax_data.items():
        facts.add(key, value, {"source": "tax_return", "type": "taxpayer_data"})
    return facts


def main():
    """Run the income tax processing example."""
    print("💰 Income Tax Processing with Symbolica")
    print("=" * 50)
    
    # 1. Load tax rules using universal YAML parser
    print("\n1. Loading income tax rules...")
    
    rules_folder = Path(__file__).parent / "income-tax"
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_folder))
    
    errors = parser.get_validation_errors()
    if errors:
        print(f"⚠️  Found {len(errors)} parsing errors:")
        for error in errors:
            print(f"   - {error}")
    
    print(f"✅ Loaded {len(rules)} tax rules from {rules_folder}")
    for rule in rules:
        print(f"   - {rule.metadata.get('name', rule.id)}")
    
    # 2. Simulate taxpayer scenarios
    print("\n2. Processing taxpayer scenarios...")
    
    # Scenario 1: Family with children eligible for multiple credits
    family_taxpayer = {
        "earned_income": 45000,
        "adjusted_gross_income": 48000,
        "filing_status": "married_filing_jointly",
        "investment_income": 2500,
        "number_of_dependents_under_17": 2,
        "education_expenses": 8000,
        "student_loan_interest": 1200,
        "state_and_local_taxes": 12000,
        "foreign_income": 0,
        "high_deductible_health_plan": True
    }
    
    print("👨‍👩‍👧‍👦 Family Taxpayer Scenario:")
    print("📋 Tax information:")
    for key, value in family_taxpayer.items():
        print(f"   - {key}: {value}")
    
    # 3. Process with Symbolica
    print("\n3. Running tax rule inference...")
    
    facts = create_facts_from_tax_data(family_taxpayer)
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts)
    
    print(f"🧠 Tax processing completed in {result.execution_time_ms:.2f}ms")
    print(f"🔥 Applied {result.rules_fired} tax rules")
    print(f"💡 Generated {len(result.conclusions)} tax determinations")
    
    # 4. Display tax determinations
    print("\n4. 📊 Tax Determinations:")
    print("-" * 40)
    
    if not result.conclusions:
        print("ℹ️  No special tax provisions apply - standard tax treatment")
    else:
        # Group by unique determinations to avoid duplicates
        unique_determinations = {}
        for conclusion in result.conclusions:
            key = f"{conclusion.fact.key}:{conclusion.fact.value}"
            if key not in unique_determinations:
                unique_determinations[key] = conclusion
        
        for i, (key, conclusion) in enumerate(unique_determinations.items(), 1):
            print(f"\n{i}. {conclusion.fact.key}: {conclusion.fact.value}")
            if hasattr(conclusion, 'confidence') and conclusion.confidence < 1.0:
                print(f"   Confidence: {conclusion.confidence:.0%}")
            print(f"   Source Rule: {conclusion.metadata.get('name', conclusion.rule_id)}")
            
            # Display additional metadata
            for meta_key, meta_value in conclusion.metadata.items():
                if meta_key not in ['name', 'source_file', 'format']:
                    print(f"   {meta_key}: {meta_value}")
    
    # 5. Show reasoning trace
    print("\n5. 🔍 Tax Rule Reasoning:")
    print("-" * 40)
    
    trace_explanation = inference.explain_trace()
    print(trace_explanation)
    
    # 6. Generate natural language explanations
    print("\n6. 📝 Tax Advice Explanations:")
    print("-" * 40)
    
    llm_bridge = LLMBridge()  # Using fallback explanations
    
    if result.conclusions:
        unique_determinations = {}
        for conclusion in result.conclusions:
            key = f"{conclusion.fact.key}:{conclusion.fact.value}"
            if key not in unique_determinations:
                unique_determinations[key] = conclusion
        
        for conclusion in unique_determinations.values():
            explanation = llm_bridge.explain_conclusion(conclusion)
            print(f"\n• {explanation}")
    
    # 7. Test high-income scenario
    print("\n" + "=" * 50)
    print("🏦 High-Income Taxpayer Scenario")
    print("=" * 50)
    
    high_income_taxpayer = {
        "earned_income": 180000,
        "adjusted_gross_income": 220000,
        "filing_status": "married_filing_jointly", 
        "investment_income": 15000,
        "number_of_dependents_under_17": 1,
        "state_and_local_taxes": 25000,
        "foreign_income": 50000,
        "retirement_withdrawal_early": True,
        "retirement_withdrawal_amount": 30000,
        "age": 45
    }
    
    print("💼 High-income taxpayer information:")
    for key, value in high_income_taxpayer.items():
        print(f"   - {key}: {value}")
    
    # Process high-income scenario
    facts = create_facts_from_tax_data(high_income_taxpayer)
    result = inference.run(facts)
    
    print(f"\n🧠 Tax processing result:")
    print(f"   - Execution time: {result.execution_time_ms:.2f}ms")
    print(f"   - Rules applied: {result.rules_fired}")
    print(f"   - Determinations: {len(result.conclusions)}")
    
    if result.conclusions:
        print("\n📊 Tax determinations:")
        unique_determinations = {}
        for conclusion in result.conclusions:
            key = f"{conclusion.fact.key}:{conclusion.fact.value}"
            if key not in unique_determinations:
                unique_determinations[key] = conclusion
        
        for conclusion in unique_determinations.values():
            print(f"   - {conclusion.fact.key}: {conclusion.fact.value}")
            print(f"     Rule: {conclusion.metadata.get('name', conclusion.rule_id)}")
    else:
        print("\n✅ Standard tax treatment applies")
    
    # 8. Performance analysis
    print("\n8. ⚡ Tax Processing Performance:")
    print("-" * 40)
    
    perf_metrics = inference.analyze_performance()
    print(f"Total inference steps: {perf_metrics['total_steps']}")
    print(f"Average step time: {perf_metrics['avg_step_time_ms']:.2f}ms")
    print(f"Tax rules usage: {perf_metrics['rule_usage']}")
    
    # 9. Fact queries for tax planning
    print("\n9. 🔎 Tax Planning Queries:")
    print("-" * 40)
    
    # Query income-related facts
    income_facts = facts.query("*income*")
    print(f"Income-related items ({len(income_facts)} facts):")
    for fact in income_facts:
        print(f"   - {fact.key}: {fact.value}")
    
    # Query credit-related facts  
    dependent_facts = facts.query("*dependent*")
    print(f"\nDependent-related items ({len(dependent_facts)} facts):")
    for fact in dependent_facts:
        print(f"   - {fact.key}: {fact.value}")
    
    print("\n" + "=" * 50)
    print("🎯 Tax processing complete!")
    print("\nKey insights:")
    print("• Same Symbolica engine processes tax rules as database rules")
    print("• Universal if/then syntax works across all domains")
    print("• Complex tax logic handled with simple rule definitions")
    print("• Natural language explanations for tax decisions")


def demonstrate_tax_rule_types():
    """Show different types of tax rules supported."""
    print("\n" + "=" * 50)
    print("📋 Tax Rule Types Demonstration")
    print("=" * 50)
    
    # Load rules and show types
    rules_folder = Path(__file__).parent / "income-tax"
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_folder))
    
    print(f"📝 Loaded {len(rules)} different tax rule types:")
    
    for rule in rules:
        rule_name = rule.metadata.get('name', rule.id)
        print(f"\n• {rule_name}")
        
        # Show conditions
        all_conditions = [c for c in rule.conditions if c.metadata.get("logic_type") == "all"]
        any_conditions = [c for c in rule.conditions if c.metadata.get("logic_type") == "any"]
        
        if all_conditions:
            print("  Requires ALL of:")
            for condition in all_conditions:
                print(f"    - {condition.metadata.get('original_condition', f'{condition.field} {condition.operator.value} {condition.value}')}")
        
        if any_conditions:
            print("  Requires ANY of:")
            for condition in any_conditions:
                print(f"    - {condition.metadata.get('original_condition', f'{condition.field} {condition.operator.value} {condition.value}')}")
        
        # Show outcomes
        print("  Results in:")
        for conclusion in rule.conclusions:
            print(f"    - {conclusion.fact.key}: {conclusion.fact.value}")


if __name__ == "__main__":
    main()
    demonstrate_tax_rule_types() 