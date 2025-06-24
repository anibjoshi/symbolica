#!/usr/bin/env python3
"""
Basic Symbolica Usage Example - JSON-based for LLM Agents

Shows how LLM agents can interact with Symbolica using JSON:
1. Load rules from YAML files
2. Pass data as JSON to create facts
3. Get structured JSON output with detailed reasoning trace
"""

import json
from symbolica import FactStore, RuleEngine, Inference
from symbolica.parsers.yaml_parser import YAMLRuleParser


def main():
    # Load rules from insurance claims folder
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder("examples/insurance-claims")
    
    # Create facts from JSON data (how LLMs will typically interact)
    claim_data = {
        "claim_amount": 75000,
        "days_since_policy_start": 17,
        "police_report_filed": False,
        "prior_claims_count": 3,
        "claim_type": "theft",
        "location": "high_crime_area",
        "policy_active": True,
        "invoice_id": "INV-2024-001",
        "prior_claimed_invoice_ids": ["INV-2023-999"]
    }
    
    facts = FactStore.from_json(claim_data)
    
    # Run inference
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts)
    
    # Get structured JSON output with detailed reasoning
    output = result.to_dict()
    
    # Print key results
    print(f"Success: {output['success']}")
    print(f"Rules fired: {output['performance']['rules_fired']}")
    print(f"Unique conclusions: {len(output['unique_conclusions'])}")
    
    # Print conclusions with reasoning
    print("\n=== CONCLUSIONS ===")
    for conclusion in output['unique_conclusions']:
        print(f"• {conclusion['key']}: {conclusion['value']}")
        if conclusion['metadata'].get('tags'):
            print(f"  Actions: {conclusion['metadata']['tags']}")
    
    # Show detailed reasoning trace
    print("\n=== REASONING TRACE ===")
    if 'reasoning_trace' in output:
        print(output['reasoning_trace']['summary'])
        print("\nDetailed steps:")
        for step in output['reasoning_trace']['steps']:
            print(f"\nStep {step['step_number']}:")
            print(f"Rule: {step['rule_applied']['name']}")
            
            # Show condition evaluations
            if step['condition_evaluations']:
                print("Condition evaluations:")
                for eval in step['condition_evaluations']:
                    print(f"  {eval['explanation']}")
            
            # Show conclusions from this step
            if step['conclusions_drawn']:
                print("Conclusions:")
                for conclusion in step['conclusions_drawn']:
                    print(f"  • {conclusion['key']}: {conclusion['value']}")
    
    # Show compact JSON output for LLMs
    print("\n=== JSON OUTPUT FOR LLM ===")
    compact_output = {
        "success": output["success"],
        "conclusions": output["unique_conclusions"],
        "reasoning": output["reasoning_trace"]["summary"] if "reasoning_trace" in output else "No reasoning available",
        "performance": {
            "rules_fired": output["performance"]["rules_fired"],
            "execution_time_ms": output["performance"]["total_execution_time_ms"]
        }
    }
    print(json.dumps(compact_output, indent=2))


if __name__ == "__main__":
    main() 