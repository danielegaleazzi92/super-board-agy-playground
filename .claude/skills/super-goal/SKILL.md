---
name: super-goal
description: Drive a whole project to a written spec with one run. An exhaustive interview turns the idea into a spec folder (requirements R1…, every answer as a decision D1…, priorities); acceptance tests tagged [R<n>] become the finish line; then a loop files tickets for every unmet requirement, lets super-board build, test, review and merge them, re-measures, and repeats until every requirement is met or only human decisions remain. Doubts met during development are decided by the spec's priorities and logged; the final recap lists only what differs from the spec, the choices made where it was silent, and what waits for you. Web, Android and Unity; Claude, Codex or Antigravity lanes. Use when the user says "super-goal", "/super-goal", "build the whole project from the spec", "spec-driven run", "run until the spec is met", or "interview me and build it".
---

# super-goal — from a spec to a finished product, in one run

Four verbs. State lives in the spec folder (`goal.spec_dir`, default `docs/goal/`) and on the
super-board board, never in this session.

| Verb | Where | What it does |
|---|---|---|
| `super-goal interview` | interactive | exhaustive questionnaire → spec folder, `Status: draft` |
| `super-goal plan` | interactive | spec → acceptance tests tagged `[R<n>]` (red) + tickets; you approve → `Status: approved` |
| `super-goal run [--agy\|--codex] [--low\|--high]` | unattended | the loop: measure → ticket the gaps → `super-board run` → measure … → recap |
| `super-goal recap` | any | rebuild `docs/goal/recap.md` from the last trace and the ledger |

No verb → ask which one. In Codex: `$super-goal <verb>`; in Antigravity: `/super-goal <verb>`.

## Routing

| If user says | Load |
|---|---|
| `super-goal interview` | `references/interview.md` |
| `super-goal plan` | `references/spec-format.md` → "Acceptance tests", then `references/loop.md` → "Tickets" |
| `super-goal run` / "resume the goal" | `references/loop.md` |
| `super-goal recap` | `references/loop.md` → "Recap" |
| spec, decision or deviation file format | `references/spec-format.md` |

## Rules

| Rule | Value |
|---|---|
| Finish line | `super-goal.py trace` over the acceptance-test results. "Done" is its exit 0, NEVER an agent's opinion |
| Acceptance tests | written in `plan`, approved by the user, then READ-ONLY for lanes (`goal.acceptance_paths`). A lane that cannot pass one logs a deviation; it NEVER edits the test |
| Doubts while building | decide by `decisions.md`, then `priorities.md`, then repo precedent, then the smallest reversible choice — and log it (`spec-format.md` → "Deviations"). NEVER park a card for a doubt the spec answers |
| Still a human's | irreversible choices, money, auth, destructive schema, legal/licensing, store accounts, signing, paid assets → Blocked 🙋 as super-board does; the loop goes on around them |
| The ledger | one file per entry in `deviations/`, only when the result differs from the spec or the spec was silent. Same result = no entry |
| Board | super-board does every build, test, review and merge. super-goal NEVER builds or merges itself |
| Spec changes | only the user changes `requirements.md` / `decisions.md` / acceptance tests after approval |
| Scripts | `python3 .claude/skills/super-goal/scripts/super-goal.py init / trace / ledger / recap` |
