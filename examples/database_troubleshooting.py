#!/usr/bin/env python3
"""
Database Troubleshooting Example with Symbolica.

This example demonstrates how to:
- Load rules with if/then syntax from a folder
- Process database metrics
- Run inference with all/any logic
- Generate natural language explanations

Shows Symbolica's generalized reasoning capabilities across domains.
"""

import os
from pathlib import Path
from symbolica import FactStore, RuleEngine, Inference, LLMBridge
from symbolica.parsers.yaml_parser import YAMLRuleParser


def create_facts_from_metrics(metrics: dict) -> FactStore:
    """Create facts from a metrics dictionary.
    
    Args:
        metrics: Dictionary of metric name -> value
        
    Returns:
        FactStore containing the facts
    """
    facts = FactStore()
    for key, value in metrics.items():
        facts.add(key, value, {"source": "metrics", "type": "measurement"})
    return facts


def main():
    """Run the database troubleshooting example."""
    print("🔍 Database Troubleshooting with Symbolica")
    print("=" * 50)
    
    # 1. Load rules from folder using enhanced YAML parser
    print("\n1. Loading rules with if/then syntax...")
    
    rules_folder = Path(__file__).parent / "sample-rules"
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_folder))
    
    errors = parser.get_validation_errors()
    if errors:
        print(f"⚠️  Found {len(errors)} parsing errors:")
        for error in errors:
            print(f"   - {error}")
    
    print(f"✅ Loaded {len(rules)} rules from {rules_folder}")
    for rule in rules:
        print(f"   - {rule.metadata.get('name', rule.id)}")
    
    # 2. Simulate database metrics (problematic scenario)
    print("\n2. Simulating database metrics...")
    
    # Scenario: High CPU usage with slow queries
    database_metrics = {
        "cpu_utilization": 95,           # High CPU
        "cpu_wait_time": 25,             # High wait time
        "context_switches_per_sec": 6000, # High context switches
        "avg_query_time": 2500,          # Slow queries
        "slow_query_count": 75,          # Many slow queries
        "table_scan_ratio": 0.4,         # High table scans
        "sort_operations": 1200,         # Many sorts
        "memory_mb": 8192,               # Total memory
        "available_memory_mb": 400,      # Low available memory
        "page_faults_per_sec": 150,      # High page faults
        "cache_hit_ratio": 80,           # Low cache hit ratio
    }
    
    print("📊 Current database metrics:")
    for metric, value in database_metrics.items():
        print(f"   - {metric}: {value}")
    
    # 3. Create facts from metrics
    print("\n3. Converting metrics to facts...")
    
    facts = create_facts_from_metrics(database_metrics)
    print(f"✅ Created {len(facts)} facts from metrics")
    
    # 4. Create rule engine and run inference
    print("\n4. Running inference...")
    
    engine = RuleEngine(rules)
    inference = Inference(engine)
    
    # Run inference
    result = inference.run(facts)
    
    print(f"🧠 Inference completed in {result.execution_time_ms:.2f}ms")
    print(f"🔥 Fired {result.rules_fired} rules")
    print(f"💡 Generated {len(result.conclusions)} diagnoses")
    
    # 5. Display diagnoses and recommendations
    print("\n5. 🏥 Diagnoses and Recommendations:")
    print("-" * 40)
    
    if not result.conclusions:
        print("✅ No issues detected - database appears healthy!")
    else:
        # Group conclusions by unique diagnosis to avoid duplicates
        unique_conclusions = {}
        for conclusion in result.conclusions:
            key = conclusion.fact.value
            if key not in unique_conclusions:
                unique_conclusions[key] = conclusion
        
        for i, (diagnosis, conclusion) in enumerate(unique_conclusions.items(), 1):
            print(f"\n{i}. {diagnosis}")
            print(f"   Confidence: {conclusion.confidence:.0%}")
            print(f"   Source Rule: {conclusion.metadata.get('name', conclusion.rule_id)}")
            
            # Display metadata (priority, severity, etc.)
            metadata_fields = ["priority", "severity", "category"]
            for field in metadata_fields:
                if field in conclusion.metadata:
                    print(f"   {field.title()}: {conclusion.metadata[field]}")
            
            # Display recommendations if available
            if "recommendations" in conclusion.metadata:
                recommendations = conclusion.metadata["recommendations"]
                if isinstance(recommendations, list):
                    print("   Recommendations:")
                    for rec in recommendations:
                        print(f"     • {rec}")
                else:
                    print(f"   Recommendation: {recommendations}")
    
    # 6. Show detailed reasoning trace
    print("\n6. 🔍 Detailed Reasoning Trace:")
    print("-" * 40)
    
    trace_explanation = inference.explain_trace()
    print(trace_explanation)
    
    # 7. Generate natural language explanations (without LLM)
    print("\n7. 📝 Natural Language Explanations:")
    print("-" * 40)
    
    llm_bridge = LLMBridge()  # Using fallback explanations
    
    if result.conclusions:
        unique_conclusions = {}
        for conclusion in result.conclusions:
            key = conclusion.fact.value
            if key not in unique_conclusions:
                unique_conclusions[key] = conclusion
        
        for conclusion in unique_conclusions.values():
            explanation = llm_bridge.explain_conclusion(conclusion)
            print(f"\n• {explanation}")
    
    # 8. Performance analysis
    print("\n8. ⚡ Performance Analysis:")
    print("-" * 40)
    
    perf_metrics = inference.analyze_performance()
    print(f"Total inference steps: {perf_metrics['total_steps']}")
    print(f"Average step time: {perf_metrics['avg_step_time_ms']:.2f}ms")
    print(f"Rules usage: {perf_metrics['rule_usage']}")
    
    # 9. Query specific facts for detailed investigation
    print("\n9. 🔎 Fact Queries for Investigation:")
    print("-" * 40)
    
    # Query CPU-related facts
    cpu_facts = facts.query("cpu_*")
    print(f"CPU-related metrics ({len(cpu_facts)} facts):")
    for fact in cpu_facts:
        print(f"   - {fact.key}: {fact.value}")
    
    # Query memory-related facts
    memory_facts = facts.query("*memory*")
    print(f"\nMemory-related metrics ({len(memory_facts)} facts):")
    for fact in memory_facts:
        print(f"   - {fact.key}: {fact.value}")
    
    # 10. Demonstrate rule validation
    print("\n10. ✅ Rule Validation:")
    print("-" * 40)
    
    validation_errors = engine.validate_rules()
    if validation_errors:
        print(f"Found {len(validation_errors)} validation issues:")
        for error in validation_errors:
            print(f"   - {error}")
    else:
        print("All rules passed validation!")
    
    print("\n" + "=" * 50)
    print("🎯 Troubleshooting analysis complete!")
    print("\nNext steps:")
    print("• Address high-priority issues first")
    print("• Monitor metrics after implementing recommendations")
    print("• Consider adding more rules for edge cases")


