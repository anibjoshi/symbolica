# Symbolica v2 — Evaluation Strategy

| | |
|---|---|
| Status | Active — defines how Symbolica's value is measured and proven |
| Version | 1.0 (2026-06-11) |
| Upstream | `symbolica-prd.md` v1.6 (§1.0 north star), `symbolica-spec.md` (Case schema), v1 lesson: an unevaluated system cannot prove it works even when it does |

---

## 1. The value claim

Per real deployment, the claim Symbolica must be able to substantiate, with every
clause measured and no clause achievable by gaming another:

> *"X% of this agent's decisions are handled by promoted policy at statistically
> non-inferior quality (shadow-validated), saving $Y and Z ms per decision net of loop
> costs, with 100% of decisions replayable and explained, and zero policy bypasses."*

## 2. North star: Quality-Gated Coverage (QGC)

**QGC = covered decisions / total decisions, counted only while the quality gate is
green.** Coverage earned during a red gate counts as zero.

**The quality gate** is a rolling non-inferiority test of rule decisions against the
fallback baseline (the agent's own judgment), evaluated per decision family over a
sliding window:

- **Inputs**, in order of evidentiary strength: (1) outcome joins (cases whose
  `outcome` backfilled — ground truth); (2) shadow comparisons (§5); (3) adjudicated
  samples from the golden set (§4.2).
- **Test**: severity-weighted agreement/precision of rule decisions ≥ baseline − δ,
  with a configured non-inferiority margin δ, minimum sample n, and window w (defaults
  set empirically at M5; recorded in deployment config).
- **States**: green (counting), red (rules still execute unless the governor pauses
  them, but coverage counts zero and the loop prioritizes the failing family for
  re-distillation), insufficient-data (new families start here; counts zero until n
  reached — coverage must be *earned*).

**Why not raw coverage:** a loop that promotes overly broad rules drives raw coverage
up while making worse decisions deterministically at scale. Any metric improvable by
doing the job worse cannot be the north star. QGC can only rise by being broad *and*
right.

**Honest expectations:** most decision traffic in typical agent systems is novel or
fuzzy; mature deployments may settle at 30–60% QGC. The value story is carried by the
per-covered-decision claim (consequential, repeated, now governed), not the raw
percentage.

## 3. Metric hierarchy

| Tier | Metric | Definition | Source | Role |
|---|---|---|---|---|
| **1 Quality** (the gate) | Outcome precision | rule decisions matching backfilled outcomes, severity-weighted | case store outcome joins | strongest evidence |
| | Shadow non-inferiority | paired rule-vs-agent agreement/quality on identical live traffic | shadow mode (§5) | the promotion gate for consequential keys |
| | Adjudicated agreement | agreement with human judgment on sampled decisions | golden set (§4.2) | calibrates the other two |
| | Severe-error rate | severity ≥3 wrong decisions per 1k covered | cases + outcomes | the "never again" counter |
| **2 Economics** | Net $ / decision | (baseline LLM cost − rule cost) − amortized loop cost (distillation tokens, simulation compute) | telemetry + L1 accounting | the adoption hook |
| | Latency delta | p50/p99 covered vs uncovered decision latency | telemetry | |
| **3 Loop health** (leading) | Repair round-trips | validate→repair iterations to clean candidate (target ≤3) | loop telemetry | distillation quality proxy |
| | Rule survival rate | % of promoted rules not retired within N days | revision history | the single best loop-quality proxy |
| | Gap-closure rate | uncovered-cluster mass converted to QGC per cycle | FR-14.10 clustering | is the loop aimed right? |
| | Promotion acceptance | % candidates passing gates / % approved by governor | loop telemetry | |
| **4 Governance** (the moat) | Reconstructibility | % decisions fully replayable + explained (target 100%, measured anyway) | trace store audit | |
| | Bypass rate | decisions taken on covered paths without engine consultation (target 0 under middleware) | host integration audit | |
| | Incident MTTR | time from bad decision to expedited revision live (FR-14.8) | audit log | |

Anti-gaming: each tier guards another — economics is conditional on the Tier-1 gate;
loop health can't be optimized by skipping gates (survival rate punishes it);
governance metrics are unaffected by the rest.

## 4. Evaluation assets (what must exist for any of this to be measurable)

### 4.1 The case store as eval substrate
- **Temporal splits, never random.** Train/eval splits are by time; random splits leak
  and flatter the system. Drift — the actual failure mode — only shows up in
  time-ordered evaluation.
- **Outcome backfill** (`outcome` on Case, S-6) is a first-class loop activity, not
  optional telemetry: outcomes are what let policy *exceed* the agent it learned from
  (§7).
- **Severity labels** (`severity` on Case, S-6): host-declared consequence class 1–4;
  weights every Tier-1 metric. A wrong routing and a wrong $5,000 refund are not the
  same unit.

### 4.2 Golden sets
Per decision family: a versioned, human-adjudicated set of cases with correct
decisions, grown deliberately — the loop samples covered decisions for adjudication
(weighted toward low-margin and high-severity ones) and governor review feeds the set.
Golden sets are versioned artifacts with provenance, used to calibrate outcome- and
shadow-based metrics and as regression suites on every promotion.

### 4.3 Counterfactual honesty
When a rule decides, the agent's hypothetical decision is unobserved; when a decision
is taken, the alternative's outcome is unobserved. Offline `simulate()` replays cases
generated *under the old policy* and cannot fully answer "is the new policy
non-inferior on live traffic?" — only shadow mode can. Selection bias is acknowledged,
not hidden: metrics state their evidence source (outcome / shadow / adjudicated).

## 5. Shadow mode (FR-14.7, promoted to M5)

Candidate (or probationary newly-promoted) rules evaluate **silently** on live
traffic: the engine computes their verdicts, the agent still decides for real, and
paired comparisons accumulate. Promotion of rules emitting consequential keys (the
approval-gated patterns of FR-14.5) **requires** shadow non-inferiority over the
configured minimum sample; routine keys may promote on simulation alone. Shadow runs
ride the same branch isolation (AD-16) — no live-state contamination — and shadow
verdicts/comparisons are recorded for the gate. Canary rollout (graduated live
traffic) is the same machinery pointed at enforcement and stays P2.

## 6. Platform evals (ship with the repo; gate releases)

Deployment value is host-specific; the *platform* must prove its machinery works with
ground truth known by construction:

- **Policy-recovery benchmarks** (M5): plant a hidden ground-truth ruleset in a
  benchmark domain (e.g., loan approval, support routing); generate cases through it
  with controlled label noise; run the full loop blind. Measure **fidelity** (verdict
  agreement with hidden truth on held-out facts), **statistical efficiency** (cases
  needed per rule recovered), **robustness** (fidelity vs noise rate), and **repair
  convergence** (round-trips). These are reproducible, public, and regression-gated.
- **Conformance + determinism + the v1-bug gauntlet** (M3/M4): table stakes, already
  specified (NFR-3.2, NFR-5.1).
- **The graduation demo** (M5 flagship): starts from a *memory-using* agent on a
  benchmark domain and shows the graduation — observation → distillation → gates →
  promotion → measured QGC — as a scripted, reproducible report.

## 7. The imitation ceiling, and the path past it

Distillation from agent decisions caps policy quality at agent quality. The ladder
out: (1) imitation (decisions as labels) to bootstrap coverage; (2) **outcome
correction** — where outcomes contradict decisions, outcomes win as distillation
targets; (3) adjudication — golden-set judgments override both. Tier-1 metrics report
against the strongest available evidence so progress past the ceiling is visible, and
rule survival under outcome joins is the long-run scoreboard.

## 8. Milestone ownership

| Milestone | Evaluation deliverables |
|---|---|
| M3/M4 | Conformance, determinism matrix, v1 gauntlet, performance baselines (already planned) |
| M5 | QGC computation in loop telemetry; shadow mode; golden-set mechanism; policy-recovery benchmark suite v1; graduation demo report; calibrate gate defaults (δ, n, w) and OQ-6 |
| M6 | L1 cost accounting feeding Tier-2 net economics |
| M7 | Survival/retirement telemetry (FR-14.6) completing Tier 3 |
