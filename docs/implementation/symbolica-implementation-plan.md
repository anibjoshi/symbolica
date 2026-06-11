# Symbolica v2 — Implementation Plan (Milestones & Epics)

| | |
|---|---|
| Status | Active — the high-level execution map |
| Version | 1.0 (2026-06-11) |
| Upstream | `symbolica-prd.md` v1.5 (§17 milestones), `symbolica-architecture.md` v1.2, `symbolica-spec.md` v1.0, `symbolica-nfr.md` |
| Downstream | Per-milestone detail docs + testing plans (see §5 Document Plan) |

This document breaks the PRD's milestones into **epics** — PR-sized, independently
reviewable units with explicit upstream references. Detail (task lists, interfaces,
test matrices) lives in the per-milestone documents written when that milestone starts;
this document only changes when scope moves between milestones.

---

## 1. Ground Rules

1. **Spec-first, tests-before-code (NFR-3.2).** Every epic starts by committing its
   conformance/golden tests (xfail), then implements until green. The spec wins over
   the implementation (S-11).
2. **Branch model.** Long-lived `v2-rebuild` branch off `main`; one PR per epic into
   `v2-rebuild`; `main` keeps v1 until M4 exit, then `v2-rebuild` merges and v1 is
   deleted. CI gates every PR from E0.1 onward.
3. **Epic = the review unit.** Each epic lists its upstream references (FR/NFR/S/AD
   ids); a PR that changes behavior outside its epic's references is split.
4. **Definition of done (every epic):** referenced conformance tests green · new code
   ≥90% covered · mypy strict + ruff + import-linter clean · golden diagnostics for
   any new codes · no performance regression vs stored baselines (once E4.4 lands) ·
   detail doc's checklist for that epic ticked.
5. **Sizes** are relative (S < M < L) and exist for sequencing judgment, not estimates.

## 2. Milestone Map

```
M0 foundation ─▶ M1 expr core ─▶ M2 format+analysis ─▶ M3 runtime ─▶ M4 data layer + release (engine ships)
                                                                          │
                                                                          ▼
                                                       M5 Loop v0 (product ships) ─▶ M6 L1 LLM ─▶ M7 L2 temporal + loop maturity
```

M1 and M2 can overlap after E1.3 (the analyzer consumes compiled-expression field
sets); M5's OQ-8 decision (strata-inference) gates M6's E6.1 design.

---

## 3. Milestones & Epics

### M0 — Foundation & Contracts *(no engine logic; everything mechanical from the spec)*

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E0.1 Scaffolding & CI** | `v2-rebuild` branch; package skeleton per architecture §3 (empty modules, `py.typed`); `pyproject` (deps: `jsonschema`, `stratadb`; extras; hatchling); ruff + mypy strict + **import-linter contracts** (AD-2, incl. the `expr`/`runtime` storage ban); GitHub Actions: lint/type/test on 3 OS × 3.10–3.13, coverage ≥90% gate | NFR-2.2/2.3, NFR-3.1/3.3, AD-2/14 | M |
| **E0.2 Schemas as artifacts** | `ruleset.schema.json` (format 2, S-1), `case.schema.json` (S-6), `trace.schema.json` (S-7) under `dsl/schema/`; valid/invalid document corpora as tests | FR-5.1, S-1/6/7, NFR-4.3/4.4 | S |
| **E0.3 Diagnostics module** | `Diagnostic` type; closed code registry with per-code payload dataclasses + message templates (S-5); json_path/span locations; suggestion helpers (edit-distance); golden-diagnostic test format | FR-9.1, S-5, NFR-3.4 | M |
| **E0.4 Conformance harness** | Golden-triplet runner (`tests/conformance/cases/*.json`), FR-traceability CI script (FR id ↔ test-tag map, fails on uncovered §5–§11 FRs), S-9 examples E1–E6 committed as xfail | NFR-3.2, S-9/11 | M |

