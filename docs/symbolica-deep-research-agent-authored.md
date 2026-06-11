# Designing a World-Class Hybrid (Neuro-Symbolic) Rule Engine: Industry & Academic Survey for Symbolica v2

## TL;DR
- **For agent-authored rules, emit a JSON-first rule envelope carrying short, Python-like marked expression *strings* — not nested JSON/JsonLogic ASTs and not free-form YAML.** Evidence consistently shows LLMs are weakest on bespoke DSL syntax under-represented in pretraining, that deeply nested JSON schemas raise error rates, and that executable Python-like programs outperform abstract encodings (Hypothesis Search: 30% vs 17%); JSON envelopes parse and validate more reliably than YAML, which carries the Norway-problem and indentation footguns. This **confirms** the v2 `"= expr"` sigil + structured-error-on-missing-fact positions and **contradicts** any inclination toward YAML-as-carrier or full-AST encodings.
- **The harness should be a closed propose → validate → simulate → promote → monitor loop with machine-actionable diagnostics** (error codes, JSON-path localization, fix suggestions, near-miss/counterfactual traces). Repair-loop evidence shows most gains land in the first 1–3 round-trips and that rich runtime/trace feedback beats binary pass/fail; structured outputs guarantee *shape*, never *correctness*, so simulation over recorded cases and per-rule precision/recall telemetry are mandatory, not optional.
- **Symbolica's defensible white space is the combination no one else ships together**: deterministic explainable symbolic core + `PROMPT()` LLM-in-rule leaves with determinism contracts (cache/replay/vote) + agent-consumable traces + an agent-authored-ruleset governance harness. Guardrails (NeMo/Guardrails AI), policy engines (OPA/Cedar), and decision engines (GoRules/Camunda) each own a slice, but none unify probabilistic leaves, repair-oriented traces, and machine governance.

---

## Key Findings

### §I — Agent-authored rules & the agentic harness (TOP PRIORITY)

1. **LLMs author executable code/programs more reliably than bespoke DSLs or abstract encodings.** Grammar Prompting (Wang et al., NeurIPS 2023, arXiv 2305.19234) states plainly that "DSLs are by definition specialized and thus unlikely to have been encountered often enough (or at all) during pretraining for the LLM to acquire its full syntax," and that grammar scaffolding "shows limited benefits for DSLs common in pretraining data." A Microsoft study (Bassamzadeh & Methani, arXiv 2407.02742, 2024) found that even fine-tuned and RAG-optimized DSL generation "still got the syntax wrong many times" with measurable hallucination of function/parameter names. Hypothesis Search (Wang et al., ICLR 2024, arXiv 2309.05660) showed concrete Python program representations reach 30% on an ARC subset vs 17% for direct prompting — "both abstract hypothesis generation and concrete program representations benefit LLMs."

2. **JSON beats YAML for LLM emission reliability; deeply nested JSON ASTs hurt.** A function-calling study (CallNavi, arXiv 2501.05255) found "JSON Outperforms YAML" across syntax, structure, and task accuracy for both input and output, with YAML→YAML the worst configuration. BPMN Assistant (arXiv 2509.24592, 2025) found JSON process models scored 0.72 similarity vs 0.70 for native XML but "demonstrated greater reliability, with fewer total failures." Practitioner guidance converges on keeping JSON nesting to 2–3 levels because "deeply nested schemas increase error rates and slow down schema compilation."

3. **Constrained decoding/structured outputs guarantee shape, not correctness.** Per OpenAI ("Introducing Structured Outputs in the API"), "with Structured Outputs, gpt-4o-2024-08-06 achieves 100% reliability in our evals, perfectly matching the output schemas," versus roughly 35.9% reliability via prompt engineering alone. But ExtractBench (arXiv 2602.12247, Table 8) found structured-output mode can *reduce* accuracy and validity: GPT-5's credit-agreement pass rate is 70.0% in structured mode, overall structured-mode validity fell from 51% (107/210) to 37% (77/210) versus prompt-based extraction, and the resume schema was "rejected outright by all providers in structured mode (0/42)" despite 62% prompt-mode validity — because grammar-state maintenance competes with content attention. Multiple sources document the "schema-compliant but semantically wrong" failure mode (valid JSON, wrong answer), and failures also shift to refusals rather than disappearing.

