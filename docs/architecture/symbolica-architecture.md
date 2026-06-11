# Symbolica v2 — Technical Architecture

| | |
|---|---|
| Status | Active — the engineering blueprint for the v2 implementation |
| Version | 1.2 (2026-06-11) — §11 Data Layer (AD-14…AD-18); v1.2 leverages further StrataDB capabilities: time travel, native hash chain, durability modes, read-only audit opens (AD-19, AD-20) |
| Upstream | `docs/product/symbolica-prd.md` (requirements, v1.3), `docs/product/symbolica-nfr.md` (quality gates) |
| Rationale | `docs/analysis/symbolica-rebuild-design.md`, `docs/analysis/symbolica-research-synthesis.md` |
| Downstream | `symbolica-spec.md` (normative definitions — next document), implementation plan |

This document describes **how the system is built**: packages, components, data types,
pipelines, and the rules that bind them. It does not restate requirements (PRD) and it
does not define normative language semantics (spec). Where it makes a binding
engineering decision not found in either, the decision is marked **[AD-n]**
(architecture decision) and indexed in §13.

---

## 1. Architectural Goals (ranked)

Derived from the PRD principles and the NFR gates; when goals conflict, the higher one wins:

1. **Correctness by construction** — bug classes from v1 must be structurally
   impossible, not merely fixed (one evaluator, marked expressions, total `reason()`).
2. **Determinism** — bit-stable results across runs/threads/platforms (NFR-5); no
   ambient state anywhere in the evaluation path.
3. **Inspectability** — every behavior explains itself (diagnostics, traces, why-not);
   internal structure mirrors the explanation structure.
4. **Performance within reason** — meet NFR-1 targets with straightforward Python;
   no exotic optimization that compromises goals 1–3 (no Rete, no bytecode VM in v2).
5. **Small surface, hard boundaries** — few public types, strict import direction,
   layers replaceable without touching the core.

## 2. System Context

```
                       ┌────────────────────────────────────────────┐
                       │                Host process                 │
                       │                                            │
  Authoring LLM ◀──────┤  symbolica.loop                            │
  (distill/repair)     │   ObservedEngine · distill · repair ·      │
                       │   simulate-gate · promote                  │
                       │        │ uses public API only              │
                       │        ▼                                   │
  Downstream agent ◀───┤  symbolica (core engine)                   │──▶ StrataDB
  (verdict + trace)    │   compile · Engine.reason · validate ·     │    (embedded data
                       │   simulate · Recorder                      │     layer, §11:
                       │        │ optional extras                   │     cases · telemetry
  LLM providers  ◀─────┤  symbolica.llm (L1) · symbolica.temporal   │     rulesets · audit
  (PROMPT leaves)      │  (L2)                                      │     replay · temporal)
                       └────────────────────────────────────────────┘
```

Boundary rules: the engine performs **no network I/O** except L1 provider calls
(NFR-9.2 — StrataDB is embedded, so persistence is also process-local); the loop layer
consumes **only the public API** — anything it needs that isn't public becomes public,
never imported privately **[AD-1]**.

## 3. Distribution & Package Layout

One distribution (`symbolica` on PyPI), pure-Python wheel. Core dependencies: stdlib +
`jsonschema` + `stratadb` (the data layer, §11 — a native-wheel dependency; the
`symbolica` wheel itself stays pure-Python). Extras: `symbolica[openai]`,
`[anthropic]`, `[yaml]` (review projection).

