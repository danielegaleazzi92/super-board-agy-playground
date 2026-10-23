# super-goal plan · run · recap

The session that runs these is an orchestrator, exactly like `super-board run`: it measures,
files tickets and starts board runs. It NEVER builds, tests, reviews or merges itself.

## Config

In the active super-board config (`.claude/super-board/configs/<slug>.json`):

```json
"goal": {
  "spec_dir": "docs/goal",
  "acceptance_command": "npx playwright test e2e/acceptance --reporter=junit",
  "results": ["test-results/*.xml"],
  "acceptance_paths": ["e2e/acceptance/"],
  "autonomy": "decide-and-log",
  "max_iterations": 20,
  "max_stale_iterations": 3
}
```

`autonomy: "decide-and-log"` switches the lanes from "park the card when unsure" to "decide
by the spec and log it" (run.md → "Goal mode"). `"ask"` keeps super-board's normal ❓ blocks.

## Plan (interactive, once)

1. `vision.md` says `Status: draft` and the interview listed no open questions → go on;
   else ask for the missing answers first.
2. **Acceptance tests.** For every `Verify: auto` requirement write its tests at the layer
   `platforms.md` gives for the project's platform, named `[R<n>] …`, in `goal.acceptance_paths`.
   They must FAIL now (nothing is built) — run `goal.acceptance_command` and show it.
   A test that passes before any work proves nothing: rewrite it.
3. **Tickets.** One vertical slice per ticket, under the size cap, in super-board's ticket
   format (`docs/agents/issue-tracker.md`), plus one line in the body:
   `Implements: R<n>[, R<m>]`. Dependencies as `## Blocked by`. Use `to-tickets` when installed.
   File them on the board in `Backlog`.
4. Open one PR with the spec folder + acceptance tests; the user reviews and merges it.
   This is the approval: after the merge set `Status: approved` (in that PR) and move the
   tickets to `Ready`. From here the acceptance tests are read-only for lanes.

## Run (unattended)

One iteration:

```
1. Preconditions  vision.md Status: approved · config goal block · board onboarded · no other goal run
                  (lock: .claude/super-board/inflight/goal.lock, same create-or-fail as the wave lock)
2. Measure        run goal.acceptance_command (failures are expected, its exit code is not a halt)
                  gh issue list --state all --json number,title,state,body,labels --limit 500 > <tmp>/board.json
                  super-goal.py trace --dir <spec> --results <goal.results…> --board <tmp>/board.json --out <spec>/trace.json
3. Decide         exit 0  → every auto requirement met → Recap, stop ✅
                  exit 20 → only blocked / manual left  → Recap, stop 🙋
                  exit 10 → go on
4. Ticket gaps    for each id in needs_tickets: a requirement with failing or untested acceptance
                  and no open ticket. Read the failing test output, then file the smallest tickets
                  that make it pass (format as in Plan → 3), straight to Ready. Never re-file a
                  closed ticket's text: say what is still failing and why.
5. Build          super-board run --autonomous [--agy|--codex] [--low|--high] until its own done
                  condition (board drained or only Blocked left). Same flags every iteration;
                  `--autonomous=full` only when the user asked for it at plan time (decisions.md).
6. Ledger         super-goal.py ledger --dir <spec> — problems → one `tech-debt` ticket to fix the
                  files; never edit them from the orchestrator.
7. Progress       compare trace summaries: no new `met` in max_stale_iterations iterations, or
                  max_iterations reached → Recap, stop 🛑 with the requirements that did not move.
8. Loop to 2.
```

Report one block per iteration, in the session and appended to
`docs/super-board/runs/<date>-goal.md`:

```
Goal iteration 4 · 18/24 met · 3 failing · 1 untested · 2 manual · 5 deviations
  🆕 tickets #51 #52 (R14, R17) · 🙋 #47 waits for you (R9)
Next: super-board run (6 cards)
```

### Keeping it alive without a person

State is the board plus the spec folder, so a fresh session continues where the last one
stopped. Run an iteration per tick instead of one session for days:

| Host | Tick command (every hour) |
|---|---|
| Antigravity | `agy -p "/super-goal run --agy" --print-timeout 55m` |
| Claude Code | a scheduled Claude Code task / `/loop 1h /super-goal run`, or `claude -p "/super-goal run"` with `worker_backend: "claude-p"` |
| Codex | `codex exec "$super-goal run --codex"` |

Windows: Task Scheduler running Git Bash (`bash -lc "cd <repo> && <tick>"`); Linux/macOS: cron.
The goal lock makes an overlapping tick exit at once. A tick that finds the plan's usage guard
paused (`super-board-usage.sh check`) exits and waits for the next tick: the reset is free.
The machine needs the platform toolchain (platforms.md) and must stay awake.

## Recap

`python3 .claude/bin/super-board-decisions.py report --out <spec>/robot-decisions.md` first (every
decision the robot took instead of asking), then
`super-goal.py recap --dir <spec> --trace <spec>/trace.json --out <spec>/recap.md`, committed
with a `📝 [docs] goal: recap` PR, and printed to the user. Sections: requirements with status ·
deviations (only results that differ) · choices where the spec was silent · waiting for you ·
judge by hand · how to try, and a link to `robot-decisions.md` with its 🔴 count.
Nothing else: no list of doubts that changed nothing.
