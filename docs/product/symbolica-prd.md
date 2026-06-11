# Symbolica v2 — Product Requirements Document

| | |
|---|---|
| Status | **Source of truth** — supersedes prior docs for scope; design docs remain as rationale |
| Version | 1.6 (2026-06-11) — v1.4: StrataDB data layer; v1.5: StrataDB leverage (FR-14.9/14.10, OQ-8); v1.6: vision corrected (hybrid symbolic decision intelligence; policy layer; memory-graduation positioning), north star → quality-gated coverage, shadow mode into M5 (FR-14.7), Case severity, `symbolica-evaluation.md` |
| Owner | anibjoshi |
| Related | `symbolica-user-flows.md` (personas & flows), `symbolica-nfr.md` (detailed NFRs + verification), `symbolica-evaluation.md` (metrics & evaluation strategy), `symbolica-rebuild-design.md` (architecture rationale), `symbolica-research-synthesis.md` (evidence), `symbolica-correctness-bugs.md` (v1 failure catalog), `symbolica-as-is-analysis.md` (v1 baseline) |

Requirement IDs (`FR-x.y`, `NFR-x.y`) are stable and referenced by conformance tests,
issues, and PRs. Priorities: **P0** = required for v2 core release; **P1** = required
for the layer release it belongs to; **P2** = planned, not committed.

---

## 1. Product Vision

**Symbolica is a hybrid symbolic decision intelligence system: a deterministic,
explainable decision core that learns its rules from the agents it governs — and can
consult a model *inside* a rule where narrow judgment is genuinely needed.**

It is hybrid twice over. At **execution time**, neural leaves serve symbolic
skeletons: rules are deterministic, but a condition can delegate one bounded judgment
to an LLM under a determinism contract. At **authoring time**, the roles invert:
agents write the rules, and the symbolic layer's verification — schema, static
analysis, simulation against held-out cases, shadow comparison on live traffic — is
what makes machine-authored policy safe to trust. The symbolic side contributes proof;
the neural side contributes knowledge.

In an agentic stack, Symbolica is **the policy layer**. Agents are how a system
handles the novel; policy is how it handles the settled. The product is a loop: an
agent acts; its decisions **and outcomes** are recorded as cases; an authoring agent
distills cases into declarative rules; the engine compiles, verifies, and executes
those rules deterministically — in microseconds, with machine-readable explanations —
and every trace feeds the next round of distillation and repair. Promotion is gated by
evidence, so policy is not a recording of what the agent did but a **vetted
improvement on it**. Humans govern by exception, not by authoring.

The engine is the stack's fixed point — the one component whose behavior can be
proven, replayed, and governed. AI is what makes filling it with good rules cheap.

### 1.0 North-star metric

**Quality-gated coverage (QGC)**: the fraction of an agent's decisions handled by
promoted rules **while the rolling quality gate is green** — non-inferiority of rule
decisions versus the fallback baseline, severity-weighted, on the strongest available
evidence (outcome joins > shadow comparisons > adjudicated samples). Coverage earned
during a red gate counts as zero; new decision families count zero until the gate has
sufficient data. *Raw coverage is explicitly rejected as the north star: it is
improvable by promoting overly broad rules — i.e., by doing the job worse.*

Secondary: net economics per covered decision (minus loop costs), distillation
efficiency (≤3 repair round-trips), and rule survival rate. Honest expectation: mature
deployments may settle at 30–60% QGC — the value claim rides on quality and
governance per covered decision, not the raw percentage. Gate definition, metric
hierarchy, and evaluation assets: `symbolica-evaluation.md`.

### 1.1 The three loops

| Loop | Cadence | Actor | Surface |
|---|---|---|---|
| **Decide** | µs, every agent turn | Engine, as **middleware** gating agent actions (primary deployment mode; tool-style consultation is secondary — a gate the agent can skip is prompt-level safety again) | `reason()`, verdict, trace-for-LLM |
| **Distill** | minutes–hours | Authoring agent via the harness | record → distill → validate → simulate → promote |
| **Govern** | days, by exception | Human governor | promotion review, provenance, audit/replay |

Cold start is a first-class flow: a fresh deployment runs in **observation mode** —
every decision falls through to the agent and is recorded; the first ruleset is
distilled from those cases, and coverage grows from 0% upward.

### 1.2 Why this product (market position)

Research (2024–2026) confirms the white space: guardrails engines (NeMo Guardrails,
Guardrails AI), agent policy engines (OPA-for-agents, Cedar, Microsoft Agent Governance
Toolkit), and decision engines (GoRules, Camunda DMN) each own a slice, but **no
shipping engine combines (a) LLM judgments as first-class typed, cost-accounted
predicates inside declarative rules, (b) replayable, agent-consumable decision traces,
and (c) an agent-authored-ruleset lifecycle.** That intersection is Symbolica.