def demonstrate_healthy_scenario():
    """Demonstrate inference with healthy database metrics."""
    print("\n" + "=" * 50)
    print("🌟 Healthy Database Scenario")
    print("=" * 50)
    
    # Load rules
    rules_folder = Path(__file__).parent / "sample-rules"
    parser = YAMLRuleParser()
    rules = parser.parse_rules_from_folder(str(rules_folder))
    
    # Healthy metrics
    healthy_metrics = {
        "cpu_utilization": 45,           # Normal CPU
        "cpu_wait_time": 5,              # Low wait time
        "context_switches_per_sec": 2000, # Normal context switches
        "avg_query_time": 150,           # Fast queries
        "slow_query_count": 5,           # Few slow queries
        "available_memory_mb": 2048,     # Plenty of memory
        "page_faults_per_sec": 20,       # Low page faults
        "cache_hit_ratio": 95,           # High cache hit ratio
    }
    
    print("📊 Healthy database metrics:")
    for metric, value in healthy_metrics.items():
        print(f"   - {metric}: {value}")
    
    # Create facts and run inference
    facts = create_facts_from_metrics(healthy_metrics)
    
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts)
    
    print(f"\n🧠 Inference result:")
    print(f"   - Execution time: {result.execution_time_ms:.2f}ms")
    print(f"   - Rules fired: {result.rules_fired}")
    print(f"   - Diagnoses: {len(result.conclusions)}")
    
    if result.conclusions:
        print("\n⚠️  Issues detected:")
        for conclusion in result.conclusions:
            print(f"   - {conclusion.fact.value} (confidence: {conclusion.confidence:.0%})")
    else:
        print("\n✅ No issues detected - database is healthy!")


def demonstrate_other_domains():
    """Show how the same rule format works for other domains."""
    print("\n" + "=" * 50)
    print("🏢 Insurance Claims Example")
    print("=" * 50)
    
    # Example insurance rule in same if/then format
    insurance_yaml = """
rule:
  name: "high_risk_claim"
  if:
    all:
      - "claim_amount > 50000"
      - "claimant_age < 25"
    any:
      - "accident_type == motorcycle"
      - "previous_claims > 2"
  then:
    risk_level: "high"
    confidence: 0.85
    priority: "urgent"
    requires_investigation: true
"""
    
    parser = YAMLRuleParser()
    rules = parser.parse_rules(insurance_yaml)
    
    print("📋 Insurance rule loaded:")
    for rule in rules:
        print(f"   - {rule.metadata.get('name', rule.id)}")
    
    # Create insurance facts
    claim_data = {
        "claim_amount": 75000,
        "claimant_age": 22,
        "accident_type": "motorcycle",
        "previous_claims": 1
    }
    
    facts = create_facts_from_metrics(claim_data)
    
    engine = RuleEngine(rules)
    inference = Inference(engine)
    result = inference.run(facts)
    
    if result.conclusions:
        for conclusion in result.conclusions:
            print(f"📊 {conclusion.fact.key}: {conclusion.fact.value}")
            print(f"   Confidence: {conclusion.confidence:.0%}")
    else:
        print("✅ Standard risk level - no special handling needed")
    
    print("\n🔍 This demonstrates Symbolica's domain-agnostic approach:")
    print("   • Same if/then syntax works for any domain")
    print("   • Database troubleshooting, insurance, tax rules, etc.")
    print("   • Unified reasoning engine across all use cases")


if __name__ == "__main__":
    main()
    demonstrate_healthy_scenario()
    demonstrate_other_domains() 