```
symbolica/
  __init__.py        # the entire public API, re-exported; nothing else is public
  engine.py          # Engine facade
  diagnostics.py     # Diagnostic, DiagnosticCode registry, severity
  errors.py          # the few real exceptions (StrictModeError, CompileError wrapper)
  dsl/
    schema/          # ruleset.schema.json (format 2), trace.schema.json, case.schema.json
    parser.py        # JSON doc -> RuleSet (jsonschema validation + structural lift)
    analyzer.py      # static analysis: deps, cycles, emit conflicts, shadowing, reachability
    yaml_view.py     # [extra] RuleSet -> YAML human-review projection (render-only)
  expr/
    ast_gate.py      # ast.parse + node whitelist + limits  -> ValidatedAst
    compiler.py      # ValidatedAst -> CompiledExpr (closure tree, fields, cost class)
    functions.py     # builtins; FunctionTable (frozen at engine build)
    interpolate.py   # "{= expr }" template -> CompiledTemplate
    values.py        # type-discipline helpers (comparisons, arithmetic, MISSING signal)
  runtime/
    executor.py      # pass loop, eligibility, firing, convergence
    context.py       # RunContext: fact view, working memory, deadline, hook, diags
    verdict.py       # staging + priority resolution + verdict/changed assembly
    result.py        # ExecutionResult, why_not/near_misses (lazy, trace-derived)
    trace.py         # TraceBuilder (hook impl), trace levels, serialization, masking
  lifecycle/
    api.py           # compile_ruleset, validate, simulate
    ruleset.py       # RuleSet, with_rule/without_rule, revision hashing
    cases.py         # Case, CaseStore protocol, Recorder
    telemetry.py     # Telemetry protocol, coverage helpers
  storage/
    strata.py        # ALL StrataDB access (the only `import stratadb` site, AD-15):
                     #   spaces, branch lifecycle, CAS promotion pointer, txns
    backends.py      # StrataDB impls of CaseStore/Telemetry/ruleset repo/audit log/
                     #   replay store — the default (and only bundled) backends
  llm/               # L1: provider adapters, PromptLeaf, response cache, replay store
  temporal/          # L2: event-time window functions over the storage layer
  loop/              # ObservedEngine, distill, repair, gate, promote (product layer)
```

**Import direction (enforced in CI via import-linter [AD-2]):**

```
diagnostics ◀── everything
dsl ──▶ expr (compiles conditions)        loop ──▶ lifecycle, storage, engine (public only)
runtime ──▶ expr, dsl(types only)         llm/temporal ──▶ expr (leaf protocol), storage
engine ──▶ dsl, expr, runtime, lifecycle  storage ──▶ stratadb (sole import site)
```
No module imports `engine` except `__init__`/`loop`. `expr` and `runtime` import
neither `storage` nor `stratadb` — the evaluation path is storage-free **[AD-14]**.
`expr` imports nothing but `diagnostics` + stdlib — it is the security kernel and
stays maximally auditable.

## 4. Core Data Types

All frozen dataclasses (or equivalent) unless stated; everything hashable/serializable
that crosses a boundary.

| Type | Module | Essence |
|---|---|---|
| `RuleSet` | lifecycle.ruleset | Parsed, schema-valid document + `revision` (canonical-JSON SHA-256). Pure data, no behavior |
| `Rule` | dsl.parser | One parsed rule; conditions still as marked strings + tree structure |
| `CompiledExpr` | expr.compiler | `eval(ctx) -> Value` closure tree + `fields: frozenset[str]` + `cost: CostClass` + source span |
| `CompiledTemplate` | expr.interpolate | Literal segments + embedded `CompiledExpr`s |
| `CompiledRule` | dsl.analyzer | Rule + compiled when/set/emit + static metadata (deps, after, order key) |
| `CompiledRuleSet` | lifecycle.api | Tuple of `CompiledRule` in canonical order + dependency graph + `fact_schema()` + load diagnostics (warnings) |
| `Engine` | engine | `CompiledRuleSet` + `FunctionTable` + config (allowlist, limits, telemetry). Immutable; picklable (NFR-2.7) |
| `RunContext` | runtime.context | Per-call mutable state: fact view, working memory, staged emits, deadline, `TraceBuilder`, diagnostics list. Never escapes `reason()` |
| `Diagnostic` | diagnostics | `code, severity, message, json_path \| (rule_id, expression, span), suggestion?` |
| `ExecutionResult` | runtime.result | Frozen: verdict, changed, fired, covered, diagnostics, converged, duration_ms, trace |
| `Trace` | runtime.trace | Versioned, level-dependent record; `for_llm()`, `to_json()`; carries replay cache (L1) |
| `Case` | lifecycle.cases | `case_id, facts, decision, outcome?, source, timestamp, meta` — versioned schema |

