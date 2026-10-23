# super-goal interview — exhaustive questionnaire to a draft spec

Interactive. The goal is a spec complete enough that the run never needs to ask. Every answer
is written down as it is given, so a stopped interview resumes where it left off.

## Steps

1. `python3 .claude/skills/super-goal/scripts/super-goal.py init --dir <goal.spec_dir>`.
2. Read what exists: README, AGENTS.md, `docs/super-board/PROJECT.md`, the code tree,
   `.claude/bin/super-board-platform.sh detect`. An existing project is interviewed about the
   change, not about what the code already answers.
3. Walk the areas below in order. One question at a time with `AskUserQuestion` (≤ 4 options,
   recommended first, "Other" for free text). After each answer append `## D<n>` to
   `decisions.md` at once.
4. After each area, write or update the `## R<n>` requirements it produced and read them back in
   one short list: "R7–R11 from this area — anything missing or wrong?"
5. Close with `priorities.md`: ask the user to order the 4–8 qualities that came up
   (data safety, offline, performance, polish, scope, time).
6. Show the counts (`n requirements · n decisions · n manual`) and the open questions you could
   not settle. Leave `Status: draft`. Next: `super-goal plan`.

## Areas

| # | Area | Must settle |
|---|---|---|
| 1 | Vision | the one-line goal, who it is for, what success looks like, what is OUT of scope |
| 2 | Platform | web / Android / Unity (and targets: browsers, min Android API, Unity version, devices, orientations) |
| 3 | Users and flows | each user type, each main flow step by step, first-run experience, empty states |
| 4 | Features | per feature: inputs, outputs, rules, limits, errors and what the user sees for each |
| 5 | Data | what is stored, where, for how long, offline behaviour, sync, migration from old data, export |
| 6 | UI and feel | navigation, layout per device, accessibility, language(s), tone, references the user likes |
| 7 | Game (Unity) | core loop, controls, progression, economy numbers, save points, difficulty, win/lose, session length |
| 8 | Non-functional | performance numbers, battery, app size, security, privacy, analytics events |
| 9 | Assets | art, audio, fonts, icons: who supplies them, placeholders allowed, licences |
| 10 | Release | store accounts, signing, versioning, what "done" means for the first release |

Skip an area only when the platform makes it moot, and say so in `decisions.md`.

## Rules

- NEVER invent an answer. A question the user defers becomes `Choice: open` and is listed at step 6.
- Prefer numbers to adjectives: "under 2 s", "50 levels", "3 lives", never "fast", "many".
- A requirement the user calls subjective gets `Verify: manual`, and you ask what would make it
  testable before accepting that.
- Mirror the user's language in questions; write the spec files in the project's language
  (AGENTS.md → UI language / code language).
