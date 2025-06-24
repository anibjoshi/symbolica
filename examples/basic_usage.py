#!/usr/bin/env python3
"""
Basic usage example for Symbolica.

This example demonstrates:
- Creating facts and rules
- Running inference
- Getting explanations
"""

from symbolica import (
    FactStore, RuleEngine, Inference, LLMBridge,
    Fact, Rule, Condition, Conclusion, OperatorType
)


def main():
    """Run the basic usage example."""
    print("🔬 Symbolica Basic Usage Example")
    print("=" * 40)
    
    # 1. Create a fact store and add some facts
    print("\n1. Setting up facts...")
    facts = FactStore()
    
    facts.add("server_1_status", "down")
    facts.add("server_1_type", "web_server")
    facts.add("server_2_status", "running")
    facts.add("server_2_type", "database")
    facts.add("network_latency", 250)  # milliseconds
    
    print(f"Added {len(facts)} facts to the store")
    
    # 2. Create some rules
    print("\n2. Creating rules...")
    
    # Rule 1: If a server is down, generate a high severity alert
    rule1 = Rule(
        id="server_down_alert",
        conditions=[
            Condition(field="key", operator=OperatorType.CONTAINS, value="status"),
            Condition(field="value", operator=OperatorType.EQ, value="down")
        ],
        conclusions=[
            Conclusion(
                fact=Fact(key="alert_severity", value="high"),
                confidence=0.9,
                rule_id="server_down_alert"
            )
        ],
        priority=10
    )
    
    # Rule 2: If network latency is high, generate a medium severity alert
    rule2 = Rule(
        id="high_latency_alert",
        conditions=[
            Condition(field="key", operator=OperatorType.EQ, value="network_latency"),
            Condition(field="value", operator=OperatorType.GT, value=200)
        ],
        conclusions=[
            Conclusion(
                fact=Fact(key="alert_severity", value="medium"),
                confidence=0.7,
                rule_id="high_latency_alert"
            )
        ],
        priority=5
    )
    
    # Rule 3: If we have a high severity alert, we need immediate action
    rule3 = Rule(
        id="immediate_action_required",
        conditions=[
            Condition(field="key", operator=OperatorType.EQ, value="alert_severity"),
            Condition(field="value", operator=OperatorType.EQ, value="high")
        ],
        conclusions=[
            Conclusion(
                fact=Fact(key="action_required", value="immediate"),
                confidence=1.0,
                rule_id="immediate_action_required"
            )
        ],
        priority=15
    )
    
    print(f"Created {3} rules")
    
    # 3. Create rule engine and add rules
    print("\n3. Setting up rule engine...")
    engine = RuleEngine([rule1, rule2, rule3])
    
    # Validate rules
    errors = engine.validate_rules()
    if errors:
        print(f"⚠️  Found {len(errors)} validation errors:")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ All rules are valid")
    
    # 4. Create inference engine
    print("\n4. Running inference...")
    inference = Inference(engine)
    
    # Run inference
    result = inference.run(facts)
    
    print(f"🧠 Inference completed in {result.execution_time_ms:.2f}ms")
    print(f"📊 Processed {result.facts_processed} facts")
    print(f"🔥 Fired {result.rules_fired} rules")
    print(f"💡 Drew {len(result.conclusions)} conclusions")
    
    # 5. Display conclusions
    print("\n5. Conclusions:")
    for i, conclusion in enumerate(result.conclusions, 1):
        print(f"   {i}. {conclusion.fact.key} = {conclusion.fact.value}")
        print(f"      Confidence: {conclusion.confidence:.0%}")
        print(f"      From rule: {conclusion.rule_id}")
        print()
    
    # 6. Show reasoning trace
    print("6. Reasoning trace:")
    explanation = inference.explain_trace()
    print(explanation)
    
    # 7. Demonstrate LLM bridge (without actual LLM)
    print("\n7. Natural language explanation:")
    llm_bridge = LLMBridge()  # No LLM client, will use fallback
    
    if result.conclusions:
        nl_explanation = llm_bridge.explain_conclusion(result.conclusions[0])
        print(nl_explanation)
    
    # 8. Query facts
    print("\n8. Querying facts:")
    server_facts = facts.query("server_*")
    print(f"Found {len(server_facts)} server-related facts:")
    for fact in server_facts:
        print(f"   - {fact.key} = {fact.value}")
    
    # 9. Performance analysis
    print("\n9. Performance analysis:")
    perf_metrics = inference.analyze_performance()
    print(f"   - Total steps: {perf_metrics['total_steps']}")
    print(f"   - Average step time: {perf_metrics['avg_step_time_ms']:.2f}ms")
    print(f"   - Conclusions per step: {perf_metrics['conclusions_per_step']:.1f}")
    
    print("\n✨ Example completed!")


if __name__ == "__main__":
    main() 