**[AD-3] Facts are wrapped, not copied.** `reason()` wraps the caller's mapping in a
read-only `FactView` (recursive on access, memoized) rather than deep-copying. Dotted
access (`a.b`) resolves through the view; the host's object is never mutated. Deep copy
is O(facts) per call and would dominate the 1 ms budget.

## 5. The Compile Pipeline

```
JSON doc ──(1) jsonschema──▶ valid doc ──(2) lift──▶ RuleSet
  ──(3) expr compile (per when/set/emit/template)──▶ CompiledExpr·s
  ──(4) analyze: dep graph (fields produced/consumed), after graph, cycles,
        emit conflicts, shadowing, reachability──▶ diagnostics + canonical order
  ──(5) freeze──▶ CompiledRuleSet (errors ⇒ compile fails with all diagnostics, not first)
```

Properties: stage 3 is where **all** AST gating happens — `ast_gate` is the only call
site of `ast.parse` in the entire codebase **[AD-4]**, making the security surface one
function. Stage 4 computes everything the runtime must never compute per-call
(ordering, field sets, conflict tables). Compile collects diagnostics exhaustively
(repair loops need the full list, not fail-fast) **[AD-5]**.

## 6. The Expression Engine

**Closure-tree compilation [AD-6].** Each AST node compiles to a Python closure
`(ctx) -> Value`; composites close over their children. No interpretation dispatch at
runtime, no bytecode VM. This meets NFR-1 comfortably, keeps the evaluator ~small
enough to audit, and makes per-node behavior (deadline check, hook emit) explicit.

**One evaluator, hook-based tracing [AD-7].** The closure calls
`ctx.hook.on_*(...)` only when a hook is installed (`standard`/`full` trace levels;
`minimal` runs hook-free). The trace is a byproduct of the only evaluation — the v1
two-evaluator drift class is structurally impossible.

**MISSING as a control-flow signal [AD-8].** A missing fact raises an internal
`MissingFactSignal` (carrying the name and span), caught at the rule-evaluation
boundary and converted to the `MISSING_FACT` diagnostic. `has()`/`default()` are
**compile-time special forms** — they compile to direct guarded lookups, never
triggering the signal. Rationale: the happy path pays zero cost; sentinel-value
propagation (the alternative) infects every operator with MISSING-handling logic.
Exact absorption semantics (e.g. `False and missing`) are defined in the spec; the
architecture supports either via the signal boundary.

**Cost-ordered short-circuit [AD-9].** At compile time each operand of a boolean group
gets a `CostClass` (`CHEAP` for pure-symbolic, `EXPENSIVE` for `PROMPT()`/external
function leaves). The compiler emits the group with operands sorted CHEAP-first
(stable within class, preserving source order). Done once at compile, not per-eval;
the spec defines the observable-equivalence rule this must satisfy.

