# Symbolica

A powerful symbolic reasoning engine for LLM agents with natural language explanation capabilities.

## Features

- **Core symbolic reasoning** with FactStore, RuleEngine, and Inference components
- **Multiple rule formats** supporting JSON, YAML, and specialized troubleshooting syntax
- **LLM framework integrations** for LangGraph and Semantic Kernel
- **Natural language explanations** via LLMBridge with fallback support
- **Flexible backends** (memory, graph, distributed)
- **Performance analytics** and detailed reasoning traces

## Quick Start

### Installation

```bash
pip install symbolica
```

### Basic Usage

```python
from symbolica import FactStore, RuleEngine, Inference

# Create facts
facts = FactStore()
facts.add("temperature", 75)
facts.add("humidity", 80)

# Define rules (can load from files)
rules = [
    # Rules can be loaded from JSON, YAML, or troubleshooting format
]

# Run inference
engine = RuleEngine(rules)
inference = Inference(engine)
result = inference.run(facts)

# Get explanations
for conclusion in result.conclusions:
    print(f"Conclusion: {conclusion.fact.value}")
    print(f"Confidence: {conclusion.confidence}")
```

### Database Troubleshooting Example

Symbolica includes specialized support for database troubleshooting rules with an intuitive `if/then` syntax:

```yaml
rule:
  name: "cpu_saturation_detected"
  if:
    all:
      - "cpu_utilization > 90"
      - "cpu_wait_time > 20"
      - "context_switches_per_sec > 5000"
  then:
    diagnosis: "CPU saturation detected"
    confidence: 0.9
    priority: "critical"
```

```python
from symbolica.parsers.troubleshooting_parser import load_troubleshooting_rules

# Load rules from folder
rules, errors = load_troubleshooting_rules("./sample-rules")

# Create facts from metrics
database_metrics = {
    "cpu_utilization": 95,
    "cpu_wait_time": 25,
    "context_switches_per_sec": 6000,
}

facts = FactStore()
for key, value in database_metrics.items():
    facts.add(key, value)

# Run inference
engine = RuleEngine(rules)
inference = Inference(engine)
result = inference.run(facts)

# Get diagnoses
for conclusion in result.conclusions:
    print(f"🏥 {conclusion.fact.value}")
    print(f"   Confidence: {conclusion.confidence:.0%}")
    print(f"   Priority: {conclusion.metadata.get('priority', 'normal')}")
```

## Rule Format Support

### 1. Troubleshooting Rules (YAML)

Perfect for operational monitoring and diagnostics:

```yaml
rule:
  name: "rule_name"
  if:
    all:
      - "metric > threshold"
      - "another_metric < limit"
    any:
      - "condition_a == value"
      - "condition_b != value"
  then:
    diagnosis: "Human-readable diagnosis"
    confidence: 0.85
    metadata:
      priority: "high"
      recommendations:
        - "Action item 1"
        - "Action item 2"
```

Key features:
- **Separation of logic and output** - `if:` for conditions, `then:` for results
- **First-class output fields** - `diagnosis` and `confidence` are required
- **Extensibility** - Additional metadata in `metadata:` block
- **Logical grouping** - `all:` (AND) and `any:` (OR) constructs

### 2. Standard YAML Rules

```yaml
rules:
  - id: "rule_1"
    conditions:
      - field: "temperature"
        operator: ">"
        value: 100
    conclusions:
      - field: "status"
        value: "overheating"
```

### 3. JSON Rules

```json
{
  "rules": [
    {
      "id": "rule_1",
      "conditions": [
        {"field": "count", "operator": ">", "value": 10}
      ],
      "conclusions": [
        {"field": "alert", "value": "high_count"}
      ]
    }
  ]
}
```

## LLM Framework Integrations

### LangGraph Integration

```python
from symbolica.bridges.langraph_hooks import SymbolicaNode

# Add to your LangGraph workflow
def create_workflow():
    workflow = StateGraph(State)
    
    # Add symbolic reasoning node
    workflow.add_node("reasoning", SymbolicaNode(rules_path="./rules"))
    
    return workflow
```

### Semantic Kernel Integration

```python
from symbolica.bridges.semantic_kernel_hooks import SymbolicaPlugin

# Add to your Semantic Kernel
kernel = Kernel()
kernel.add_plugin(SymbolicaPlugin(rules_path="./rules"), plugin_name="symbolica")

# Use in prompts
result = await kernel.invoke("symbolica", "evaluate_facts", facts=facts)
```

## Natural Language Explanations

```python
from symbolica import LLMBridge

# Configure with your preferred LLM
llm_bridge = LLMBridge(
    provider="openai",  # or "anthropic", "azure", etc.
    api_key="your-api-key"
)

# Generate explanations
explanation = llm_bridge.explain_conclusion(conclusion)
trace_explanation = llm_bridge.explain_reasoning_trace(inference_result.trace)
```

## Examples

- **Basic Usage**: `examples/basic_usage.py`
- **Database Troubleshooting**: `examples/database_troubleshooting.py`
- **Rule Formats**: `examples/sample-rules/`

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Run specific test
pytest tests/test_troubleshooting_parser.py -v
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please see our contributing guidelines for details.