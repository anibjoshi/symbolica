# Symbolica Core Refactoring Plan

## 🎯 **Problem Statement**

Current `symbolica/core/` files are becoming monolithic:
- `optimized_rule_engine.py`: **619 lines** (multiple responsibilities)
- `rule_engine.py`: **473 lines** (rule management + evaluation + optimization)
- `inference.py`: **433 lines** (inference + tracing + explanation + performance)
- `fact_store.py`: **390 lines** (storage + indexing + querying)
- `types.py`: **218 lines** (all data types mixed together)

As the project grows, these will become **unmaintainable monoliths**.

## 🏗️ **Proposed Modular Architecture**

### **New Directory Structure**
```
symbolica/core/
├── __init__.py                    # Main exports
├── types/                         # Data Types (Single Responsibility)
│   ├── __init__.py
│   ├── base_types.py             # Fact, Condition, Rule, Conclusion
│   ├── inference_types.py        # InferenceResult, ReasoningTrace, InferenceStep
│   ├── validation_types.py       # ValidationError, BackendType
│   └── operator_types.py         # OperatorType enum and logic
├── engines/                       # Rule Engine Architecture
│   ├── __init__.py
│   ├── base_engine.py            # Abstract RuleEngine interface
│   ├── rule_manager.py           # Rule CRUD operations
│   ├── evaluation_strategies.py  # Standard/Optimized strategy pattern
│   └── unified_engine.py         # Single intelligent engine
├── evaluation/                    # Rule Evaluation Logic
│   ├── __init__.py
│   ├── condition_evaluator.py    # Condition evaluation + caching
│   ├── rule_matcher.py           # Rule matching algorithms
│   └── logical_evaluator.py      # AND/OR/short-circuit logic
├── optimization/                  # Performance Optimizations
│   ├── __init__.py
│   ├── rule_indexer.py           # Fact-to-rule index builder
│   ├── evaluation_cache.py       # Condition evaluation caching
│   ├── performance_monitor.py    # Performance tracking
│   └── adaptive_optimizer.py     # Auto-optimization strategies
├── storage/                       # Data Storage Layer
│   ├── __init__.py
│   ├── fact_store.py             # Fact storage and querying
│   ├── rule_repository.py        # Rule storage and management
│   └── index_manager.py          # Index management
└── inference/                     # Inference Orchestration
    ├── __init__.py
    ├── inference_engine.py       # Main inference orchestration
    ├── trace_generator.py        # Reasoning trace generation
    ├── explanation_generator.py  # Natural language explanations
    └── step_executor.py          # Individual inference step execution
```

## 📋 **Detailed Refactoring Breakdown**

### **1. Types Module (`types/`)**
**Current:** All types mixed in `types.py` (218 lines)
**New:** Split by logical grouping

```python
# types/base_types.py
@dataclass
class Fact: ...
@dataclass  
class Condition: ...
@dataclass
class Rule: ...
@dataclass
class Conclusion: ...

# types/inference_types.py
@dataclass
class InferenceStep: ...
@dataclass
class ReasoningTrace: ...
@dataclass
class InferenceResult: ...

# types/validation_types.py
@dataclass
class ValidationError: ...
class BackendType(Enum): ...

# types/operator_types.py
class OperatorType(Enum): ...
# + operator evaluation logic
```

### **2. Engines Module (`engines/`)**
**Current:** Massive `rule_engine.py` + `optimized_rule_engine.py` (1092 lines total)
**New:** Modular engine architecture

```python
# engines/base_engine.py
from abc import ABC, abstractmethod

class BaseRuleEngine(ABC):
    @abstractmethod
    def evaluate(self, facts: FactStore) -> List[Conclusion]: ...
    
    @abstractmethod
    def add_rule(self, rule: Rule) -> None: ...
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]: ...

# engines/rule_manager.py
class RuleManager:
    def add_rule(self, rule: Rule) -> None: ...
    def remove_rule(self, rule_id: str) -> bool: ...
    def validate_rules(self) -> List[ValidationError]: ...
    def get_conflicts(self) -> List[Tuple[Rule, Rule, str]]: ...

# engines/evaluation_strategies.py
class EvaluationStrategy(ABC):
    @abstractmethod
    def evaluate_rules(self, rules: List[Rule], facts: FactStore) -> List[Conclusion]: ...

class StandardStrategy(EvaluationStrategy): ...
class OptimizedStrategy(EvaluationStrategy): ...

# engines/unified_engine.py
class RuleEngine(BaseRuleEngine):
    def __init__(self, rules=None, strategy="auto"):
        self.rule_manager = RuleManager(rules)
        self.strategy = self._select_strategy(strategy)
    
    def evaluate(self, facts: FactStore) -> List[Conclusion]:
        return self.strategy.evaluate_rules(self.rule_manager.rules, facts)
```