**Deadline [AD-10].** `RunContext.deadline` is a monotonic timestamp; composite
closures call `ctx.check()` (one comparison) before descending. No signals, no
threads — works everywhere (kills v1 bug #7 structurally).

**Type discipline.** All comparisons/arithmetic route through `expr.values` helpers
that implement the spec's type matrix and emit `TYPE_MISMATCH`/`DIVISION_BY_ZERO`
diagnostics via the same signal mechanism as MISSING.

## 7. The Runtime

`Engine.reason(facts, *, strict, deadline_ms, trace)`:

```
1  ctx = RunContext(FactView(facts), deadline, TraceBuilder(level), [])
2  loop pass = 1..max_passes:
3      fired_this_pass = 0
4      for rule in canonical_order:                      # precomputed at compile
5          if not eligible(rule, ctx): continue          # enabled ∧ unfired ∧ after-sat
6          outcome = rule.when.eval(ctx)                 # ONE evaluation; hook traces it
7          if outcome is error-signal: ctx.diag(...); continue
8          if outcome is truthy:
9              vals = eval_all(rule.set | rule.emit)     # compute first…
10             if any error: ctx.diag(...); continue     # …rule did NOT fire (atomic)
11             apply set -> working memory; stage emit   # …apply after (FR-7.6)
12             mark fired; fired_this_pass += 1
13     if fired_this_pass == 0: converged = True; break
14 verdict = resolve_staged_emits(priority desc, doc order)   # runtime/verdict.py
15 return ExecutionResult(verdict, …, trace=builder.finalize())
```

Load-bearing details:

- **Eligibility is re-derived per pass from `ctx`**, not cached across passes — `after`
  satisfaction changes as rules fire.
- **Line 6 is the only condition evaluation.** The trace records it; the firing
  decision uses it. (v1 evaluated twice with different engines — bug #5.)
- **Lines 9–11 enforce atomicity**: compute-then-apply, so a failing `emit` expression
  can't leave partial writes (v1 bug #6).
- **Verdict resolution is a fold at the end** (line 14), not in-place overwrites —
  priority-wins is implemented in exactly one place, `runtime/verdict.py`, with the
  staged list preserved in the trace so "who lost the conflict" is visible.
- `why_not`/`near_misses` are **computed lazily from the trace** (NFR-1.8): the trace
  records per-condition outcomes at `standard` level; the why-not module replays the
  recorded values against the compiled condition structure — no extra evaluation
  during `reason()`.

## 8. Concurrency & Immutability Model

- Everything reachable from `Engine` is deeply immutable after construction; all
  mutation lives in `RunContext`, created and dropped inside `reason()` **[AD-11]**.
- Zero engine-level locks. Thread safety = absence of shared mutable state, verified
  by the NFR-2.1 stress test, not by synchronization.
- No module-level caches in evaluation paths (v1's global `lru_cache` is replaced by
  compile-time work owned by the engine instance).
- Scale-out: engines pickle (compiled closures are rebuilt on unpickle from the
  retained `RuleSet` — pickling stores data, not code **[AD-12]**); `simulate()`
  parallelizes across processes.
- L1 response cache and replay store are the only cross-call state; they live in
  explicit store objects backed by the data layer (§11) with StrataDB's own
  transaction/concurrency contract — never inside `Engine`.

## 9. Diagnostics Architecture

One `Diagnostic` type for compile-time and run-time. Codes are a closed registry in
`diagnostics.py` (enum + payload dataclass per code) — adding a code is a reviewed,
versioned act, and the `llms.txt` diagnostic table is **generated from this registry**
(NFR-10.2). Compile diagnostics carry `json_path`; runtime diagnostics carry
`(rule_id, expression, span)`. `strict=True` converts the first error-severity runtime
diagnostic into a raised `StrictModeError` carrying the diagnostic. Suggestions (e.g.
nearest fact name by edit distance) are computed by the diagnostic's constructor
helper, so every emission site gets them for free.

## 10. Trace & Replay Architecture

`TraceBuilder` implements the evaluator hook. Levels are additive: `minimal` (fired,
verdict, diagnostics, ids), `standard` (+ per-rule condition outcomes, consumed field
values, deciding sub-condition, staged-emit resolution), `full` (+ every node event).
Masking (FR-8.4) is applied by the builder at record time — masked values never enter
the trace structure **[AD-13]**, so no later serialization can leak them. The trace
embeds `engine_version`, `ruleset_revision`, effective config (NFR-5.4), W3C
trace-context ids, and — when L1 is active — the external-call records that double as
the replay cache. Replay mode constructs an `Engine` whose L1 leaf resolver reads
exclusively from a supplied trace (NFR-5.3); replay is therefore a *configuration* of
the same engine, not a second code path.

## 11. Data Layer — StrataDB

**[AD-14] The evaluator is storage-free; everything persistent lives in StrataDB.**
`reason()` is pure compute — `Engine` holds no DB handle, and `expr`/`runtime` cannot
import the storage package (enforced with the AD-2 import rules). All persistence —
cases, telemetry, ruleset revisions, promotion/audit records, L1 cache/replay, temporal
series — goes through StrataDB (embedded, Rust core, PyO3 bindings; in-process like the
engine itself, so adopting it does not reintroduce a network hop or violate NFR-9.2).
`Strata.cache()` (in-memory) serves tests and ephemeral deployments, so "no files on
disk" remains possible without a second backend implementation.

**[AD-15] Single access site.** `storage/strata.py` is the only module that imports
`stratadb` — the persistence analogue of `ast_gate` [AD-4]. It owns the space layout,
branch lifecycle, transactions, and the promotion pointer; `storage/backends.py` builds
the protocol implementations (`CaseStore`, `Telemetry`, ruleset repository, audit log,
replay store) on top of it. The protocols remain the API; StrataDB is the bundled (and
only) backend.

### Primitive mapping

| Symbolica concern | StrataDB primitive | Notes |
|---|---|---|
| Cases (FR-10.7) | JSON store `case:<id>` + vector index | Auto-embed enables similarity retrieval: batch cases by decision family for distillation; `delete` satisfies NFR-9.3 erasure |
| Telemetry (FR-10.5) | Event log, type `decision` | Coverage = fold over events; append-only by construction |
| Ruleset repository (FR-10.1) | JSON store `ruleset:<revision>` | Content-hash key; `json_history` gives revision archaeology for free |
| Active-ruleset pointer | State cell `active_ruleset` | See promotion below |
| Promotion / audit records (NFR-7.5) | Event log, types `promotion`, `incident` | The event log is natively **hash-chained and immutable** — tamper evidence comes from the substrate; Symbolica's verifier checks Strata's chain rather than maintaining its own |
| L1 response cache + replay (FR-12.2) | KV `llm:<cache_key>` | Cache key per RESEARCH_SYNTHESIS §3.5; replay reads exclusively from here |
| Temporal series (L2) | Event log per metric, paginated reads | Event-time timestamps in payloads; window functions read ranges |
| Undistillable batches (FR-14.3) | JSON store `undistillable:<batch_id>` | Candidate + final diagnostics attached |

All Symbolica data lives in dedicated spaces (`symbolica.cases`, `symbolica.audit`, …)
so a host may hand Symbolica the **same database instance its agent already uses** for
memory — policy and memory share one store, one backup, one branch model — or a
dedicated path. Constructors take a `Strata` handle or a path.

**[AD-19] Durability mode per concern.** Audit/promotion records write in `Always`
mode (zero loss; ~2 ms is irrelevant at promotion frequency); cases and telemetry in
`Standard` (<30 µs writes — a telemetry append is noise inside the 1 ms `reason()`
budget; last ~100 ms at risk is acceptable for counters); candidate-branch simulation
workspaces in `Cache` (disposable by definition).

**[AD-20] Time travel is the audit substrate.** StrataDB's point-in-time snapshots
(`db.at(timestamp)`) and per-key version history upgrade auditability from "replay the
decision from its trace" to **reconstruct the world as it was**: the active ruleset
revision, the case store, and telemetry as of any decision's timestamp; behavioral
forensics ("what changed between Tuesday and Thursday") is a snapshot diff. Trace
replay (NFR-5.3) remains the per-decision mechanism; time travel supplies the
surrounding state. Audit and governor tooling open the database **read-only**
(`read_only=True`) as a least-privilege default (NFR-7.7).

### Candidate lifecycle on branches

**[AD-16] One branch per candidate ruleset.** The loop's distill→simulate→promote
pipeline maps directly onto StrataDB branching:

```
fork_branch("cand-<revision>")        # isolated copy-on-write workspace
  write candidate ruleset, run simulate(); simulation artifacts stay on the branch
  diff_branches("default", "cand-…")  # feeds the promotion review (what changes)
promote: write ruleset:<rev> on default + CAS pointer swap   reject: delete branch
```

Candidate evaluation can never contaminate live data — isolation is the database's
guarantee, not loop-code discipline.

**[AD-17] Promotion is a CAS swap.** The active ruleset is a state cell holding the
revision id; promotion executes inside one transaction: append the `promotion` audit
event + `state_cas(active_ruleset, new_rev, expected_version)`. A `ConflictError`
means a concurrent promotion won — the loop re-reads, re-validates against the new
active revision, and retries or escalates. This implements NFR-6.5's atomicity and
FR-14.8's expedited revision with the same primitive.

**[AD-18] `stratadb` is a required dependency.** The product (the loop) is meaningless
without persistence, and `Strata.cache()` covers the zero-setup path, so optionality
would buy a second backend's maintenance cost for no user benefit. Consequence: the
PRD's NFR-2.3 dependency budget is amended (stdlib + `jsonschema` + `stratadb`); the
`symbolica` wheel remains pure-Python while `stratadb` ships prebuilt native wheels —
the CI matrix (NFR-2.2) verifies installability on every supported platform/Python.

## 12. L1 / L2 / Loop Attachment Points

- **External leaves (L1)**: `expr.functions` defines a `LeafProtocol` —
  `(args, ctx) -> Value` plus declared `CostClass` and a `call_record` for the trace.
  `PROMPT` is one implementation; the core knows the protocol, not the provider.
  Cache → provider → record, with assert/suggest semantics implemented *inside* the
  leaf so the evaluator stays ignorant of retries.
- **Temporal (L2)**: registered as ordinary CHEAP functions closed over the host's
  `TemporalStore` instance; the store's thread contract is its own (RLock, as in v1's
  one good component).
- **Loop**: pure consumer. `ObservedEngine` wraps `Engine` + fallback callable +
  `Recorder`; `distill`/`repair` drive an authoring model with artifacts the core
  already exports (schema, llms.txt, diagnostics, simulation reports). Nothing in the
  loop has private access **[AD-1]**.

## 13. Testing Architecture (how NFR-3.2 is wired)

- `tests/conformance/cases/*.json` — golden triplets `(ruleset, facts, expected)`
  tagged with FR ids; one runner parametrizes all of them. The spec's worked examples
  are committed here verbatim.
- `tests/conformance/diagnostics/` — golden diagnostics (code + json_path + suggestion).
- `tests/properties/` — hypothesis strategies for rulesets/facts; invariants
  (totality, determinism, atomicity).
- `tests/regression/test_v1_bugs.py` — the 11 named v1 bugs.
- `tests/benchmarks/` — NFR-1 suite with stored baselines.
- FR-traceability: CI script greps test markers, fails on any §5–§11 FR without one.

## 14. Architecture Decision Index

| AD | Decision | Driver |
|---|---|---|
| AD-1 | Loop layer uses public API only | Hard boundary; forces API completeness |
| AD-2 | Import direction enforced by import-linter in CI | v1's layering eroded silently |
| AD-3 | FactView wrapper, no deep copy | NFR-1.1 latency budget |
| AD-4 | Single `ast.parse` call site (`ast_gate`) | Auditable security kernel |
| AD-5 | Compile collects all diagnostics, no fail-fast | Repair-loop round-trip economy |
| AD-6 | Closure-tree compilation, no VM | NFR-1 with auditability; no-Rete decision |
| AD-7 | One evaluator + trace hook | Kills v1 two-evaluator drift class |
| AD-8 | MISSING via internal signal; `has`/`default` as special forms | Zero happy-path cost |
| AD-9 | Cost ordering at compile time | Deterministic, no per-eval sorting |
| AD-10 | Monotonic deadline checks in closures | Thread/platform-safe (v1 bug #7) |
| AD-11 | All mutation confined to RunContext | Lock-free thread safety |
| AD-12 | Pickle carries RuleSet data, closures rebuilt | Process scale-out without code pickling |
| AD-13 | Masking at trace-record time | Leak-proof by construction (FR-8.4) |
| AD-14 | Evaluator storage-free; all persistence in StrataDB | Determinism of `reason()`; single data layer |
| AD-15 | Single `import stratadb` site (`storage/strata.py`) | Auditable persistence surface, mirrors AD-4 |
| AD-16 | One StrataDB branch per candidate ruleset | DB-guaranteed isolation for simulate (FR-14.4) |
| AD-17 | Promotion = transactional audit-append + state-cell CAS | Atomic promotion (NFR-6.5, FR-14.8) |
| AD-18 | `stratadb` required dependency; `Strata.cache()` covers ephemeral | One backend; zero-setup path preserved |
| AD-19 | Durability mode per concern (Always/Standard/Cache) | Loss tolerance matched to data criticality |
| AD-20 | Time travel as audit substrate; read-only opens for audit tooling | World-state reconstruction (NFR-5.4); least privilege (NFR-7.7) |

## 15. Deferred to the Spec

Grammar EBNF; the full type matrix; MISSING absorption semantics in boolean groups;
observable-equivalence rule for cost reordering; exact trace/Case JSON Schemas;
diagnostic payload schemas and message templates; worked conformance examples.
