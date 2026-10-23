# Swarm: parallel testers, one verdict (Tester, optional)

Fan N testers out over slices of the change, drain them, and return one aggregated handoff.
From pstack's `swarm`; here it is bounded to the Tester lane and off by default.

Use it when one Tester would otherwise walk every page and flow in sequence: a change that
touches several features of the project verifier's map, several ACs that exercise different
routes, or a `qa` card against a live URL with many page types.

## Config

```json
"qa": { "swarm": { "slices": 3 } }
```

`slices` 0 (default) = off. 1–6 = the maximum number of parallel testers. On Codex and
Antigravity lanes (no sub-agents) the slices run one after another, inline, with the same
briefs and the same aggregation; say `swarm: inline` in the handoff.

## Phase A: Frame

1. The done predicate is the card's ACs plus the test-gap check (super-qa → "Test-gap check");
   the artifact is the ordinary Tester handoff (run.md → Tester) with the aggregated table.
2. Cut the slices. Prefer, in order: features the project verifier selected for the changed
   paths (`super-board-project-verifier.py select`); page types or flows from
   `docs/super-qa/flows.md`; AC groups. Every AC lands in exactly one slice; a slice with no AC
   covers an adjacent path the diff may have broken (regression slice).
3. Each tester gets its own output directory under the run's scratch location and its own
   port or fixture reset when it drives the app. Testers never share a server, a queue or a
   screenshot folder (pstack: *separate before serializing shared state*).

## Phase B: Fan out

Every brief stands alone: the issue number, the branch and exact head SHA under test, the ACs
of its slice, how to launch and drive, what evidence to capture (screenshot embed format,
console/network errors), the `gh` budget (≤ 50 calls, prefer local git), and the report
format: `PASS` · `ISSUES` · `BLOCKED` with evidence. A tester that can prove a defect reports
`ISSUES` and lists every issue it can prove, not only the first.

Claude workflow lane: all testers in one message, read-only on the repo except their output
directory. Codex and Antigravity: the same briefs, one at a time.

## Phase C: Aggregate

- Drop a result that does not name the head SHA its brief gave it; rerun that slice once;
  a second miss is a **gap**. A gap never counts as a pass.
- Any `ISSUES` → the card fails QA: bounce per run.md → Tester with every proven issue in
  the `❌` comment (one `root-cause-hash` per distinct cause).
- Any `BLOCKED` with the others green → ordinary QA on that slice yourself before deciding;
  still blocked → Block template with the reason.
- All `PASS`, no gaps, test-gap check done → the ordinary pass handoff.

## Phase D: Handoff

The pass or fail comment keeps its required lines (`Local tests:`, per-AC proof, screenshots)
and adds:

```
Swarm: 3 slices · pass 2 · issues 1 · gaps 0 (inline on Antigravity)
| Slice | ACs | Result | Evidence |
|---|---|---|---|
| checkout | AC1, AC2 | PASS | <raw screenshot URL pinned to sha> |
| import csv | AC3 | ISSUES | e2e/import.spec.ts:41 · <URL> |
| regression: dashboard | – | PASS | <URL> |
```

Raw tester output stays in the run directory; the comment carries the table and one line per
issue, never the dumps.
