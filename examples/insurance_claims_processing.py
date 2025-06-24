#!/usr/bin/env python3
"""
Insurance Claims Processing Example with Symbolica.

This example demonstrates how to:
- Load insurance rules using the same universal if/then syntax  
- Process insurance claims data
- Detect fraud patterns, eligibility issues, and approval requirements
- Generate natural language explanations for claim decisions

Shows Symbolica's domain-agnostic capabilities across insurance processing.
"""

import os
from pathlib import Path
from symbolica import FactStore, RuleEngine, Inference, LLMBridge
from symbolica.parsers.yaml_parser import YAMLRuleParser


def create_facts_from_claim_data(claim_data: dict) -> FactStore:
    """Create facts from insurance claim data.
    
    Args:
        claim_data: Dictionary of claim information
        
    Returns:
        FactStore containing the facts
    """
    facts = FactStore()
    for key, value in claim_data.items():
        facts.add(key, value, {"source": "claim", "type": "claim_data"})
    return facts


def main():
    """Run the insurance claims processing example."""
    print("🛡️  Insurance Claims Processing with Symbolica")
    print("=" * 50)
    
    # 1. Load insurance rules using universal YAML parser
    print("\n1. Loading insurance claims rules...")
    
    rules_folder = Path(__file__).parent / "insurance-claims"
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_folder))
    
    errors = parser.get_validation_errors()
    if errors:
        print(f"⚠️  Found {len(errors)} parsing errors:")
        for error in errors:
            print(f"   - {error}")
    
    print(f"✅ Loaded {len(rules)} insurance rules from {rules_folder}")
    for rule in rules:
        print(f"   - {rule.metadata.get('name', rule.id)}")
    
    # 2. Simulate claim scenarios
    print("\n2. Processing insurance claim scenarios...")
    
    # Scenario 1: Suspicious high-value claim
    suspicious_claim = {
        "claim_amount": 75000,
        "policy_start_date": "2024-01-15",
        "claim_date": "2024-02-01", 
        "claim_type": "theft",
        "location": "high_crime_area",
        "police_report_filed": False,
        "policy_active": True,
        "prior_claims_count": 3,
        "days_since_policy_start": 17,
        "invoice_id": "INV-2024-001",
        "prior_claimed_invoice_ids": ["INV-2023-999", "INV-2023-888"],
        "beneficiary_info_complete": True,
        "pre_existing_condition": False
    }
    
    print("🚨 Suspicious Claim Scenario:")
    print("📋 Claim information:")
    for key, value in suspicious_claim.items():
        print(f"   - {key}: {value}")
    
    # 3. Process with Symbolica
    print("\n3. Running claims processing inference...")
    
    facts = create_facts_from_claim_data(suspicious_claim)
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts)
    
    print(f"🧠 Claims processing completed in {result.execution_time_ms:.2f}ms")
    print(f"🔥 Applied {result.rules_fired} claim rules")
    print(f"💡 Generated {len(result.conclusions)} claim determinations")
    
    # 4. Display claim determinations
    print("\n4. ⚖️  Claim Processing Results:")
    print("-" * 40)
    
    if not result.conclusions:
        print("✅ No issues detected - claim approved for standard processing")
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
            
            # Display tags if present
            if 'tags' in conclusion.metadata:
                tags = conclusion.metadata['tags']
                if isinstance(tags, list):
                    print(f"   Action Tags: {', '.join(tags)}")
                else:
                    print(f"   Action Tag: {tags}")
    
    # 5. Show reasoning trace
    print("\n5. 🔍 Claims Processing Logic:")
    print("-" * 40)
    
    trace_explanation = inference.explain_trace()
    print(trace_explanation)
    
    # 6. Generate natural language explanations
    print("\n6. 📝 Claims Decision Explanations:")
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
    
    # 7. Test legitimate claim scenario
    print("\n" + "=" * 50)
    print("✅ Legitimate Claim Scenario")
    print("=" * 50)
    
    legitimate_claim = {
        "claim_amount": 8500,
        "policy_start_date": "2022-01-15",
        "claim_date": "2024-03-15",
        "claim_type": "auto_accident",
        "police_report_filed": True,
        "policy_active": True,
        "prior_claims_count": 0,
        "days_since_policy_start": 790,
        "invoice_id": "INV-2024-NEW-001",
        "prior_claimed_invoice_ids": [],
        "beneficiary_info_complete": True,
        "pre_existing_condition": False,
        "location": "suburban_area"
    }
    
    print("🏠 Legitimate claim information:")
    for key, value in legitimate_claim.items():
        print(f"   - {key}: {value}")
    
    # Process legitimate scenario
    facts = create_facts_from_claim_data(legitimate_claim)
    result = inference.run(facts)
    
    print(f"\n🧠 Claims processing result:")
    print(f"   - Execution time: {result.execution_time_ms:.2f}ms")
    print(f"   - Rules applied: {result.rules_fired}")
    print(f"   - Determinations: {len(result.conclusions)}")
    
    if result.conclusions:
        print("\n⚖️  Claim determinations:")
        unique_determinations = {}
        for conclusion in result.conclusions:
            key = f"{conclusion.fact.key}:{conclusion.fact.value}"
            if key not in unique_determinations:
                unique_determinations[key] = conclusion
        
        for conclusion in unique_determinations.values():
            print(f"   - {conclusion.fact.key}: {conclusion.fact.value}")
            print(f"     Rule: {conclusion.metadata.get('name', conclusion.rule_id)}")
            if 'tags' in conclusion.metadata:
                tags = conclusion.metadata['tags']
                if isinstance(tags, list):
                    print(f"     Actions: {', '.join(tags)}")
    else:
        print("\n✅ No red flags - claim approved for standard processing")
    
    # 8. Performance analysis
    print("\n8. ⚡ Claims Processing Performance:")
    print("-" * 40)
    
    perf_metrics = inference.analyze_performance()
    print(f"Total inference steps: {perf_metrics['total_steps']}")
    print(f"Average step time: {perf_metrics['avg_step_time_ms']:.2f}ms")
    print(f"Insurance rules usage: {perf_metrics['rule_usage']}")
    
    # 9. Fact queries for investigation
    print("\n9. 🔎 Claims Investigation Queries:")
    print("-" * 40)
    
    # Query claim amount related facts
    amount_facts = facts.query("*amount*")
    print(f"Amount-related items ({len(amount_facts)} facts):")
    for fact in amount_facts:
        print(f"   - {fact.key}: {fact.value}")
    
    # Query date-related facts
    date_facts = facts.query("*date*")
    print(f"\nDate-related items ({len(date_facts)} facts):")
    for fact in date_facts:
        print(f"   - {fact.key}: {fact.value}")
    
    print("\n" + "=" * 50)
    print("🎯 Claims processing complete!")
    print("\nKey insights:")
    print("• Same Symbolica engine processes insurance rules as tax/database rules")
    print("• Universal if/then syntax works across all domains")
    print("• Complex fraud detection with simple rule definitions")
    print("• Automated claim approval/rejection workflows")


