#!/usr/bin/env python3
"""
JSON Demo for Symbolica - Perfect for LLM Agents

This demonstrates the new JSON-based interface that makes Symbolica
ideal for integration with LLM agents in LangGraph and other frameworks.
"""

import json
from symbolica import FactStore, RuleEngine, Inference
from symbolica.parsers.yaml_parser import YAMLRuleParser


def demonstrate_json_interface():
    """Show how LLM agents can use Symbolica with JSON."""
    
    print("🤖 Symbolica JSON Interface for LLM Agents")
    print("=" * 50)
    
    # 1. LLM sends JSON data to Symbolica
    print("\n📝 Input: LLM passes JSON data")
    claim_json = {
        "claim_amount": 75000,
        "policy_active": True,
        "claim_type": "theft",
        "police_report_filed": False
    }
    print(json.dumps(claim_json, indent=2))
    
    # 2. Symbolica converts JSON to facts automatically
    facts = FactStore.from_json(claim_json)
    print(f"\n✅ Converted to {len(facts)} facts automatically")
    
    # 3. Load rules and run inference
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder("examples/insurance-claims")
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts)
    
    # 4. LLM receives structured JSON output
    print("\n📤 Output: Structured JSON for LLM")
    output = result.to_dict()
    
    # Show simplified output
    simplified_output = {
        "success": output["success"],
        "conclusions": output["unique_conclusions"],
        "performance": {
            "rules_fired": output["performance"]["rules_fired"],
            "execution_time_ms": output["performance"]["total_execution_time_ms"]
        }
    }
    
    print(json.dumps(simplified_output, indent=2))
    
    print("\n🎯 Benefits for LLM Agents:")
    print("✅ No manual fact creation - just pass JSON")
    print("✅ Structured output easy to parse")
    print("✅ Reasoning trace available in JSON")
    print("✅ Perfect for LangGraph node integration")


if __name__ == "__main__":
    demonstrate_json_interface() 