**Exit:** CI green on the full matrix; schemas + diagnostic catalog reviewed; goldens
committed (xfail until M3).

### M1 — Expression Core *(`expr/` — the security kernel)*

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E1.1 AST gate** | `ast_gate.py`: parse, node whitelist, length/depth limits; the **only** `ast.parse` site; hostile-expression security corpus (dunders, imports, comprehension smuggling, `is`, f-strings, depth bombs) | S-3.1–3.3, AD-4, NFR-2.4 | M |
| **E1.2 Value discipline** | `values.py`: full S-3.5 operator/type matrix; bool⊄int guard; null-equality rule (SD-5); `/`→float, `%`/`**` semantics + exponent guard (SD-7); error signal types | S-3.5, SD-2/5/6/7, FR-6.3 | M |
| **E1.3 Closure compiler** | AST → `CompiledExpr` closure tree; name/path resolution incl. dotted/subscript semantics (S-3.4, SD-4); MISSING signal (AD-8); field-set extraction; cost classes | S-3.4, AD-6/8, FR-6.1 | L |
| **E1.4 Boolean semantics** | Absorption (SD-9); strict-bool logic (SD-8); chained comparisons; compile-time cost ordering (AD-9); **order-independence property tests** (hypothesis: any operand order ⇒ same result+diagnostics) | S-3.6, SD-8/9, FR-6.5 | L |
| **E1.5 Builtins & functions** | S-3.8 builtins; `has`/`default` special forms (SD-10); `FunctionTable` frozen at build; `FUNCTION_ERROR` wrapping; reserved-name enforcement | S-3.7/3.8, FR-6.2, FR-11.1 | M |
| **E1.6 Templates** | `{= }` interpolation: parse, escapes, stringification (SD-13), output limit; `=`-marking + `==` escape helpers (S-1.4/SD-1) | S-1.4, S-3.9 | S |
| **E1.7 Eval context & limits** | `RunContext`-facing eval side: monotonic deadline checks (AD-10), hook protocol (AD-7, no-op impl), recursion/limit diagnostics; thread-safety stress on shared `CompiledExpr` | FR-6.6, AD-7/10/11, NFR-2.1 | M |

**Exit:** all S-3 conformance + security suite green; expression property/fuzz
strategies running nightly; zero platform-conditional behavior.

### M2 — Format & Static Analysis *(`dsl/`)*

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E2.1 Parser & RuleSet** | JSON doc → schema validation → `RuleSet` lift; value marking applied via E1.6; canonical-JSON revision hashing; collect-all-diagnostics compile pipeline (AD-5) | S-1, FR-5.*, FR-10.1, AD-5 | M |
| **E2.2 Dependency analysis & canonical order** | Field-dep graph from compiled field sets; `after` validation (targets, cycles); **SCC condensation ordering** (SD-14); `execution_order()` | S-4.1, FR-7.4/7.5, SD-14 | L |
| **E2.3 Conflict & reachability analysis** | Emit-conflict (same key/priority/co-firable), shadowing, unreachable rules; golden diagnostics for each | FR-9.2, S-5 | L |
| **E2.4 Fact-schema introspection** | `fact_schema()` from compiled field sets + usage-inferred type constraints | FR-10.8 | S |

**Exit:** FR-5/FR-9 conformance green incl. golden diagnostics; `compile_ruleset`/
`validate` API shells stable.

