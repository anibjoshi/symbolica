# Symbolica — As-Is Architecture & Status Analysis

*Baseline document for the architectural-cleanup refactor. Reflects the codebase at commit `e088461` (branch `main`), 2026-06-10.*

---

## 1. Executive Summary

Symbolica is a **YAML-driven, deterministic rule engine for AI agents**, written in pure Python (only runtime dependency: PyYAML). Its differentiators are:

- **Safe AST-based expression evaluation** (no `eval()`, whitelisted node types, timeouts, recursion/length limits).
- **Hybrid neuro-symbolic rules** via a built-in `PROMPT()` function that calls an LLM (OpenAI/Anthropic) from inside rule conditions and actions, with prompt-injection hardening and type coercion.
- **Explainability**: every execution produces structured reasoning traces designed to be fed back to an LLM.
- **Temporal reasoning**: a thread-safe time-series/TTL fact store with windowed aggregate functions.
- **Forward chaining** (iterative execution with explicit `triggers` and DAG-derived ordering) and **backward chaining** (goal-seeking) — though backward chaining is currently broken (see §10.1).

The architecture is broadly layered and sensible (public `core` → `_internal` implementation → optional `llm` module), but the codebase shows clear **mid-refactor artifacts**: a runtime-broken public API, a dead parallel security module, duplicated evaluator logic, an unenforced `enabled` field, conflicting pytest configs, version drift, and an untracked schema directory. These are catalogued in §10 and are the natural worklist for the cleanup.

**Size:** ~19k lines of Python total; ~5.5k in the shipped `symbolica/` package (excluding tests), ~7.5k of tests, ~1.7k in the standalone `visualization/` toolkit, the rest in examples.

---

## 2. Project Overview

| Aspect | Detail |
|---|---|
| Package name | `symbolica` (hatchling build; wheel ships only `symbolica/`) |
| Version | `0.0.3` in `symbolica/__init__.py` — but the last merged branch was named `v0.1.2` (drift, §10.8) |
| Python support | 3.8 – 3.12, `py.typed`, strict mypy config |
| Runtime deps | `pyyaml>=6.0` only |
| Optional deps | `openai` (implied, not declared), `langchain`, `semantic-kernel` extras |
| License | MIT |
| Status | Beta (classifier: Development Status 4) |
| CI | **None** — no `.github/workflows/` |

---

## 3. Repository Layout

```
symbolica/                  # the shipped package
  __init__.py               # public API surface (~96 lines)
  core/                     # public layer
    engine.py               # Engine — orchestrator/facade (614 lines)
    models.py               # Rule, Facts, ExecutionResult, Goal, ExecutionContext
    interfaces.py            # ConditionEvaluator, ExecutionStrategy ABCs
    exceptions.py            # exception hierarchy + ErrorCollector
    services/                # loader.py, function_registry.py, temporal_service.py
    validation/              # ValidationService + 4 schema/structure validators
    config/system_config.py  # central limits/constants
  _internal/                 # implementation layer (not public)
    evaluation/              # AST evaluator stack (core/trace/path), builtins, field extractor
    strategies/              # dag.py (topo ordering), backward_chainer.py (goal seeking)
    storage/temporal_store.py
  llm/                       # optional LLM integration (adapter, PROMPT evaluator, security)
  schemas/rule.schema.json   # JSON Schema for rule files — UNTRACKED in git
  tests/                     # unit/ + integration/ + fixtures (~7.5k lines)
visualization/               # standalone, NOT packaged — AST/DAG/rule visualizers
examples/                    # 11 numbered, progressive examples (the de-facto feature catalog)
```

---

## 4. Architecture

### 4.1 Layering

