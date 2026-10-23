# Clean the diff (Builder, before the draft PR)

The last step before `git push` on a first pass or a rebuild: read your own merge-base diff
(`git diff origin/<base>...HEAD`) and remove what an agent writes and a reviewer pays for.
Behaviour stays the same; the tests prove it. From pstack's `no-comments`, `unslop` and the
`Comment Sicko` agent, bounded to the board's rules.

## What leaves

| Smell | Why | Do instead |
|---|---|---|
| Comments that narrate the code (`// increment the counter`, `// call the API`) | a reader skims comments instead of code; when they drift, the model follows the comment and ships the wrong behaviour | delete; the code is the explanation |
| `// IMPORTANT`, `// do not remove`, `// fine for now` without a reason code cannot express | a claim, not a constraint | encode it: a type, an assertion, a test, a lint rule; then delete the sentence |
| Commented-out code, banners, section dividers | dead weight the next agent copies | delete |
| `try/catch` that swallows or only re-logs | hides the failure the AC asked to handle | let it propagate, or handle it with the project's error type and a test for that path |
| `any`, casts, `@ts-ignore`, `eslint-disable` added by this PR | the type system was telling you something | see [type-discipline.md](type-discipline.md); a suppression survives only for a rule that is style-only, with its reason on the same line |
| Nesting deeper than three levels, flags that switch a function between two jobs | spaghetti growth | early return, split the function, one job each |
| A helper, abstraction, option or dependency the AC did not need | over-engineering; the Reviewer will file it anyway | the ponytail ladder: needed at all? in the codebase? stdlib? native? one line? |
| Noise in generated files, lockfiles, snapshots that the change did not require | review time, size cap | revert them |

## What stays

- License and legal headers.
- Doc comments that define a public API contract.
- A link to the issue, ADR or vendor doc that explains a constraint the code cannot express
  (one line, with the reference, no sermon).
- `// prettier-ignore` and similar formatter pragmas.
- Behaviour forced by a dependency, platform or protocol you cannot change: keep the shortest
  comment that names the external cause.

Doubt is not a reason to keep a comment. Doubt about *code* is: never change behaviour in this
step. If the cleanup needs a shape change, it is a ticket, not a last-minute refactor.

## Steps

1. Diff against the merge base. Walk every hunk once with the table above.
2. Apply the removals. Rerun the ticket's tests (and the project's lint/typecheck): green means
   behaviour held. Red means you changed behaviour: revert that cleanup and move on.
3. Rerun `git diff --shortstat` against the size cap (super-build → "Keep each PR small").
4. One line in the PR `history` block: `cleaned: <n> comments, <n> suppressions, <what else>` or
   `cleaned: nothing to remove`. No file list.
5. A constraint you could not encode in scope → a sentence in the PR `risk` block naming it, so
   the Reviewer can decide, and a `## Fix` line for a follow-up ticket if it matters.

The Reviewer reads the same table: a narrating or contradicting comment that survived, or a
swallowed error, is a **Should fix** finding (class Over-engineering for extra building, Bug when
the swallowed path is one the AC covers). It never blocks a merge on its own.
