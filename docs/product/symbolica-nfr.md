# Symbolica v2 — Non-Functional Requirements (Detailed)

*Normative elaboration of `symbolica-prd.md` §15. IDs NFR-1.x–NFR-4.x extend the families already
committed in the PRD (existing IDs unchanged); families NFR-5–NFR-10 are introduced
here. Every NFR has a **verification** — the test, benchmark, or check that proves it.
An NFR without a committed verification does not count as met.*

Priorities: **P0** = v2 core release gate · **P1** = layer-release gate · **P2** = tracked target.

---

## NFR-1 — Performance

Baseline configuration for all targets (the **reference profile**): 100-rule ruleset,
≤50 facts, ≤8 conditions/rule, no `PROMPT()` leaves, warm engine, single thread,
commodity x86-64 core (the CI runner class, pinned and documented). All numbers are
measured by the committed `pytest-benchmark` suite; CI fails on >15% regression vs the
stored baseline (see NFR-3.6).

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-1.1 | P0 | Pure-symbolic `reason()` p50 < 1 ms, p99 < 5 ms on the reference profile | Benchmark suite, percentiles asserted |
| NFR-1.2 | P0 | Throughput ≥ 5,000 `reason()`/s single-thread on the reference profile | Benchmark suite |
| NFR-1.3 | P0 | `compile()` of 1,000 rules < 1 s (≈1 ms/rule amortized) | Benchmark suite |
| NFR-1.4 | P0 | `import symbolica` < 150 ms; no import-time I/O, network, or heavy initialization | CI check: `python -X importtime`, asserted budget |
| NFR-1.5 | P1 | Memory: compiled ruleset ≤ 64 MB RSS delta at 1,000 rules (p50 rule ≤ 32 KB compiled) | Benchmark suite, `tracemalloc`/RSS measurement |
| NFR-1.6 | P0 | Trace overhead vs `trace='minimal'` baseline: `standard` ≤ 25%, `full` ≤ 3× | Benchmark suite, per-level comparison |
| NFR-1.7 | P1 | `simulate()` ≥ 1,000 cases/s on the reference profile (parallelism across processes permitted; engines are immutable) | Benchmark suite |
| NFR-1.8 | P1 | `why_not()` and `near_misses()` compute lazily from the trace — zero cost on runs where they are not called | Benchmark: `reason()` timing invariant to their presence |

**Honesty rule (normative):** no performance number appears in README/docs/marketing
unless it is produced by the committed benchmark suite, and it must always state the
profile (ruleset size, facts, trace level, hardware, percentile). This is a direct
response to v1's unsubstantiated "6,000+ executions/second" claim.

## NFR-2 — Platform, Concurrency, Dependencies, Sandboxing

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-2.1 | P0 | Thread safety: concurrent `reason()` on one engine from any thread (incl. non-main) yields results identical to sequential execution. No `signal`, no thread-affine or main-thread-only constructs anywhere in the engine | Dedicated stress test: N threads × M runs, byte-compare serialized results vs sequential; named regression for v1 bug #7 |
| NFR-2.2 | P0 | Platforms: Linux, macOS, Windows; CPython 3.10–3.13. No platform-conditional *semantics* (a feature either works identically everywhere or does not exist) | Full CI matrix (3 OS × 4 Python); conformance suite must pass on every cell |
| NFR-2.3 | P0 | Dependencies: core = stdlib + `jsonschema` + `stratadb` (the data layer, FR-10.9). L1 provider SDKs and YAML rendering are extras. Transitive dependency tree of core ≤ 8 packages. The evaluation path (`expr`/`runtime`) performs no storage I/O regardless (AD-14) | CI check: fresh-venv install + `pip list` assertion; import-linter rule banning `storage`/`stratadb` imports in `expr`/`runtime` |
| NFR-2.4 | P0 | Sandboxing: no `eval`/`exec`/`compile`-of-user-strings; AST whitelist at compile time; expressions cannot perform I/O, imports, attribute access on non-fact objects, or reach Python builtins; per-expression and per-run resource limits per FR-6.6 | Security conformance suite: corpus of hostile expressions (imports, dunders, comprehension smuggling, deep nesting, gigantic literals) must all yield compile-time diagnostics; fuzzing per NFR-6.2 |
| NFR-2.5 | P0 | Resource exhaustion safety: adversarial-but-schema-valid rulesets (max-size expressions, max rules, pathological `after` graphs, deep condition trees) cannot exceed 2× the deadline or unbounded memory | Property tests generating adversarial rulesets at the documented limits |
| NFR-2.6 | P1 | Supply chain: Dependabot enabled; release artifacts built in CI from tagged commits only; the `symbolica` wheel is pure-Python (`stratadb` ships prebuilt native wheels; installability verified on every CI matrix cell) | Repo config + release workflow review + matrix install check |
| NFR-2.7 | P1 | Parallelism guidance is honest: docs state that pure-Python evaluation is GIL-bound — scale-out is via processes (engines pickle/rebuild cheaply) or threads only for L1 I/O concurrency | Doc review + pickling round-trip test |

