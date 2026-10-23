# /super-goal

Drive a whole project to a written spec with one run, on top of [super-board](../super-board/README.md).

1. `/super-goal interview` — an exhaustive questionnaire becomes `docs/goal/`: requirements `R1…`,
   every answer as a decision `D1…`, priorities.
2. `/super-goal plan` — acceptance tests tagged `[R<n>]`, red; tickets with `Implements: R<n>`.
   You merge the spec PR: that is the approval.
3. `/super-goal run [--agy|--codex]` — measure, ticket what is unmet, let the board build it,
   measure again, until every requirement passes or only your decisions are left.
4. `docs/goal/recap.md` — what differs from the spec and why, choices made where it was silent,
   what waits for you, what to judge by hand, how to try it.

"Done" is `super-goal.py trace` exit 0 over real test results, never an agent's opinion.
Web, Android and Unity ([platforms](../super-board/references/platforms.md)).