```
        ┌──────────────────────────────────────────────┐
        │ Public API (symbolica/__init__.py)           │
        │   Engine, Rule, Facts, ExecutionResult,      │
        │   Goal, facts(), goal(), exceptions          │
        └───────────────────────┬──────────────────────┘
                                │
        ┌───────────────────────▼──────────────────────┐
        │ core/ — orchestration & domain               │
        │   Engine (facade) ── services (Loader,       │
        │   FunctionRegistry, TemporalService) ──      │
        │   validation (ValidationService + schema     │
        │   validators) ── models ── interfaces        │
        └───────────────────────┬──────────────────────┘
                                │ (Engine hard-instantiates these)
        ┌───────────────────────▼──────────────────────┐
        │ _internal/ — implementation                  │
        │   ASTEvaluator ⟶ {CoreEvaluator,             │
        │     TraceEvaluator, ExecutionPathEvaluator,  │
        │     FieldExtractor}                          │
        │   DAGStrategy, BackwardChainer               │
        │   TemporalStore                              │
        └───────────────────────┬──────────────────────┘
                                │ (optional, graceful degradation)
        ┌───────────────────────▼──────────────────────┐
        │ llm/ — LLMClientAdapter, PromptEvaluator,    │
        │   PromptSanitizer/OutputValidator, LLMConfig │
        └──────────────────────────────────────────────┘
```

Import direction is clean: `_internal` depends only on `core` (models, exceptions, interfaces) and conditionally on `llm` (via `TYPE_CHECKING` / runtime injection). No circular imports. `visualization/` is fully decoupled — it duck-types against public `Rule` attributes and only lazily imports `symbolica` in two helper functions.

### 4.2 Dependency wiring

There is **no dependency injection**. `Engine.__init__` (`core/engine.py:40-113`) directly constructs every collaborator: `FunctionRegistry`, `ValidationService`, `RuleLoader`, `TemporalService`, `ASTEvaluator`, `DAGStrategy`, `BackwardChainer`. The `interfaces.py` ABCs (`ConditionEvaluator`, `ExecutionStrategy`) exist and are implemented (`ASTEvaluator`, `DAGStrategy`) but Engine never accepts alternative implementations — the abstractions are currently decorative at the construction boundary.

LLM integration is wired conditionally: if an `llm_client` is passed, Engine attempts to import `LLMClientAdapter` + `PromptEvaluator` and injects the prompt evaluator into the evaluator stack; on import failure it logs and continues without `PROMPT()` (`core/engine.py:76-100`).

### 4.3 Execution flow (`Engine.reason`)

1. `reason(input_facts)` (`engine.py:298`) — coerces `dict` → `Facts`, creates a mutable `ExecutionContext`.
2. `_execute_rules_iteratively` (`engine.py:327`) — loops up to `max_iterations` (default 10):
   - Computes order for *remaining* (not-yet-fired) rules via `DAGStrategy.get_execution_order` (priority-aware topological sort), falling back to plain priority ordering on DAG failure.
   - For each rule: evaluates the condition with tracing; on true, evaluates `facts:` (intermediate state) and `actions:` (verdict outputs) — values may themselves be expressions or `{{ template }}` strings; records reasoning and which rule's `triggers` caused this firing.
   - Converges when an iteration fires nothing.
3. Returns a frozen `ExecutionResult` (verdict, fired_rules, timing, reasoning, intermediate facts) carrying the `ExecutionContext` privately for rich hierarchical traces.

Each rule fires **at most once per `reason()` call**. Errors during a rule's evaluation are logged, recorded, and treated as "did not fire" rather than aborting the run.

---

## 5. Domain Model (`core/models.py`)

| Class | Mutability | Fields / purpose |
|---|---|---|
| `Rule` (l.14) | frozen | `id`, `priority`, `condition` (expression string), `actions` (verdict outputs, required), `facts` (intermediate state), `tags`, `triggers` (rule IDs to chain), `description`, `enabled`. Heavy `__post_init__` validation. |
| `Facts` (l.48) | frozen | immutable input container with `get`/`__getitem__`/`__contains__`; `facts(**kw)` factory. |
| `ExecutionResult` (l.68) | frozen | `verdict`, `fired_rules`, `execution_time_ms`, `reasoning`, `intermediate_facts`, private `_context`. Rich accessors: `get_llm_context()`, `get_hierarchical_reasoning()`, `explain_decision_path()`, `get_critical_conditions()`, JSON variants. |
| `Goal` (l.158) | frozen | `target_facts: Dict` only; `goal(**kw)` factory. **Mismatched with its consumer** — see §10.1. |
| `ExecutionContext` (l.180) | mutable | working state during a run: `enriched_facts`, `fired_rules`, reasoning steps, per-rule execution-path traces, verdict/intermediate tracking, `get_llm_reasoning_context()`. |

