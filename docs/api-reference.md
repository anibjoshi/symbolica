# API Reference

This document provides detailed API documentation for all Symbolica components.

## Core Components

### FactStore

The `FactStore` class manages symbolic facts with indexing and querying capabilities.

```python
class FactStore:
    def __init__(self) -> None
    def add(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> Fact
    def get(self, key: str) -> List[Fact]
    def get_latest(self, key: str) -> Optional[Fact]
    def query(self, pattern: str) -> List[Fact]
    def remove(self, key: str, value: Any = None) -> int
    def clear(self) -> None
    def serialize(self) -> Dict[str, Any]
    def deserialize(self, data: Dict[str, Any]) -> None
```

#### Methods

**`add(key, value, metadata=None)`**
- Adds a new fact to the store
- Returns the created `Fact` object
- Automatically assigns timestamp and default confidence

**`get(key)`**
- Returns all facts with the specified key
- Returns empty list if no facts found

**`query(pattern)`**
- Supports various query patterns:
  - `key:pattern` - Search by key pattern
  - `value:pattern` - Search by value pattern
  - `meta.field:pattern` - Search by metadata field
  - `*pattern*` - Wildcard search
  - `regex:pattern` - Regular expression search

### RuleEngine

The `RuleEngine` class evaluates rules against facts using configurable backends.

```python
class RuleEngine:
    def __init__(self, rules: Optional[List[Rule]] = None, backend: str = "memory") -> None
    def add_rule(self, rule: Rule) -> None
    def remove_rule(self, rule_id: str) -> bool
    def get_rule(self, rule_id: str) -> Optional[Rule]
    def evaluate(self, facts: FactStore, max_iterations: int = 100) -> List[Conclusion]
    def evaluate_with_trace(self, facts: FactStore, max_iterations: int = 100) -> Tuple[List[Conclusion], ReasoningTrace]
    def validate_rules(self) -> List[ValidationError]
    def get_statistics(self) -> Dict[str, Any]
```

#### Methods

**`evaluate(facts, max_iterations=100)`**
- Runs inference on the fact store
- Returns list of conclusions
- Stops when no new conclusions can be drawn or max iterations reached

**`evaluate_with_trace(facts, max_iterations=100)`**
- Same as evaluate but also returns detailed reasoning trace
- Useful for debugging and explanations

### Inference

The `Inference` class orchestrates the reasoning process and generates explanations.

```python
class Inference:
    def __init__(self, engine: RuleEngine) -> None
    def run(self, facts: FactStore, max_iterations: int = 100, timeout_seconds: Optional[float] = None) -> InferenceResult
    def step_by_step(self, facts: FactStore, max_iterations: int = 100) -> Iterator[InferenceStep]
    def explain_conclusion(self, conclusion: Conclusion, facts: FactStore) -> str
    def explain_trace(self, trace: Optional[ReasoningTrace] = None) -> str
    def analyze_performance(self, trace: Optional[ReasoningTrace] = None) -> Dict[str, Any]
```

## Data Types

### Fact

```python
@dataclass
class Fact:
    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
```

### Rule

```python
@dataclass
class Rule:
    id: str
    conditions: List[Condition]
    conclusions: List[Conclusion]
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
```

### Condition

```python
@dataclass
class Condition:
    field: str
    operator: OperatorType
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
```

#### Supported Operators

- `OperatorType.EQ` ("==") - Equality
- `OperatorType.NE` ("!=") - Not equal
- `OperatorType.GT` (">") - Greater than
- `OperatorType.LT` ("<") - Less than
- `OperatorType.GTE` (">=") - Greater than or equal
- `OperatorType.LTE` ("<=") - Less than or equal
- `OperatorType.IN` ("in") - Value in collection
- `OperatorType.CONTAINS` ("contains") - Collection contains value
- `OperatorType.REGEX` ("regex") - Regular expression match
- `OperatorType.EXISTS` ("exists") - Field exists

### Conclusion

```python
@dataclass
class Conclusion:
    fact: Fact
    confidence: float
    rule_id: str
    supporting_facts: List[Fact] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### InferenceResult

```python
@dataclass
class InferenceResult:
    conclusions: List[Conclusion]
    trace: ReasoningTrace
    execution_time_ms: float
    facts_processed: int
    rules_fired: int
```

## Bridges

### LLMBridge

```python
class LLMBridge:
    def __init__(self, llm_client: Any = None, model_name: str = "gpt-3.5-turbo") -> None
    def explain_conclusion(self, conclusion: Conclusion, context: Optional[str] = None) -> str
    def explain_trace(self, trace: ReasoningTrace, context: Optional[str] = None) -> str
    def suggest_rules(self, facts: FactStore, logs: List[str], domain: Optional[str] = None) -> List[Rule]
    def summarize_facts(self, facts: FactStore, max_facts: int = 50) -> str