4. **Repair-loop convergence: most gains in the first 1–3 round-trips; rich feedback beats binary pass/fail.** Across code-repair studies, "most gains occur in the first two rounds … diminishing returns after the third iteration." TraceCoder (arXiv 2602.06875) shows binary pass/fail feedback causes "Performance Degradation" and "Fixation & Stagnation" loops, arguing for runtime/trace-level diagnostics over execution-result-only signals. FeedbackEval (arXiv 2504.06939) studies six feedback types (structured tool signals, NL suggestions, composite) and finds structured diagnostics materially improve repair.

5. **Procedural-memory / self-improvement systems give a proven loop architecture.** Voyager (arXiv 2305.16291) stores skills as *executable code* (not NL), retrieved by embedding similarity but executed deterministically, with an iterative prompt loop incorporating "environment feedback, execution errors, and self-verification." ACE (Agentic Context Engineering, arXiv 2510.04618, Stanford/SambaNova/Berkeley) maintains an "evolving playbook" of itemized bullets with `helpful`/`harmful` counters, updated by a Generator→Reflector→Curator loop with incremental "delta" updates to avoid "context collapse," yielding +10.6% on agents and +8.6% on finance; it learns from "natural execution feedback" without labels. Reflexion (NeurIPS 2023, arXiv 2303.11366) shows verbal self-reflection stored in episodic memory beats refinement-only by 8% absolute. SoK: Agentic Skills (arXiv 2602.20867) catalogs the governance risks: code injection, skill drift, poisoned distillation.

6. **ILP revived with LLMs is real and points to "generate-then-verify."** Gandarela et al. (AAAI 2025, arXiv 2408.16779) have LLMs generate Prolog theories scored by a formal interpreter with precision/recall/F1 feedback, finding "the largest LLMs can achieve competitive results against a SOTA ILP system baseline" but that "tracking long predicate relationship chains is a more difficult obstacle than theory complexity for LLMs." ILP-CoT (arXiv 2509.21874) induces intermediate Prolog-form rules then translates to NL "while preserving logical fidelity." ReaComp (arXiv 2605.05485) compiles LLM reasoning traces into reusable symbolic solvers requiring no test-time LLM calls (91.3% on PBEBench-Lite). The recurring lesson: **LLM-direct rule text is noise-sensitive; pairing generation with a deterministic verifier is what makes it reliable** — exactly Symbolica's value proposition.

7. **Safety/governance for machine-authored policy is an emerging discipline.** Microsoft's Agent Governance Toolkit (github.com/microsoft/agent-governance-toolkit) states verbatim: "Prompt-level safety ('please follow the rules') is not a control surface. It is a polite request to a stochastic system. OWASP LLM01:2025 states this explicitly: 'it is unclear if there are fool-proof methods of prevention for prompt injection,'" and Microsoft's red-team testing quantifies prompt-based safety at roughly a 26.67% policy-violation rate. The OWASP Top 10 for Agentic Applications (released Dec 9, 2025, genai.owasp.org, >100 contributing experts) ranks "ASI01 – Agent Goal Hijack" as the #1 risk (citing the real-world EchoLeak example) and emphasizes minimizing agent capability. The prescribed pattern: emit/action allowlists, capability scoping, human approval gates, tamper-evident audit, and provenance (who/what authored a rule, from what evidence).

### §C — Hybrid neuro-symbolic patterns (the differentiator)

8. **Production guardrails are mostly probabilistic, and that's a documented weakness Symbolica can exploit.** NeMo Guardrails (EMNLP 2023 demo, arXiv 2310.10501) uses Colang flows; its dialog rails are "inherently probabilistic" — generating a canonical-form intent then vector-matching against rules. A Lean-4 deterministic-guardrails paper (arXiv 2604.01483) critiques both NeMo and Guardrails AI as "fundamentally misaligned with the deterministic requirements of financial regulation." This validates Symbolica's deterministic-skeleton/probabilistic-leaf identity.

9. **Determinism contracts for LLM calls: what practitioners actually ship.** Temperature 0 is *not* a determinism guarantee ("Change anything — model version, hidden defaults, even whitespace … you can still get different outputs at temperature 0"); seeds make randomness replayable only with identical inputs/implementation. Deterministic record/replay is becoming a first-class agent primitive: "During replay, LLM and tool calls are fetched exclusively from the trace. No external nondeterminism can leak in," with event-type isolation, input-consistency validation, and metadata/version verification. Self-consistency (majority vote over K samples) improves reliability; adaptive variants are highly cost-efficient — Early-Stopping Self-Consistency (Li et al., "Escape Sky-high Cost," arXiv 2401.10480, ICLR 2024) reduces chain-of-thought sampling on GSM8K by −80.1% (also −84.2% on Coin Flip, −78.5% on CommonsenseQA) "while attaining comparable performances." These map directly to Symbolica's needs: cache keyed on (prompt, model, temperature), record/replay for tests/audits, retry-and-vote, and confidence thresholds with symbolic fallback.

