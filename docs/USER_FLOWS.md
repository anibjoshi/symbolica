# Symbolica v2 — User Flows

*Companion to `PRD.md` (the source of truth for requirements). This document describes
how each persona onboards, works day-to-day, and troubleshoots. API names follow the
PRD; where a flow implies a requirement not yet in the PRD, it is marked **[gap]**.*

---

## 0. The map

Symbolica runs three loops at three speeds (PRD §1.1). Each persona lives in one:

```
 ┌─────────────────  DECIDE (µs, every agent turn)  ─────────────────┐
 │  Host app ──facts──▶ engine.reason() ──verdict+trace──▶ agent     │
 │       └── uncovered? agent decides, Recorder logs a Case          │
 └───────────────────────────────┬───────────────────────────────────┘
                                 │ cases, telemetry
 ┌─────────────────  DISTILL (minutes–hours, harness)  ──────────────┐
 │  Authoring agent: distill(cases) → validate ⇄ repair → simulate   │
 │  → candidate passes gate → promotion offered                      │
 └───────────────────────────────┬───────────────────────────────────┘
                                 │ promotion requests, audit events
 ┌─────────────────  GOVERN (days, by exception)  ───────────────────┐
 │  Human governor: review diff + simulation report + provenance,    │
 │  approve/reject; investigate incidents via decision_id replay     │
 └────────────────────────────────────────────────────────────────────┘
```

| Persona | Loop | Onboards by | Succeeds when |
|---|---|---|---|
| Host developer | Decide | embedding the engine (§1) | rules gate the agent reliably; integration <1 day |
| Authoring agent | Distill | receiving its contract (§2) | promotable ruleset in ≤3 repair round-trips |
| Human governor | Govern | configuring approval policy (§3) | reviews take minutes; audits answer "why" conclusively |
| Downstream agent | Decide | nothing (host wires it) (§4) | conditions correctly on verdicts + traces |

---

## 1. Host Developer

The only persona who writes integration code. Everything else flows from this setup.

### 1.1 Onboarding (target: under an hour to observation mode)

**Step 1 — install and run with zero rules.** A zero-rule engine is valid (FR-10.7):

```python
pip install symbolica

from symbolica import Engine, compile_ruleset, Recorder

engine = Engine(compile_ruleset({"format": 2, "rules": []}))
recorder = Recorder("cases.jsonl")
```

**Step 2 — wrap the agent's decision points (observation mode).** Identify where the
agent makes consequential decisions (approve/route/escalate/tool-call). At each:

```python
result = engine.reason(facts)
if result.covered:
    decision = result.verdict
else:
    decision = agent.decide(context)                  # fallback: agent judgment
    recorder.record(facts, decision, source="agent")  # this becomes training data
```

From this moment the deployment is accumulating cases. Nothing else is required on
day 0 — **onboarding is complete before any rule exists.**

**Step 3 — fact extraction.** `reason()` takes structured facts; producing them is the
host's job. Start with whatever structured data is already at hand (API responses,
order records). Once rules exist, `compiled.fact_schema()` (FR-10.8) lists exactly
which facts the ruleset reads — use it to drive an extractor (e.g., as the
structured-output schema for an extraction LLM call) and to catch drift between what
rules expect and what the host supplies.

**Step 4 — guardrails before the first promotion.** Configure the engine-enforced
capability boundary and (with the governor) the approval policy:

```python
engine = Engine(compiled,
                emit_allowlist={"route.*", "escalate", "refund.amount", "refund.approved"},
                telemetry=my_sink)        # coverage + per-rule counters
```

### 1.2 Day-to-day usage

- **Middleware placement** (primary mode, PRD §1.1): `reason()` runs *around* agent
  actions — the agent cannot skip it. Tool-style consultation (agent chooses to ask) is
  acceptable only for advisory rules, never for safety/policy gating.
- **Feed the trace forward**: append `result.trace.for_llm()` to the agent's context so
  it knows *why* — agents that see reasons produce better fallback decisions and better
  recorded cases.
- **Record outcomes when they arrive** (refund charged back, escalation resolved):
  `recorder.record(..., outcome=...)` — outcomes power per-rule precision in simulation
  and retirement decisions later.
- **Adopt new rulesets atomically**: promotion hands back a new immutable engine;
  swap the reference (`app.engine = new_engine`). No locks, no partial states; in-flight
  `reason()` calls finish on the old engine.

### 1.3 Troubleshooting (host developer)

