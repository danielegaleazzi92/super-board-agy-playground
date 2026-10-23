# Principles the board applies, and where

Engineering principles from Lauren Tan's [pstack](https://github.com/cursor/plugins/tree/main/pstack)
(Cursor) and its [Claude Code port](https://github.com/michael-denyer/pstack-claude), folded into
the lanes. They live in references, not in AGENTS.md or a system prompt: a lane loads one when
its step fires, so every message does not pay for all of them (pstack: *guard the context window*).

| Principle | One line | Fires in | Reference |
|---|---|---|---|
| Attack the premise | Two fixes that share one premise failed the same gate → write the premise down and test it before the third fix | Builder rebuild · rebuild-cap gate · Tester rebuild | [super-build → attack-the-premise.md](../../super-build/references/attack-the-premise.md) |
| Type-system discipline | Make impossible states unrepresentable; parse external data at the boundary; brand ids that must not mix | Builder code shape · Reviewer lens | [super-build → type-discipline.md](../../super-build/references/type-discipline.md) |
| No comments · clean the diff | Narrating comments, swallowed errors, untyped values and deep nesting leave before the PR opens; behaviour proved unchanged by the tests | Builder before the draft PR · Reviewer | [super-build → clean-the-diff.md](../../super-build/references/clean-the-diff.md) |
| Attack the diff (interrogate) | Independent reviewers try to break the change; the lead sorts findings into Act on · Consider · Noted · Dismissed | Reviewer, per `interrogate.trigger` | [super-review → interrogate.md](../../super-review/references/interrogate.md) |
| Swarm | Parallel testers on slices, one aggregated verdict; a gap never counts as a pass | Tester, per `qa.swarm` | [super-qa → swarm.md](../../super-qa/references/swarm.md) |
| Prove it works | Check the real artifact, not a proxy; script the check so a reviewer can rerun it | Tester evidence · project verifier · Reviewer rerun | [super-qa → project-verifier.md](../../super-qa/references/project-verifier.md) · run.md → Tester |
| Exhaust the design space | Two genuinely different shapes before a choice that is expensive to reverse | lint · Builder rung 3 | [design-preflight.md](design-preflight.md) |
| Encode lessons in structure | A recurring mistake is fixed at the boundary that allowed it: architecture, then types, then lint, then a test; prose last | super-collect `prs` | [super-collect → correction-prevention.md](../../super-collect/references/correction-prevention.md) |
| Reflect | After a verified run, route bounded lessons into existing skill files, never silently | post-run calibration | [calibration.md](calibration.md) |
| Never block on the human | Reversible decisions proceed with a record; irreversible ones still wait | `run --autonomous[=full]` | [block-template.md → Autonomous mode](block-template.md) |
| Keep it small | One card, one PR under the size cap; split past it, never pad | Builder · merge policy | super-build → "Keep each PR small" |
| Catch up | Plain-words brief of what the board did since you last looked, before you act | `super-board catchup` | [catchup.md](catchup.md) |

What the board deliberately does not take from pstack: its planning skills (brownfield-only;
tickets come from `/super-goal`, `/to-tickets` and `super-collect`), the `poteto-mode` router
(the five verbs route here), and `babysit` (the merge gate, rebase pass, CI check and
review-thread protocol already shepherd every PR to merge).

Rules for adding a principle: one reference per principle, loaded by the step that needs it;
a row here; no copy into AGENTS.md. A principle that nothing in a lane reads is not adopted.