10. **Policy-as-code for agents is the adjacent winning pattern.** OPA is being positioned as "the missing guardrail for AI agents" — enforcing tool/parameter allowlists *between* agent and tools so "even if the agent is tricked … OPA blocks it before it reaches the target system," with audit trails that can be "replayed for analysis or debugging." "Tool eligibility" is described as "a deterministic product contract that defines which tools are available … before the model acts." This is the action-allowlist model Symbolica should adopt for generated rules' side effects.

### §B — Expression & DSL design

11. **Missing-data semantics is the highest-leverage decision, and the field is genuinely split.** CEL (Google) treats a missing map/JSON key as an **error** ("Since there's not a safe default value for a missing key, CEL defaults to error"), propagating it except through `&&`/`||` short-circuiting and the `has()` macro — but the error itself terminates evaluation, with no in-language catch. FEEL (DMN/OMG) uses **null-friendly three-valued logic** (true/false/null). Rego (OPA) uses **undefined-propagation**: a reference to a non-existent field makes the expression undefined and the rule simply doesn't fire (distinct from false), with `default` for fallback. SQL uses NULL/3VL. For rules over often-incomplete LLM-extracted facts, **CEL's error-on-missing is the safest against silent-wrong-answers** and aligns with Symbolica's "missing fact is a structured error" position — but it must be a *catchable, localizable* error the agent can act on, not a hard abort.

12. **CEL is the design north star for embedded, safe, fast expressions.** "Non-Turing complete … evaluates in linear time, is mutation free … orders of magnitude faster than equivalently sandboxed JavaScript," with `cel.Program` "stateless, thread-safe, and cachable," AST source positions for error localization, and optional gradual type-checking. GoRules ZEN compiles its expression language to bytecode and sandboxes JS Function nodes in QuickJS isolates with a 50ms timeout. Both validate Symbolica's whitelisted-AST/no-`eval`/resource-limit approach.

### §A — Execution semantics of mature engines

13. **Salience/priority survived; recency/specificity/LEX-MEA are largely seen as footguns for maintainability.** Drools uses salience + LIFO and explicitly advises "it is a good idea not to count on rules firing in any particular order." CLIPS offers recency (default), LEX, MEA, complexity, etc., but practitioner literature documents salience-driven looping and "strange behavior." OPS5's refraction ("the same instantiation is never executed more than once") is the ancestor of fire-once semantics. **Highest-priority-wins for verdict conflicts (Symbolica's position) is the survivor; the classic recency/specificity stack is a maintainability hazard for machine authors** who can't reason about implicit ordering. (Forgy/OPS5/CLIPS sources are pre-LLM-era classics.)

14. **Lightweight embedded engines abandon Rete and truth maintenance.** GoRules ZEN, json-rules-engine, and similar evaluate graph/table structures once per request rather than maintaining stateful Rete networks. Oracle's own docs note "many business rules use cases do not fit this usage profile and thus do not benefit from … Rete while incurring the overhead." This **confirms** Symbolica's run-to-fixpoint-once / fire-at-most-once design for small rulesets.

### §D/§F — Explainability, verification & governance

15. **Decision-table verification is mature and directly reusable as agent diagnostics.** Calvanese et al. (BPM 2016, arXiv 1603.07466) give formal semantics and "scalable algorithms" for detecting overlapping rules and missing rules via geometric interpretation of decision tables. DMN hit policies (Unique/Any/Priority/First) plus completeness indicators formalize conflict and gap detection; tools (Trisotech, Sparx EA, Camunda) ship overlap/gap/subsumption checks. **These analyses become machine-actionable diagnostics** an LLM author consumes — "rules 4 & 5 overlap on Credit Score <610 vs [600..625]" is exactly the localized, fix-suggestive feedback that cuts repair round-trips.

### §G/§E — Performance & temporal

