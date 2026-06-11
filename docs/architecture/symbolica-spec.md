# Symbolica v2 — Technical Specification

| | |
|---|---|
| Status | **Normative** — conformance tests derive from this document |
| Version | 1.0 (2026-06-11) |
| Upstream | `docs/product/symbolica-prd.md` v1.5 (requirements), `docs/architecture/symbolica-architecture.md` v1.2 (structure) |
| Audience | Implementers and the conformance suite. Two implementers working from this spec alone must produce engines that pass each other's golden tests |

**Conformance language:** MUST/MUST NOT are binding; SHOULD is binding unless a
documented reason exists. Every normative clause is testable; section numbers (`S-n.m`)
are referenced by conformance-test tags. Decisions made *by this spec* (i.e., choices
the PRD left open) are marked **[SD-n]** and indexed in §10.

---

## S-1. Ruleset Document Format

### S-1.1 Top level

A ruleset is a JSON object: `{"format": 2, "rules": [...]}` with optional `"name"`
(string) and `"meta"` (object). Unknown top-level keys → `SCHEMA_VIOLATION`. `format`
MUST equal `2`; any other value → `SCHEMA_VIOLATION` with a message naming the
supported format. An empty `rules` array is **valid** (zero-rule engine, FR-10.7).

### S-1.2 Rule object

Fields per PRD FR-5.2. Normative constraints the JSON Schema cannot express:

- `id` unique within the document (`DUPLICATE_RULE_ID`, second occurrence's path).
- Exactly one of `after` / `after_any` may be present (both → `SCHEMA_VIOLATION`).
- Every id in `after`/`after_any` MUST name a rule in this document
  (`UNKNOWN_AFTER_TARGET`); the `after` digraph MUST be acyclic (`AFTER_CYCLE`,
  reporting one full cycle). Self-reference is a cycle.
- At least one of `set`/`emit`, each non-empty if present (`SCHEMA_VIOLATION`).
- `set` and `emit` keys MUST match `^[a-z_][a-z0-9_.]*$` (dots allowed for namespacing,
  e.g. `refund.amount`; no leading/trailing/double dots).
- `meta.provenance`, if present, is an object with optional string fields `author`,
  `source`, `created_at` (RFC 3339) and optional array `evidence` (case ids). The
  engine preserves it untouched (FR-10.1).

### S-1.3 Conditions

`when` is a **condition**: either an expression string (S-3) or exactly one of
`{"all": [c₁…cₙ]}`, `{"any": [c₁…cₙ]}`, `{"not": c}`, recursively. `all`/`any` arrays
MUST be non-empty (`SCHEMA_VIOLATION`). A condition tree is semantically equivalent to
the boolean expression obtained by joining children with `and`/`or`/`not` — all S-3.6
semantics (typing, absorption, reordering) apply to the tree exactly as to the
expression form.

### S-1.4 Value marking in `set`/`emit` **(normative core — kills v1 bugs #1–#3)**

For each JSON value `v` in `set`/`emit`:

1. `v` is not a string → **literal**, used verbatim.
2. `v` is a string whose first non-space character is `=`:
   - starts with `==` → **literal string**: everything after the first `=` (one `=`
     consumed; leading spaces before `==` preserved? No — see [SD-1]).
   - otherwise → **expression**: the text after the first `=` is compiled per S-3.
3. `v` is any other string containing the two-character sequence `{=` → **template**
   (S-3.9).
4. Any other string → **literal**.

**[SD-1]** Leading whitespace before the `=` marker is permitted and consumed together
with the marker; in the `==` escape, the literal is the string with exactly the first
`=` removed and leading whitespace preserved as written after removal. Examples:
`"  = a + b"` → expression `a + b`; `"==hello"` → literal `"=hello"`; `"== x"` →
literal `"= x"`.

## S-2. Value Domain & Types

Values are JSON values with refined numerics:

| Type | Definition |
|---|---|
| `null` | JSON null |
| `bool` | `true`/`false`. **`bool` is NOT a numeric type** — implementations in Python MUST guard against `bool ⊂ int` (`true == 1` is `TYPE_MISMATCH`-class, see S-3.5) |
| `int` | Arbitrary-precision integer |
| `float` | IEEE-754 binary64. `NaN`/`Infinity` cannot appear in documents (JSON) and MUST NOT be produced: any operation that would produce them yields `LIMIT_EXCEEDED` (overflow → ±inf) or follows S-3.5 (0/0 → `DIVISION_BY_ZERO`) **[SD-2]** |
| `string` | Unicode |
| `list` | Ordered, heterogeneous |
| `object` | String-keyed mapping (facts, nested structures) |

**Numeric class** `num` = {int, float}. Mixed int/float comparison and arithmetic are
permitted; arithmetic on mixed operands yields float (except `/`, S-3.5).

## S-3. Expression Language

### S-3.1 Lexical & parsing

Expressions parse with Python's `ast.parse(expr, mode='eval')`. Therefore lexical rules
(string quoting and escapes, numeric literals, identifiers) are Python's. Constraints:
numeric literals with underscores are permitted; complex, bytes, and f-string literals
are rejected by the node whitelist.

### S-3.2 Grammar (EBNF over the accepted AST shape)

```
expr        = or_expr ;
or_expr     = and_expr , { "or" , and_expr } ;
and_expr    = not_expr , { "and" , not_expr } ;
not_expr    = "not" , not_expr | comparison ;
comparison  = arith , { comp_op , arith } ;            (* chains allowed, S-3.6 *)
comp_op     = "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" | "not in" ;
arith       = term , { ("+" | "-") , term } ;
term        = factor , { ("*" | "/" | "%") , factor } ;
factor      = ("+" | "-") , factor | power ;
power       = postfix , [ "**" , factor ] ;            (* right-assoc, Python *)
postfix     = primary , { "." ident | "[" expr "]" } ;
primary     = ident | literal | list_display | call | "(" expr ")" ;
call        = ident , "(" , [ expr , { "," expr } ] , ")" ;
list_display= "[" , [ expr , { "," expr } ] , "]" ;
literal     = INT | FLOAT | STRING | "true" | "false" | "null"
            | "True" | "False" | "None" ;
```

**[SD-3]** Both JSON-style (`true/false/null`) and Python-style (`True/False/None`)
keyword literals are accepted (machine authors emit both); all six are reserved names.
`is`/`is not` are **rejected** (`FORBIDDEN_CONSTRUCT`) — identity has no meaning over
JSON values; authors must use `==`/`has()`.

Anything outside this grammar (comprehensions, lambdas, dicts/sets/tuples, slices,
keyword/starred arguments, attribute access on call results is *allowed* — postfix
applies to any primary — but f-strings, walrus, await, etc.) → `FORBIDDEN_CONSTRUCT`
at compile time, naming the construct.

### S-3.3 Static validation (compile time)

In order: length ≤ 2,000 chars → AST parse (`BAD_EXPRESSION_SYNTAX`) → node whitelist
(`FORBIDDEN_CONSTRUCT`) → AST depth ≤ 32 (`LIMIT_EXCEEDED`) → name/call resolution:
called names MUST be builtins (S-3.8), special forms (S-3.7), or registered functions
(`UNKNOWN_FUNCTION`, with nearest-name suggestion); non-called names are fact
references; reserved names MUST NOT be used as fact references (`RESERVED_NAME`).
Reserved: the six keyword literals, builtin/special-form names, `PROMPT`, and all
registered function names.

### S-3.4 Name resolution & path semantics

- A bare name resolves in working memory (input facts ∪ `set` writes). Unresolvable →
  **missing** (S-3.6) with path = the name.
- `x.y`: `x` must resolve to an `object`; then key `"y"`. Missing key → missing with
  path `x.y`. `x` not an `object` → **type error** with path and actual type
  (PRD OQ-3 resolved: `TYPE_MISMATCH`).
- `x[k]`: `x` is `list` → `k` MUST be `int` (else type error); negative indices
  Python-style; out of range → missing with path `x[k]`. `x` is `object` → `k` MUST
  be `string`; absent key → missing. `x` is `string` → `k` MUST be `int`; out of
  range → missing; result is a 1-char string. Other bases → type error. **[SD-4]**
  (out-of-range/absent-key = *missing data*, not type error — repairable the same way.)

### S-3.5 Operator semantics & type matrix

All cells not listed → **type error** (`TYPE_MISMATCH`, reporting operator, operand
types, and operand source spans).

| Operator | Accepted operand types | Result |
|---|---|---|
| `==` `!=` | same type; `int`↔`float` (numeric equality); **`null` vs anything** | `bool`. `null == null` → true; `null == non-null` → false **[SD-5]**. Lists/objects compare structurally (recursive, same rules) |
| `<` `<=` `>` `>=` | `num`↔`num`; `string`↔`string` (Unicode code-point lexicographic) | `bool` |
| `in` / `not in` | needle: any; container: `list` (structural-equality membership) or `string` (needle MUST be `string`; substring) | `bool` |
| `+` | `num`+`num`; `string`+`string` (concat) **[SD-6]** | `num` (float if either float) / `string` |
| `-` `*` | `num` only (no string/list repetition) | int if both int, else float |
| `/` | `num`/`num` | **always `float`** (true division). Divisor `== 0` (int or float) → `DIVISION_BY_ZERO` |
| `%` | `num` % `num`, Python semantics (result sign follows divisor) | int if both int, else float. Zero divisor → `DIVISION_BY_ZERO` |
| `**` | `num` ** `num`. If both int and exponent < 0 → result float (Python). **Guard**: both-int with \|exponent\| > 1024, or any operand magnitude that overflows binary64 in float context → `LIMIT_EXCEEDED` **[SD-7]** | `num` |
| unary `-` `+` | `num` | `num` |
| `not` | `bool` **only** | `bool` |
| `and` `or` | `bool` operands **only**; result `bool` — **no truthiness anywhere** [SD-8]; semantics: S-3.6 | `bool` |

**[SD-8] No truthiness.** A non-`bool` operand to `not`/`and`/`or`, a non-`bool`
condition result, or a non-`bool` `{"not": c}` child is a type error. `when` MUST
evaluate to `bool`. This is the no-coercion rule (FR-6.3) applied to logic.

### S-3.6 Evaluation semantics: errors, MISSING, and boolean absorption

Evaluation of any node yields exactly one of: a **value**, **missing(path)**, or
**type-class error** (`TYPE_MISMATCH`/`DIVISION_BY_ZERO`/`LIMIT_EXCEEDED`/
`FUNCTION_ERROR` — collectively "errors"; missing is also an error for propagation,
distinguished only by code `MISSING_FACT`).

- **Default propagation:** an error in any operand makes the enclosing node yield that
  error. Multiple available errors → report the one whose source span starts earliest
  (deterministic).
- **Boolean absorption [SD-9] (the deferred decision, resolved):** `and`/`or` (and the
  equivalent `all`/`any` trees) are **commutative with absorption**, CEL-style:
  - `and`: if **any** operand yields `false` → result `false`, all errors in other
    operands absorbed. Else if any operand errors → that error. Else `true`.
  - `or`: if any operand yields `true` → `true`, errors absorbed. Else if any errors →
    error. Else `false`.
  - `not`: propagates (no absorption).
  - Absorbed errors MUST NOT appear in `result.diagnostics`; they MUST be recorded in
    the trace at `standard`+ levels on the operand's record (`"absorbed": true`).
  - **Consequence (the observable-equivalence rule for FR-6.5):** because absorption
    is commutative, result and surfaced diagnostics are independent of operand
    evaluation order. Implementations MAY evaluate operands in any order (cost-ordered,
    AD-9), MAY short-circuit on a deciding value, and on encountering an error MUST
    continue evaluating remaining operands until a deciding value is found or all are
    exhausted. Which operands appear as *evaluated* in the trace is expressly
    order-dependent and not conformance-relevant.
- **Chained comparisons** `a OP₁ b OP₂ c` desugar to `(a OP₁ b) and (b OP₂ c)` with
  each operand expression evaluated **at most once**; absorption applies to the
  conjunction.
- At the **rule boundary**: a `when` yielding an unabsorbed error → the rule does not
  fire; one diagnostic (the error, carrying `rule_id`) is appended to the run. A `set`/
  `emit` value or template yielding any error → rule does not fire, atomically
  (FR-7.6), diagnostic appended. There is **no absorption** outside boolean operands.

### S-3.7 Special forms (compile-time rewrites; not callable values)

- `has(path)` — `path` MUST be a bare name/dotted/subscript chain with **constant**
  subscripts (else `BAD_EXPRESSION_SYNTAX`). Returns `bool`: `true` iff full resolution
  succeeds (S-3.4) without missing *or* type error along the path **[SD-10]**. Never
  yields an error itself.
- `default(path, fallback)` — `path` as above; `fallback` any expression. Resolution
  success → resolved value; resolution failure (missing or path-type-error) →
  `fallback`'s value **[SD-10]**. Errors *in the fallback expression* propagate
  normally. `fallback` is evaluated only when needed.

### S-3.8 Built-in functions

Arity/type violations → `TYPE_MISMATCH`. All are total given the listed domains.

| Function | Signature | Notes |
|---|---|---|
| `len(x)` | `list\|string → int` | |
| `sum(xs)` | `list[num] → num` | empty → `0` (int); any non-num element → type error |
| `min(...)` / `max(...)` | `(num, num, …≥2) → num` or `(list[num]) → num` | empty list → type error |
| `abs(x)` | `num → num` | |
| `round(x)` / `round(x, n)` | `num → int` / `(num, int) → float` | banker's rounding (IEEE/Python) **[SD-11]** |
| `contains(c, x)` | `(list, any) → bool` (membership) or `(string, string) → bool` (substring) | |
| `startswith(s, p)` / `endswith(s, p)` | `(string, string) → bool` | |
| `lower(s)` / `upper(s)` | `string → string` | Unicode default case mapping |
| `has` / `default` | special forms (S-3.7) | |

Registered custom functions: declared arity enforced at compile time where call sites
are static; a raising function yields `FUNCTION_ERROR` (code joins the S-3.6 error
class) carrying the exception type/message — never a crash (FR-11.1). *(`FUNCTION_ERROR`
is added to the FR-9.1 registry by this spec **[SD-12]**.)*

### S-3.9 String templates

Syntax inside any `set`/`emit` string not marked as an expression: `{=` *expr* `}` —
expression text runs to the **first** unquoted `}` (template expressions may not
contain `}`-bearing constructs at top level — subscripts use `]`; this is sufficient).
Escape: `{{=` produces literal `{=`. Unterminated `{=` → `BAD_EXPRESSION_SYNTAX` at
compile time.

Interpolated value → string conversion **[SD-13]**: `string` as-is; `int` decimal;
`float` shortest round-trip (Python `repr`); `bool` → `"true"`/`"false"`; `null` →
`"null"`; `list`/`object` → compact canonical JSON (sorted keys, `,`/`:` separators).
Template output length > 65,536 chars → `LIMIT_EXCEEDED`. Any expression error fails
the rule per S-3.6.

## S-4. Execution Semantics

### S-4.1 Canonical execution order (FR-7.5, completed)

At compile time:

1. Build the **field-dependency digraph**: edge A → B iff some key written by A
   (`set` ∪ `emit` keys) is referenced by B (`when` fields ∪ fields of B's value
   expressions, per compiled field sets). `after` edges are added as dependency edges.
2. **[SD-14]** Field-dependency cycles are legal (unlike `after` cycles): condense the
   graph into strongly-connected components; topologically order the SCC DAG
   (Kahn's algorithm; among simultaneously-ready SCCs, the one containing the
   highest-priority rule first, then lowest document index — deterministic).
3. Within each SCC: priority descending, then document index ascending.
4. The concatenation is the **canonical order** — total, deterministic, exposed via
   `engine.execution_order()`.

### S-4.2 The run

```
working ← copy of input facts;  fired ← [];  staged ← [];  diags ← []
for pass in 1..max_passes (default 16):
    fired_this_pass ← 0
    for rule in canonical_order:
        if rule.id ∈ fired: continue
        if not after_satisfied(rule, fired): continue        # after: all; after_any: ≥1
        r ← eval(rule.when, working)                          # the ONLY evaluation
        if r is error: diags += [r@rule]; continue            # did not fire; no retry this pass? see [SD-15]
        if r == false: continue
        vals ← eval all set/emit values & templates           # compute-then-apply
        if any error: diags += [first@rule]; mark rule FAILED (never retried); continue
        working[k] ← v for (k,v) in set-vals                  # visible immediately
        staged += [(key, value, rule.priority, doc_index) for emit-vals, allowlist-checked]
        fired += [rule.id]; fired_this_pass += 1
    if fired_this_pass == 0: converged ← true; break
if not converged: diags += NOT_CONVERGED(warning)
```

**[SD-15] Error-rule retry semantics:** a rule whose `when` yields an unabsorbed error
in pass *p* MAY become evaluable later (e.g., the missing fact is `set` by another rule
in pass *p*). Such a rule **is re-evaluated in subsequent passes** (it has not fired);
its error diagnostic is recorded **once per distinct error code+path per rule per
run**, not per pass. A rule whose `set`/`emit` *application* failed is marked FAILED
and is **not** retried (its partial side effects were rolled back; retrying would make
run cost unbounded); FAILED is recorded in the trace.

Disabled rules are excluded before execution (load time) and never appear in the
canonical order.

### S-4.3 Working memory vs verdict

**[SD-16]** `emit` values do **not** enter working memory — they are verdict-only.
A rule whose output other rules must read uses `set` (optionally `set` + `emit` of the
same key, written explicitly twice). Rationale: a single explicit channel for
inter-rule dataflow keeps the dependency graph (S-4.1) and the verdict semantics
independent. `set` writes overwrite earlier `set` writes (sequential semantics, no
conflict resolution, no diagnostic — order is canonical and deterministic).

### S-4.4 Verdict assembly (FR-7.6, completed)

After the run, group `staged` by key. Per key the winner is: highest `priority`; tie →
**lowest document index** wins. The losing entries are retained in the trace
(`standard`+) as `overridden_by`. `verdict` = winners; `changed` = the subset of
`verdict` whose value differs (deep structural equality, S-3.5 `==` rules with
`null == non-null → false` semantics) from the input fact of the same key, or whose
key is absent in input. `covered` = `fired ≠ []`. Emit keys failing the allowlist were
never staged: `EMIT_NOT_ALLOWED` (warning) + trace event, per FR-10.6.

### S-4.5 Deadline & strict mode

The monotonic deadline (default 5,000 ms; `deadline_ms` overrides) is checked at every
composite-expression node and between rules; expiry → `LIMIT_EXCEEDED` (error) on the
run, evaluation stops, partial results return with `converged = false`. `strict=True`:
the first **error**-severity diagnostic raises `StrictModeError` carrying it
(warnings never raise).

## S-5. Diagnostics Catalog (normative payloads)

Common envelope: `{code, severity, message, suggestion?}` + location: compile-time →
`json_path` (RFC 6901 pointer into the ruleset document); runtime → `rule_id`,
`expression`, `span` (`[start, end)` char offsets into the expression).

| Code | Sev | Phase | Extra payload fields | Message template (values single-quoted) |
|---|---|---|---|---|
| `SCHEMA_VIOLATION` | error | compile | `schema_path` | `'<json_path>' <constraint violated>.` |
| `DUPLICATE_RULE_ID` | error | compile | `other_path` | `Rule id '<id>' is already defined at '<other_path>'.` |
| `UNKNOWN_AFTER_TARGET` | error | compile | `target` | `Rule '<id>' lists '<target>' in after, but no such rule exists.` + suggestion |
| `AFTER_CYCLE` | error | compile | `cycle` (id list) | `after dependencies form a cycle: <id → id → … → id>.` |
| `EMIT_CONFLICT` | error | compile | `key`, `rule_ids` | `Rules <ids> emit '<key>' at equal priority <p> and can fire together.` |
| `SHADOWED_RULE` | warning | compile | `by_rule` | `Rule '<id>' can never win '<key>': '<by_rule>' (priority <p>) subsumes its condition.` |
| `UNREACHABLE_RULE` | warning | compile | `reason` | `Rule '<id>' can never fire: <reason>.` |
| `BAD_EXPRESSION_SYNTAX` | error | compile | `detail` | `Invalid expression syntax at <span>: <detail>.` |
| `FORBIDDEN_CONSTRUCT` | error | compile | `construct` | `'<construct>' is not allowed in expressions.` |
| `UNKNOWN_FUNCTION` | error | compile | `name` | `Unknown function '<name>'.` + nearest-name suggestion |
| `RESERVED_NAME` | error | compile | `name` | `'<name>' is reserved and cannot be used as a fact or function name.` |
| `TYPE_MISMATCH` | error | both | `op`, `left_type`, `right_type` | `Cannot apply '<op>' to <left_type> and <right_type>.` |
| `MISSING_FACT` | error | runtime | `path` | `Fact '<path>' is not defined.` + nearest-fact suggestion (edit distance ≤ 2) |
| `DIVISION_BY_ZERO` | error | runtime | — | `Division by zero in '<expression>'.` |
| `FUNCTION_ERROR` | error | runtime | `function`, `exception` | `Function '<function>' raised <exception>.` |
| `LIMIT_EXCEEDED` | error | both | `limit`, `actual` | `<limit description> exceeded (<actual> > <limit>).` |
| `BUDGET_EXCEEDED` | error | runtime (L1) | `budget`, `spent` | `Run budget exhausted ($<spent> of $<budget>).` |
| `NOT_CONVERGED` | warning | runtime | `passes` | `Run did not converge within <passes> passes.` |
| `EMIT_NOT_ALLOWED` | warning | runtime | `key`, `rule_id` | `Rule '<rule_id>' emitted '<key>', which is outside the allowlist; dropped.` |
| `NEAR_DUPLICATE_RULE` | warning | loop | `similar_to`, `similarity` | `Candidate '<id>' is <similarity> similar to existing rule '<similar_to>'; consider amending it instead.` |

The `llms.txt` diagnostic table is generated from this catalog (NFR-10.2).

## S-6. Case Schema

```json
{ "$id": "symbolica/case/v1", "type": "object", "additionalProperties": false,
  "required": ["case_id", "case_version", "facts", "decision", "source", "timestamp"],
  "properties": {
    "case_id":      {"type": "string"},
    "case_version": {"const": 1},
    "facts":        {"type": "object"},
    "decision":     {"type": "object"},
    "outcome":      {"type": ["object", "null"],
                     "description": "delayed ground truth; null until known"},
    "source":       {"enum": ["agent", "human", "rules"]},
    "timestamp":    {"type": "string", "format": "date-time"},
    "masked_paths": {"type": "array", "items": {"type": "string"}},
    "meta":         {"type": "object"} } }
```

`decision` and `outcome` are host-defined objects; `simulate()` compares candidate
verdicts against `decision` (and `outcome` where present) by deep equality on shared
keys. Masking (FR-8.4) is applied before persistence; `masked_paths` lists what was.

## S-7. Trace Schema (level-additive)

Top level (all levels): `trace_version` (1), `decision_id` (UUIDv4), `trace_id`/
`span_id` (W3C trace-context; host-suppliable), `engine_version`, `ruleset_revision`,
`format` (2), `level`, `config` (effective `max_passes`, `deadline_ms`, allowlist hash,
limits — NFR-5.4), `timestamp`, `duration_ms`, `fired` (ordered ids), `verdict`,
`covered`, `converged`, `diagnostics`, `masked_paths`.

`standard` adds `rules`: one record per **evaluated** rule:
`{rule_id, pass, eligible, evaluated, fired \| failed, condition_result
(true|false|error), fields: {path: value-or-"<masked>"}, deciding: <span of the
operand that decided>, absorbed: [spans], emits: [{key, value, staged|overridden_by|
dropped_by_allowlist}]}`. Eligible-but-unevaluated and ineligible rules appear only as
ids in `skipped` (with reason `after_unsatisfied | already_fired`).

`full` adds per-node events: `{span, op, value-or-error, duration_us}` in evaluation
order, plus per-pass boundaries. L1 adds `external_calls`:
`{call_id, rule_id, span, template_id, prompt_hash (standard) | prompt_text (full),
model, model_snapshot, params_hash, response, cost, latency_ms, cache_hit}` — this
array is the replay cache (NFR-5.3).

`why_not(rule_id)` and `near_misses(n)` are **derived** from `standard`-level data
(field values + condition structure): re-resolve each failed comparison's recorded
values; for `<value> OP <constant>` report the constant as the counterfactual boundary.
At `minimal` level they return an explanatory error value, not a guess.

## S-8. Engine & Lifecycle API Contract (signatures, normative)

```python
compile_ruleset(doc: dict | str) -> CompiledRuleSet            # raises CompileError(diagnostics) on any error-severity diag
validate(doc: dict | str) -> list[Diagnostic]                  # never raises
Engine(compiled, *, functions={}, emit_allowlist=None, telemetry=None,
       masks=(), max_passes=16, deadline_ms=5000)
Engine.reason(facts: Mapping, *, strict=False, deadline_ms=None,
              trace='standard') -> ExecutionResult
Engine.execution_order() -> list[str]
CompiledRuleSet.fact_schema() -> dict        # {path: {"types": [...], "rules": [ids]}}
CompiledRuleSet.revision -> str              # SHA-256 of canonical JSON (sorted keys, no ws)
simulate(candidate, cases, *, baseline=None, processes=None) -> SimulationReport
Recorder(store).record(facts, decision, *, outcome=None, source, meta=None) -> Case
```

`reason()` MUST be callable concurrently from any threads (NFR-2.1) and MUST NOT raise
except `StrictModeError` (strict) and `TypeError` for non-Mapping `facts` — every other
condition is a diagnostic (NFR-6.1).

## S-9. Worked Conformance Examples (golden — committed verbatim)

**E1 — marking, priority conflict, changed-view.** Rules: `a`(prio 1, `when: "x > 0"`,
emit `{tier: "bronze", date: "2024-10-15", half: "= x / 2"}`); `b`(prio 100,
`when: "x > 0"`, emit `{tier: "gold"}`). Facts `{x: 10, tier: "gold"}` →
`fired = ["b", "a"]` (same priority class — order by S-4.1: no deps, priority desc),
`verdict = {tier: "gold", date: "2024-10-15", half: 5.0}` (b wins `tier` by priority;
`date` is a **literal string**; `half` is float), `changed = {date: …, half: 5.0}`
(`tier` equals input), `covered = true`, no diagnostics. *(v1 bugs #1, #4, #8.)*

**E2 — missing fact + absorption + why_not.** Rule `r`(prio 0, `when: {"all":
["score > 5", "vip == true"]}`, emit `{approved: true}`). Facts `{score: 3}` →
`fired = []`; **no** `MISSING_FACT` diagnostic (`score > 5` is false → `vip` error
absorbed); `why_not("r")` reports failed condition `score > 5` with actual `3`,
boundary `5`, and second operand absorbed-missing `vip`. Facts `{score: 9}` →
diagnostic `MISSING_FACT` `{path: "vip", rule_id: "r"}`, rule did not fire.

**E3 — set vs emit, passes, after.** Rules: `assess`(prio 10, `when: "amount > 100"`,
set `{band: "high"}`); `route`(prio 0, `when: "band == 'high'"`, emit
`{queue: "senior"}`); `notify`(prio 0, after `["route"]`, `when: "true"`… *invalid —
`true` is a bool literal, fine*: `when: "queue == 'senior'"` would be missing —
`emit` isn't readable [SD-16] — so `notify` uses `when: "band == 'high'"`, after
`["route"]`, emit `{ping: true}`). Facts `{amount: 250}` → pass 1 fires `assess` then
`route` (canonical order puts producer first), `notify` ineligible until `route` fired
→ same pass, later position: fires in pass 1 if ordered after `route`, else pass 2 —
canonical order (S-4.1: `notify` depends on `route` via after-edge) guarantees same
pass: `fired = ["assess", "route", "notify"]`, one pass, `converged = true`,
`verdict = {queue: "senior", ping: true}` (`band` is set-only, not in verdict).

**E4 — type discipline.** Rule with `when: "1 == '1'"` → compile OK; run yields
`TYPE_MISMATCH` (`==`, int, string), rule not fired. `when: "flag"` with
`facts = {flag: 1}` → `TYPE_MISMATCH` (condition must be bool). `"true == 1"` →
`TYPE_MISMATCH` (bool is not numeric).

**E5 — templates and defaults.** Emit `{msg: "Hi {= upper(default(name, 'friend')) }",
eq: "==literal"}`, facts `{}` → `verdict = {msg: "Hi FRIEND", eq: "=literal"}`.

**E6 — zero rules.** `{format: 2, rules: []}`, any facts → `verdict = {}`,
`fired = []`, `covered = false`, `converged = true`, no diagnostics.

*(The committed suite expands these to ≥1 golden case per S-section clause.)*

## S-10. Spec Decision Index (choices made by this document — flag for review)

| SD | Decision | Section |
|---|---|---|
| SD-1 | `=`-marker whitespace handling; `==` escape strips exactly one `=` | S-1.4 |
| SD-2 | No NaN/Infinity anywhere; float overflow → `LIMIT_EXCEEDED` | S-2 |
| SD-3 | Both `true/false/null` and `True/False/None` accepted; `is` rejected | S-3.2 |
| SD-4 | Out-of-range index / absent key = `MISSING_FACT` (not type error) | S-3.4 |
| SD-5 | `null` is equality-comparable to anything (equal only to itself); order-comparison with null is a type error | S-3.5 |
| SD-6 | `+` concatenates strings; no other string/list operators | S-3.5 |
| SD-7 | Integer `**` exponent guard (\|exp\| ≤ 1024) | S-3.5 |
| SD-8 | No truthiness: `not`/`and`/`or`/conditions are strictly `bool` | S-3.5 |
| SD-9 | CEL-style commutative absorption in `and`/`or`; absorbed errors trace-only — this is what makes cost-reordering (FR-6.5) sound | S-3.6 |
| SD-10 | `has`/`default` treat path-type-errors like missing (uniform "resolution failure") | S-3.7 |
| SD-11 | `round` = banker's rounding | S-3.8 |
| SD-12 | `FUNCTION_ERROR` added to the diagnostic registry | S-3.8, S-5 |
| SD-13 | Template stringification rules (JSON-style bool/null; canonical JSON for structures) | S-3.9 |
| SD-14 | Field-dependency cycles legal via SCC condensation; `after` edges join the dependency graph | S-4.1 |
| SD-15 | Error-erroring rules re-evaluate next pass (dedup'd diagnostics); failed-application rules never retry | S-4.2 |
| SD-16 | `emit` is verdict-only — never readable by other rules; `set` is the sole inter-rule channel | S-4.3 |

## S-11. Conformance

An implementation conforms iff it passes the committed golden suite
(`tests/conformance/`) generated from this spec, the property invariants (totality,
determinism, atomicity — NFR-6.1/5.1), and produces byte-identical serialized results
across the support matrix for the entire suite. The spec wins over the implementation;
where the suite and spec disagree, the suite is wrong.