## NFR-3 — Engineering Quality

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-3.1 | P0 | CI on every PR: ruff, mypy (strict), pytest across the full matrix, coverage ≥ 90% on core packages, conformance suite, benchmark regression check. No merge on red | Branch protection + workflow definition |
| NFR-3.2 | P0 | Conformance suite as spec twin: every FR in PRD §5–§11 has ≥1 table-driven golden test (rules + facts → expected verdict/fired/diagnostics) written **before** implementing code; all 11 v1 bugs have named regression tests (`test_v1_bug_07_thread_silence`, …) | Traceability check: CI script maps FR IDs ↔ test markers and fails on uncovered FRs |
| NFR-3.3 | P0 | Fully typed: `py.typed`, public API 100% annotated, mypy strict passes with zero ignores in core | CI |
| NFR-3.4 | P0 | Diagnostics are tested artifacts: golden-diagnostic tests assert `code`, `json_path`, and `suggestion` content (not just "an error occurred") for every code in the FR-9.1 registry | Conformance suite section |
| NFR-3.5 | P2 | Mutation testing on `expr/` and `runtime/`: ≥ 70% mutation score, nightly | Nightly `mutmut`/`cosmic-ray` job |
| NFR-3.6 | P0 | Benchmark baselines stored in-repo; CI compares and fails on >15% regression at p50 on any NFR-1 metric; baseline updates are explicit, reviewed commits | Benchmark workflow |

## NFR-4 — Stability & Compatibility

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-4.1 | P1 | Trace schema versioned (`trace_version`); stable across patch releases; additive-only within a minor series | Schema-snapshot test |
| NFR-4.2 | P0 | SemVer on the public API (`symbolica` top-level + documented submodules). Breaking changes only at major versions; deprecations live ≥ 1 minor release with a runtime `DeprecationWarning` before removal | API-snapshot test (public symbols + signatures diffed against committed snapshot) |
| NFR-4.3 | P0 | Ruleset format versioned by integer (`"format": 2`). The engine rejects unknown formats with a clear diagnostic; any future format 3 ships with a migration tool for format-2 documents | Conformance tests for unknown-format rejection |
| NFR-4.4 | P0 | `Case` schema versioned; recorded cases from version N readable by all later minor releases (the case store is long-lived training data — breaking it destroys accumulated experience) | Round-trip tests against archived fixture files from each released version |
| NFR-4.5 | P1 | Replay compatibility: a trace recorded by version X replays on X and X+minor releases; replay across majors is best-effort and says so | Replay fixture tests |

## NFR-5 — Determinism & Reproducibility

The product's core claim; verified, not asserted.

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-5.1 | P0 | Bit-stable results: identical (ruleset revision, facts, function registry) ⇒ identical serialized `verdict`, `fired`, `diagnostics` across runs, threads, processes, OSes, and supported Python versions | CI determinism job: run conformance corpus on every matrix cell, compare result-corpus hash across all cells |
| NFR-5.2 | P0 | No ambient nondeterminism in the engine: no wall-clock reads affecting results (deadline uses injected/monotonic clock; `decision_id` and timestamps live only in trace metadata, never in verdict-affecting paths), no RNG, no dict-iteration-order dependence (all orderings explicit), no env-var behavior switches | Code-review checklist + grep-based CI lint (`time.time`, `random`, `os.environ` banned in core paths) + NFR-5.1 catches violations |
| NFR-5.3 | P1 | Replay fidelity (L1): a replayed run consumes external-call results exclusively from the recorded trace; cache miss during replay is a hard, identifying error — never a silent live call | L1 conformance: record run, replay with a poisoned/absent provider, byte-compare results |
| NFR-5.4 | P0 | Effective-config transparency: every limit and default in play (`max_passes`, deadline, limits, allowlist, ruleset revision, engine version) is readable on the engine and stamped into the trace, so any result is reconstructible from its trace alone; the data layer's time-travel snapshots (`db.at(t)`, AD-20) additionally reconstruct the full surrounding state (ruleset, cases, telemetry) at the decision's timestamp | Trace-content conformance test + loop audit test |