16. **Rete pays off only with large rulesets and high fact-churn.** Rete (Forgy 1982, pre-LLM classic) trades memory for speed by caching partial matches, exploiting "temporal redundancy" (few facts change per cycle) and "structural similarity." For sub-millisecond evaluation of ~10–1,000 rules evaluated once per agent turn, compile-to-closures/bytecode (CEL/ZEN style) is the right choice. A credible "sub-millisecond p50" claim must specify ruleset size, fact count, expression complexity, warm vs cold, and exclude LLM-call latency. For temporal primitives, CEP windowing (sliding/tumbling, watermarks for late events) is the reference vocabulary; an embedded non-distributed engine needs only the minimal subset (windowed aggregates over a local time-series store), and `sustained(condition, duration)` should be defined as *continuous coverage of the window* rather than v1's arbitrary 80%-coverage heuristic.

### §H — Ecosystem

17. **Drools-class engines were displaced by embedding friction and DSL learnability; lightweight engines won on zero-ceremony embedding, schema-first formats, and a clear governance story.** OPA/CEL/ZEN/json-rules-engine win their niches by being embeddable, fast, and JSON/schema-centric. The 2024–2026 "rules/policy for agents" space (OPA-for-agents, Cedar, tool-eligibility layers, NeMo/Guardrails AI) is crowded on *gating agent actions* but empty on *agent-authored, LLM-in-the-loop, trace-explainable rulesets*.

---

## Comparative Tables

### Table A — Conflict resolution & refire semantics (§A)

| Engine | Era | Conflict resolution | Refire semantics | Verdict for Symbolica |
|---|---|---|---|---|
| OPS5 | pre-LLM (1979) | Recency → specificity (LEX/MEA); refraction | Refraction: instantiation fires once | Refraction = ancestor of fire-once |
| CLIPS | pre-LLM | Salience + strategy (recency default; LEX, MEA, complexity, simplicity, breadth, random) | Refraction; reactivates on new facts | Too many implicit strategies for machine authors |
| Jess | pre-LLM | Salience + depth/breadth | Rete-based reactivation | Same |
| Drools (Phreak) | modern | Salience + LIFO; advises not relying on order | Reactivates on working-memory change (TMS) | Highest-priority-wins survives; TMS overkill for embedded |
| GoRules ZEN | modern | Table hit policy / graph order | Evaluate once per request | Matches run-once embedded model |
| json-rules-engine | modern | Priority field; event order | Evaluate once | Matches fire-once |
| **Symbolica v2** | LLM-era | **Highest-rule-priority-wins** | **Fire at most once/run, fixpoint** | Confirmed by lightweight-engine consensus |

### Table B — Expression marking, type/missing-data, sandboxing (§B)

| Lang | Expr vs literal | Type system | Missing-data semantics | Sandboxing / termination |
|---|---|---|---|---|
| **CEL** (Google) | All input is expression; data via typed context | Gradual typing; dynamic+optional static check | **Error** on missing map/JSON key; propagates except `&&`/`||`/`has()` | Non-Turing-complete, linear-time, mutation-free; AST cacheable |
| **Rego** (OPA) | Rules/expressions over JSON `input`/`data` | Dynamic | **Undefined**-propagation (≠ false); rule doesn't fire; `default` fallback | Datalog-derived; query-optimized; bounded |
| **FEEL** (DMN) | Boxed expressions / cells | Typed (DMN datatypes) | **Null** + three-valued logic (true/false/null) | Spec-defined; no general I/O |
| **Starlark** | Python-like config language | Dynamic (Python subset) | KeyError-style errors | No I/O, deterministic, no recursion, bounded |
| **JsonLogic** | Nested JSON AST (`{"op":[args]}`) | JS-coercion | Returns null/false-ish; permissive | Tiny, no I/O; but verbose for authors |
| **GoRules JDM/ZEN** | ZEN expression strings in JSON cells | Dynamic, date/list aware | Errors halt the graph | Bytecode VM; JS Function nodes in QuickJS, 50ms timeout |
| **Symbolica v2** | **`"= expr"` sigil; unmarked = literal** | Typed coercion (str/int/float/bool) | **Structured, catchable, localized error** | Whitelisted AST, no `eval`, resource limits, compile-time validation |

---

## Design Recommendations for Symbolica v2