**Versus agentic memory** (the first question every adopter asks): memory changes what
the model *knows*; Symbolica changes what the system *does*. A lesson in memory is
advice to a stochastic reader — unenforced, unvetted, re-paid on every decision, and
unmeasurable. The knowledge maturity ladder is *episodic memory → semantic lesson →
tested rule → governed policy*: memory systems are the first two steps; **Symbolica is
what a memory graduates into once it is load-bearing.** Most agent systems only ever
need the first two steps — memory is horizontal. A system graduates when its decisions
trip the **four triggers**: (1) repetition at volume (economics), (2) consequence —
money, access, regulation (governance), (3) consistency obligations (determinism),
(4) adversarial exposure (enforcement). That segment is narrower and worth far more
per system.

**Portfolio position:** StrataDB serves the horizontal market (memory for every
agent); Symbolica serves the graduation (policy for load-bearing agents). They share
one database, so the upgrade path is in place before it is needed: the cases and
memories are already in StrataDB when the first incident or cost review triggers
graduation — and graduation itself is one line of code (FR-14.1).

### 1.3 Why a clean break from v1

v1 had 11 confirmed silent-wrong-answer defect classes rooted in *undefined semantics*
(heuristic expression detection, diff-based verdicts, swallowed errors, double
evaluation by divergent evaluators, cosmetic triggers, dead `enabled`, thread-fatal
timeouts — see `symbolica-correctness-bugs.md`). The v1 test suite pinned the buggy behavior.
v2 is specified first, tested against the spec, then implemented.

## 2. Users

| Persona | Description | Primary needs |
|---|---|---|
| **Authoring agent** (primary author) | An LLM agent that writes, repairs, and retires rules from experience/feedback | A schema it can emit reliably; machine-actionable diagnostics; simulation feedback; near-miss traces |
| **Host developer** | Python developer embedding Symbolica in an agent stack | Tiny API; determinism; thread safety; speed; zero ceremony |
| **Human governor** | Reviews and approves machine-authored policy; audits decisions | Readable rule projection; provenance; audit trails; approval gates |
| **Downstream agent** | The agent consuming `reason()` results mid-loop | Compact structured verdicts and traces it can condition on |

Humans do **not** hand-author rules in the primary workflow. Every format/API decision
optimizes for "an LLM can emit and repair this reliably" over human ergonomics.

**Who this is not for:** systems whose decisions never trip the four graduation
triggers (§1.2) — purely creative, exploratory, or low-stakes agents — should use
agentic memory alone. Symbolica's target is agents whose decisions are repeated,
consequential, consistency-bound, or adversarial-exposed.

## 3. Product Principles

1. **Nothing is inferred; everything is marked.** No heuristics deciding what a value means.
2. **One evaluator.** Tracing is a hook on the only evaluation, never a second implementation.
3. **Errors are data.** Structured, coded, localized diagnostics; nothing is silently swallowed.
4. **Determinism is the contract.** Same ruleset + facts + functions ⇒ same result, on any thread, any OS.
5. **The trace is a product surface,** consumed by agents for decisions and repairs.
6. **Safety is enforced by the engine,** never delegated to prompt-level compliance.

## 4. Scope Overview

| Release | Contents | Status |
|---|---|---|
| **v2 Core** (`2.0.0a`) | Rule format + schema, expression language, executor, results/traces/why-not, diagnostics, lifecycle APIs (validate/simulate), case recording, coverage telemetry, static analysis, function registry | This PRD §5–§11, P0 |
| **Loop v0** (`symbolica.loop`) | Observation mode, distillation, repair loop, simulation gating, promotion with provenance — **the product layer, co-developed with core** | §14, P0 |
| **L1: LLM layer** | `PROMPT()` predicate with determinism contract | §12, P1 |
| **L2: Temporal layer** | Event-time windowed aggregates, TTL facts | §13, P1 |
| **Out of scope** | See §16 | — |

---

## 5. Rule Definition Format

### FR-5.1 (P0) Canonical format is JSON, validated by a published JSON Schema
A ruleset is a JSON document. The schema (draft 2020-12) ships inside the package, is
versioned (`"format": 2`), and doubles as the **structured-output contract** handed to
authoring LLMs. Rule objects are shallow: ≤3 nesting levels excluding condition trees.

### FR-5.2 (P0) Rule object

```json
{
  "id": "premium_eligible",
  "priority": 100,
  "when": { "all": [
      "age >= 18",
      { "any": ["credit_score >= 750",
                { "all": ["credit_score >= 650", "employment_years >= 2"] }] },
      { "not": "bankruptcy" }
  ]},
  "after": ["kyc_complete"],
  "set":  { "risk_band": "low" },
  "emit": { "approved": true,
            "monthly_rate": "= base_rate * 0.9",
            "summary": "Approved at {= monthly_rate} for {= applicant_name}" },
  "enabled": true,
  "tags": ["underwriting"],
  "meta": { "description": "..." }
}
```