A deliberate design split: inputs and outputs are frozen; only the in-flight `ExecutionContext` mutates.

---

## 6. Feature Set

The 11 numbered examples are the authoritative feature catalog:

| # | Feature | Key API |
|---|---|---|
| 01 | Basic YAML rules, priorities, reasoning output | `Engine.from_yaml/from_file`, `reason()` |
| 02 | Custom functions (safe lambdas; `allow_unsafe` for full functions) | `register_function()` |
| 03 | Rule chaining / workflows | `triggers:` on rules, DAG ordering |
| 04 | LLM integration in conditions/actions | `PROMPT("...", "bool")`, `llm_client=` |
| 05 | Temporal functions on time-series data | `store_datapoint()`, `recent_avg/max/min/count`, `sustained_above/below`, TTL facts |
| 06 | Backward chaining / goal seeking | `goal()`, `find_rules_for_goal()`, `can_achieve_goal()` — **currently broken (§10.1)** |
| 07 | Everything combined; multi-file loading | `Engine.from_directory()` |
| 08 | LangGraph integration pattern | hybrid: LangGraph conversation + Symbolica routing |
| 09 | Nested structured conditions | `all:` / `any:` / `not:` YAML trees |
| 10 | Template evaluation in actions | `"{{ expression }}"` substitution |
| 11 | Mathematical + temporal combined | arithmetic operators + temporal funcs |

### 6.1 Rule YAML format

```yaml
rules:
  - id: "premium_eligible"          # required, ^[A-Za-z0-9_-]+$
    priority: 100                    # higher fires first
    condition:                       # string expression OR structured tree
      all:
        - "age >= 18"
        - any:
            - "credit_score >= 750"
            - all:
                - "credit_score >= 650"
                - "employment_years >= 2"
        - not: "bankruptcy == true"
    facts:                           # intermediate facts visible to later rules
      risk_band: "low"
    actions:                         # final verdict outputs (required)
      approved: true
      summary: "{{ PROMPT('Summarize for {name}') }}"
    triggers: ["send_offer"]         # forward-chain these rules next
    tags: ["underwriting"]
    enabled: true                    # parsed but NOT enforced (§10.2)
```

Structured `all/any/not` trees are flattened to a single expression string by `RuleLoader.ConditionParser` (`core/services/loader.py:18-65`) before evaluation. `if`/`then` are accepted as aliases for `condition`/`actions`.

### 6.2 Expression language

AST-subset of Python: booleans (`and/or/not`), comparisons (incl. `in`, `is`), arithmetic (`+ - * / % **`), names, constants, lists, subscripts, and calls to **registered functions only**. Built-ins (`_internal/evaluation/builtin_functions.py`): `len`, `sum`, `abs`, `startswith`, `endswith`, `contains`, plus `PROMPT` (LLM) and the nine temporal functions registered by `TemporalService`.

---

## 7. Subsystem Detail

### 7.1 Validation pipeline (`core/validation/`)

Layered, runs at load time and on `add_rule`:

1. **YamlStructureValidator** — root must be a dict with required `rules` list; allowed top-level keys: `rules`, `version`, `description`, `metadata`.
2. **RuleStructureValidator** — per-rule required (`id`, `condition`, `actions`, with `if/then` aliases) and allowed fields, type checks.
3. **IdentifierValidator** — IDs/function names must be Python identifiers and not in `SYSTEM_RESERVED_KEYWORDS` (`schema_constants.py` — covers Python keywords, built-in function names, temporal function names).
4. **ValidationService** (`validation_service.py`) — semantic checks across the rule set: per-field validity, duplicate IDs, `triggers` referencing existing rules, no self-triggers, no circular trigger chains (3-color DFS).

`SchemaValidator` is a facade over 1–3. There is also a JSON Schema (`symbolica/schemas/rule.schema.json`, draft 2020-12) that formalizes the same contract — but the Python validators are hand-rolled and the JSON schema is **not used at runtime and not committed to git** (§10.7).

### 7.2 Services (`core/services/`)

