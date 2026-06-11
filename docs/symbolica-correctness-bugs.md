# Confirmed Correctness Bugs (Silent Wrong Answers)

*All bugs below were reproduced live on `main` (commit `e088461`, 2026-06-10) with the probe
script in this repo's history (`/tmp/symbolica_probes.py`). None of them raise an error a
caller would see — they all produce plausible-but-wrong `ExecutionResult`s, which is exactly
the "unknown bugs giving wrong answers during benchmarks" failure mode.*

Severity legend: 🔴 wrong answers in common usage · 🟠 wrong answers in specific-but-realistic usage · 🟡 cost/consistency hazard.

---

## 1. 🔴 String action values are silently arithmetic-evaluated (`Engine._is_expression`)

`engine.py:129-186` guesses whether an action value is an expression using substring
heuristics. Any string containing `-`, `*`, `%`, etc. is fed to the arithmetic evaluator;
unknown names resolve to `None` only if lucky enough to raise.

**Reproduced:**

| YAML action value | Facts | Result in verdict |
|---|---|---|
| `date: "2024-10-15"` | — | `1999` (int!) — evaluated as `2024 − 10 − 15` |
| `phone: "555-1234"` | — | `-679` |
| `label: "high-risk"` | — | `"high-risk"` (only because `high`/`risk` aren't facts; if they were numbers, you'd get their difference) |