**R1 — Canonical rule format: JSON-first envelope with embedded marked expression strings. (Confidence: HIGH. CONFIRMS the `"= expr"` sigil position; CONTRADICTS YAML-as-carrier.)**
Use a flat, shallow (≤2–3 nesting levels) JSON object per rule: `id`, `priority`, `after`, `if` (condition tree), `then` (typed emits), `metadata` (provenance). JSON validates more reliably than YAML for LLM emission (CallNavi: "JSON Outperforms YAML"); YAML's Norway problem and indentation sensitivity create silent-wrong-structure bugs. Keep a YAML *human-review projection* if desired, but the canonical authored/stored artifact the agent emits and repairs should be JSON validated against a published JSON Schema (the GoRules `llms.txt` + Zod-schema generate-then-validate pattern is the model). Ship an `llms.txt`-style machine doc.

**R2 — Expression encoding: in-string Python-like marked expressions, NOT JsonLogic/full-AST, NOT structured expression objects. (Confidence: MEDIUM-HIGH. CONFIRMS sigil position; CONTRADICTS any full-AST encoding.)**
The literature gap is real (no single head-to-head benchmark of expression-string vs JsonLogic-AST error rates exists), but every proxy points the same way: LLMs emit executable, familiar-syntax code far more reliably than verbose nested encodings (Hypothesis Search 30% vs 17%), deeply nested JSON raises error rates, and ILP chains hurt "more than theory complexity." A short `"= account.balance >= txn.amount"` string aligns with Python-trained priors; a JsonLogic `{">=":[{"var":"account.balance"},{"var":"txn.amount"}]}` multiplies tokens and nesting depth. Parse the marked string with your whitelisted AST (CEL/Starlark-class) at compile time. The sigil cleanly separates expression from literal — keep it.

**R3 — Missing-data: structured, catchable, localizable error (CEL-style), not null-propagation. (Confidence: HIGH. CONFIRMS the v2 position, with one refinement.)**
CEL's error-on-missing is the safest choice against silent-wrong-answers over incomplete LLM-extracted facts, and contrasts favorably with Rego's undefined silent-non-firing and FEEL/SQL 3VL (which propagate ambiguity). **Refinement:** the error must be a first-class result object with the missing field's JSON-path and the rule id — not a hard abort. Provide an explicit `has(field)`/`default(field, x)` macro so authors can opt into tolerance deliberately. This makes "missing fact" a repairable diagnostic, not a crash.

**R4 — Verdict conflict resolution: keep highest-priority-wins; reject recency/specificity. (Confidence: HIGH. CONFIRMS the v2 position.)**
Salience/priority is the only conflict strategy that survived into modern practice; recency/specificity/LEX-MEA are documented footguns even for human authors and are far worse for machine authors who cannot reason about implicit firing order. Make priority explicit and require it; surface ties as a *validation diagnostic* (overlapping same-priority rules with conflicting emits = error), reusing DMN overlap-detection algorithms.

**R5 — Rule chaining via `after: [rule_ids]`, fire-once, run-to-fixpoint; no Rete, no TMS. (Confidence: HIGH. CONFIRMS the v2 positions.)**
Lightweight embedded engines (ZEN, json-rules-engine) and Oracle's own guidance confirm Rete and truth-maintenance are net-negative for small, evaluate-once rulesets in agent loops. DAG-ordered single-pass forward chaining is correct. Keep `after` explicit gating — it doubles as a machine-readable dependency graph the harness can analyze for cycles/unreachability.

**R6 — Determinism contracts for `PROMPT()`: cache + record/replay + optional vote + confidence-gated symbolic fallback. (Confidence: HIGH. Strengthens v1 identity.)**
Cache keyed on (prompt, model, temperature, schema). Ship deterministic record/replay (LLM leaves fetched exclusively from the trace during replay, with model/version metadata verification) as the substrate for tests and audits. Offer retry-and-vote (self-consistency) with adaptive early-stopping (ESC-style) for high-stakes leaves, and a confidence threshold below which the rule takes a declared symbolic fallback branch. Always type-coerce `PROMPT()` returns via constrained decoding / function-calling **but** treat schema-validity as necessary-not-sufficient: validate semantic plausibility (range/enum/cross-field checks) because "schema-compliant but wrong" is the dominant failure (ExtractBench).

**R7 — Cost/latency: lazy short-circuit ordering so cheap symbolic predicates gate expensive `PROMPT()` leaves; per-evaluation budget ceilings; batch parallel prompts. (Confidence: HIGH.)**
Evaluate symbolic predicates first and short-circuit (`&&`/`||`) before any LLM leaf, mirroring CEL's commutative-operator design. Enforce a per-evaluation cost/latency ceiling that, when exceeded, returns a structured budget-exceeded result rather than blocking.