- **RuleLoader** — `from_yaml/from_file/from_directory` → `List[Rule]`; owns the structured-condition → string conversion; `strict_validation` flag toggles schema vs. legacy validation.
- **FunctionRegistry** — name-validated registration; lambdas considered safe, full functions require `allow_unsafe=True`; `register_system_function()` bypasses reserved-keyword checks (used for temporal builtins).
- **TemporalService** — owns `TemporalStore`; registers the nine temporal functions; exposes stats/cleanup/TTL operations that `Engine` re-exports.

### 7.3 Internal evaluator stack (`_internal/evaluation/`)

Composition, not inheritance — `ASTEvaluator` (`evaluator.py:23`) fronts four parts:

- **CoreEvaluator** (`core_evaluator.py`) — the real evaluator. `ast.parse(mode='eval')` with `@lru_cache` on parse; whitelist of ~15 safe node types (`SAFE_NODE_TYPES`, l.25-43); `SecurityError` on anything else; SIGALRM-based `evaluation_timeout()`; recursion-depth and expression-length limits from `SystemConfig`. Dispatches per node type; `_eval_call` special-cases `PROMPT` to delegate to an injected `PromptEvaluator`.
- **TraceEvaluator** — wraps CoreEvaluator; returns `ConditionTrace` (expression, result, field→value map, `explain()`).
- **ExecutionPathEvaluator** — parallel implementation that builds a step-by-step `ExecutionPath` (typed `ExecutionStep` nodes with timing and child results) used for hierarchical/LLM reasoning output. *Note: re-implements evaluation rather than instrumenting CoreEvaluator — see §10.4.*
- **FieldExtractor** — AST visitor that extracts referenced field names (excluding function names/literals), with regex fallback; consumed by `DAGStrategy` and `BackwardChainer` for dependency analysis.

`ASTEvaluator._update_function_registry()` manually fans registration out to all four components (§10.5).

### 7.4 Strategies (`_internal/strategies/`)

- **DAGStrategy** (`dag.py`) — builds a rule-dependency graph from extracted condition fields vs. produced `actions`/`facts` fields; 3-color DFS cycle detection (`DAGError`); Kahn's-algorithm topological sort with priority tie-breaking; `get_dependency_analysis()` reports depth/independence. Despite the package keywords advertising "parallel execution," **execution is sequential** — the DAG is used only for ordering.
- **BackwardChainer** (`backward_chainer.py`) — indexes `produced field → rules`; `find_supporting_rules` / `can_achieve_goal` with recursive sub-goal chaining (hard-coded max depth 5, visited-set loop protection). Operates on `goal.field` / `goal.expected_value` — attributes the `Goal` model does not have (§10.1).

### 7.5 Temporal store (`_internal/storage/temporal_store.py`)

- Time series: `Dict[key, deque(maxlen=max_points_per_key)]` of `TimeSeriesPoint(timestamp, value)`; windowed `avg/max/min/count` and `sustained_condition` (requires ~80% window coverage).
- TTL facts: `Dict[key, (value, expires_at)]` with lazy expiry on read plus periodic cleanup.
- All access behind a `threading.RLock`; defaults: 1h max age, 1000 points/key, 300s cleanup interval; tracks a rough memory estimate.

### 7.6 LLM module (`symbolica/llm/`)

- **LLMClientAdapter** (`client_adapter.py`) — duck-type detection of OpenAI vs. Anthropic clients; **sync-only** `complete()`; per-call latency via `perf_counter`; cost estimated at ~4 chars/token (no model-specific pricing); keeps last 100 calls of history; pre-flight prompt security scan.
- **PromptEvaluator** (`prompt_evaluator.py`) — implements `PROMPT(template, return_type='str', max_tokens?)`: sanitizes fact values, substitutes `{var}` placeholders, calls the adapter, then `OutputValidator` coerces the response (regex number extraction for int/float; word-list matching for bool, defaulting to `False`; 500-char truncation). Includes its own `PromptSanitizer` with ~20 regex injection patterns, length caps, and special-char-density checks; logs execution IDs, cost, tokens, threats.
- **security.py** — a *parallel* set of `PromptSanitizer` / `OutputValidator` / `SimpleAuditor` / `LLMSecurityHardener` classes with a `ThreatLevel` enum. **Never imported by production code** — only by its own test file (§10.3).
- **LLMConfig** — knobs: max_tokens 50, max response 200 chars, temperature 0.1, timeout 10s, max cost/execution $0.50, max prompt 2000 chars.
- No response caching, no async path, no retry logic.

