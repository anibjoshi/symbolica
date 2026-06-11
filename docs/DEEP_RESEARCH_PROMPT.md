# Deep Research Prompt — Designing a World-Class Hybrid (Neuro-Symbolic) Rule Engine

## Context

We are rebuilding **Symbolica**, an open-source, Python-embedded rule engine for AI
agents, from scratch (v2). It is a *hybrid* engine: a deterministic, explainable symbolic
core that can invoke LLM judgments at designated points inside rules. The v1 innovations
we intend to preserve and strengthen — treat these as the product's identity, not
negotiable features:

1. **LLM-in-the-loop rules**: a `PROMPT()` function callable inside declarative rule
   conditions and actions, with typed return coercion (str/int/float/bool), prompt-injection
   hardening, and cost/latency accounting — a deterministic rule skeleton with
   probabilistic leaves.
2. **Explainability as a first-class output**: every execution yields machine-readable
   reasoning traces (which rules fired, why, with which field values and intermediate
   steps) designed to be fed back to an LLM agent as context for its next decision.
3. **Declarative YAML rule DSL** with safe, sandboxed, Python-like expressions
   (whitelisted-AST evaluation, no `eval`, resource limits) and nested `all/any/not`
   condition trees.
4. **Temporal reasoning primitives**: time-series fact storage with windowed aggregates
   (`recent_avg`, `sustained_above`), and TTL facts.
5. **Forward chaining** to a fixpoint with dependency-aware (DAG) ordering and explicit
   rule-to-rule gating; goal-directed (backward) querying as a planned layer.

Target profile: embedded Python library (not a server), rulesets of ~10–1,000 rules
inside agent loops, sub-millisecond p50 for pure-symbolic evaluation, zero-dependency
core, LLM calls only where rules explicitly request them.

**Critical framing — rules are authored by agents, not humans.** Symbolica v2 is the
substrate for an *agentic harness*: an LLM agent writes, tests, repairs, and retires the
rules; the engine provides deterministic execution, structured validation diagnostics,
simulation against recorded cases, and execution traces as the feedback signal. Humans
review and govern; they do not hand-write rules. Evaluate every design question below
through this lens — "easy for an LLM to emit and repair reliably" outranks "pleasant for
a human to read."

Our current v2 design positions (challenge these where industry evidence disagrees):
expressions are syntactically marked (`"= expr"` sigil; everything unmarked is a
literal); verdict conflicts resolved by highest-rule-priority-wins; referencing a missing
fact is a structured *error* on the result (not null-propagation); rule chaining is gated
via `after: [rule_ids]` on the dependent rule; pass-based forward chaining, each rule
fires at most once per run; all parsing/security validation at compile time; the engine
is immutable after build.

## Research Mission

Survey how the industry and academia build, specify, and operate rule/decision engines —
classical, modern-cloud, and LLM-hybrid — and distill concrete, cited design
recommendations for Symbolica v2. We want to steal the best ideas and avoid the known
failure modes, not reinvent either.

## Research Questions

### ⭐ I. Agent-authored rules & the agentic harness (top priority, 2023–2026)
- **Rule induction by LLMs**: what is the state of the art in having LLMs distill
  experience/demonstrations/feedback into symbolic rules or programs — code-as-policies,
  Voyager-style skill libraries, DSPy program synthesis, Reflexion-style self-critique,
  agent procedural-memory systems (Letta/MemGPT lineage, ACE), and classical Inductive
  Logic Programming revived with LLMs? What representations do LLMs author *reliably*
  (JSON vs DSL strings vs code), and what error rates are reported?
- **Validate-repair loops**: best practices for machine-actionable diagnostics that an
  LLM can act on (structure, error codes, fix suggestions, JSON-path localization);
  evidence on repair-loop convergence (how many round-trips, what diagnostic features
  cut them); structured outputs / constrained decoding against a JSON Schema as a
  validity guarantee — limits and failure modes.