**R8 — Diagnostic format for repair loops: structured, coded, JSON-path-localized, fix-suggestive, with near-miss/counterfactual data. (Confidence: HIGH. New capability mandated by §I.)**
Every validation/execution failure returns: a stable `error_code`, a JSON-path to the offending node, a human+machine message, and where possible a suggested fix. For *behavioral* failures in simulation, return near-miss "why-not" data: which condition failed and the counterfactual value that would have flipped it (DMN-style). Evidence shows rich runtime/trace feedback prevents the "fixation/stagnation" loops that binary pass/fail causes (TraceCoder), and that most repair gains land in 1–3 round-trips — so front-load diagnostic richness.

**R9 — Harness loop architecture: propose → validate → simulate → promote → monitor, with provenance and allowlists. (Confidence: HIGH. New capability mandated by §I.)**
- **Propose:** agent emits JSON rule(s) constrained by an emit/action **allowlist** (capability scoping for generated rules).
- **Validate:** compile-time AST/schema/type checks + static ruleset analysis (overlap, gaps, unreachable rules, cycles in `after`) → structured diagnostics (R8).
- **Simulate:** shadow-run against recorded cases; verdict-diff vs current ruleset; compute per-rule precision/recall.
- **Promote:** canary/champion-challenger rollout; human approval gate for high-capability actions; record provenance (who/what authored the rule, from which evidence/cases).
- **Monitor:** per-rule telemetry; auto-flag/retire underperforming rules.
This mirrors ACE's Generator→Reflector→Curator with incremental updates and Voyager's verify-before-commit, adapted to a deterministic engine. Store rules with ACE-style `helpful`/`harmful`-equivalent telemetry counters.

**R10 — Safety: prompt-level instructions are not a control surface; enforce deterministically. (Confidence: HIGH. New, mandated by §I.)**
Generated rules' side effects must pass through a deterministic allowlist/capability check at execution time (the OPA "tool eligibility" pattern), not rely on the authoring agent's good behavior — Microsoft's toolkit documents prompt-only safety leaving a ~26.67% policy-violation rate, and OWASP ranks Agent Goal Hijack as the #1 agentic risk. Maintain tamper-evident audit + provenance for every rule version. This is both a safety control and a regulatory-readiness feature.

---

## Open Debates

- **Error vs undefined vs null on missing data.** CEL (error), Rego (undefined/silent-non-fire), FEEL/SQL (null/3VL) genuinely disagree. We recommend catchable-error, but a minority view holds that for *exploratory* agent rules, Rego-style undefined-non-fire reduces brittleness. Resolve empirically via the simulation harness.
- **Does constrained decoding help or hurt?** Guarantees shape and eliminates parse failures (OpenAI 100% schema adherence), but ExtractBench shows it can degrade accuracy on long/complex schemas (GPT-5 86.9%→70.0%) and shift failures to refusals. Live debate; likely schema-complexity-dependent.
- **How much should rules be "code" vs "data"?** Voyager/CodeAct argue executable code is the most reliable, testable, composable representation; the policy-engine tradition argues for declarative data. Symbolica's marked-expression-in-JSON is a deliberate middle path; whether to allow richer code-like skills is unresolved.
- **Self-consistency cost vs benefit for rule leaves.** Voting improves reliability but multiplies cost/latency; some studies show no improvement or slight degradation at T=0. Make it opt-in per leaf.

---

## Annotated Bibliography (strongest sources)