### M3 — Runtime *(`runtime/` + `engine.py` — the engine becomes real)*

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E3.1 FactView & RunContext** | Read-only memoizing fact wrapper (AD-3); working memory; per-run mutable state container (AD-11) | AD-3/11, FR-7.1 | M |
| **E3.2 Executor** | Pass loop per S-4.2: eligibility, fire-once, compute-then-apply atomicity, error-retry vs FAILED (SD-15), convergence/`NOT_CONVERGED` | S-4.2, FR-7.2/7.3/7.6, SD-15/16 | L |
| **E3.3 Verdict & allowlist** | Staged-emit fold: priority-wins + doc-order tiebreak, `changed` view, `covered`; engine-enforced emit allowlist | S-4.4, FR-7.6, FR-10.6 | M |
| **E3.4 Trace** | `TraceBuilder` hook: three levels per S-7, masking at record time (AD-13, FR-8.4), serialization, `for_llm()` | S-7, FR-8.2/8.4, AD-7/13 | L |
| **E3.5 Result & explanations** | `ExecutionResult`; `why_not`/`near_misses` derived lazily from standard-level trace (counterfactual boundaries) | FR-8.1/8.3, S-7, NFR-1.8 | M |
| **E3.6 Engine facade & APIs** | `Engine` (immutable, picklable AD-12), `reason()` totality contract (S-8), `strict` mode, `compile_ruleset`/`validate` final API | S-8, FR-10.1/10.2/10.4, NFR-6.1 | M |
| **E3.7 Correctness gauntlet** | S-9 goldens flipped to passing; **11 named v1-bug regressions**; determinism hash job across matrix (NFR-5.1); totality property suite; thread stress; banned-construct lint (NFR-5.2) | NFR-2.1, NFR-5.1/5.2, NFR-6.1/6.3 | L |

**Exit:** every P0 core FR conformance-green; the gauntlet green on all matrix cells.

### M4 — Data Layer, Hardening & Engine Release *(`storage/`, `lifecycle/`, ship `2.0.0a1`)*

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E4.1 StrataDB layer** | `storage/strata.py` (sole import site, spaces, durability modes AD-19, transactions) + `backends.py` (CaseStore, Telemetry, ruleset repo, hash-chain-verified audit log) | FR-10.9, AD-15/19, NFR-7.5 | L |
| **E4.2 Recording & telemetry** | `Case` + `Recorder` (zero-rule observation works); coverage helpers; masking into persistence; read-only audit opens | FR-10.5/10.7, NFR-7.7/8.4, S-6 | M |
| **E4.3 Simulation** | `simulate()` with process-pool parallelism (pickle AD-12), `SimulationReport` (diffs vs baseline, per-rule precision/recall) | FR-10.3, S-8 | M |
| **E4.4 Benchmarks & fuzzing** | NFR-1 suite with stored baselines + CI regression gate; nightly fuzz of the three untrusted inputs with committed corpus; adversarial-ruleset limits | NFR-1.*, NFR-3.6, NFR-6.2, NFR-2.5 | M |
| **E4.5 Authoring & docs surface** | Generated `llms.txt` (catalog-synced, doc-tested); YAML review projection; quickstart-as-CI-test; example corpus rewritten for v2 | FR-5.5/5.6, NFR-10.1/10.2 | M |
| **E4.6 Release engineering** | API snapshot test (NFR-4.2); packaging; delete v1 from branch; `2.0.0a1`; side-by-side v1-bug-correctness report; merge `v2-rebuild` → `main` | NFR-2.6/4.2, PRD §17 ship gate | M |

**Exit (the engine ships):** PRD §17 M4 criteria — NFR-1 met & published, CI green,
v2 correct on every `symbolica-correctness-bugs.md` case.

### M5 — Loop v0 *(`loop/` — the product ships)*

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E5.1 Observation mode** | `ObservedEngine` one-line wrapper (fallback + auto-record) | FR-14.1 | S |
| **E5.2 Distillation** | `distill()`: authoring-contract assembly (schema + llms.txt + live context), structured-output candidate generation | FR-14.2 | L |
| **E5.3 Repair loop** | Diagnostic-driven repair ≤3 round-trips; budget-exhaustion → undistillable escalation; `NEAR_DUPLICATE_RULE` via vector search | FR-14.3/14.9 | M |
| **E5.4 Gate & promotion** | Branch-per-candidate (AD-16), simulation gate, CAS promotion + approval policy + expedited revision (AD-17), provenance stamping | FR-14.4/14.5/14.8, AD-16/17 | L |
| **E5.5 Gap clustering & coverage** | Uncovered-case embedding/clustering for distillation targeting; coverage/cluster telemetry | FR-14.10, NFR-8.4 | M |
| **E5.6 Flagship demo** | The §14 acceptance demo as a reproducible script + report; calibrates OQ-6 (case-volume threshold); OQ-8 decision input (strata-inference) | PRD §14/§17 M5 | M |