| Field | Req | Type | Semantics |
|---|---|---|---|
| `id` | required | string `^[a-z][a-z0-9_]*$`, ≤64 chars | Unique in ruleset |
| `priority` | required | integer | Conflict resolution weight (§7.6). Required — no silent default |
| `when` | required | condition (see FR-5.3) | Fire condition |
| `after` | optional | array of rule ids | Eligibility gate: all listed rules must have fired (FR-7.4). `after_any` variant: at least one |
| `set` | optional | object | Working-memory writes; visible to later rules; **not** in verdict |
| `emit` | optional* | object | Verdict outputs (*at least one of `set`/`emit` required) |
| `enabled` | optional, default true | boolean | Disabled rules are excluded at load and reported (FR-6.5) |
| `tags` | optional | array of strings | Selection/telemetry grouping |
| `meta` | optional | object | Free-form; `provenance` sub-object reserved (FR-10.1) |

### FR-5.3 (P0) Conditions
A condition is either an **expression string** or a tree of `{"all": [...]}`,
`{"any": [...]}`, `{"not": <condition>}` nodes, recursively. Empty `all`/`any` arrays
are load-time errors.

### FR-5.4 (P0) Values: literal by default, expression by marker
In `set`/`emit`, every JSON value is a **literal** unless it is a string starting with
`=` (after optional leading whitespace), which marks an **expression**, or a string
containing `{= ... }`, which marks an **interpolated template**. A literal string that
must begin with `=` is escaped as `==`. There is no other inference of any kind.
*(Rationale: kills the entire v1 bug class #1–#3; in-string marked expressions are the
most reliably LLM-emitted encoding — symbolica-research-synthesis.md §2.)*

### FR-5.5 (P1) YAML is a derived, human-review projection only
The engine may *render* a ruleset to YAML for human review. YAML is never the stored or
authored artifact. If YAML *input* is ever accepted (P2), it is parsed in strict mode
(YAML 1.2 core schema, no implicit booleans).

### FR-5.6 (P1) `llms.txt`-style machine documentation
The package ships a compact machine-readable authoring guide (schema + expression
grammar + diagnostic catalog + examples) for inclusion in authoring-agent prompts.

## 6. Expression Language

### FR-6.1 (P0) Grammar
Expressions are a Python-syntax subset, parsed with `ast.parse(mode='eval')` and
validated against a node whitelist at **compile time**:

- Operators: `and or not`, `== != < <= > >= in not in`, `+ - * / % **`, unary `+ -`
- Operands: names, dotted access on mapping facts (`account.balance`), subscripts
  (`items[0]`, `user["id"]`), literals (int, float, string, bool, null/None), lists
- Calls: registered functions only, by simple name
- Everything else (attribute access on non-fact objects, comprehensions, lambdas,
  f-strings, starred args, keywords args, sets, dicts) → compile-time diagnostic

### FR-6.2 (P0) Built-in functions
`len, sum, min, max, abs, round, contains, startswith, endswith, lower, upper,
has(field), default(field, fallback)`. Names are reserved; user functions cannot shadow
them or each other.

