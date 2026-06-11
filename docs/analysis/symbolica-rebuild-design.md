# Symbolica v2 — Rebuild Design

*Clean-break rebuild. Core first (rules, expressions, chaining, explainability); LLM,
temporal, and backward chaining follow as separate increments. Built in place on a
long-lived branch; `main` keeps v1 until parity. Companion docs: `symbolica-as-is-analysis.md`
(what exists), `symbolica-correctness-bugs.md` (what must never happen again),
`symbolica-research-synthesis.md` (industry/academic research → decisions; updated 2026-06-11 —
this design incorporates its outcomes).*

---

## 1. Design principles

Each principle traces to a class of v1 failures:

1. **No heuristics — everything explicit.** v1 *guessed* whether an action value was an
   expression (bugs #1–#3). In v2, nothing is inferred from string contents; expressions
   are syntactically marked.
2. **One evaluator.** v1 had two divergent implementations, evaluated every condition
   twice, and the deciding one skipped the security checks (bug #5). v2 has a single
   evaluator; tracing is a hook, not a second implementation.
3. **Errors are data, never silence.** v1 swallowed every failure into "condition is
   false" or "rule fired with no actions" (bugs #6, #11). v2 returns structured errors on
   the result; `strict=True` raises instead.
4. **Defined execution semantics.** Priority conflicts, trigger gating, verdict contents,
   and `enabled` were undefined or wrong (bugs #4, #8, #9, #10). v2 ships a written
   semantics contract with conformance tests.
5. **Thread-safe and platform-neutral by construction.** No signals (bug #7), no shared
   mutable evaluator state; the engine is immutable after build, all per-run state lives
   in a per-call context.
6. **Compile once, run many.** Rules are parsed, security-validated, and
   dependency-analyzed at load time into immutable compiled forms. Runtime never parses.

## 2. The v2 rule language (clean break)

```yaml
version: 2
rules:
  - id: premium_eligible
    priority: 100
    when:
      all:
        - age >= 18
        - any:
            - credit_score >= 750
            - all:
                - credit_score >= 650
                - employment_years >= 2
        - not: bankruptcy
    set:                       # intermediate facts (working memory, not verdict)
      risk_band: low
    emit:                      # verdict outputs
      approved: true
      monthly_rate: "= base_rate * 0.9"     # '=' prefix marks an expression
      summary: "Approved at {= monthly_rate} for {= name}"   # string interpolation
  - id: notify
    after: [premium_eligible]  # gating lives on the DEPENDENT rule
    when: approved == true
    emit:
      notification: queued
```

Decisions, mapped to the v1 bug they eliminate:

| Construct | v2 rule | Eliminates |
|---|---|---|
| **Expression marking** | Plain YAML values are always literals. A string starting with `=` is an expression. `{= expr }` interpolates inside strings (a real implementation, in core). Literal leading `=` is escaped `==`. | #1, #2, #3 |
| **`when` / `set` / `emit`** | Renamed from `condition`/`facts`/`actions` — the old names were ambiguous (`facts` collided with input facts; `actions` implied imperative effects). `emit` values go to the verdict; `set` values go to working memory only. | — |
| **Verdict** | The verdict contains **every `emit` of every fired rule**, even if the value equals an input fact. A separate `result.changed` view diffs against inputs for callers who want that. | #4 |
| **Priority & conflicts** | Execution order = dependency order, then priority (high first), then document order — fully deterministic. When multiple fired rules `emit` the same key, **highest priority wins**; equal priority on the same key is a load-time validation error unless the rules are mutually exclusive by `after` chains. | #8 |
| **Chaining** | `after: [rule_ids]` on the *dependent* rule: it is not eligible until all listed rules have fired (an `after_any` variant covers OR). This actually gates execution. v1's `triggers` (annotation on the antecedent, gating nothing) is gone. | #9 |
| **`enabled: false`** | Excluded at load time; never evaluated, reported in `engine.skipped_rules`. | #10 |
| **Missing facts** | Referencing an undefined fact yields a structured `MISSING_FACT` diagnostic (rule id, expression, JSON-path to the missing name); the rule does not fire, the run continues, and the trace marks the missing read distinctly — it is **never** coerced to false. Deliberate tolerance is explicit: `default(credit_score, 0)` / `has(credit_score)`. `strict=True` raises. *(CEL-style; chosen over Rego-style silent undefined because the harness repair loop consumes diagnostics — see symbolica-research-synthesis.md §1.)* | #11 |
| **No implicit coercion** | Cross-type comparison (`1 == "1"`) is a type diagnostic, never a boolean (CEL's rule — coercion is "a common source of bugs"). Type coercion exists in exactly one place: explicit typed `PROMPT()` returns. | #1-class |
| **Schema** | One source of truth: a versioned JSON Schema (draft 2020-12) shipped in the package and enforced at load. The hand-rolled validator stack is gone; only semantic checks (duplicate ids, unknown `after` targets, conflict analysis, cycles) remain in code. | symbolica-as-is-analysis.md §10.7 |

Expression language: same scope as v1 (boolean/comparison/arithmetic/membership on
names, constants, lists, subscripts, registered function calls) — that part was sound.
Same whitelist-AST security posture, enforced once at **compile time**.

## 3. Architecture

```
symbolica/
  __init__.py        # Engine, RuleSet, facts(), ExecutionResult, errors — the whole API
  engine.py          # thin facade: build (compile) + reason (execute)
  dsl/
    schema_v2.json   # the rule-file contract (versioned, packaged)
    parser.py        # YAML -> validated raw structures (jsonschema) -> Rule objects
    analyzer.py      # load-time: duplicate ids, after-targets, emit-conflict analysis,
                     #   dependency graph + cycle detection (compile-time, not per-run)
  expr/
    compiler.py      # parse + AST whitelist + field extraction -> CompiledExpr (frozen)
    evaluator.py     # THE evaluator: eval(CompiledExpr, Bindings, deadline, hook=None)
    functions.py     # builtin registry; engine-level registry frozen at build time
    interpolate.py   # "{= expr }" string interpolation (compiled at load too)
  runtime/
    executor.py      # pass-based forward chaining per §4
    context.py       # per-run working memory; verdict assembly with priority resolution
    result.py        # ExecutionResult: verdict, changed, fired, errors, trace
    trace.py         # structured per-rule trace built from evaluator hook events
  analysis/          # optional introspection: explain ordering, dependency reports
```

Key mechanics:

- **`CompiledRule`**: at `Engine.build(ruleset)`, every `when`, `= expr`, and
  interpolation is compiled to a `CompiledExpr` — AST validated, fields pre-extracted,
  length/recursion-checked, and **compiled to closures with cost-ordered short-circuit
  evaluation**: within `and`/`or`, cheap symbolic predicates evaluate before expensive
  leaves, so an LLM `PROMPT()` leaf is reached only when it can still change the
  outcome. A per-evaluation budget ceiling returns a structured `BUDGET_EXCEEDED`
  diagnostic instead of blocking. (No Rete — see symbolica-research-synthesis.md §2 for the evidence
  and the recorded reversal thresholds.) The dependency DAG and execution order skeleton are computed
  here. Load fails loudly on any violation. The Engine and everything in it is immutable
  afterward — "add a rule" means building a new engine from `ruleset.with_rule(r)`,
  which removes the v1 registry-desync and concurrent-mutation classes entirely.
- **One evaluation per rule per pass.** The executor calls the evaluator once; the boolean
  result both gates and is recorded. Tracing is an `on_step` callback the evaluator
  invokes with `(node, value)` events — the trace is a *byproduct* of the only
  evaluation, so it cannot disagree with it (kills the double-eval/double-`PROMPT()`
  class before the LLM layer even returns).
- **Deadline timeout**: the evaluator checks `time.monotonic() > deadline` at node-visit
  granularity. Works on every platform and thread; no `signal`.
- **Dependency injection where it matters**: `Engine(ruleset, *, functions=...,
  executor=..., clock=...)` — defaults provided, fakes injectable for tests.

## 4. Execution semantics (the contract)

1. Inputs are immutable `Facts`. Working memory starts as a copy.
2. Execution proceeds in **passes**. In each pass, every *eligible* unfired rule is
   evaluated in the fixed order (dependency → priority desc → document order). Eligible =
   `enabled`, not yet fired, and all `after` antecedents fired.
3. A true `when` fires the rule: `set` entries update working memory; `emit` entries are
   staged for the verdict. A rule fires **at most once per run** — by spec, a rule whose
   inputs change *after* it fired does not re-fire within the run (fact-version
   refraction was considered and rejected for v2: implicit re-fire is invisible control
   flow machine authors can't reason about; see symbolica-research-synthesis.md §2).
4. An evaluation error means the rule **did not fire** (it is *not* in `fired`), and a
   structured `RuleError {rule_id, phase, expression, error}` is appended to
   `result.errors`. `set`/`emit` application is **all-or-nothing per rule**: values are
   computed first, applied only if all succeed.
5. Run ends at fixpoint (a pass fires nothing) or `max_passes` (default 16; hitting the
   cap is reported on the result, not silent).
6. **Verdict assembly** happens at the end: for each emitted key, the value from the
   highest-priority firing rule wins; document order breaks exact ties (and load-time
   analysis warns about them). `result.fired` lists rules in firing order.
7. Determinism guarantee: identical ruleset + facts + registered functions ⇒ identical
   `verdict`, `fired`, `errors` (function purity is the caller's responsibility and is
   documented as such).
8. **Trace schema** (modeled on OPA decision logs + W3C trace-context — the closest
   thing to an industry standard): `decision_id`, `trace_id`/`span_id`, fired rule ids
   in order, field values consumed per rule, structured diagnostics, and (once the LLM
   layer lands) per-`PROMPT()` call records with a replay cache. Compact and structured
   — evidence says concise structured traces serve downstream LLMs best; verbosity
   configurable.
9. **"Why-not" output is first-class**: for near-miss rules, the result reports ranked
   failed conditions — field, threshold, and the counterfactual value that would have
   flipped the outcome — capped small (the ECOA/FICO ≤4 ranked-reasons model). This is
   simultaneously the explainability surface and the harness's rule-repair signal.

## 5. Testing strategy

- **Conformance suite as the spec's twin**: table-driven golden tests — (`rules.yaml`,
  `facts`, expected `verdict`/`fired`/`errors`) triplets — one per clause of §4 and per
  DSL construct of §2. These are written **before** the executor (TDD at the spec level).
- **The 11 reproduced v1 bugs become regression tests** asserting the *correct* v2
  behavior (e.g., `date: "2024-10-15"` stays a string; worker-thread `reason()` equals
  main-thread; failed rule absent from `fired`).
- **Concurrency test**: N threads × M `reason()` calls on one engine, results must be
  identical and error-free.
- Unit tests per module (compiler, evaluator, interpolation, conflict analysis), plus a
  benchmark harness (pytest-benchmark) so the performance claim is measured, not asserted.
- CI from day one (GitHub Actions): ruff + mypy + pytest matrix (3.10–3.12; dropping 3.8/3.9
  — both EOL) gating every PR to the rebuild branch.

## 6. Delivery plan (branch: `v2-rebuild`)

| Phase | Deliverable | Gate |
|---|---|---|
| **P0** | This design + JSON Schema v2 + conformance-test skeletons | Design review (you) |
| **P1** | `expr/`: compiler + single evaluator + interpolation, fully tested (incl. deadline, thread-safety, security suite ported from v1's `test_security.py` ideas) | Conformance green |
| **P2** | `dsl/`: parser, schema validation, load-time analyzer (conflicts, cycles, `after` targets) | Bad-input corpus green |
| **P3** | `runtime/`: executor, verdict assembly, errors, traces; public `Engine`/`ExecutionResult` | Full §4 conformance + the 11 regression tests green |
| **P4** | Migration: rewrite examples 01–03, 07, 09 for v2 syntax; benchmark harness; delete v1 core from the branch; version `1.0.0a1` | Benchmarks produce correct answers; side-by-side report vs v1 |
| **Later layers** (each spec-first, separate increments) | **L1: LLM `PROMPT()`** — single evaluation already fixes double-billing; determinism contract: cache key = (prompt, model, model-snapshot, temperature, output schema); record/replay store (replayed runs fetch LLM results exclusively from the trace); DSPy-style assert-vs-suggest failure semantics (hard error vs retry-with-feedback then symbolic fallback); opt-in retry-and-vote with early stopping; structured outputs for shape with refusal handling and post-hoc semantic validation — return schemas stay scalar-only (complex schemas degrade extraction accuracy). **L2: temporal** — port `TemporalStore`; event-time windowed aggregates with one bounded-lateness parameter; `sustained()` redefined with an explicit max-gap/coverage parameter (no more 80% magic). **L3: goal seeking** — re-specified; v1's was never functional. | — |

Estimated shape: P1–P3 is where the correctness lives and is genuinely small — the v1
core was ~5.5k lines with duplication; v2 core should land well under that.

## 7. Agent-authored rules — the harness (direction change, 2026-06-10)

**Rules are written by agents, not humans.** Symbolica v2 is the substrate for an
agentic harness in which an LLM agent authors, tests, and maintains the ruleset, and the
engine provides deterministic execution plus the feedback signals the agent learns from.
This adjusts the design above as follows:

1. **Canonical format is JSON, schema-first.** The JSON Schema (§2) becomes the
   *structured-output contract* given directly to the authoring LLM — constrained
   decoding then guarantees syntactic validity by construction. YAML remains a derived,
   human-review view only. Rule objects stay **shallow (≤2–3 nesting levels)** — deep
   nesting measurably raises LLM emission error rates. Ship an `llms.txt`-style machine
   doc of the schema for authoring agents. *(Research resolved the expression-encoding
   question: keep in-string `"= expr"` marked expressions — LLMs emit familiar
   Python-like code far more reliably than JsonLogic-style ASTs or structured
   expression objects; see symbolica-research-synthesis.md §2.)*
2. **Diagnostics are a first-class API.** Every validation/compile failure returns a
   structured diagnostic — JSON-path to the offending element, error code, message, and
   where possible a suggested fix — designed for an automated repair loop, not a stack
   trace for a human. Diagnostic quality is tested like any feature.
3. **Ruleset lifecycle APIs** on top of the immutable engine:
   `validate(candidate) → diagnostics`, `simulate(candidate_ruleset, recorded_cases) →
   verdict diffs vs active ruleset`, `promote(ruleset) → new engine`, plus per-rule
   **provenance** (author agent, source conversation/evidence, created-at) and runtime
   **telemetry** (evaluations, fires, error counts) so the harness can monitor and
   retire underperforming rules. Immutable-engine-with-cheap-rebuild (§3) is what makes
   candidate evaluation safe and trivially parallel.
4. **Static ruleset analysis is promoted from nicety to safety requirement.** Agents
   will produce conflicting, shadowed, and unreachable rules at much higher rates than
   humans; the load-time analyzer (§3 `dsl/analyzer.py`) must detect overlap, shadowing,
   unreachability, and emit-conflicts, and report them as structured diagnostics the
   authoring agent can act on.
5. **Traces close the loop.** `ExecutionResult` traces (§4) are the reward/feedback
   signal: the harness feeds misfire traces and near-miss analysis ("which condition
   failed, on what value") back to the authoring agent for rule repair. "Why not"
   explanations move from explainability sugar to core training signal.
6. **The harness itself is a separate layer** (likely `symbolica.harness` or a sibling
   package, built after P4): propose → validate → simulate → promote → monitor loop,
   with optional human approval gates. The engine stays agnostic — it exposes the
   substrate APIs above and nothing agent-specific.
7. **Safety hardening for machine-authored rules** (from the research — prompt-level
   instructions are not a control surface; ~26.7% violation rates for prompt-only
   safety): `emit`/action **allowlists enforced deterministically by the engine at
   execution time** (not by the harness, so they can't be bypassed); per-rule ACE-style
   helpful/harmful telemetry counters driving automatic retirement;
   canary/champion-challenger promotion; tamper-evident provenance for every rule
   version.

## 8. What we deliberately drop

- `triggers` (replaced by `after`), `if/then` aliases, the `from_yaml` module-level alias.
- The hand-rolled four-validator stack (JSON Schema + one analyzer instead).
- `llm/security.py` (dead), `ExecutionPathEvaluator`/`TraceEvaluator` (hook subsumes both).
- Python 3.8/3.9 support; the unused langchain/semantic-kernel extras until something uses them.
- The `visualization/` toolkit stays untouched on `main` for now; it re-implements
  analysis with weaker heuristics and will be rebuilt against `analysis/` later if wanted.