def demonstrate_claims_rule_types():
    """Show different types of insurance rules supported."""
    print("\n" + "=" * 50)
    print("📋 Insurance Rule Types Demonstration")
    print("=" * 50)
    
    # Load rules and show types
    rules_folder = Path(__file__).parent / "insurance-claims"
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_folder))
    
    print(f"📝 Loaded {len(rules)} different insurance rule types:")
    
    rule_categories = {
        "Fraud Detection": [],
        "Eligibility Checks": [],
        "Approval Requirements": [],
        "Policy Validation": []
    }
    
    for rule in rules:
        rule_name = rule.metadata.get('name', rule.id)
        
        # Categorize rules based on name patterns
        if any(word in rule_name.lower() for word in ['duplicate', 'missing', 'repeat']):
            rule_categories["Fraud Detection"].append(rule)
        elif any(word in rule_name.lower() for word in ['expired', 'exclusion', 'condition']):
            rule_categories["Eligibility Checks"].append(rule)
        elif any(word in rule_name.lower() for word in ['high-value', 'senior', 'approval']):
            rule_categories["Approval Requirements"].append(rule)
        else:
            rule_categories["Policy Validation"].append(rule)
    
    for category, category_rules in rule_categories.items():
        if category_rules:
            print(f"\n🏷️  {category}:")
            for rule in category_rules:
                rule_name = rule.metadata.get('name', rule.id)
                print(f"   • {rule_name}")
                
                # Show sample conditions
                conditions = [c for c in rule.conditions if c.metadata.get("logic_type") in ["all", "any"]][:2]  # Show first 2
                for condition in conditions:
                    original = condition.metadata.get('original_condition', f'{condition.field} {condition.operator.value} {condition.value}')
                    print(f"     - {original}")


def demonstrate_cross_domain_compatibility():
    """Demonstrate that the same engine works across all three domains."""
    print("\n" + "=" * 50)
    print("🌐 Cross-Domain Compatibility Test")
    print("=" * 50)
    
    print("Testing the same Symbolica engine across all domains...")
    
    domains = [
        ("database", "sample-rules"),
        ("tax", "income-tax"),
        ("insurance", "insurance-claims")
    ]
    
    parser = YAMLRuleParser()
    
    for domain_name, folder_name in domains:
        rules_folder = Path(__file__).parent / folder_name
        if rules_folder.exists():
            rules = parser.parse_rules_from_folder(str(rules_folder))
            errors = parser.get_validation_errors()
            
            print(f"\n📂 {domain_name.title()} Domain:")
            print(f"   ✅ Loaded {len(rules)} rules")
            if errors:
                print(f"   ⚠️  {len(errors)} parsing errors")
            else:
                print(f"   ✅ No parsing errors")
            
            # Test rule engine creation
            try:
                engine = RuleEngine(rules)
                print(f"   ✅ Rule engine created successfully")
            except Exception as e:
                print(f"   ❌ Rule engine creation failed: {e}")
        else:
            print(f"\n📂 {domain_name.title()} Domain: Folder not found")
    
    print(f"\n🎯 Result: Same universal engine works across all domains!")
    print(f"   • No domain-specific parsers needed")
    print(f"   • Consistent if/then syntax")
    print(f"   • Unified reasoning engine")


if __name__ == "__main__":
    main()
    demonstrate_claims_rule_types()
    demonstrate_cross_domain_compatibility() 