### FR-6.3 (P0) Type discipline — no implicit coercion
Cross-type comparison or arithmetic (`1 == "1"`, `"a" < 2`) yields a `TYPE_MISMATCH`
diagnostic, never a boolean. `==`/`!=` between identical types only; int and float are
mutually comparable; `null` equals only `null`. *(CEL's rule — symbolica-research-synthesis.md §3.1.)*

### FR-6.4 (P0) Missing-data semantics
Referencing an undefined fact yields a `MISSING_FACT` diagnostic carrying rule id,
expression, and the missing name; the enclosing rule does not fire; the run continues;
the trace marks the missing read distinctly. A missing fact is **never** coerced to
false/null. Explicit tolerance: `has(f)` and `default(f, x)`. `strict=True` on
`reason()` raises on the first diagnostic. *(Decision record: symbolica-research-synthesis.md §1.)*

### FR-6.5 (P0) Short-circuit + cost-ordered evaluation
`and`/`any`/`all`/`or` short-circuit. Within a boolean group, the engine may reorder
operand evaluation by static cost class (symbolic before LLM/external) — observable
behavior (result, diagnostics for the *deciding* path) must be order-independent;
side-effecting functions are unsupported (NFR-2.4).

### FR-6.6 (P0) Resource limits
Per-expression: max length (default 2,000 chars), max AST depth (default 32). Per
`reason()` call: wall-clock deadline (default 5 s) checked at node granularity via
monotonic clock — **no signals**. Exceeding limits yields `LIMIT_EXCEEDED` diagnostics.

## 7. Execution Semantics

### FR-7.1 (P0) Inputs
`reason(facts, *, strict=False, deadline_ms=None, trace='standard')` accepts a mapping
(nested JSON-like values allowed). Input facts are immutable for the duration of the run.

### FR-7.2 (P0) Pass-based forward chaining to fixpoint
Execution proceeds in passes. Each pass evaluates every *eligible* unfired rule in the
canonical order (FR-7.5). Run ends when a pass fires nothing, or at `max_passes`
(default 16); hitting the cap sets `result.converged = False` (never silent).

### FR-7.3 (P0) Fire-once
A rule fires at most once per run. By spec, changed inputs after firing do not re-fire
a rule within the same run. *(Refraction rejected — symbolica-research-synthesis.md §2.)*

### FR-7.4 (P0) Eligibility
Eligible = `enabled` ∧ not yet fired ∧ all `after` antecedents fired (`after_any`: ≥1).

### FR-7.5 (P0) Canonical order
Topological order on the load-time dependency graph (fact producers before consumers),
then `priority` descending, then document order. The order is total, deterministic, and
exposed via `engine.execution_order()`.

### FR-7.6 (P0) Firing and verdict assembly
On a true `when`: all `set`/`emit` values are computed first, then applied atomically
(all-or-nothing per rule; any evaluation failure → rule did not fire + diagnostic).
`set` updates working memory immediately. `emit` values are staged; at end of run, for
each emitted key the value from the **highest-priority** firing rule wins; exact ties
broken by document order (and flagged at load time, FR-9.2). `result.verdict` contains
**every** emitted key — including values equal to input facts (kills v1 bug #4).

### FR-7.7 (P0) Determinism
Identical (ruleset, facts, registered functions) ⇒ byte-identical `verdict`, `fired`,
`diagnostics` — across runs, threads, processes, and platforms. Registered functions
must be pure; the docs state this and the simulation harness can detect violations.

## 8. Results, Traces, Explanations

### FR-8.1 (P0) `ExecutionResult`
Immutable, with: `verdict` (dict), `changed` (verdict minus keys equal to input values —
a *view*, not the primary surface), `fired` (ordered rule ids), `covered` (bool: did any
rule fire — the per-decision coverage signal), `diagnostics` (list, FR-9.1), `converged`
(bool), `duration_ms`, `trace` (FR-8.2), `why_not(...)` (FR-8.3).

### FR-8.2 (P0) Trace schema
Modeled on OPA decision logs + W3C trace-context: `decision_id` (unique per run),
`trace_id`/`span_id` (W3C-compatible, propagatable), engine + ruleset version/revision,
per-rule records (rule id, eligible/evaluated/fired, condition result, field values
consumed, which sub-condition decided the outcome), and per-external-call records (L1).
Three verbosity levels: `minimal` (fired + verdict), `standard` (default; + field
values and deciding conditions), `full` (+ every evaluation step). Serializes to
compact JSON; `result.trace.for_llm()` returns the structured-compact projection
(evidence: concise structured traces serve downstream LLMs best).

### FR-8.3 (P0) Why-not / near-miss explanations
`result.why_not(rule_id)` returns, for any non-fired rule: ranked failed conditions
(max 4), each with the expression, the field(s), the actual value(s), and where
computable for comparisons against constants, the **counterfactual boundary value**
that would have flipped it. `result.near_misses(n)` ranks non-fired rules by fraction
of satisfied conditions. *(ECOA/FICO ranked-reasons model; doubles as the harness
repair signal.)*

### FR-8.4 (P1) Field masking
Hosts can declare fact paths as masked. Masked values are replaced with `"<masked>"`
in traces, telemetry records, and recorded cases — before any persistence or sink —
with the masked paths listed in the artifact (OPA `erased`/`masked` precedent).
Masking never affects evaluation, only serialization. *(See NFR-9.1.)*

## 9. Diagnostics & Static Analysis

### FR-9.1 (P0) Diagnostic object
Every load-time and run-time problem is a `Diagnostic`: stable `code` (registry below),
`severity` (`error|warning|info`), `message` (one sentence, machine-parseable values
quoted), `json_path` (location in the ruleset document) or `rule_id`+`expression`
(runtime), and optional `suggestion` (a concrete fix, e.g. closest-matching fact name
for `MISSING_FACT`, via edit distance). Diagnostic quality is tested like a feature
(golden diagnostics in the conformance suite).

Initial code registry: `SCHEMA_VIOLATION, DUPLICATE_RULE_ID, UNKNOWN_AFTER_TARGET,
AFTER_CYCLE, EMIT_CONFLICT, SHADOWED_RULE, UNREACHABLE_RULE, BAD_EXPRESSION_SYNTAX,
FORBIDDEN_CONSTRUCT, UNKNOWN_FUNCTION, RESERVED_NAME, TYPE_MISMATCH, MISSING_FACT,
DIVISION_BY_ZERO, FUNCTION_ERROR, LIMIT_EXCEEDED, BUDGET_EXCEEDED, NOT_CONVERGED,
EMIT_NOT_ALLOWED, NEAR_DUPLICATE_RULE` (loop layer, FR-14.9). Normative payloads and
message templates: `docs/architecture/symbolica-spec.md` §S-5.

### FR-9.2 (P0) Load-time static analysis
On `compile()`: schema validation; id/`after`/cycle checks; **emit-conflict analysis**
(same key, same priority, non-mutually-exclusive ⇒ `EMIT_CONFLICT` error); shadowing
(a rule whose condition is subsumed by an earlier same-key higher-priority rule ⇒
`SHADOWED_RULE` warning); unreachable rules (unsatisfiable `after` chains ⇒
`UNREACHABLE_RULE`). *(DMN decision-table analysis lineage; agents produce these defects
at high rates, so this is a safety requirement.)*

## 10. Ruleset Lifecycle APIs (engine-side substrate for the harness)

### FR-10.1 (P0) Compile & provenance
`compile(ruleset_json) → CompiledRuleSet | Diagnostics`. Rulesets carry `revision`
(content hash) and optional per-rule `meta.provenance` (`author`, `source`,
`created_at`, `evidence`) which the engine preserves into traces untouched.

### FR-10.2 (P0) Validate
`validate(ruleset_json) → list[Diagnostic]` — full compile pipeline without
instantiation; the primary repair-loop API.

### FR-10.3 (P0) Simulate
`simulate(candidate: CompiledRuleSet, cases: Iterable[Case]) → SimulationReport`, where
`Case = (facts, expected_verdict?)`. Report: per-case verdict **diff vs a baseline
ruleset** (or vs expectations), per-rule stats (evaluations, fires, diagnostics,
precision/recall where expectations exist), and aggregate deltas. Runs are parallel-safe
(engines are immutable).

### FR-10.4 (P0) Immutable engine, cheap rebuild
`Engine(compiled)` is immutable. Ruleset mutation = `ruleset.with_rule(r)` /
`.without_rule(id)` + recompile. Compile of 1,000 rules completes < 1 s (NFR-1.3).

### FR-10.5 (P0) Telemetry counters & coverage
An optional `Telemetry` sink receives per-run records: per-rule counters (evaluated,
fired, diagnostics) and the run's `covered` flag. **Coverage** (covered runs / total
runs, per tag and overall) is computable from this stream and is the product's
north-star metric (§1.0). ACE-style helpful/harmful accounting for promotion/retirement
lives in the loop layer; the engine only emits counts.

### FR-10.6 (P0) Emit allowlist (capability scoping)
`Engine(..., emit_allowlist=set_of_keys_or_patterns)` — a fired rule emitting a key
outside the allowlist produces `EMIT_NOT_ALLOWED`, the emit is dropped, the event is
traced. Enforced by the engine at execution time, not by the harness. *(Prompt-level
safety is not a control surface.)*

### FR-10.7 (P0) Case schema & recording
`Case` is a core, versioned schema: `{case_id, facts, decision, outcome?, severity?,
source (agent|human|rules), timestamp, meta}` — the unit of recorded experience that
distillation and `simulate()` both consume (FR-10.3's cases are this type). `severity`
(1–4, host-declared consequence class) weights all quality metrics; `outcome` backfill
is a first-class loop activity — outcomes are what let policy exceed the judgment it
was distilled from (`symbolica-evaluation.md` §7). The core
ships a `Recorder` utility: `record(facts, decision, *, outcome=None, source=...)`
appending to a pluggable case store (bundled backend: StrataDB, FR-10.9). When a `reason()` call
is uncovered (`covered == False`), the host records the agent's fallback decision as a
case — this is **observation mode**, and it must work with an empty ruleset (a
zero-rule engine is valid, returns empty verdicts, and reports `covered=False`).

### FR-10.8 (P0) Fact-schema introspection
`compiled.fact_schema()` returns the set of fact names (with inferred type constraints
from usage) referenced by the ruleset — the host uses it to drive fact extraction
(e.g., as a structured-output schema for an extractor LLM), and the loop layer uses it
to detect rules referencing facts no extractor produces.

### FR-10.9 (P0) Data layer — StrataDB
All persistent state — cases, telemetry, ruleset revisions, promotion/audit records,
L1 response cache/replay, temporal series, undistillable batches — is stored in
**StrataDB** (embedded, in-process) via a single storage module; the store *protocols*
(CaseStore, Telemetry, …) remain the API and StrataDB is the bundled backend. Candidate
rulesets are isolated on StrataDB **branches** during simulation (FR-14.4); promotion
is a transactional audit-append + **CAS** swap of the active-ruleset state cell
(FR-14.5, FR-14.8, NFR-6.5); audit records ride the append-only event log (NFR-7.5).
Hosts may pass the same `Strata` instance their agent uses for memory, or a dedicated
path; in-memory mode (`Strata.cache()`) supports tests and ephemeral deployments. The
evaluation path performs no storage I/O regardless (AD-14). StrataDB **time-travel
snapshots** (`db.at(t)`) back audit and incident flows: any decision is investigable
against the full data state at its timestamp — active ruleset, cases, telemetry — not
just its own trace. Primitive mapping and decisions AD-14…AD-20:
`docs/architecture/symbolica-architecture.md` §11.

## 11. Function Registry

### FR-11.1 (P0) Registration at build time only
Custom functions are provided to `Engine(...)` at construction (name → callable, with
declared arity and cost class `cheap|expensive`). No post-build registration. Names
must be valid identifiers, not reserved, not duplicated. Functions must be pure and
exception-safe; a raising function produces a `Diagnostic`, not a crash.

## 12. L1 — LLM Layer (`PROMPT()`) — P1

- **FR-12.1** `PROMPT(template, type=...)` callable in conditions and `=` expressions;
  return types: `bool | int | float | str | enum([...])` — scalars only.
- **FR-12.2** Determinism contract: response cache keyed on (rendered prompt, model,
  model snapshot, temperature, output schema); **record/replay** mode where replayed
  runs read LLM results exclusively from a trace store and fail loudly on cache miss.
- **FR-12.3** Failure semantics per call site: `assert` (diagnostic, rule doesn't fire)
  or `suggest(retries=N, fallback=value)` (retry with error feedback, then symbolic
  fallback). Refusals are a first-class outcome, never coerced.
- **FR-12.4** Typed extraction via structured outputs / function calling; semantic
  validation after shape (range/enum checks). No word-list bool coercion (v1 failure).
- **FR-12.5** Cost accounting per call (tokens, $ estimate from a versioned price
  table, latency, cache hit) in the trace; per-run budget ceiling → `BUDGET_EXCEEDED`.
- **FR-12.6** Providers: OpenAI + Anthropic clients adapted behind one interface; sync
  first, async API reserved.
- **FR-12.7** Opt-in self-consistency voting (K samples, early stopping) per call site.

## 13. L2 — Temporal Layer — P1

- **FR-13.1** Event-time series store backed by the data layer (FR-10.9: one StrataDB
  event-log stream per metric; v1 `TemporalStore`'s windowing semantics carried over,
  its ad-hoc deque storage retired) with explicit timestamps, TTL facts, and one
  bounded-lateness parameter.
- **FR-13.2** Window functions: `recent_avg/min/max/count(key, duration)` over
  event-time sliding windows.
- **FR-13.3** `sustained(key, predicate, duration, max_gap)` — true iff the predicate
  holds for every sample in the window **and** no inter-sample gap exceeds `max_gap`.
  No implicit coverage heuristics.

## 14. The Loop (`symbolica.loop`) — the product layer — P0

Ships in the same distribution as the engine (engine remains usable standalone),
consumes only public engine APIs (§10), and implements the distill/govern loops of §1.1:

- **FR-14.1 (P0) Observation mode**: ships as a one-line wrapper (`ObservedEngine` or
  equivalent) coupling `reason()` + `Recorder` (FR-10.7): covered decisions return the
  verdict; uncovered decisions invoke the host's fallback callable and record the
  resulting case automatically — recording must not be a separate call the host can
  forget. Works from coverage 0% (empty ruleset).
- **FR-14.2 (P0) Distillation**: `distill(cases, *, authoring_model, current=None) →
  candidate ruleset` — drives an authoring LLM with the JSON Schema as its
  structured-output contract and the `llms.txt` authoring guide (FR-5.6); proposes new
  or amended rules from recorded cases.
- **FR-14.3 (P0) Repair loop**: validate → feed diagnostics (with JSON-paths and
  suggestions) back to the authoring model → re-emit; budgeted at ≤3 round-trips
  (front-loaded diagnostic richness is the engine-side enabler, FR-9.1). **Budget
  exhaustion is a defined outcome, not a loop**: the case batch is marked
  *undistillable*, retained in the case store with the failed candidate + final
  diagnostics attached, and surfaced to the governor; it is excluded from subsequent
  automatic distillation until a human or an instruction change unblocks it.
- **FR-14.4 (P0) Simulation gate**: candidates must pass `simulate()` (FR-10.3) over
  held-out cases — verdict precision vs recorded decisions/outcomes, coverage delta, and
  diff-vs-current review — before promotion is offered.
- **FR-14.5 (P0) Promotion**: stamps provenance (FR-10.1), bumps ruleset revision,
  optional human approval gate (configurable per emit-key pattern: e.g. auto-promote
  rules emitting `route.*`, require approval for `refund.*`).
- **FR-14.6 (P1) Monitoring & retirement**: consumes telemetry (FR-10.5); per-rule
  helpful/harmful counters from outcomes; flags underperformers for re-distillation or
  retirement.
- **FR-14.7 (P1, M5) Shadow mode**: candidate (or probationary newly-promoted) rules
  evaluate **silently** on live traffic — the engine computes their verdicts, the
  agent still decides for real, paired comparisons accumulate as evaluation data
  (`symbolica-evaluation.md` §5). Promotion of rules emitting approval-gated keys
  **requires** shadow non-inferiority over a configured minimum sample; routine keys
  may promote on simulation alone. Offline `simulate()` cannot answer live
  non-inferiority — its cases were generated under the old policy. Canary rollout
  (graduated *enforcement*) is the same machinery and stays P2.
- **FR-14.8 (P0) Expedited revision (incident mitigation)**: a governed fast path to
  disable or demote a specific rule *now*: `ruleset.without_rule(id)` (or a priority
  demotion) + recompile + swap, recorded as a revision with provenance
  (`source: incident`, actor, reason) but **exempt from the simulation gate** — the only
  promotion path that is. Approval policy may still require a governor confirmation;
  the disabled rule's triggering case is auto-queued for distillation as a
  counter-example.
- **FR-14.9 (P1) Semantic near-duplicate detection**: at validate time, each candidate
  rule is vector-searched (FR-10.9 auto-embed) against the active ruleset; similarity
  above a threshold yields a `NEAR_DUPLICATE_RULE` warning diagnostic naming the
  existing rule — steering the authoring agent to amend rather than add. Complements
  the syntactic `SHADOWED_RULE` analysis (FR-9.2).
- **FR-14.10 (P1) Coverage-gap clustering**: uncovered cases are embedded and
  clustered; distillation batches target the largest clusters first, so authoring
  effort tracks the biggest coverage gaps. Cluster summaries appear in loop telemetry
  (which gap is growing, which was closed by the last promotion).

The flagship acceptance demo (M5) is a **graduation demo**: start from an agent
already using agentic memory (StrataDB) on a benchmark decision domain; wrap it in
observation mode; record decisions **and outcomes**; distill, repair to green in ≤3
round-trips; pass the simulation **and shadow** gates; promote — and show
quality-gated coverage > 50% on held-out and shadow data at non-inferior quality, with
measured net cost/latency reduction. The companion **policy-recovery benchmarks**
(hidden ground-truth ruleset, noisy generated cases, measure recovery fidelity and
efficiency — `symbolica-evaluation.md` §6) ship with the repo and gate the release.

---

## 15. Non-Functional Requirements

The table below is the P0 summary. **`symbolica-nfr.md` is the normative elaboration**: it
extends these families, adds families NFR-5 (determinism & reproducibility), NFR-6
(reliability), NFR-7 (security), NFR-8 (observability), NFR-9 (privacy), NFR-10 (DX),
and binds every NFR to a committed verification method. An NFR without a verification
in CI does not count as met.

| ID | Requirement |
|---|---|
| **NFR-1.1** (P0) | Pure-symbolic `reason()` p50 < 1 ms, p99 < 5 ms for 100-rule rulesets / ≤50 facts / warm engine, on a commodity x86-64 core; measured by a committed pytest-benchmark suite with the exact configuration published. No performance claims without a committed benchmark |
| **NFR-1.2** (P0) | Throughput ≥ 5,000 `reason()`/s single-thread under NFR-1.1 conditions |
| **NFR-1.3** (P0) | `compile()` of 1,000 rules < 1 s |
| **NFR-2.1** (P0) | Thread-safe: concurrent `reason()` on one engine from any thread, identical results (regression for v1 bug #7). No `signal`, no thread-hostile or main-thread-only constructs |
| **NFR-2.2** (P0) | Platform: Linux/macOS/Windows; CPython 3.10–3.13 |
| **NFR-2.3** (P0) | Dependencies: core = stdlib + `jsonschema` + `stratadb` (the data layer, FR-10.9; native wheels — the `symbolica` wheel itself stays pure-Python). L1 adds provider SDKs as extras (`symbolica[openai]`, `[anthropic]`). No PyYAML in core |
| **NFR-2.4** (P0) | Sandboxing: no `eval`/`exec`, AST whitelist, no I/O or imports from expressions, resource limits per FR-6.6 |
| **NFR-3.1** (P0) | CI (GitHub Actions) on every PR: ruff, mypy (strict), pytest matrix (3 OS × 4 Python), coverage ≥ 90% on core, conformance suite, benchmark regression check |
| **NFR-3.2** (P0) | Conformance suite: every FR in §5–§11 has at least one table-driven golden test (rules + facts + expected verdict/fired/diagnostics) written **before** the implementing code; all 11 v1 bugs have named regression tests |
| **NFR-3.3** (P0) | Typed: `py.typed`, public API fully annotated |
| **NFR-4.1** (P1) | Trace serialization stable across patch versions; schema versioned |

## 16. Out of Scope (non-goals for v2)

- Rete/incremental matching and truth maintenance (reversal thresholds recorded in symbolica-research-synthesis.md §2)
- Backward chaining / goal seeking (L3, unscheduled; v1's was never functional)
- A rules server, REST API, or UI; multi-tenant ruleset storage
- Human-authoring conveniences (YAML input, `if/then` aliases) beyond the YAML review projection
- The v1 `visualization/` toolkit (revisit against `analysis/` APIs post-core)
- Differentiable/probabilistic reasoning (Scallop-style) — traces only
- Cross-run fact persistence (facts are per-`reason()`; temporal store is the explicit exception)

## 17. Release Plan & Acceptance

| Milestone | Contents | Exit criteria |
|---|---|---|
| **M0** | JSON Schema v2 + conformance-suite skeleton + diagnostic catalog | Schema review; golden-test format agreed |
| **M1** | Expression core (compiler, evaluator, builtins, limits) | FR-6.* conformance green; security suite green; thread-safety test green |
| **M2** | Format + static analysis (parser, FR-9.2 analyzer) | FR-5.*, FR-9.* green incl. golden diagnostics |
| **M3** | Runtime (executor, verdict, traces, why-not, lifecycle APIs) | FR-7/8/10/11 green; all 11 v1 regression tests green |
| **M4** | Benchmarks + examples + docs; `2.0.0a1` on the `v2-rebuild` branch | NFR-1.* met and published; `llms.txt` authored; example corpus rewritten |
| **M5** | **Loop v0** (observation mode, distillation, repair, simulation gate, **shadow mode**, promotion) | FR-14.1–14.5 + 14.7 green; **graduation demo** (§14): memory-using agent → observation → distill/repair ≤3 round-trips → simulation + shadow gates → promoted; QGC > 50% at non-inferior quality, net savings measured; policy-recovery benchmarks published; gate defaults (δ, n, w) + OQ-6 calibrated |
| **M6** | L1 LLM layer | FR-12.* green incl. record/replay determinism test |
| **M7** | L2 temporal; loop monitoring/retirement | FR-13.*, FR-14.6 |

**The engine ships** (`2.0.0a1`, M4) when its exit criteria hold, CI is green on the
full matrix, and a side-by-side run shows v2 producing correct answers on every case
from `symbolica-correctness-bugs.md` where v1 produced wrong ones. **The product ships** (M5)
when the flagship loop demo passes — that demo, not the engine benchmarks, is the
headline claim.

## 18. Open Questions (tracked, non-blocking)

1. Fact-version refraction — revisit only on demonstrated missed-update bugs (owner: post-M4 review).
2. Whether `priority` should be required vs defaulted — currently **required** (FR-5.2); revisit with harness telemetry.
3. Dotted access semantics on missing *intermediate* objects (`a.b` where `a` exists but isn't a mapping) — currently `TYPE_MISMATCH`; confirm in M1.
4. Retry-and-vote default-off cost/benefit (L1).
5. Async `reason()` (only relevant once L1 latency matters in async hosts).
6. Minimum case volume before first distillation — placeholder heuristic is ~50 per
   decision family (`symbolica-user-flows.md` §5); calibrate empirically during the M5 flagship
   demo and replace the heuristic with a measured threshold (owner: M5 exit review).
7. Privacy posture on rules distilled from erased cases: NFR-9.3 takes the position
   that rules are aggregates and survive case erasure (with dangling provenance
   references reported by the verifier) — needs governor/legal sign-off before any
   deployment subject to GDPR-style erasure (owner: pre-M5).
8. Should L1 route `PROMPT()` through **strata-inference** (StrataDB's inference
   engine: local llama.cpp + cloud providers) instead of direct provider adapters
   (FR-12.6)? Local small models would make cheap judgment leaves (classification,
   routing) near-free and co-locate response caching with the replay store. Depends on
   strata-inference maturity — decide before M6 (owner: M5 exit review).