The same heuristic also has **false negatives** (see #2), so the bug is bidirectional.

## 2. 🔴 Division and bare field references in actions are never evaluated

The "looks like a URL/path" guard (`engine.py:183`) returns *not-an-expression* for **any
string containing `/`**, and single words are always literals.

**Reproduced** with `amount=10`:

| Action value | Expected | Actual |
|---|---|---|
| `half: "amount / 2"` | `5.0` | the literal string `"amount / 2"` |
| `double: "amount * 2"` | `20` | `20` ✓ |
| `copy: "amount"` | `10` | the literal string `"amount"` |

Multiplication works, division silently doesn't. A benchmark with mixed arithmetic gets a
mix of computed numbers and un-evaluated source strings.

## 3. 🔴 `{{ template }}` substitution does not exist

There is **no template engine anywhere in the package**. `{{` only makes
`_is_expression()` return True (`engine.py:160`); the evaluator then rejects `{...}` as an
unsafe AST set-literal, the exception is swallowed (`engine.py:206`), and the raw string
comes back.

**Reproduced:** `msg: "{{ amount * 2 }}"` → verdict contains the literal string
`"{{ amount * 2 }}"`. The README and `examples/10_template_evaluation/` advertise a feature
the engine cannot perform.

## 4. 🔴 `verdict` omits facts that match the input value (`ExecutionContext.set_fact`)

`models.py:197-202` only records an action's output in the verdict if the value is *new or
different from the input facts*.

**Reproduced:** input `{score: 10, approved: True}`, rule fires and sets `approved: true`
→ `fired_rules == ['confirm']` but `verdict == {}`. Any harness reading
`result.verdict["approved"]` gets a KeyError or wrong default even though the rule fired.

## 5. 🔴 Every condition is evaluated **twice**, by two different evaluator implementations

`_can_rule_fire` (engine.py:370) evaluates via `TraceEvaluator`→`CoreEvaluator`; if true,
`_execute_rule` (engine.py:396) **re-evaluates** via `ExecutionPathEvaluator`, a separate
hand-copied implementation. Consequences, all reproduced or verified in source:

- A condition function is **called 2× per fired rule** (probe F: counter = 2). For
  `PROMPT()` that is **double the LLM cost and latency** on every fired rule, and an
  additional call per *non*-fired rule per iteration. 🟡
- A non-deterministic function (any LLM) can pass the gate and fail/differ on the second
  evaluation — the action-application decision uses the *second* result. 🔴
- The second evaluator (`execution_path_evaluator.py:41`) **skips the AST security
  whitelist, the SIGALRM timeout, the recursion-depth limit, and the expression-length
  limit** that `CoreEvaluator` enforces (`core_evaluator.py:111-124`). The two
  implementations have already drifted (e.g. unary-op labeling) and will keep drifting. 🟠

## 6. 🔴 A rule whose execution *fails* is recorded as **fired** with no actions applied

`engine.py:443-463`: every exception path calls `context.rule_fired(rule.id, "Rule
execution failed: ...")` and returns False. **Reproduced** (probe E): `fired_rules ==
['r']`, `verdict == {}`. Benchmarks that count fired rules or join fired-rules→expected
verdicts get corrupted data, and because the ID is in `fired_rules`, the rule can never
retry in later iterations. If the failure happens mid-way through applying multiple
actions, earlier `set_fact` calls **remain applied** (partial writes).

## 7. 🔴 `reason()` silently fires **zero rules** in any non-main thread

`CoreEvaluator.evaluate` wraps everything in a SIGALRM-based timeout
(`core_evaluator.py:75-90`). `signal.signal()` raises `ValueError` outside the main
thread; the blanket `except Exception` converts it to `EvaluationError`; `_can_rule_fire`
swallows that and returns False.

**Reproduced** (probe G): same engine, same facts — main thread fires the rule; a
`threading.Thread` worker returns `fired_rules == []`, `verdict == {}`, **no error**.
Any benchmark harness using a thread pool gets all-empty results. (Same code path means
the evaluation timeout is also a no-op on Windows.)

## 8. 🟠 Priority is inverted for conflicting writes

Higher-priority rules fire **first**, and actions are last-writer-wins on the shared
context. **Reproduced** (probe J): `high` (priority 100, sets `tier: gold`) fires before
`low` (priority 1, sets `tier: bronze`) → final verdict `tier: 'bronze'`. The
lowest-priority rule wins every conflict — the opposite of what priority semantics imply
and of how the README presents priorities.

## 9. 🟠 `triggers:` do not gate anything — "rule chaining" is attribution only

A rule listed in another rule's `triggers` fires whenever its own condition is true, even
if the would-be triggering rule never fired. **Reproduced** (probe K): `step1` did not
fire, `step2` (only reachable via `step1`'s `triggers`) fired anyway. `triggers` only
affect the `(triggered by ...)` annotation in reasoning text (`engine.py:467-473`).
Workflows that rely on trigger gating compute results from states that should be
unreachable.

## 10. 🟠 `enabled: false` is ignored

**Reproduced** (probe H): a rule with `enabled: false` fires and writes its actions.
`_execute_rules_iteratively` (engine.py:334) never checks the flag. Benchmark configs that
disable rule variants are actually running all of them.

## 11. 🟠 Typo'd or missing fields make conditions silently false

A missing fact evaluates to `None` (`core_evaluator.py:345`); `None > 5` raises
`TypeError` → wrapped → swallowed by `_can_rule_fire` → rule just doesn't fire.
**Reproduced** (probe I): condition `scoer > 5` (typo) with `score=10` → no error, no
fire. There is no strict mode and no warning surfaced on the result object — the only
trace is a Python `logging` warning.

## 12. 🟡 Additional hazards verified in source (not probed)

- **Backward chaining API crashes** (`Goal` has no `.field`) — see symbolica-as-is-analysis.md §10.1;
  `examples/06` is broken.
- **`PROMPT()` bool coercion defaults to `False`** on any unrecognized response, and
  int/float coercion regex-extracts the *first* number from prose
  (`prompt_evaluator.py`, OutputValidator) — wrong answers that look like model errors.
- **Shared mutable `_recursion_depth`** on `CoreEvaluator` (`core_evaluator.py:101,123`)
  is reset per call — concurrent `reason()` calls on one engine corrupt the counter
  (spurious or missed recursion errors) even before the threading bug in #7.
- **`_can_rule_fire` + `_execute_rule` race the context**: condition checked, then facts
  mutated by the rule itself; within one iteration a later rule sees earlier rules'
  writes, but rules already evaluated this iteration don't re-fire until the next
  iteration — order-dependent results when combined with #8.

---

## Why the test suite doesn't catch these

The ~7.5k-line suite largely **pins the buggy behavior** rather than the intended
behavior: string-action tests assert the heuristic's current output, no test asserts
verdict contents for re-asserted facts, no test runs `reason()` off the main thread, no
test asserts a priority-conflict winner, and trigger tests only check the reasoning
annotation. Coverage numbers are high; semantic coverage is not.

## Suggested fix order for the refactor

1. **Single evaluator** with optional tracing hooks (kills #5 and the security-bypass drift).
2. **Explicit action-value semantics** — a syntax marker for expressions (e.g. only
   `{{ ... }}` is evaluated, everything else is a literal), implemented once, with a real
   template/expression pass (kills #1, #2, #3).
3. **Verdict = all action outputs of fired rules** (kills #4).
4. **Error policy**: failed rule ≠ fired rule; surface evaluation errors on the result
   (kills #6, demotes #11 to a lint).
5. **Replace SIGALRM** with a deadline check inside `_eval_node` (kills #7).
6. **Decide and document conflict semantics** (priority wins ⇒ apply in reverse order or
   first-writer-wins) (#8), make `triggers` actually gate (#9), honor `enabled` (#10).