- **Expression authoring reliability**: for embedded expressions specifically, is there
  evidence on whether LLMs emit fewer errors with in-string marked expressions
  (`"= a * b"`), structured expression objects (`{"expr": "a * b"}`), or full AST/JSON
  encodings (JsonLogic-style)? This directly decides our DSL surface.
- **Automated ruleset governance**: systems where machine-authored policies are
  auto-tested before promotion — shadow/simulation runs over recorded cases, verdict
  diffing, per-rule precision/recall telemetry, automatic retirement of underperforming
  rules, canary rollout of rule changes. Who has built this (industry or research), and
  what loop architecture (propose → validate → simulate → promote → monitor) do they use?
- **Feedback-signal design**: what trace/explanation formats demonstrably help an LLM
  *repair* a rule (near-miss "why not" data, counterfactual values, minimal failing
  cases)? Any published evals on machine-readable explanations as agent feedback?
- **Safety & oversight for machine-authored policy**: containment patterns (emit/action
  allowlists, capability scoping for generated rules), human approval gates, audit and
  provenance requirements (who/what authored a rule, from what evidence) — including any
  regulatory perspective on machine-authored decision logic.

### A. Execution semantics of mature engines
- How do Drools (Rete/Phreak), CLIPS, Jess, and the OPS5 lineage define **agenda and
  conflict resolution** (salience, recency, specificity, refraction)? Which strategies
  survived in practice and which are regarded as footguns?
- How do they handle **truth maintenance and retraction** (facts invalidated after rules
  fired on them)? Is a truth-maintenance system worth it for small rulesets in agent
  loops, or is run-to-fixpoint-once the industry norm for embedded engines?
- "Fire at most once per run" vs re-activation semantics: what do modern lightweight
  engines (GoRules/Zen, json-rules-engine, Grule, Experta/durable_rules) choose, and why?

### B. Expression & DSL design
- Compare **CEL (Google), Rego (OPA), FEEL (DMN), Starlark, JsonLogic, GoRules JDM**:
  how does each distinguish expressions from literals/data, what type system and coercion
  rules do they use, and how do they sandbox (resource limits, no I/O, termination
  guarantees)?
- **Missing-data semantics** is a key open decision: contrast CEL's error-value
  propagation, FEEL's null-friendly three-valued logic, Rego's undefined-propagation, and
  SQL-style NULL. What does each choice do to rule-author ergonomics and to silent-wrong-
  answer risk? Which approach fits "rules over LLM-extracted, often-incomplete facts"?
- Determinism guarantees: how do CEL/Rego specify evaluation determinism, and how do they
  document/enforce function purity for user-registered functions?
- YAML as a rule carrier: known pitfalls (typing surprises, the Norway problem,
  anchors/merge abuse) and how schema-first engines (JDM, Camunda DMN XML/JSON) mitigate
  format-induced bugs.

### C. Hybrid neuro-symbolic patterns (the differentiator — go deep, prioritize 2023–2026)
- How do production systems combine LLM judgments with deterministic logic today:
  guardrails engines (NVIDIA NeMo Guardrails/Colang, Guardrails AI), LLM-as-judge
  pipelines, semantic routers, policy engines gating agent actions (OPA-for-agents
  patterns, Anthropic/OpenAI tool-permission patterns), constrained decoding / structured
  outputs as a determinism tool?
- **Determinism contracts for LLM calls inside rules**: caching keyed on
  (prompt, model, temperature), record/replay for audits and tests, seed parameters,
  retry-and-vote (self-consistency), confidence thresholds with symbolic fallbacks. What
  do practitioners actually ship? What are documented failure modes of bool/number
  coercion of LLM outputs, and the state of the art for typed extraction (function
  calling, JSON schema, logit bias)?
- Cost/latency control patterns: budget ceilings per evaluation, lazy evaluation order so
  cheap symbolic predicates short-circuit before LLM predicates, batch/parallel prompt
  evaluation.