| Symptom | First tool | Likely cause → fix |
|---|---|---|
| A rule never fires | `result.why_not("rule_id")` | Ranked failed conditions with actual values and the boundary value that would flip them. Typically a fact-name mismatch (check `fact_schema()` vs extractor output) or a threshold off by the reported margin |
| Wrong verdict | `result.trace` (standard level) | Shows which rule won the emit and which condition decided it. If two rules legitimately disagree → priority/emit-conflict issue; check load-time `EMIT_CONFLICT`/`SHADOWED_RULE` warnings you may have ignored |
| Verdict missing a key entirely | `result.fired` + `why_not` | No rule emitting that key fired — distinguish "near miss" (repairable threshold) from "no rule covers this" (needs distillation) |
| `MISSING_FACT` diagnostics dominate | `result.diagnostics` | Extractor and ruleset disagree on names/shape. The diagnostic's `suggestion` includes the closest matching fact name. Fix the extractor or have the authoring agent add `default()` |
| `converged == False` | trace, pass-by-pass | `set`-chain ping-ponging across passes; raise `max_passes` only after understanding the chain — usually a rule design smell to send back to distillation |
| Coverage stalls | telemetry + case store | Healthy: residual decisions are genuinely novel. Unhealthy: cases cluster (distiller failing on a pattern) — inspect `near_misses()` on uncovered cases |
| Latency regression | trace `duration_ms`, per-call records | Almost always an L1 `PROMPT()` leaf evaluating earlier than expected — check cost-ordering, cache hit rate in trace |
| "It worked yesterday" | `decision_id` + replay | Replay the run (LLM leaves served from trace cache), diff ruleset revisions — provenance says which promotion changed behavior |

---

## 2. Authoring Agent

A machine persona: "onboarding" means assembling its contract; "usage" is the
distill–repair cycle; "troubleshooting" is encoded repair strategy per diagnostic code.

### 2.1 Onboarding — the authoring contract

The loop layer assembles the authoring prompt from three package-shipped artifacts:

1. **The JSON Schema** (`format: 2`) — supplied as the structured-output schema, so
   emitted rulesets are syntactically valid by construction.
2. **The `llms.txt` authoring guide** (FR-5.6) — expression grammar, the `=` marker and
   `==` escape, builtins (`has`, `default`, …), reserved names, the diagnostic catalog,
   worked examples, and the house rules: shallow nesting, one decision per rule,
   `priority` always explicit, prefer `default()` over omitting conditions.
3. **The live context** — `fact_schema()` of facts actually available, the current
   ruleset (for amendments), the emit allowlist (don't author rules that will be
   blocked), and the case batch to distill.

### 2.2 Usage — the distill–repair–gate cycle

```
cases ─▶ DISTILL (propose candidate ruleset, JSON, schema-constrained)
            │
            ▼
        VALIDATE ──diagnostics──▶ REPAIR (≤3 round-trips, FR-14.3)
            │ clean                  │ each diagnostic: code + json_path + suggestion
            ▼                        ▼
        SIMULATE over held-out cases (FR-14.4)
            │ report: precision vs recorded decisions, coverage delta,
            │         verdict diffs vs current ruleset, per-rule stats
            ▼
        pass → promotion offered      fail → behavioral repair with why_not data
```

A behavioral repair turn looks like: *"Rule `refund_small` fired on case 17 where the
human declined (chargeback history). `why_not` on the declining path shows no rule
references `chargeback_count`. Amend or add a guard."* The simulation report — not
prose — is the feedback payload.

### 2.3 Troubleshooting — repair strategy per diagnostic

| Diagnostic | Encoded repair move |
|---|---|
| `SCHEMA_VIOLATION` / `BAD_EXPRESSION_SYNTAX` | Rare under constrained decoding; re-emit the node at `json_path` only |
| `MISSING_FACT` | Use the `suggestion` (closest fact name); if genuinely optional, wrap in `default()`/`has()` |
| `TYPE_MISMATCH` | Check `fact_schema()` types; never "fix" by string-comparing numbers |
| `EMIT_CONFLICT` | Two same-priority rules emit one key: either differentiate priorities (and state why) or make conditions mutually exclusive |
| `SHADOWED_RULE` | The new rule can never win — usually means amend the existing rule instead of adding one |
| `UNREACHABLE_RULE` / `AFTER_CYCLE` | Re-derive the `after` chain from the dependency the cases actually show |
| `EMIT_NOT_ALLOWED` | Out of capability scope — drop the emit; flag for governor if the scope itself seems wrong |
| Simulation: low precision on one rule | Tighten with a guard from the failing cases' distinguishing facts; don't lower priority to "hide" it |
| Simulation: coverage delta ≈ 0 | The candidate restates existing coverage — distill from *uncovered* cases only |

