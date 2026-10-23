# Interrogate: attack the diff with independent reviewers

Spawn reviewers that try to break the change from independent angles, then judge their
findings as the lead reviewer. The signal comes from independence (different model, different
lens, no shared framing), not from assigned personas. The deliverable is a sorted verdict that
feeds the normal Reviewer report; nothing is auto-applied. From pstack's `interrogate` and the
`thermo-nuclear-code-quality-review` lens of its Claude Code port.

It complements the truth-check (super-review → "Adversarial mode"): the truth-check asks *is
what the PR claims true?*; interrogate asks *how does this break?*

## Trigger: `config.interrogate.trigger`

| Value | Runs when |
|---|---|
| `off` | never |
| `risky` (default) | labels ∩ {`security`, `migration`, `payments`, `auth`} ≠ ∅, or `merge_policy` would route the PR to a human (money, auth, schema), or the merge-base diff ≥ `interrogate.min_lines` (default 200) |
| `non-trivial` | the same rule as `truth_gate: non-trivial` (diff ≥ 10 lines or those labels) |
| `always` | every card |

`interrogate.reviewers` (default 2, max 4) is the number of reviewers. The budget rules of
`rate-limit-etiquette.md` apply to each: ≤ 50 `gh` calls, prefer local git; over budget →
`confidence: insufficient_data` for that reviewer, which never counts as a finding.

## Step 1: Scope and intent

Package the merge-base diff (`git diff $(git merge-base HEAD origin/<base>)...HEAD`), the files
it touches and the surrounding modules a reviewer needs. State the intent in one paragraph from
the issue, the ACs and the PR description. Reviewers judge the execution against that intent;
they never question the intent (the ticket owns it).

## Step 2: Reviewers

Each reviewer gets the same brief, read-only, with the diff, the intent, the rubric below and
the quality lens. Independence per host:

| Host | How |
|---|---|
| Claude workflow lane | sub-agents in one message, `readonly`; alternate `model` (`opus`, `sonnet`) and lens order so no two share model and first lens; never pass the Builder's summary |
| Codex lane · Antigravity lane (`--agy`) | no sub-agents: two inline passes in this order, each written to its own scratch file before the next starts: (a) correctness and root causes, (b) structure and quality. Report `reviewers: inline` in the report header; this is less independent and says so |

**Reviewer brief (use verbatim, fill `<…>`):**

```
You are Reviewer <A|B> in an adversarial review of PR #<P>. Find real problems: bugs, design
flaws, security issues, maintainability risks. Do not praise, do not restate what the code
does, do not question the intent.
Intent: <paragraph>
Diff: <merge-base diff or path>
Rubric: correctness (edge cases, errors swallowed, idempotency, concurrency: trace the call chain
before claiming nil/race) · root cause vs symptom (guard clauses that mask an invariant, retries
hiding a broken contract, casts hiding a modelling error) · structure (validation at the
boundary, coupling, dual paths kept alive, bolted-on vs integrated) · verification (tests test
behaviour, bug fix has a test for the bug, no proxy checks) · complexity budget (abstractions
with one caller, config for cases that do not exist, dead code) · security (input to dangerous
sinks, auth gaps, secrets in logs; show the input path).
Quality lens: be ambitious about structural simplification. Is there a reframing that deletes
whole branches, helpers, modes or layers while keeping behaviour? Flag: a file this PR pushes
past 1000 lines; ad-hoc conditionals bolted into unrelated flows; thin wrappers and identity
abstractions; new any/unknown/casts; feature logic leaking into shared paths; a bespoke helper
where a canonical one exists; needless sequential orchestration or non-atomic updates.
Budget: at most 50 gh calls; prefer local git. Over budget: confidence insufficient_data.
Return findings as: severity (critical | warning | nit), location file:line, finding, evidence
(why it matters, with the execution path), suggestion (optional). "No findings" is a valid
answer.
```

## Step 3: Synthesize

Merge findings that describe the same problem; note which reviewers raised each. A finding two
reviewers raised independently is the strongest signal. Where one reviewer says the opposite of
another, keep both as context for the verdict.

## Step 4: Lead judgment

You are a pragmatic senior engineer, not an aggregator. Four buckets, each finding in one, with
the reviewers that raised it and a one-line reason:

| Bucket | Means | Becomes |
|---|---|---|
| **Act on** | would block a real PR: correctness, security, data, failing required tests; or maintainability damage clearly in scope | a finding in the Reviewer report with the normal class (Gap · Bug · Verification miss · Scope drift · Over-engineering) and severity (Blocker · Should fix) |
| **Consider** | legitimate, cost unclear now | **Should fix** or **Nit** in the report, owner builder, never a bounce alone |
| **Noted** | valid but not actionable here: premature, context-dependent, low impact | one line under `Dismissed:` in the report comment, no row |
| **Dismissed** | wrong, nitpick, missing context, "I would have done it differently" | the same line, with the reason |

Filters: nitpick gravity (a review that is all nits means the code is fine; say so) ·
hypothetical vs actual (trace the call site; a null the type system prevents is not a finding)
· premature abstraction (does the code need to change a second way?) · missing context (the
reviewer suggests changing code this PR did not touch, or a pattern the codebase already uses).
Be slower to dismiss security and correctness findings, even from one reviewer.

Quality-lens findings follow the board's existing rule: **Should fix**, class Over-engineering
when they add building, **never a Blocker on their own**, never a bounce alone, and they do not
lower the truth-check confidence. A simplification that would cut validation, security,
data-loss protection or accessibility is not a finding.

## Step 5: Report

In the one Reviewer report comment (run.md → Reviewer, step 8), after the findings table:

```
Interrogate: reviewers A (opus) · B (sonnet) — or `inline` · act-on 1 · consider 1 · dismissed 3
Agreement: A and B both raised R4; A alone raised R5 (kept: traced path); B's "extract a
service" dismissed (one caller)
```

Act-on rows go through step 7 of the Reviewer lifecycle like any finding (bounce, block, or
merge). Never auto-apply a suggestion; the Reviewer changes no product code.