**Exit (the product ships):** flagship demo passes — coverage >50% on held-out cases,
≤3 repair round-trips, measured cost/latency savings.

### M6 — L1 LLM Layer

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E6.1 Leaf protocol & providers** | `LeafProtocol` (cost class, call records); provider adapters **or** strata-inference routing per OQ-8 decision | FR-12.1/12.6, OQ-8 | L |
| **E6.2 Determinism contract** | Cache (full key incl. model snapshot); record/replay engine mode (replay-only resolver, loud cache miss) | FR-12.2, NFR-5.3 | M |
| **E6.3 Typed extraction & failure semantics** | Structured outputs, refusal handling, semantic validation; assert/suggest with feedback retries + symbolic fallback | FR-12.3/12.4 | M |
| **E6.4 Cost control** | Per-call accounting in trace, run budget → `BUDGET_EXCEEDED`, opt-in voting with early stopping | FR-12.5/12.7 | M |

### M7 — L2 Temporal & Loop Maturity

| Epic | Scope | Refs | Size |
|---|---|---|---|
| **E7.1 Temporal functions** | Event-log-backed series; `recent_*` windows; rigorous `sustained(max_gap)`; bounded lateness | FR-13.* | M |
| **E7.2 Monitoring & retirement** | Helpful/harmful counters from outcomes; underperformer flagging → re-distillation queue | FR-14.6 | M |
| *(backlog)* | Canary/champion-challenger (FR-14.7, P2); event projections & graph provenance when StrataDB lands them (watch list) | FR-14.7 | — |

---

## 4. Cross-Cutting Tracks (run continuously, owned per-milestone)

- **Conformance & traceability** — every epic adds its goldens; the FR-map script
  blocks merges with uncovered FRs (E0.4 onward).
- **Determinism** — the matrix hash job (E3.7) runs on every PR after M3.
- **Performance** — baselines from E4.4 gate every later PR (NFR-3.6).
- **Security** — hostile corpora grow with every new construct; bandit/CodeQL from E0.1.

## 5. Document Plan (what gets written next)

Per milestone, two documents in `docs/implementation/`, written **when the milestone
starts** (M0's immediately):

- `symbolica-m<N>-plan.md` — detailed design per epic: task breakdown, module
  interfaces/signatures, data structures, sequencing within the milestone, open
  questions to resolve before coding.
- `symbolica-m<N>-testing.md` — the comprehensive testing plan: per-epic test matrix
  (conformance cases by S-section clause, property strategies, golden diagnostics,
  negative/security cases), coverage targets, and the milestone's exit-gate checklist.

Naming is fixed now so cross-references are stable: e.g. `symbolica-m0-plan.md`,
`symbolica-m0-testing.md`.

## 6. Risks & Watch Items

| Risk | Mitigation |
|---|---|
| Spec gaps discovered mid-implementation | Spec is amended first (SD-index grows), tests second, code third — never code-first |
| `stratadb` API churn (0.x) | Single import site (AD-15) bounds the blast radius; pin version per release |
| Absorption semantics (SD-9) subtler than specced | E1.4's property tests are the canary; any counterexample → spec review before code lands |
| Distillation quality below the ≤3-round-trip budget | E5.6 calibrates early; diagnostic richness (E0.3) is the lever, per research |
| Performance targets miss in pure Python | Profile before optimizing; closure compilation (AD-6) has headroom (interning, slot classes) before any architectural change |