1. **Grammar Prompting for DSL Generation** (Wang et al., NeurIPS 2023, arXiv 2305.19234) — Why LLMs struggle with bespoke DSL syntax; grammar scaffolding helps only for rare DSLs.
2. **Hypothesis Search** (Wang et al., ICLR 2024, arXiv 2309.05660) — Concrete Python programs beat abstract/direct prompting (30% vs 17%) on inductive reasoning.
3. **DSL Code Generation: Fine-Tuning vs RAG** (Bassamzadeh & Methani, Microsoft, arXiv 2407.02742) — Even optimized DSL generation "got the syntax wrong many times."
4. **CallNavi** (arXiv 2501.05255) — Direct evidence "JSON Outperforms YAML" for LLM emission across syntax/structure/task.
5. **ACE: Agentic Context Engineering** (Zhang et al., arXiv 2510.04618) — Evolving-playbook loop (Generator/Reflector/Curator), incremental updates, helpful/harmful counters, learns from execution feedback; +10.6%/+8.6%.
6. **Voyager** (Wang et al., arXiv 2305.16291) — Skills as executable code, verify-before-commit, iterative error-driven prompting; the canonical skill-library pattern.
7. **Reflexion** (Shinn et al., NeurIPS 2023, arXiv 2303.11366) — Verbal self-reflection in episodic memory; +8% over refinement-only; feedback-signal design.
8. **TraceCoder** (arXiv 2602.06875) — Binary pass/fail causes degradation/stagnation; runtime traces enable convergence.
9. **FeedbackEval** (arXiv 2504.06939) — Benchmarks six feedback types; structured diagnostics improve repair.
10. **Inductive Learning of Logical Theories with LLMs** (Gandarela et al., AAAI 2025, arXiv 2408.16779) — LLMs generate Prolog theories verified by interpreter; chain-length hurts more than complexity.
11. **ILP-CoT** (arXiv 2509.21874) — Intermediate Prolog-form rules preserve logical fidelity over direct NL.
12. **ReaComp** (arXiv 2605.05485) — Compiling LLM reasoning into reusable symbolic solvers (no test-time LLM calls); 91.3% PBEBench-Lite.
13. **CEL specification & cel-go** (google/cel-spec, cel.dev) — Error-on-missing semantics, non-Turing-complete linear-time evaluation, cacheable AST; the embedded-expression north star.
14. **OPA/Rego Policy Language** (openpolicyagent.org) — Undefined-propagation, `default` fallback, conflict-as-error; policy-as-code reference.
15. **Drools DMN FEEL handbook** (kiegroup.github.io) — Three-valued logic / null semantics for missing data.
16. **GoRules JDM / ZEN docs** (docs.gorules.io) — JSON decision model, bytecode expression VM, QuickJS sandbox, `llms.txt`, generate-then-validate schema.
17. **Semantics and Analysis of DMN Decision Tables** (Calvanese et al., BPM 2016, arXiv 1603.07466) — Scalable overlap/missing-rule detection; reusable as agent diagnostics.
18. **Camunda DMN hit policy guidance** (docs.camunda.io) — Unique/Any/Priority/First; completeness; deterministic-vs-LLM split.
19. **NeMo Guardrails** (EMNLP 2023 demo, arXiv 2310.10501) — Colang flows; probabilistic dialog rails (the weakness Symbolica avoids).
20. **Type-Checked Compliance / deterministic guardrails** (arXiv 2604.01483) — Critique of probabilistic guardrails for regulated determinism.
21. **OpenAI Structured Outputs / constrained decoding** (OpenAI docs) — gpt-4o-2024-08-06 "100% reliability in our evals" vs ~35.9% prompt-only; shape ≠ correctness.
22. **ExtractBench** (arXiv 2602.12247) — Structured-output mode can reduce accuracy (GPT-5 86.9%→70.0%; overall validity 51%→37%); failures shift to refusals.
23. **Microsoft Agent Governance Toolkit** (github.com/microsoft/agent-governance-toolkit) — "Prompt-level safety is not a control surface"; ~26.67% prompt-only violation rate; deterministic enforcement.
24. **OWASP Top 10 for Agentic Applications** (genai.owasp.org, Dec 9 2025) — ASI01 Agent Goal Hijack as #1 risk; minimize capability.
25. **Early-Stopping Self-Consistency** (Li et al., "Escape Sky-high Cost," arXiv 2401.10480, ICLR 2024) — −80.1% sampling cost on GSM8K at comparable accuracy.
26. **OPA for AI agents / tool eligibility** (codilime.com; chenyezhu.com) — Deterministic action allowlists between agent and tools.
27. **Rete algorithm** (Forgy 1982; Oracle rules-engine-algorithms docs) — When Rete pays off; why embedded engines skip it. (pre-LLM classic)
28. **SoK: Agentic Skills** (arXiv 2602.20867) — Taxonomy of skill representations and governance risks (skill drift, poisoned distillation).
29. **Deterministic replay for agents** (sakurasky.com) — Record/replay primitive design (event isolation, metadata verification).
30. **LLM determinism in production** (practitioner) — Temperature 0 ≠ determinism; seeds/replay needed.