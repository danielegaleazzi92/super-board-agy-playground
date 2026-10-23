# Attack the premise (Builder rebuild)

When two fixes that share one premise have failed the same gate, suspect the premise, not the
fixes. Each failed fix is evidence against the belief it assumed; a third fix on that belief
spends the rebuild where the evidence already says the cause is not.

From pstack's `principle-attack-the-premise`. The board already measures "same cause" with the
`root-cause-hash` line (run.md → "Root-cause hash"): identical hash, same lane, two rounds in a
row is the trigger here, one round before the rebuild cap would park the card.

## When it fires

| Signal | Where you see it |
|---|---|
| Your `root-cause-hash` for this round equals the previous round's, same lane | the previous failure handoff comment on the PR |
| The Reviewer re-opened a finding as `❌ not fixed` for the second time | `<!-- super-review:report -->`, Status column |
| Tester's `❌` comment names the same AC that the last rebuild claimed fixed | the latest `[qa]` comment |

One signal is enough. No signal → ordinary rebuild (run.md → "Builder (rebuild)").

## Steps (before any code change)

1. **Write the premise down.** One sentence every failed fix assumed. "The flake comes from the
   debounce timing." "The 500 is the missing null check in `parse()`." Put it in the handoff
   comment as `premise: <sentence>` so the next round and the Reviewer can read it.
2. **Find an observation that would come out differently if the premise were false**, and make
   it. Look at how the failures are distributed (which inputs, which runs, which files), not
   only how large they are. A log line, a failing test on the untouched path, a `git bisect`,
   a run with the suspected component disabled.
3. **Script the check** when you can (`scripts/` or a test), so it reruns on the next round and
   the Reviewer can rerun it (pstack: *build the lever*, *prove it works*).
4. **Follow the evidence.**
   - Premise contradicted → the cause is elsewhere. Look for what the failures have in common
     that the premise did not predict. State the new premise, then fix that.
   - Premise confirmed → ask the next "why": the earlier fixes treated a consequence. Fix the
     cause, and remove the condition instead of compensating for it (a cleanup that runs on
     every request leaves the cause in place).
5. **Record the result** in the `[builder] [report]` comment: `premise:` (kept or replaced),
   `premise-check:` (the observation, one line, with the command or file:line), then the fix.

## Stop rules

- Do not start the next fix before the premise is written down and tested.
- A rebuild that hits the rebuild cap (`config.rebuild_cap`) with the same hash goes to Blocked
  with the Block template; the `premise:` and `premise-check:` lines go in "What I tried", so the
  human starts from the tested premise, not from zero.
- The premise is about a fact the code assumes. A requirement that changed is design-preflight's
  question, not this one.