### 7.7 Visualization toolkit (`visualization/`, not packaged)

Three classes — `ASTVisualizer` (condition AST trees), `DAGVisualizer` (dependency graph, execution levels, critical path, Graphviz DOT export), `RuleVisualizer` (facade; HTML report with embedded CSS, JSON export, text summaries). Pure stdlib; duck-types over `Rule` attributes; **re-implements dependency analysis with regex heuristics** rather than reusing `DAGStrategy`/`FieldExtractor`, so its graph can disagree with the engine's; no cycle detection; uses a `sys.path.insert` hack for its examples. README mentions plotly/matplotlib but neither is imported.

---

## 8. Testing & Tooling

- **Tests**: ~7.5k lines. `tests/unit/` (18 files: engine core/yaml/files, models, custom functions, temporal, chaining, expression actions, string action values, error scenarios, AST security, mock LLM, LLM integration/security/tracing, internal evaluator) + `tests/integration/` (end-to-end, hybrid AI arithmetic, YAML workflows). `conftest.py` provides facts/rule/YAML/directory fixtures. A `MockLLMClient` (prompt→response mapping, call history) enables LLM tests without API keys.
- **Markers**: `unit`, `integration`, `critical`, `extended`, `slow`, `performance`; Makefile exposes ~12 targets keyed to them (`make test` = critical, `test-ci`, `coverage`, etc.).
- **Config conflict**: `pytest.ini` (testpaths `symbolica/tests`, timeout 30s, its own markers) **and** `[tool.pytest.ini_options]` in `pyproject.toml` (testpaths `["symbolica", "example_usage"]` — `example_usage` doesn't exist; coverage gate `--cov-fail-under=80`; different marker list). pytest.ini wins silently; pyproject's pytest section is dead config (§10.6).
- **Lint/type**: black (88), isort, ruff (broad rule set), strict mypy — configured but **no CI to enforce any of it**.

---

## 9. Implementation Details Worth Capturing

These are behaviors a refactor must preserve (or consciously change):

1. **Security model is whitelist-AST, not sandboxed eval.** Safety rests entirely on `SAFE_NODE_TYPES` + registered-function dispatch + SIGALRM timeout + recursion/length caps. SIGALRM is **main-thread-only and Unix-only** — the timeout silently can't apply on Windows or in worker threads.
2. **Rules fire at most once per `reason()`**; iteration continues (≤10 rounds) until a fixed point. Rule errors are swallowed (logged + recorded), never propagated.
3. **`facts:` vs `actions:` distinction**: `facts` entries become intermediate state visible to later rules but excluded from the verdict; `actions` entries go to the verdict. Both support literal values, bare expressions, and `{{ template }}` strings — the value-evaluation heuristics in `Engine._evaluate_action_value` decide which path a value takes.
4. **Parse caching**: expression ASTs are `@lru_cache`d; the cache key is the expression string, shared engine-wide.
5. **Priority semantics**: priority is a tie-breaker within DAG topological levels, and the total ordering when the DAG fails.
6. **Reserved-word coupling**: adding any new built-in or temporal function requires updating `SYSTEM_RESERVED_KEYWORDS`, or user rules could shadow it / validation drifts.
7. **Graceful LLM degradation**: an engine constructed without an `llm_client` still validates rules containing `PROMPT()` (placeholder registration) — they fail only at evaluation time.
8. **TemporalStore is the only thread-safe component.** Engine itself, the function registries, and the evaluator stack have no locking; concurrent `reason()` calls on one Engine share a parse cache (safe) but `register_function` during execution is racy.
9. **Performance claim**: README's "6,000+ executions/second, sub-millisecond" has a `performance` pytest marker behind it but no committed benchmark results or CI gate.

---

## 10. Defects, Dead Code & Mid-Refactor Artifacts (refactor worklist)

### 10.1 Backward chaining is broken at runtime — public API + example 06 crash
`Goal` (`core/models.py:158`) defines only `target_facts`, but `BackwardChainer` reads `goal.field` / `goal.expected_value` throughout (`backward_chainer.py:62-97,156-187,233-234`). `Engine.find_rules_for_goal` / `can_achieve_goal` pass the Goal straight through. **Verified live**: `engine.find_rules_for_goal(goal(approved=True))` raises `AttributeError: 'Goal' object has no attribute 'field'`. `examples/06_backward_chaining/example.py` uses exactly this path, so the shipped example is broken. One side of an incomplete model migration.

### 10.2 `Rule.enabled` is parsed, validated, documented — and never enforced
`_execute_rules_iteratively` (`engine.py:327-350`) never filters on `enabled`; disabled rules fire normally.

### 10.3 `llm/security.py` is a dead parallel implementation
`PromptSanitizer`/`OutputValidator`/`SimpleAuditor`/`LLMSecurityHardener` + `ThreatLevel` duplicate (with different logic) the classes inside `prompt_evaluator.py`. No production import exists; only `tests/unit/test_llm_security_hardening.py` exercises it. Pick one implementation and delete the other.

### 10.4 Duplicated evaluation logic in the evaluator stack
`ExecutionPathEvaluator` re-implements node evaluation (its `_compare` at `execution_path_evaluator.py:151` is a copy of `CoreEvaluator._compare` at `core_evaluator.py:203`); its unary handler mislabels arithmetic `+/-` as `BOOLEAN_NOT` (`execution_path_evaluator.py:280`). Two evaluators can drift semantically — a prime refactor target (instrument one evaluator instead of maintaining two).

### 10.5 Manual function-registry fan-out
`ASTEvaluator._update_function_registry()` (`evaluator.py:45-68`) copies the function table into four components; a partial failure desynchronizes them. Should be one shared registry reference.

### 10.6 Conflicting/dead build & test config
Duplicate pytest configuration (`pytest.ini` vs `[tool.pytest.ini_options]`; the latter is silently ignored and references a nonexistent `example_usage` path and an unenforced 80% coverage gate). No CI workflow exists despite extensive Makefile/lint/mypy setup.

### 10.7 `symbolica/schemas/` is untracked
`rule.schema.json` formalizes the YAML contract but isn't committed, isn't loaded at runtime, and overlaps with the hand-rolled validators — three sources of truth for the rule schema (JSON schema, validator classes, `schema_constants.py`).

### 10.8 Version & docs drift
`__version__ = "0.0.3"` vs. merged branch `v0.1.2`; main README's example index omits 08/09 inconsistently vs. `examples/README.md`; package description/keywords advertise "parallel execution" which doesn't exist; visualization README mentions plotly/matplotlib that are never used.

### 10.9 Smaller items
- Engine reaches into evaluator privates (`_evaluator._core`) for action-value evaluation; `add_rule`/`update_rule` rebuild the `BackwardChainer` by hand.
- Hard-coded constructor wiring makes Engine untestable with fakes despite existing ABCs (§4.2).
- BackwardChainer max depth (5) hard-coded; SIGALRM timeout platform limits (§9.1).
- Visualization duplicates dependency analysis with weaker heuristics and a `sys.path` hack.
- `from_yaml` module-level alias kept "for backward compatibility" at version 0.0.x.
- LLM cost estimation is a 4-chars/token heuristic with no per-model pricing; no caching/retry/async despite deterministic low-temperature prompts.

---

## 11. Suggested Refactor Focus (derived from the above)

1. **Fix correctness first**: Goal/BackwardChainer contract (10.1), `enabled` enforcement (10.2) — both need tests that currently don't exist.
2. **Collapse duplication**: one evaluator with pluggable tracing (10.4), one LLM security implementation (10.3), one source of truth for the rule schema (10.7), one pytest config (10.6).
3. **Introduce real seams**: constructor-inject `ConditionEvaluator`/`ExecutionStrategy`/registry into Engine (4.2, 10.5) — the interfaces already exist.
4. **Align docs/metadata with reality**: version, README example index, "parallel" claims (10.8).
5. **Add CI** to enforce the already-configured lint/type/test/coverage gates.