## NFR-6 — Reliability & Failure Behavior

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-6.1 | P0 | Totality: for any ruleset accepted by `compile()` and any JSON-representable facts, `reason()` returns a result (possibly with diagnostics) — it never raises (except under `strict=True`), never hangs past 2× deadline, never corrupts the engine for subsequent calls | Property-based tests (hypothesis): generated rulesets × generated facts; invariant suite |
| NFR-6.2 | P0 | Fuzzing: nightly fuzz of the three untrusted inputs — ruleset documents (vs `compile`), expression strings (vs the compiler), facts (vs `reason`) — with a committed regression corpus; crashes are P0 bugs | Nightly job (hypothesis + atheris or equivalent); corpus in-repo |
| NFR-6.3 | P0 | Diagnostic completeness: every non-firing caused by an error is attributable — `result.diagnostics` explains every rule that was eligible and evaluated but errored. Silent behavior differences are the defect class that killed v1; zero tolerance | Conformance: error-injection tests assert one diagnostic per induced failure |
| NFR-6.4 | P1 | L1 provider failure containment: timeouts/outages yield `LLM_UNAVAILABLE` diagnostics within the configured timeout; bounded retries with exponential backoff and a retry cap (no retry storms); a provider outage degrades only rules with `PROMPT()` leaves — symbolic rules are unaffected | L1 tests with fault-injecting mock provider |
| NFR-6.5 | P1 | Loop-layer fault isolation: a failed distillation/simulation never touches the active engine; promotion is atomic (new engine fully built and validated before swap is offered) | Loop integration tests |

## NFR-7 — Security

Threat model: **expressions and rulesets are untrusted input** (machine-authored,
possibly by a compromised or manipulated agent); **facts are untrusted data** (extracted
from user-controlled conversations); the host process is trusted.

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-7.1 | P0 | The expression sandbox (NFR-2.4) holds against deliberately malicious rulesets: no code execution, no I/O, no access to host objects beyond provided facts/functions | Hostile-expression corpus + fuzzing (NFR-6.2); external review before 2.0 final |
| NFR-7.2 | P0 | Capability containment: `emit_allowlist` is enforced in the engine's execution path; no configuration of the loop layer can widen what rules may emit | Conformance + a test that drives the loop with a hostile authoring model emitting out-of-scope rules |
| NFR-7.3 | P1 | Prompt-injection resistance (L1): facts interpolated into `PROMPT()` templates are sanitized/delimited; injection attempts in fact values cannot alter the template's instructions; typed-output parsing never executes response content | L1 red-team corpus (carried over from v1's test ideas, rebuilt) |
| NFR-7.4 | P1 | Trace hygiene: at `standard` level, traces store the `PROMPT()` template id + rendered-prompt **hash** (not full text); full text only at `full` level, which docs flag as potentially containing user data | Trace-content tests |
| NFR-7.5 | P1 | Audit integrity: promotion records and revision history live in StrataDB's **natively hash-chained**, append-only, sequence-numbered event log (FR-10.9) — tamper evidence from the substrate; Symbolica's verifier checks Strata's chain | Loop tests: tamper with a record, verifier detects |
| NFR-7.6 | P1 | Static analysis security gates in CI: bandit (or semgrep ruleset) clean; CodeQL enabled on the repo | CI config |
| NFR-7.7 | P1 | Least privilege for audit: governor/audit tooling opens the database read-only (`Strata.open(..., read_only=True)`); only the engine/loop write paths hold writable handles | Code review + loop tests |

