# Research Synthesis → v2 Design Decisions

*Reconciles the two research reports (`symbolica-rule-engine-research.md`,
`symbolica-deep-research-agent-authored.md`) and records the resulting design decisions.
2026-06-11. Each decision below is reflected in `symbolica-rebuild-design.md`.*

---

## 1. The one genuine conflict between the reports: missing-data semantics

- **Report 1 (engine survey)** recommends *against* our position (High confidence):
  Rego-style `undefined` + per-rule `default`, arguing hard errors over LLM-extracted,
  routinely-incomplete facts make rulesets brittle and noisy.
- **Report 2 (agent-authored)** recommends *for* our position (High confidence):
  CEL-style error-on-missing is "the safest choice against silent-wrong-answers," with
  the refinement that the error must be a catchable, JSON-path-localized diagnostic —
  not an abort — plus explicit `has()` / `default()` macros for deliberate tolerance.

**Resolution: keep structured-error-on-missing (Report 2), for three reasons.**

1. The two positions converge operationally — in both, the rule does not fire. The
   difference is whether the non-firing is *recorded as a diagnostic* or *silent*. v1's
   single worst defect class was silent non-firing (typo'd field → no fire, no signal,
   symbolica-correctness-bugs.md #11). Rego's undefined-propagation reproduces that failure mode.
2. Report 1's own stated threshold cuts our way once authorship is agentic: the harness
   repair loop *consumes* errors as its feedback signal. A missing-fact diagnostic with
   rule id + JSON-path is exactly what the authoring agent needs to add a `default()` or
   fix the field name; silent undefined gives it nothing.
3. Both reports agree on the invariants regardless of camp: never coerce missing to
   `false`, surface missing distinctly in the trace, provide an explicit opt-in default
   mechanism.

**Adopted semantics:** referencing a missing fact yields a structured
`MISSING_FACT` diagnostic on the result (rule does not fire, run continues; `strict=True`
raises); `has(f)` and `default(f, x)` builtins are the deliberate tolerance path; traces
mark missing-fact reads distinctly. Both reports suggest the same empirical check: the
simulation harness can measure brittleness on real recorded cases, and the decision gets
revisited only if missing-fact diagnostics dominate real rulesets even with `default()`
available.

## 2. Positions confirmed by both reports (no change)

| v2 position | Evidence highlight |
|---|---|
| No Rete; pass-based forward chaining, compile-time everything | Oracle NRE docs, Phreak's lazy redesign; our profile (small rulesets, per-turn fact churn, LLM-dominated latency) is Rete's anti-profile. Reversal threshold recorded: persistent facts + >5k rules + symbolic eval becoming the bottleneck. |
| Fire-at-most-once per run | Lightweight-engine consensus (ZEN, json-rules-engine). Report 1 proposed fact-version refraction instead (Medium-High); **rejected for v2** — implicit re-fire is exactly the kind of invisible control flow machine authors can't reason about. Decision recorded: a rule whose inputs change after it fired does *not* re-fire within a run, by spec, not by accident. |
| Highest-priority-wins verdict conflicts + document-order tiebreak + load-time overlap analysis | Drools 6.0 model (salience then file order); DMN overlap/subsumption analysis (Calvanese et al.). Both reports: priority survived, recency/specificity stacks are footguns — worse for machine authors. |
| `after:` explicit gating, no truth maintenance | Confirmed; `after` doubles as the dependency graph the harness analyzes. |
| Immutable engine, compile-time validation | Starlark hermeticity, CEL compile-time checking. |
| JSON-first canonical format, shallow nesting, JSON Schema as the structured-output contract | CallNavi ("JSON outperforms YAML"), Norway problem, GoRules generate-then-validate pattern. |
| In-string `"= expr"` marked expressions — **not** JsonLogic ASTs, **not** `{"expr": ...}` objects | Hypothesis Search (concrete programs 30% vs 17% abstract), grammar-prompting DSL findings, nesting-depth error rates. Settles the question we left open in §7 of the design. |
| Harness loop: propose → validate → simulate → promote → monitor | Mirrors ACE (Generator→Reflector→Curator) and Voyager's verify-before-commit. |

## 3. Positions revised or extended by the research

1. **No implicit type coercion in expressions** (new, CEL's rule — "a common source of
   bugs"). `1 == "1"` is a compile-or-eval-time type diagnostic, never `false`/`true`.
   Coercion exists in exactly one place: explicit typed `PROMPT()` returns.
2. **Compile rules to closures with cost-ordered, short-circuiting predicate
   evaluation** (extends §3): within `and`/`or`, cheap symbolic predicates evaluate
   before expensive leaves so `PROMPT()` is reached only when it can change the outcome.
   Per-evaluation budget ceiling returns a structured `BUDGET_EXCEEDED` diagnostic.
3. **Trace schema modeled on OPA decision logs + W3C trace-context** (extends §4):
   `decision_id`, `trace_id`/`span_id`, fired rule ids, consumed field values,
   per-`PROMPT()` call records (prompt hash, model+snapshot, response, cost, latency,
   cache-hit), and a replay cache (OPA `nd_builtin_cache` precedent). Compact and
   structured — evidence says concise structured traces help downstream LLMs; verbosity
   configurable.
4. **"Why-not" output is a first-class result feature**: for near-miss rules, ranked
   failed conditions with field, threshold, and the counterfactual value that would have
   flipped it — capped small (ECOA/Reg B "specific reasons," FICO ≤4 reason codes;
   Wachter counterfactuals). Doubles as the harness repair signal (TraceCoder: trace-level
   feedback prevents repair stagnation; most repair gains land in round-trips 1–3).
5. **`PROMPT()` determinism contract** (L1 spec, strengthened): cache key =
   (prompt, model, **model snapshot**, temperature, output schema); record/replay store
   where replayed runs fetch LLM results exclusively from the trace; DSPy-style
   **assert vs suggest** failure semantics (hard error vs retry-with-feedback-then-
   symbolic-fallback); opt-in retry-and-vote with early stopping; structured outputs for
   shape with **refusal handling** and post-hoc semantic validation (range/enum/cross-
   field) because schema-valid-but-wrong is the dominant failure mode (ExtractBench:
   structured mode can *reduce* accuracy on complex schemas — keep PROMPT() return
   schemas trivially simple: scalar types only).
6. **`sustained()` redefined** (L2 spec): condition holds across `[now − duration, now]`
   over event-time samples with an explicit, documented max-gap/coverage parameter —
   replacing v1's arbitrary 80% heuristic. Temporal layer = event-time windowed
   aggregates + one bounded-lateness parameter; no CEP state machine.
7. **Harness safety hardening** (extends §7): emit/action **allowlists enforced
   deterministically at execution time** (prompt-level instructions are not a control
   surface — Microsoft AGT ~26.7% prompt-only violation rate; OWASP ASI01), per-rule
   ACE-style helpful/harmful telemetry counters, canary/champion-challenger promotion,
   tamper-evident provenance per rule version, and an `llms.txt`-style machine doc of
   the rule schema for authoring agents.

## 4. Deferred / empirical questions (tracked, not blocking)

- Fact-version refraction (re-fire on changed inputs) — revisit only if real rulesets
  demonstrate missed-update bugs under fire-once.
- Retry-and-vote cost/benefit at temp≈0 — opt-in per leaf; measure in the harness.
- Constrained-decoding accuracy degradation on complex schemas — mitigated by
  scalar-only PROMPT() schemas; re-evaluate if richer extraction is added.
- Whether priority should exist at all vs pure dependency ordering (Drools maintainers'
  long-term direction) — keep priority; revisit post-v2 with harness telemetry.

## 5. Phase-plan impact

- **P0 exit criteria updated**: design review now includes this synthesis; JSON Schema
  is authored as the LLM structured-output contract from day one.
- **P1 (expr core)** picks up: no-coercion typing, closure compilation, cost-ordered
  short-circuit, `has()`/`default()` builtins, MISSING semantics, budget ceiling hook.
- **P3 (runtime)** picks up: OPA-modeled trace schema, why-not/near-miss output,
  structured diagnostics with error codes + JSON-path.
- **L1 (LLM layer)** spec is now largely written (item 3.5 above).
- **Harness phase** inherits §3.7 requirements; allowlist enforcement lands in the
  *engine* (execution-time check), not the harness, so it can't be bypassed.