### **3. Evaluation Module (`evaluation/`)**
**Current:** Evaluation logic scattered across engine files
**New:** Focused evaluation components

```python
# evaluation/condition_evaluator.py
class ConditionEvaluator:
    def __init__(self, cache_enabled=True):
        self.cache = EvaluationCache() if cache_enabled else None
    
    def evaluate_condition(self, condition: Condition, fact: Fact) -> bool: ...
    def evaluate_with_cache(self, condition: Condition, fact: Fact) -> bool: ...

# evaluation/rule_matcher.py
class RuleMatcher:
    def can_rule_fire(self, rule: Rule, facts: List[Fact]) -> bool: ...
    def get_matching_facts(self, rule: Rule, facts: List[Fact]) -> List[List[Fact]]: ...
    def find_applicable_rules(self, rules: List[Rule], facts: List[Fact]) -> List[Rule]: ...

# evaluation/logical_evaluator.py
class LogicalEvaluator:
    def evaluate_all_conditions(self, conditions: List[Condition], facts: List[Fact]) -> bool: ...
    def evaluate_any_conditions(self, conditions: List[Condition], facts: List[Fact]) -> bool: ...
    def short_circuit_and(self, conditions: List[Condition], facts: List[Fact]) -> bool: ...
```

### **4. Optimization Module (`optimization/`)**
**Current:** Optimization logic mixed in `optimized_rule_engine.py`
**New:** Dedicated optimization components

```python
# optimization/rule_indexer.py
class RuleIndexer:
    def build_fact_to_rules_index(self, rules: List[Rule]) -> Dict[str, Set[str]]: ...
    def get_relevant_rules(self, fact_names: Set[str]) -> Set[str]: ...
    def update_index(self, rule: Rule) -> None: ...

# optimization/evaluation_cache.py
class EvaluationCache:
    def get(self, condition: Condition, fact_value: Any) -> Optional[bool]: ...
    def set(self, condition: Condition, fact_value: Any, result: bool) -> None: ...
    def get_stats(self) -> Dict[str, Any]: ...

# optimization/performance_monitor.py
class PerformanceMonitor:
    def track_inference(self, execution_time_ms: float, rules_fired: int) -> None: ...
    def get_performance_metrics(self) -> Dict[str, Any]: ...
    def suggest_optimizations(self) -> List[str]: ...

# optimization/adaptive_optimizer.py
class AdaptiveOptimizer:
    def should_optimize(self, rule_count: int, fact_count: int) -> bool: ...
    def select_strategy(self, performance_history: List[Dict]) -> str: ...
    def adapt_based_on_performance(self, metrics: Dict[str, Any]) -> None: ...
```

### **5. Storage Module (`storage/`)**
**Current:** `fact_store.py` handles everything (390 lines)
**New:** Separated storage concerns

```python
# storage/fact_store.py (slimmed down)
class FactStore:
    def __init__(self, backend_type="memory"):
        self.backend = self._create_backend(backend_type)
    
    def add(self, key: str, value: Any, metadata: Dict = None) -> None: ...
    def query(self, pattern: str) -> List[Fact]: ...
    def get_all_facts(self) -> List[Fact]: ...

# storage/rule_repository.py
class RuleRepository:
    def store_rule(self, rule: Rule) -> None: ...
    def load_rule(self, rule_id: str) -> Optional[Rule]: ...
    def list_rules(self, filter_criteria: Dict = None) -> List[Rule]: ...
    def delete_rule(self, rule_id: str) -> bool: ...

# storage/index_manager.py
class IndexManager:
    def create_index(self, field_name: str) -> None: ...
    def update_index(self, field_name: str, old_value: Any, new_value: Any) -> None: ...
    def query_index(self, field_name: str, value: Any) -> List[str]: ...
```

