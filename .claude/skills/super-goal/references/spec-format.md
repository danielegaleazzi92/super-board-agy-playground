# super-goal — spec folder, acceptance tests, deviations

`super-goal.py init` scaffolds the folder; this file says what goes in each part.

```
docs/goal/
├── vision.md          Status: draft | approved · Goal · Users · Out of scope · How to try
├── requirements.md    ## R<n> — <title>   (Priority, Verify, Acceptance)
├── decisions.md       ## D<n> — <question>   (Choice, Why)  — every interview answer
├── priorities.md      ordered list: what wins when two requirements collide
├── deviations/        DV-<issue>-<k>.md, written by lanes during the run
├── trace.json         last measurement (super-goal.py trace --out)
└── recap.md           the final report (super-goal.py recap --out)
```

## requirements.md

```markdown
## R12 — Save progress offline
Priority: must | should | could
Verify: auto | manual
Acceptance:
- [ ] closing the app mid-level and reopening resumes at the same checkpoint
- [ ] with no network, saving never shows an error
```

| Rule | Value |
|---|---|
| Ids | `R<n>`, never reused, never renumbered; a dropped requirement stays with `Priority: dropped` |
| One requirement | one user-visible capability; 1–5 acceptance bullets, each assertable by a test |
| `Verify: manual` | only what no test can judge (fun, feel, art direction, store review). Listed in the recap under "Judge by hand"; never blocks "done" |
| Non-functional | write them as requirements with numbers (`R30 — cold start under 2 s on a mid phone`), so a test can hold them |

## decisions.md

Every interview answer, including the obvious ones, as `## D<n> — <question>` + `Choice:` +
`Why:`. Lanes read it before deciding anything; a deviation names the D it departs from.

## priorities.md

An ordered list. When two requirements cannot both hold, the higher one wins and the loss is a
deviation. Example: `1. never lose user data · 2. works offline · 3. 60 fps on mid phones · 4. visual polish`.

## Acceptance tests

Written in `super-goal plan`, red, before any feature code. Every `Verify: auto` requirement has
at least one. The test name carries its ids: `[R12] resumes at the checkpoint after a restart`.

| Platform | Where | Results file for `trace` |
|---|---|---|
| web | `e2e/acceptance/*.spec.ts` (Playwright) + unit where enough | Playwright `--reporter=junit` → `test-results/acceptance.xml` |
| android | `app/src/test/…/acceptance/` (JVM) · `app/src/androidTest/…/acceptance/` · `.maestro/acceptance/` | `app/build/test-results/**/*.xml`, `app/build/outputs/androidTest-results/**/*.xml`, `maestro test --format junit --output …` |
| unity | `Assets/Tests/Acceptance/EditMode`, `…/PlayMode` | `-testResults .sb-test/editmode.xml` / `playmode.xml` (NUnit 3) |

`goal.acceptance_command` runs them all and leaves the result files at `goal.results` (globs).
Config `goal.acceptance_paths` lists the folders lanes may not edit.

## Deviations

A file per entry, created by the lane that made the choice, committed in its PR:
`docs/goal/deviations/DV-<issue>-<k>.md`. One file each, so parallel PRs never conflict.

```markdown
# DV-34-1 — Save locally, sync when back online
Type: deviation
Refs: R12, D4
Prescribed: save to the cloud at every checkpoint (D4)
Realized: save locally at every checkpoint, upload when the network returns
Why: R12 (works offline) outranks D4 in priorities.md; cloud-first failed R12's second bullet
Reversible: yes — one ticket, the sync service is behind an interface
Evidence: PR #41, test [R12] resumes offline
```

| Type | When | `Prescribed:` |
|---|---|---|
| `deviation` | the result differs from a requirement, decision or acceptance test | what the spec said, quoted |
| `autonomous` | the spec said nothing and the choice is visible to a user or costly to undo | `nothing (spec silent on <topic>)` |

**Filter rule.** No file when the doubt was resolved and the result matches the spec, or when the
choice is invisible and cheap to change (variable names, file layout). `super-goal.py ledger`
rejects a deviation whose Prescribed and Realized say the same thing.
The Reviewer checks every PR: a behaviour that differs from the spec with no file is a Gap
finding; a file that is not a deviation is Scope drift.