- Academic neuro-symbolic work worth mining for an engine like ours: scallop, DSPy
  assertions, LLM+ASP/Prolog hybrids, neuro-symbolic agent papers — only where they yield
  implementable engine design ideas, not as a general literature review.

### D. Explainability & decision auditing
- What do DMN's decision requirements graphs, credit-decisioning systems (FICO, Experian),
  and regulated-industry audit logs teach about **trace formats**? Is there any emerging
  standard for machine-readable decision traces that LLM agents consume well?
- "Why" AND "why not" explanations: how do engines expose near-miss analysis (which
  condition failed, what value would have flipped it)? Any evidence on what trace shape
  most improves downstream LLM decision quality?

### E. Temporal & streaming reasoning
- Windowing semantics from CEP engines (Drools Fusion, Esper, Flink CEP, Siddhi): sliding
  vs tumbling windows, out-of-order/late events, watermark concepts — what minimal subset
  matters for an embedded, non-distributed engine? How do they define `sustained(condition,
  duration)` correctly (v1 used an arbitrary 80%-coverage heuristic)?

### F. Verification, testing & governance of rulesets
- Static analysis of rulesets in industry: conflict/overlap/shadowing/unreachable-rule
  detection, completeness checking (DMN hit policies, decision-table analysis), SMT-based
  verification of rule properties. What's practical at 10–1,000 rules?
- How do organizations test rule changes: golden/conformance suites, property-based
  testing over fact spaces, shadow execution / champion-challenger, ruleset versioning
  and rollback. What does CI for rules look like?

### G. Performance & credible benchmarking
- How are rule engines legitimately benchmarked (OPS5 manners/waltz lineage, OPA/CEL
  benchmark suites)? What should a credible "sub-millisecond" claim specify?
- Compilation strategies for our scale: compiling rules to closures/bytecode vs tree
  interpretation vs Rete-style incremental matching — at what ruleset size and fact-churn
  rate does Rete pay off? (We need evidence to justify *not* building Rete.)

### H. Product & ecosystem lessons
- Why did Drools-class engines get displaced in modern stacks, and what made
  lightweight engines (OPA, CEL, Zen/GoRules, json-rules-engine) win their niches —
  embedding model, DSL learnability, governance story?
- For an AI-agent-focused engine specifically: who else is building "rules/policy for
  agents" right now (2024–2026), what do their APIs look like, and where is the white
  space Symbolica's innovations (LLM-in-rules + agent-consumable traces + **agent-authored
  rulesets**) can own?

## Deliverable

1. **Comparative tables** for §A (conflict resolution & refire semantics across ≥6
   engines) and §B (expression marking, type/missing-data semantics, sandboxing across
   CEL/Rego/FEEL/Starlark/JsonLogic/JDM).
2. **Findings per research question** with inline citations to primary sources (official
   docs, specs, source code, papers, conference talks). Mark pre-LLM-era sources as such.
3. **Design recommendations for Symbolica v2**, each: the recommendation, the evidence,
   confidence (high/medium/low), and — critically — whether it **confirms or contradicts**
   one of our stated v2 positions (listed in Context). Contradictions are the most
   valuable output; do not soften them.
4. **Open debates** where industry consensus doesn't exist, with the live positions.
5. **Annotated bibliography** (≤30 strongest sources, one-line "why it matters" each).

Prioritize §I, then §C and §B, over the rest if depth must be traded. For §I
specifically, recommendations should address: the canonical rule format for LLM authors
(JSON-first vs DSL), the expression-encoding choice, the diagnostic format for repair
loops, and the harness loop architecture (propose → validate → simulate → promote →
monitor). Quality bar: primary sources
over blog summaries; verify claims against specs or source code where feasible; recency
matters for §C/H (2023–2026), while §A/G classics (Forgy's Rete paper, OPS5 literature)
are expected.
