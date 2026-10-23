# `super-board catchup` — what happened since you last looked

Read-only. Rebuilds where the board stands from the board itself (GitHub, the run manifests,
the decision records) and hands back a short brief in plain words, so you can act without
rereading every comment. From pstack's `recall` and `ketchup`; the board is the shared record
here, so no chat history is read.

Use it at the start of a session, after an unattended `run`, or whenever the kanban box of
`super-board status` is not enough to decide what to do next. On Antigravity, where a new
session starts with no memory of the last one, it is the first command of the day.

## Arguments

`super-board catchup [<slug>] [--since <YYYY-MM-DD | 7d | last-run>]`

- `<slug>`: the config, as for `status`. Default: the sole config or the active marker.
- `--since`: the window. Default `last-run` = the start time of the newest manifest in
  `paths.runs_dir` (`docs/super-board/runs/`), else the last 7 days.

## Gather (≤ 20 `gh` calls, REST; never a sleep loop)

1. `python3 .claude/bin/super-board-status.py [<slug>]` for the columns and in-flight workers.
2. Merged PRs in the window: `gh pr list --state merged --search "merged:>=<date>" --json number,title,mergedAt,url`.
3. Blocked cards and their reason: the board's Blocked column, then the latest Block template
   comment on each (its last line `blocked-by:` and the reason emoji: 🙋 ❓ 🧑 🎨 👯 🛡 🔐 💳 🔑).
4. Bounces: open issues with a `loop:rebuild-N` label, and the latest `<!-- super-review:report -->`
   on their PR (round, `❌ not fixed` rows).
5. Decisions the robot took: `python3 .claude/bin/super-board-decisions.py report --since <date>`
   (label `auto-decided`), highest risk first.
6. Spec state when `config.goal` is set: `python3 .claude/bin/super-goal.py trace` (requirements
   passing / open) and `docs/goal/deviations/`.
7. Halts: `.claude/super-board/github-halt.json`, a `*-wave.pid` or lane lock that is older than
   the newest manifest (a stopped run that was not resumed).

Check every number you show against the source it came from; say so when you corrected one.

## Brief (the output contract)

Lead with the capsule, then the threads, then the problems, then the next move. Cut detail
before you cut threads.

- **Capsule.** At most 5 bullets: what the board did in the window, where it stands now.
- **Threads.** One line per card, each prefixed with exactly one tag:
  `[merged #N]` · `[open PR #N]` · `[in QA #N]` · `[in review #N]` · `[bounced #N round R]` ·
  `[blocked 🙋 #N]` (or the reason emoji) · `[decided 🤖 #N]` · `[ready #N]`.
  A card with no tag is not done; tag it.
- **Problems.** At most 5, the recurring ones: the same `root-cause-hash` twice, a card that
  bounced more than once, a halt, a quota pause, a 🙋 that has waited longest.
- **Next move.** The single most useful action, concrete: `comment done on #12`, `run
  /super-board run`, `review the 🔴 decision on #18`, `repair verify_commands`.

## Voice

Plain words, short sentences, like one person catching another up. Say what changed for the
user, not how the board did it: "the import feature is merged", not "lane chain completed".
Leave out hashes, file paths and commands unless the reader needs one to act. Call cards by
their title, with the number once. No "TL;DR", no preamble, no summary of the summary.

## Never

- Never write to GitHub, the config, or the board. No moves, no comments, no labels.
- Never start a run, a worker or the app.
- Never rebuild the brief from memory: every line comes from a source gathered above.
