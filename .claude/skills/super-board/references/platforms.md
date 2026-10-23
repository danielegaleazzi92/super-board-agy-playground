# Platform profiles — how a lane builds, tests and proves a change

Read by every lane (Builder, Tester, Reviewer) on every host (Claude, Codex, Antigravity).
The board, branches, PRs, comments and merge gate are the same on every platform. What
changes is **how you build, which test layer proves an AC, and what evidence you attach**.

The profile is config `platform` (config-schema.json). Absent = `web`. Onboard writes it from
`bash .claude/bin/super-board-platform.sh detect`; re-run that to see what it would suggest.

| Rule | Value |
|---|---|
| Commands | ALWAYS prefer `platform.commands.*` from the config over the defaults below |
| Merge | `verify_commands` (the merge gate) must hold the platform's `verify`. NEVER merge on a test you only ran in your worktree |
| Devices | `platform.devices` REPLACES the fixed 1920/1024/375 viewports in run.md's screenshot step |
| Shared machine resources | an emulator, a PlayMode editor: ALWAYS run under `super-board-platform.sh lock <resource> -- <command>`. Exit 75 = still busy after the wait: leave the card where it is, `failed` with detail `lock busy`, the next wave retries |
| Evidence path | `docs/super-board/runs/issue-<N>-qa-v<V>/` as on web; file names `<device>-<ac>-<step>.png` |
| Human-only | signing keys, store uploads, licenses, physical devices → `needs-you:` line in the PR body (merge gate exit 8) |

---

## web

Unchanged from run.md: unit/integration in the project's runner (Vitest, Jest), browser e2e in
Playwright only when the browser is the thing that broke (super-qa localisation ladder).

| Layer | Default command |
|---|---|
| verify | `npm ci --silent && npm run typecheck && npm run lint && npm test` (only scripts that exist) |
| e2e | `npm run test:e2e` or `npx playwright test` |
| screenshot | Playwright `page.screenshot()` per AC at each `platform.devices` size |

Next.js: build with `npm run build` before e2e when the Playwright config serves the production build.

---

## android

Kotlin / Gradle, Jetpack Compose or Views. Run Gradle with `--no-daemon` in worktrees: a
daemon per worktree eats memory and outlives the lane.

| AC kind | Layer (lowest that proves it) | Command |
|---|---|---|
| logic, view-model, repository | JVM unit test (JUnit, Turbine, MockK) | `./gradlew --no-daemon testDebugUnitTest` |
| Android framework without a device | Robolectric unit test | same task |
| a screen's look | screenshot test (Roborazzi / Paparazzi), JVM only | `./gradlew --no-daemon verifyRoborazziDebug` (record: `recordRoborazziDebug`) |
| UI behaviour on one screen | Compose UI test / Espresso, instrumented | `lock android-emulator -- ./gradlew --no-daemon connectedDebugAndroidTest` |
| a user flow across screens | Maestro flow in `.maestro/` | `lock android-emulator -- maestro test .maestro/<flow>.yaml` |
| static checks | lint (+ detekt / ktlint when configured) | `./gradlew --no-daemon lintDebug` |

**Evidence.** Prefer Roborazzi/Paparazzi images (deterministic, no emulator). Otherwise, under
the emulator lock: `adb exec-out screencap -p > <evidence>/<device>-<ac>.png`, one per AC per
device in `platform.devices` (`avd` names). A flow gets a short recording when it fails:
`adb shell screenrecord --time-limit 20 /sdcard/sb.mp4` then `adb pull`.

**Emulator.** One shared emulator, started outside the lane (`emulator -avd <name> -no-window
-no-snapshot-save`), waited on with `adb wait-for-device`. Tests that need a second device size
switch AVD under the same lock. A missing emulator is `🔐 missing tool` Blocked, not a test failure.

**Merge conflicts.** `gradle/libs.versions.toml` and `AndroidManifest.xml` conflict often: the
pre-flight sequences two cards touching them.

---

## unity

Unity Test Framework in batchmode. `UNITY_PATH` = the editor binary of the version in
`ProjectSettings/ProjectVersion.txt` (Windows `C:/Program Files/Unity/Hub/Editor/<ver>/Editor/Unity.exe`,
macOS `/Applications/Unity/Hub/Editor/<ver>/Unity.app/Contents/MacOS/Unity`).

| AC kind | Layer | Command |
|---|---|---|
| game rules, economy, save data, pure C# | EditMode test (NUnit) — move logic out of MonoBehaviours to test it here | `"$UNITY_PATH" -batchmode -nographics -projectPath . -runTests -testPlatform EditMode -testResults .sb-test/editmode.xml -logFile -` |
| behaviour in a scene, physics, input, UI | PlayMode test | `lock unity-playmode -- "$UNITY_PATH" -batchmode -projectPath . -runTests -testPlatform PlayMode -testResults .sb-test/playmode.xml -logFile -` |
| it builds | player build via an Editor build script | `"$UNITY_PATH" -batchmode -nographics -quit -projectPath . -executeMethod <Build.Method> -logFile -` |

- NEVER pass `-quit` with `-runTests`: the runner quits on its own and `-quit` can cut it short.
- The exit code is the verdict (non-zero = failures); attach the `-testResults` XML to the evidence.
- PlayMode screenshots: `ScreenCapture.CaptureScreenshot` inside the test, at each
  `platform.devices` resolution, saved under the evidence folder. `-nographics` gives black
  frames — leave it off for screenshot tests.

**Worktrees.** Every worktree needs its own `Library/` and a cold import can take a long time.
Right after creating the worktree, before the first editor run:
`bash .claude/bin/super-board-platform.sh seed-unity-library .claude/worktrees/issue-<N>-<lane>`.
NEVER commit `Library/`, `Temp/`, `Logs/`, `UserSettings/`.

**Merge conflicts.** Scenes (`.unity`), prefabs (`.prefab`) and `ProjectSettings/*.asset` are
YAML that git merges badly. Prefer prefabs and ScriptableObjects over scene edits; the pre-flight
sequences two cards touching the same scene or prefab instead of letting them race. Resolve
with UnityYAMLMerge, never by hand-editing fileIDs. `.meta` files always travel with their asset.

**Assets.** Binary assets go through Git LFS. A ticket that needs real art, audio or a store
listing is built with a clearly named placeholder and says so in the PR body; the asset itself
is a `needs-you:` step.