Round-trip budget exhausted (>3) → the loop layer escalates: the case batch is marked
undistillable and surfaces to the governor rather than looping forever.

---

## 3. Human Governor

### 3.1 Onboarding

Configure once, with the host developer:
- **Approval policy** (FR-14.5): per emit-key pattern — e.g. auto-promote `route.*`,
  require approval for `refund.*`/`escalate`.
- **Capability boundary**: review the `emit_allowlist` — it is the hard outer limit on
  what any machine-authored rule can ever do (engine-enforced, FR-10.6).
- **Audit sink**: where decision traces and promotion records land.

### 3.2 Usage

**Promotion review** (minutes, by exception). A promotion request contains: the rule
diff in the **YAML human-review projection** (FR-5.5), the simulation report (precision,
coverage delta, verdict diffs vs current — *read the diffs first*; they are the complete
behavioral change), and provenance (authoring agent, source cases, evidence). Approve,
reject with a note (which feeds the next distillation round), or escalate to a canary
run (FR-14.7, P2).

**Audit** ("why did the system do X on June 3?"): look up the `decision_id` → the trace
shows fired rules, field values, and per-`PROMPT()` records → **replay** the run with
LLM leaves served from the trace cache to reproduce it exactly → provenance links each
fired rule to the cases it was distilled from and who approved it. The chain
*decision → rules → cases → approval* is complete and tamper-evident.

### 3.3 Troubleshooting

| Situation | Flow |
|---|---|
| Bad decision in production | `decision_id` → trace → identify the deciding rule → immediate mitigation: demote/disable via a one-rule ruleset revision (a governed change like any other), then send the case to distillation as a counter-example |
| Suspected drift (precision falling) | Telemetry per-rule helpful/harmful trend (FR-14.6) → re-simulate the active ruleset against *recent* cases → retire or re-distill flagged rules |
| Agent keeps proposing out-of-scope rules | Review `EMIT_NOT_ALLOWED` events: either the boundary is right (tune the distiller's instructions) or the product has grown (widen the allowlist deliberately, as a reviewed change) |
| Regulator asks for reasons | The trace's deciding conditions + `why_not` ranked reasons map directly to adverse-action-style reason codes (≤4, ranked — the format was chosen for this) |

---

## 4. Downstream Agent

No onboarding — the host wires it. Its contract:
- **Obey the verdict**; covered decisions are not re-litigated by the model.
- **Condition on the trace**: `trace.for_llm()` (compact, structured) explains *why*,
  which measurably improves the agent's adjacent decisions and its fallback behavior.
- **On uncovered turns**: decide, and know the decision is recorded — the agent's own
  judgment is tomorrow's rule.

---

## 5. Lifecycle of a Deployment (all personas, end to end)

| Stage | What happens | Exit signal |
|---|---|---|
| **Day 0 — embed** | Host wraps decision points, zero rules, observation mode | First cases in the store |
| **Week 1 — observe** | Agent decides everything; cases + outcomes accumulate | Enough cases per decision family (heuristic: ~50) |
| **First distillation** | Loop runs distill → repair → simulate; governor reviews the first promotion *carefully* (it sets the precedent) | Coverage moves off 0%; first cost/latency savings measured |
| **Growth** | Distillation runs on a cadence over uncovered cases; coverage climbs; routine promotions auto-approve per policy | Coverage plateaus at the deployment's natural ceiling |
| **Steady state** | Rules handle the routine; agent judgment reserved for the novel; `PROMPT()` leaves (L1) absorb narrow judgments inside rules | North-star dashboard: coverage, precision, repair efficiency |
| **Drift / incident** | §3.3 flows: replay, counter-example distillation, retirement | Precision recovers; post-mortem traces archived |

---

## 6. Items surfaced by this document — resolved into PRD v1.2

1. ~~Recorder coupling manual~~ → **FR-14.1**: observation mode ships as a one-line
   `ObservedEngine` wrapper; recording cannot be forgotten.
2. ~~Expedited "disable now" path unspecified~~ → **FR-14.8**: governed expedited
   revision — the only promotion path exempt from the simulation gate, with provenance
   (`source: incident`) and auto-queued counter-example distillation.
3. ~~Repair-budget exhaustion implied~~ → **FR-14.3**: budget exhaustion is a defined
   outcome — case batch marked *undistillable*, surfaced to the governor, excluded from
   automatic distillation until unblocked.
4. ~~~50-case heuristic~~ → **PRD open question 6**: calibrate empirically at the M5
   flagship demo (owner: M5 exit review).