### **6. Inference Module (`inference/`)**
**Current:** `inference.py` does everything (433 lines)
**New:** Separated inference concerns

```python
# inference/inference_engine.py
class InferenceEngine:
    def __init__(self, rule_engine: BaseRuleEngine):
        self.rule_engine = rule_engine
        self.trace_generator = TraceGenerator()
    
    def run(self, facts: FactStore, max_iterations=100) -> InferenceResult: ...
    def step_by_step(self, facts: FactStore) -> Iterator[InferenceStep]: ...

# inference/trace_generator.py
class TraceGenerator:
    def start_trace(self) -> ReasoningTrace: ...
    def add_step(self, trace: ReasoningTrace, step: InferenceStep) -> None: ...
    def finalize_trace(self, trace: ReasoningTrace, conclusions: List[Conclusion]) -> None: ...

# inference/explanation_generator.py
class ExplanationGenerator:
    def explain_conclusion(self, conclusion: Conclusion, trace: ReasoningTrace) -> str: ...
    def explain_trace(self, trace: ReasoningTrace) -> str: ...
    def generate_natural_language(self, steps: List[InferenceStep]) -> List[str]: ...

# inference/step_executor.py
class StepExecutor:
    def execute_step(self, rule: Rule, facts: List[Fact]) -> InferenceStep: ...
    def measure_execution_time(self, func: Callable) -> Tuple[Any, float]: ...
```

## 🔄 **Migration Strategy**

### **Phase 1: Create New Structure (Week 1)**
1. Create new directory structure
2. Move types to `types/` modules
3. Update imports in `__init__.py`
4. Run tests to ensure no breaking changes

### **Phase 2: Refactor Engines (Week 2)**
1. Create `BaseRuleEngine` interface
2. Extract `RuleManager` from current engines
3. Implement strategy pattern for evaluation
4. Create unified `RuleEngine` class

### **Phase 3: Extract Evaluation Logic (Week 3)**
1. Move condition evaluation to `evaluation/`
2. Extract rule matching logic
3. Separate logical evaluation concerns
4. Update engine implementations

### **Phase 4: Modularize Optimization (Week 4)**
1. Extract indexing logic to `optimization/`
2. Separate caching concerns
3. Create performance monitoring
4. Implement adaptive optimization

### **Phase 5: Separate Storage & Inference (Week 5)**
1. Refactor fact store
2. Create rule repository
3. Modularize inference engine
4. Extract tracing and explanation

### **Phase 6: Integration & Testing (Week 6)**
1. Integration testing
2. Performance benchmarking
3. Update documentation
4. Finalize API

## ✅ **Benefits of This Refactoring**

### **Maintainability**
- ✅ **Single Responsibility** - Each module has one clear purpose
- ✅ **Focused Files** - No file > 200 lines
- ✅ **Easy Testing** - Test individual components in isolation
- ✅ **Clear Dependencies** - Explicit module relationships

### **Extensibility**  
- ✅ **Plugin Architecture** - Easy to add new evaluation strategies
- ✅ **Swappable Components** - Replace optimization modules independently
- ✅ **Interface-Based** - Abstract base classes for consistent APIs
- ✅ **Future-Proof** - Easy to add new features without breaking existing code

### **Developer Experience**
- ✅ **Easier Onboarding** - New developers can understand individual modules
- ✅ **Parallel Development** - Multiple developers can work on different modules
- ✅ **Debugging** - Isolate issues to specific modules
- ✅ **Code Reviews** - Smaller, focused changes

### **Performance**
- ✅ **Lazy Loading** - Import only needed modules
- ✅ **Modular Optimization** - Enable/disable optimizations independently
- ✅ **Better Caching** - Module-specific caches
- ✅ **Profiling** - Profile individual components

## 🎯 **Success Metrics**

- **File Size**: No module > 200 lines
- **Test Coverage**: Each module has dedicated tests
- **Performance**: No regression in benchmark tests
- **API Stability**: Existing code works without changes
- **Documentation**: Each module has clear documentation

This refactoring sets up Symbolica for **sustainable growth** and **long-term maintainability**! 