```

### LangGraph Integration

```python
class SymbolicaNode:
    def __init__(self, rules: List[Rule], llm_bridge: Optional[LLMBridge] = None, 
                 fact_store: Optional[FactStore] = None, node_name: str = "symbolic_reasoning") -> None
    def __call__(self, state: SymbolicaState) -> SymbolicaState
    def create_symbolic_workflow(self) -> StateGraph
```

### Semantic Kernel Integration

```python
class SymbolicaPlugin:
    def __init__(self, rule_engine: RuleEngine, llm_bridge: Optional[LLMBridge] = None,
                 fact_store: Optional[FactStore] = None) -> None
    
    # SK Functions
    def add_fact(self, context: SKContext) -> str
    def run_inference(self, context: SKContext) -> str
    def explain_reasoning(self, context: SKContext) -> str
    def query_facts(self, context: SKContext) -> str
```

## Parsers

### JSONRuleParser

```python
class JSONRuleParser:
    def __init__(self) -> None
    def parse_rules(self, json_data: Union[str, Dict[str, Any]]) -> List[Rule]
    def serialize_rules(self, rules: List[Rule]) -> str
    def get_validation_errors(self) -> List[ValidationError]
```

### YAMLRuleParser

```python
class YAMLRuleParser:
    def __init__(self) -> None
    def parse_rules(self, yaml_data: Union[str, Dict[str, Any]]) -> List[Rule]
    def serialize_rules(self, rules: List[Rule]) -> str
    def get_validation_errors(self) -> List[ValidationError]
```

## Backends

### MemoryBackend

```python
class MemoryBackend:
    def __init__(self) -> None
    def add_fact(self, fact: Fact) -> None
    def get_facts(self, pattern: Optional[str] = None) -> List[Fact]
    def remove_fact(self, key: str, value: Any = None) -> int
    def clear_facts(self) -> None
    def get_statistics(self) -> Dict[str, Any]
    def enable_optimization(self, enabled: bool = True) -> None
```

## Utilities

### Validation

```python
def validate_fact(fact: Fact) -> List[ValidationError]
def validate_rule(rule: Rule) -> List[ValidationError]
def validate_condition(condition: Condition, rule_id: str = "unknown") -> List[ValidationError]
def validate_conclusion(conclusion: Conclusion, rule_id: str = "unknown") -> List[ValidationError]

class RuleValidator:
    def __init__(self, strict: bool = True) -> None
    def add_custom_check(self, check_function: callable) -> None
    def validate(self, rule: Rule) -> List[ValidationError]

class FactValidator:
    def __init__(self, allowed_keys: Optional[List[str]] = None) -> None
    def add_custom_check(self, check_function: callable) -> None
    def validate(self, fact: Fact) -> List[ValidationError]
```

### Logging

```python
def setup_logger(name: str = "symbolica", level: LogLevel = LogLevel.INFO) -> logging.Logger
def get_logger(name: str = "symbolica") -> logging.Logger

class SymbolicaLogger:
    def __init__(self, name: str = "symbolica", level: LogLevel = LogLevel.INFO) -> None
    def set_context(self, **kwargs) -> None
    def info(self, message: str, **kwargs) -> None
    def debug(self, message: str, **kwargs) -> None
    def warning(self, message: str, **kwargs) -> None
    def error(self, message: str, **kwargs) -> None
```

## Error Handling

### ValidationError

```python
@dataclass
class ValidationError:
    rule_id: str
    error_type: str
    message: str
    field: Optional[str] = None
```

Common error types:
- `"empty_conditions"` - Rule has no conditions
- `"empty_conclusions"` - Rule has no conclusions
- `"invalid_operator"` - Unknown operator type
- `"invalid_confidence"` - Confidence not between 0 and 1
- `"duplicate_id"` - Duplicate rule ID found

## Configuration Options

### Backend Types

- `"memory"` - In-memory backend (default)
- `"graph"` - Graph-based backend (requires `symbolica[graph]`)
- `"distributed"` - Distributed backend (requires `symbolica[distributed]`)

### Log Levels

- `LogLevel.DEBUG` - Detailed debugging information
- `LogLevel.INFO` - General information (default)
- `LogLevel.WARNING` - Warning messages
- `LogLevel.ERROR` - Error messages
- `LogLevel.CRITICAL` - Critical errors

### Performance Tuning

```python
# Optimize rule engine
engine = RuleEngine(rules, backend="memory")
engine.resolve_conflicts(strategy="priority")

# Configure fact store indexing
facts = FactStore()
# Indexing is automatically optimized

# Enable backend optimizations
from symbolica.backends import MemoryBackend
backend = MemoryBackend()
backend.enable_optimization(True)
``` 