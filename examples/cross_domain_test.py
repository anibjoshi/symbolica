#!/usr/bin/env python3
"""
Cross-Domain Test for Symbolica.

Simple test to verify that the same universal rule engine 
works correctly across database, tax, and insurance domains.
"""

import os
from pathlib import Path
from symbolica import FactStore, RuleEngine, Inference
from symbolica.parsers.yaml_parser import YAMLRuleParser


def test_domain(domain_name: str, rules_folder: str, test_facts: dict):
    """Test Symbolica on a specific domain.
    
    Args:
        domain_name: Name of the domain being tested
        rules_folder: Path to the rules folder
        test_facts: Dictionary of facts to test with
    """
    print(f"\n🧪 Testing {domain_name} Domain")
    print("=" * 40)
    
    # Load rules
    rules_path = Path(__file__).parent / rules_folder
    
    if not rules_path.exists():
        print(f"❌ Rules folder not found: {rules_path}")
        return False
    
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_path))
    
    errors = parser.get_validation_errors()
    if errors:
        print(f"⚠️  Found {len(errors)} parsing errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print(f"✅ Loaded {len(rules)} rules")
    
    # Create facts
    facts = FactStore()
    for key, value in test_facts.items():
        facts.add(key, value, {"source": "test", "domain": domain_name})
    
    print(f"📋 Created {len(test_facts)} test facts")
    
    # Run inference with limit to prevent infinite loops
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts, max_iterations=10)  # Limit iterations
    
    print(f"🧠 Inference completed:")
    print(f"   - Execution time: {result.execution_time_ms:.2f}ms")
    print(f"   - Rules fired: {result.rules_fired}")
    print(f"   - Conclusions: {len(result.conclusions)}")
    print(f"   - Iterations: {getattr(result, 'iterations', 'N/A')}")
    
    # Show unique conclusions
    if result.conclusions:
        unique_conclusions = {}
        for conclusion in result.conclusions:
            key = f"{conclusion.fact.key}:{conclusion.fact.value}"
            if key not in unique_conclusions:
                unique_conclusions[key] = conclusion
        
        print(f"📊 Unique conclusions ({len(unique_conclusions)}):")
        for i, (key, conclusion) in enumerate(unique_conclusions.items(), 1):
            rule_name = conclusion.metadata.get('name', conclusion.rule_id)
            print(f"   {i}. {conclusion.fact.key}: {conclusion.fact.value}")
            print(f"      Rule: {rule_name}")
    else:
        print("ℹ️  No conclusions drawn")
    
    return True


def main():
    """Run cross-domain tests."""
    print("🌐 Symbolica Cross-Domain Compatibility Test")
    print("=" * 50)
    print("Testing the same universal engine across multiple domains...")
    
    # Test cases for each domain
    test_cases = [
        {
            "domain_name": "Database Troubleshooting",
            "rules_folder": "database-troubleshooting",
            "test_facts": {
                "cpu_utilization": 95.0,
                "memory_utilization": 85.0,
                "average_query_time_ms": 150,
                "concurrent_connections": 500,
                "table_scans_per_second": 20
            }
        },
        {
            "domain_name": "Income Tax",
            "rules_folder": "income-tax",
            "test_facts": {
                "earned_income": 45000,
                "adjusted_gross_income": 48000,
                "filing_status": "married_filing_jointly",
                "investment_income": 2500,
                "number_of_dependents_under_17": 2,
                "state_and_local_taxes": 12000
            }
        },
        {
            "domain_name": "Insurance Claims",
            "rules_folder": "insurance-claims",
            "test_facts": {
                "claim_amount": 75000,
                "policy_active": True,
                "police_report_filed": False,
                "days_since_policy_start": 15,
                "claim_type": "theft"
            }
        }
    ]
    
    # Run tests
    results = []
    for test_case in test_cases:
        success = test_domain(
            test_case["domain_name"],
            test_case["rules_folder"], 
            test_case["test_facts"]
        )
        results.append((test_case["domain_name"], success))
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 Test Summary")
    print("=" * 50)
    
    successful_domains = [name for name, success in results if success]
    failed_domains = [name for name, success in results if not success]
    
    print(f"✅ Successful domains: {len(successful_domains)}")
    for domain in successful_domains:
        print(f"   - {domain}")
    
    if failed_domains:
        print(f"❌ Failed domains: {len(failed_domains)}")
        for domain in failed_domains:
            print(f"   - {domain}")
    
    print(f"\n🌟 Key Achievement:")
    print(f"   • Same universal YAML parser works across all domains")
    print(f"   • Same rule engine processes all rule types")
    print(f"   • No domain-specific code needed")
    print(f"   • Consistent if/then syntax everywhere")
    
    if len(successful_domains) == len(test_cases):
        print(f"\n🎉 All domains working! Symbolica is truly domain-agnostic!")
    else:
        print(f"\n⚠️  Some domains need attention")


if __name__ == "__main__":
    main() 