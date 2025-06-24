# Getting Started with Symbolica

Symbolica is a symbolic reasoning engine designed to integrate seamlessly with LLM agents, providing structured logical inference with natural language explanations.

## Installation

### From PyPI (Recommended)

```bash
pip install symbolica
```

### Development Installation

```bash
git clone https://github.com/symbolica-ai/symbolica.git
cd symbolica
pip install -e ".[dev]"
```

### Optional Dependencies

Install optional dependencies for specific features:

```bash
# For graph-based backends
pip install symbolica[graph]

# For distributed processing
pip install symbolica[distributed]

# For agent framework integration
pip install symbolica[agents]

# Install everything
pip install symbolica[all]
```

## Basic Concepts

### Facts
Facts are pieces of information that the reasoning engine operates on. Each fact has:
- A **key** (string identifier)
- A **value** (any data type)
- **metadata** (additional context)
- A **confidence** level (0.0 to 1.0)
- A **timestamp**

### Rules
Rules define logical relationships and inference patterns. Each rule has:
- **Conditions** that must be satisfied
- **Conclusions** that are drawn when conditions are met
- A **priority** level for conflict resolution
- **Metadata** for additional context

### Inference
The inference engine applies rules to facts to derive new conclusions, generating a complete reasoning trace.

## Quick Start

Here's a simple example to get you started:

```python
from symbolica import FactStore, RuleEngine, Inference
from symbolica import Fact, Rule, Condition, Conclusion, OperatorType

# 1. Create a fact store and add facts
facts = FactStore()
facts.add("server_status", "down")
facts.add("server_type", "production")

# 2. Define a rule
rule = Rule(
    id="production_server_alert",
    conditions=[
        Condition(field="key", operator=OperatorType.EQ, value="server_status"),
        Condition(field="value", operator=OperatorType.EQ, value="down")
    ],
    conclusions=[
        Conclusion(
            fact=Fact(key="alert_level", value="critical"),
            confidence=0.95,
            rule_id="production_server_alert"
        )
    ]
)

# 3. Create rule engine and run inference
engine = RuleEngine([rule])
inference = Inference(engine)
result = inference.run(facts)

# 4. View results
print(f"Drew {len(result.conclusions)} conclusions:")
for conclusion in result.conclusions:
    print(f"- {conclusion.fact.key} = {conclusion.fact.value}")
```

## Working with Different Data Formats

### JSON Rules
```python
from symbolica.parsers import JSONRuleParser

parser = JSONRuleParser()
rules = parser.parse_rules({
    "rules": [
        {
            "id": "example_rule",
            "conditions": [
                {"field": "temperature", "operator": ">", "value": 80}
            ],
            "conclusions": [
                {"fact_key": "alert", "fact_value": "high_temperature"}
            ]
        }
    ]
})
```

### YAML Rules
```python
from symbolica.parsers import YAMLRuleParser

yaml_content = """
rules:
  - id: temperature_alert
    conditions:
      - field: temperature
        operator: ">"
        value: 80
    conclusions:
      - key: alert
        value: high_temperature
"""

parser = YAMLRuleParser()
rules = parser.parse_rules(yaml_content)
```

## LLM Integration

### Basic LLM Bridge
```python
from symbolica import LLMBridge
import openai

# Initialize with OpenAI client
client = openai.Client(api_key="your-api-key")
llm_bridge = LLMBridge(client, model_name="gpt-3.5-turbo")

# Get natural language explanations
explanation = llm_bridge.explain_conclusion(conclusion)
trace_explanation = llm_bridge.explain_trace(result.trace)
```

### LangGraph Integration
```python
from symbolica.bridges import SymbolicaNode

# Create a symbolic reasoning node
symbolic_node = SymbolicaNode(
    rules=my_rules,
    llm_bridge=llm_bridge
)

# Add to your LangGraph workflow
workflow.add_node("reasoning", symbolic_node)
```

### Semantic Kernel Integration
```python
from symbolica.bridges import SymbolicaPlugin
from semantic_kernel import Kernel

# Create kernel and add Symbolica plugin
kernel = Kernel()
plugin = SymbolicaPlugin(rule_engine, llm_bridge)
kernel.import_plugin(plugin, "symbolica")

# Use in your SK plans
result = kernel.invoke("symbolica", "run_inference")
```

## Performance Optimization

### Memory Backend Optimization
```python
from symbolica.backends import MemoryBackend

backend = MemoryBackend()
backend.enable_optimization(True)  # Enable performance optimizations
```

### Rule Optimization
```python
# Rules are automatically optimized based on selectivity
engine = RuleEngine(rules)
stats = engine.get_statistics()
print(f"Total rules: {stats['total_rules']}")
```

## Validation and Debugging

### Rule Validation
```python
# Validate rules
errors = engine.validate_rules()
if errors:
    for error in errors:
        print(f"Validation error: {error}")
```

### Debugging Inference
```python
# Step-by-step inference
for step in inference.step_by_step(facts):
    print(f"Step {step.step_number}: Applied rule {step.rule_applied.id}")
    print(f"  Conclusions: {len(step.conclusions_drawn)}")

# Performance analysis
metrics = inference.analyze_performance()
print(f"Average step time: {metrics['avg_step_time_ms']:.2f}ms")
```

## Next Steps

- Check out the [API Reference](api-reference.md) for detailed documentation
- Explore [examples](examples/) for more complex use cases
- Learn about [advanced features](advanced-usage.md) like custom backends and distributed processing

## Getting Help

- **Documentation**: [docs.symbolica.dev](https://docs.symbolica.dev)
- **GitHub Issues**: [github.com/symbolica-ai/symbolica/issues](https://github.com/symbolica-ai/symbolica/issues)
- **Discord Community**: [discord.gg/symbolica](https://discord.gg/symbolica)
- **Email Support**: support@symbolica.dev 