## NFR-8 — Observability & Operability

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-8.1 | P0 | Library silence: Symbolica never writes to stdout/stderr; logging via `logging` with `NullHandler` — zero output unless the host configures it. All diagnostic information flows through results, never side-channel logs | Test: capture streams across the conformance suite, assert empty |
| NFR-8.2 | P0 | Telemetry is pull-shaped and non-blocking: the `Telemetry` sink is called synchronously with a bounded-size record; a slow or raising sink cannot fail or slow `reason()` beyond a documented bound (sink exceptions are swallowed to a dead-letter counter) | Fault-injection test on the sink |
| NFR-8.3 | P1 | OpenTelemetry compatibility: `trace_id`/`span_id` are W3C trace-context compliant; an OTel host can pass its context in so engine decisions appear as spans of the host trace | Integration test with the OTel SDK |
| NFR-8.4 | P1 | Coverage observable out of the box: the bundled StrataDB telemetry sink (event log, FR-10.9) computes coverage/precision aggregates with a one-line helper — no external stack required to see the north-star metric | Loop tests |

## NFR-9 — Privacy & Data Handling

Facts and cases routinely contain end-user PII (conversations, orders, identities).

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-9.1 | P1 | Field masking: hosts can declare fact paths as masked; masked values appear as `"<masked>"` in traces, telemetry, and recorded cases, with the masked paths listed (OPA `erased`/`masked` precedent). Masking happens before any persistence | Conformance: masked field never appears in any serialized artifact. *Implies a functional addition — proposed as FR-8.4 at next PRD revision* |
| NFR-9.2 | P1 | Engine and loop perform no network transmission of facts/cases/traces except (a) configured L1 provider calls and (b) host-configured sinks. No telemetry-home, ever | Code review + socket-monitoring test in CI |
| NFR-9.3 | P2 | Case-store retention hooks: the store interface supports delete-by-case-id and delete-by-predicate (GDPR-style erasure); the bundled StrataDB store implements both. Distilled *rules* derived from erased cases persist (documented position: rules are aggregates; provenance case-references may dangle and the verifier reports them) | Store contract tests |

## NFR-10 — Developer Experience & Documentation

| ID | Pri | Requirement | Verification |
|---|---|---|---|
| NFR-10.1 | P0 | Time-to-observation-mode < 1 hour for a developer new to Symbolica, following the quickstart (which is ≤ 30 lines of code, per `symbolica-user-flows.md` §1.1) | Doc walkthrough executed in CI (quickstart is a tested script); at least one human run before 2.0 |
| NFR-10.2 | P0 | The `llms.txt` authoring guide (FR-5.6) is itself conformance-tested: every example in it compiles clean, and its diagnostic catalog stays in sync with the FR-9.1 registry (generated, not hand-maintained) | CI doc-test job |
| NFR-10.3 | P1 | Every public API has a docstring with a runnable example; doctests run in CI | CI |
| NFR-10.4 | P1 | Error-message style: one sentence, names the thing (quoted), states the constraint, points at the fix — enforced by the golden-diagnostic tests (NFR-3.4) | Conformance |

---

## Verification summary (what CI must contain when all P0s are met)

1. Lint/type: ruff + mypy strict (NFR-3.1, 3.3)
2. Conformance suite with FR-traceability map (NFR-3.2) incl. golden diagnostics (3.4), v1-bug regressions, security corpus (2.4), trace-content (5.4, 7.4), stream-silence (8.1)
3. Full-matrix determinism hash job (5.1)
4. Thread-safety stress (2.1)
5. Property/invariant suite (6.1) + nightly fuzz (6.2) + adversarial-ruleset limits (2.5)
6. Benchmark suite with stored baselines + regression gate (1.x, 3.6)
7. Import-time, dependency-count, fresh-venv checks (1.4, 2.3)
8. API/schema snapshot diffs (4.2, 4.1) + case-fixture round-trips (4.4)
9. Quickstart-as-test + llms.txt doc-tests (10.1, 10.2)
10. bandit/CodeQL (7.6), socket monitor (9.2)

## PRD follow-ups from this document — folded into PRD v1.3

- **FR-8.4** (trace/case field masking, from NFR-9.1) — added to PRD §8.
- **Open question 7** (privacy posture on rules distilled from erased cases) — added
  to PRD §18 with owner pre-M5.
