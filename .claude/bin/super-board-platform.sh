#!/usr/bin/env bash
# super-board-platform.sh — what kind of project is this, and how does a lane build, test
# and capture evidence for it. Web stays the default and keeps Playwright; Android and
# Unity get their own test layers, devices and shared-resource locks.
#
#   detect [--root DIR]                  print the platform profile as JSON (read only)
#   lock <resource> [--wait SECONDS] -- <command…>
#                                        run <command> holding a machine-wide lock on
#                                        <resource> (android-emulator, unity-editor, …):
#                                        one emulator or editor run at a time across every
#                                        worktree of this repo. Exit = the command's exit;
#                                        75 when the lock is still held after --wait (default 1800).
#   seed-unity-library <worktree>        copy the main checkout's Unity Library/ into a new
#                                        worktree before its first open: a cold import costs
#                                        minutes to hours per worktree. No-op if present.
#
# The profile is what onboard writes to config `platform` and what lanes read
# (references/platforms.md). `detect` prints:
#   {"kind":"web|android|unity|unknown", "framework":…, "signals":[…],
#    "commands":{"verify":…, "unit":…, "ui":…, "e2e":…, "build":…, "screenshot":…},
#    "devices":[…], "exclusive":[…], "size_exclude":[…], "permissions":[…], "prerequisites":[…]}
# Commands are suggestions built from what is in the repo; onboard shows them before saving.
set -euo pipefail
exec python3 - "$@" <<'PY'
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], text=True, cwd=cwd, stderr=subprocess.DEVNULL).strip()

def read(path):
    try:
        return path.read_text(errors='replace')
    except OSError:
        return ''

def web(root):
    pkg = json.loads(read(root / 'package.json') or '{}')
    deps = {**(pkg.get('dependencies') or {}), **(pkg.get('devDependencies') or {})}
    scripts = pkg.get('scripts') or {}
    pm, install = 'npm', 'npm ci --silent'
    if (root / 'pnpm-lock.yaml').exists():
        pm, install = 'pnpm', 'pnpm install --frozen-lockfile'
    elif (root / 'yarn.lock').exists():
        pm, install = 'yarn', 'yarn install --frozen-lockfile'
    elif (root / 'bun.lockb').exists() or (root / 'bun.lock').exists():
        pm, install = 'bun', 'bun install --frozen-lockfile'
    run = lambda s: f'{pm} run {s}'
    checks = [run(s) for s in ('typecheck', 'lint', 'test') if s in scripts]
    framework = 'next' if 'next' in deps else 'vite' if 'vite' in deps else 'node'
    playwright = '@playwright/test' in deps
    e2e = run('test:e2e') if 'test:e2e' in scripts else ('npx playwright test' if playwright else None)
    return dict(kind='web', framework=framework,
                signals=['package.json'] + (['next'] if framework == 'next' else []) + (['@playwright/test'] if playwright else []),
                commands=dict(verify=' && '.join([install] + checks) if checks else install,
                              unit=run('test') if 'test' in scripts else None, ui=None, e2e=e2e,
                              build=run('build') if 'build' in scripts else None,
                              screenshot='Playwright page.screenshot() inside the e2e spec' if playwright else None),
                devices=[dict(name='desktop', size='1920x1080'), dict(name='tablet', size='1024x768'),
                         dict(name='mobile', size='375x667')],
                exclusive=[], size_exclude=[],
                permissions=[f'command({pm})', 'command(npx playwright)'] if playwright else [f'command({pm})'],
                prerequisites=['node'] + (['npx playwright install --with-deps (browsers)'] if playwright else []))

def android(root):
    build_text = '\n'.join(read(p) for p in list(root.glob('*.gradle*')) + list(root.glob('*/build.gradle*'))
                           + list(root.glob('gradle/libs.versions.toml')))
    gradlew = './gradlew' if (root / 'gradlew').exists() else 'gradle'
    has = lambda *words: any(w in build_text for w in words)
    lint = [t for t, words in (('detekt', ('detekt',)), ('ktlintCheck', ('ktlint',))) if has(*words)]
    roborazzi, paparazzi = has('roborazzi'), has('paparazzi')
    maestro = (root / '.maestro').is_dir()
    screenshot = (f'{gradlew} --no-daemon verifyRoborazziDebug (record: recordRoborazziDebug)' if roborazzi
                  else f'{gradlew} --no-daemon verifyPaparazziDebug (record: recordPaparazziDebug)' if paparazzi
                  else 'adb exec-out screencap -p > <evidence>/<device>-<step>.png (under the emulator lock)')
    return dict(kind='android', framework='compose' if has('compose') else 'views',
                signals=['settings.gradle', 'com.android'] + (['maestro'] if maestro else []),
                commands=dict(verify=' '.join([gradlew, '--no-daemon', 'testDebugUnitTest', 'lintDebug'] + lint),
                              unit=f'{gradlew} --no-daemon testDebugUnitTest',
                              ui=f'bash .claude/bin/super-board-platform.sh lock android-emulator -- {gradlew} --no-daemon connectedDebugAndroidTest',
                              e2e='bash .claude/bin/super-board-platform.sh lock android-emulator -- maestro test .maestro' if maestro else None,
                              build=f'{gradlew} --no-daemon assembleDebug', screenshot=screenshot),
                devices=[dict(name='phone', avd='<your phone AVD>', size='1080x2400'),
                         dict(name='tablet', avd='<your tablet AVD>', size='2560x1600')],
                exclusive=['android-emulator'],
                size_exclude=['**/gradle.lockfile'],
                permissions=[f'command({gradlew})', 'command(adb)', 'command(emulator)']
                            + (['command(maestro)'] if maestro else []),
                prerequisites=['JDK 17+', 'Android SDK (ANDROID_HOME)', 'a running emulator or `emulator -avd <name> -no-window`']
                              + (['maestro CLI'] if maestro else []))

def unity(root):
    version = re.search(r'm_EditorVersion:\s*(\S+)', read(root / 'ProjectSettings/ProjectVersion.txt'))
    version = version.group(1) if version else None
    editor = '"$UNITY_PATH"'
    base = f'{editor} -batchmode -projectPath . -logFile -'
    lfs = 'filter=lfs' in read(root / '.gitattributes')
    has_build_script = any('BuildPipeline.BuildPlayer' in read(p) for p in root.glob('Assets/**/Editor/*.cs'))
    return dict(kind='unity', framework=f'unity {version}' if version else 'unity',
                signals=['ProjectSettings/ProjectVersion.txt'] + (['git-lfs'] if lfs else []),
                commands=dict(
                    verify=f'{base} -nographics -runTests -testPlatform EditMode -testResults .sb-test/editmode.xml',
                    unit=f'{base} -nographics -runTests -testPlatform EditMode -testResults .sb-test/editmode.xml',
                    ui=f'bash .claude/bin/super-board-platform.sh lock unity-playmode -- {base} -runTests -testPlatform PlayMode -testResults .sb-test/playmode.xml',
                    e2e=None,
                    build=(f'{base} -nographics -quit -executeMethod <YourBuildScript.Method>' if has_build_script
                           else f'{base} -nographics -quit -executeMethod <add an Editor build script>'),
                    screenshot='ScreenCapture.CaptureScreenshot in a PlayMode test, saved under the evidence folder'),
                devices=[dict(name='desktop', size='1920x1080'), dict(name='phone-landscape', size='2400x1080')],
                exclusive=['unity-playmode'],
                size_exclude=['**/*.meta', '**/Packages/packages-lock.json'],
                permissions=['command($UNITY_PATH)'] + ([f'command({os.environ["UNITY_PATH"]})'] if os.environ.get('UNITY_PATH') else []),
                prerequisites=[f'Unity {version or "<version>"} installed; UNITY_PATH points at its editor binary',
                               'an activated Unity license usable in batchmode',
                               'Git LFS for binary assets' + ('' if lfs else ' — not configured in .gitattributes'),
                               'UnityYAMLMerge set as the merge tool for .unity/.prefab',
                               'seed each new worktree: super-board-platform.sh seed-unity-library <worktree>'],
                unity_version=version)

def detect(root):
    if (root / 'ProjectSettings/ProjectVersion.txt').exists():
        return unity(root)
    gradle = any((root / n).exists() for n in ('settings.gradle', 'settings.gradle.kts'))
    if gradle and (any(root.glob('*/src/main/AndroidManifest.xml')) or 'com.android' in
                   '\n'.join(read(p) for p in list(root.glob('*/build.gradle*')) + list(root.glob('gradle/libs.versions.toml')))):
        return android(root)
    if (root / 'package.json').exists():
        return web(root)
    return dict(kind='unknown', framework=None, signals=[], commands={}, devices=[], exclusive=[],
                size_exclude=[], permissions=[], prerequisites=['set config platform by hand (references/platforms.md)'])

def pid_alive(pid):
    if os.name == 'nt':  # os.kill(pid, 0) TERMINATES the process on Windows
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def lock(argv):
    if '--' not in argv or argv.index('--') < 1 or not argv[argv.index('--') + 1:]:
        sys.exit('usage: super-board-platform.sh lock <resource> [--wait S] -- <command…>')
    head, command = argv[:argv.index('--')], argv[argv.index('--') + 1:]
    resource = head[0]
    if not re.fullmatch(r'[A-Za-z0-9._-]+', resource):
        sys.exit('lock resource must be a plain name like android-emulator')
    wait = int(head[head.index('--wait') + 1]) if '--wait' in head else 1800
    # The git common dir is shared by every worktree of the repo; the lock lives there so
    # a QA lane in .claude/worktrees/issue-7-qa and one in issue-9-qa see the same lock.
    common = Path(git('rev-parse', '--git-common-dir')).resolve()
    path = common / 'super-board-locks' / resource
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + wait
    while True:
        try:
            path.mkdir()
            (path / 'owner').write_text(f'{os.getpid()}\n{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}\n')
            break
        except FileExistsError:
            owner = read(path / 'owner').split()
            if owner and owner[0].isdigit() and not pid_alive(int(owner[0])):
                shutil.rmtree(path, ignore_errors=True)  # stale: its holder is gone
                continue
            if time.time() > deadline:
                print(f'super-board-platform: {resource} still locked by {" ".join(owner) or "?"} after {wait}s', file=sys.stderr)
                sys.exit(75)
            time.sleep(5)
    if os.name == 'nt':
        # Windows cannot exec a shell script (./gradlew) directly, and a bare 'bash' resolves
        # to System32\bash.exe (WSL) before PATH: use the PATH bash (Git Bash) explicitly.
        command = [shutil.which('bash') or 'bash', '-c', ' '.join("'" + a.replace("'", "'\\''") + "'" for a in command)]
    try:
        sys.exit(subprocess.call(command))
    finally:
        shutil.rmtree(path, ignore_errors=True)

def seed(argv):
    if len(argv) != 1:
        sys.exit('usage: super-board-platform.sh seed-unity-library <worktree>')
    worktree = Path(argv[0]).resolve()
    main = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir')).resolve().parent
    source, target = main / 'Library', worktree / 'Library'
    if target.exists():
        print(f'✓ {target} already present')
        return
    if not source.is_dir():
        print(f'… no Library/ in {main}: the first open imports from scratch')
        return
    shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns('*.lock', 'Bee', 'il2cpp_cache'))
    print(f'✓ seeded {target} from {source}')

argv = sys.argv[1:]
verb = argv[0] if argv else ''
if verb == 'detect':
    root = Path(argv[argv.index('--root') + 1] if '--root' in argv else '.').resolve()
    print(json.dumps(detect(root), indent=2))
elif verb == 'lock':
    lock(argv[1:])
elif verb == 'seed-unity-library':
    seed(argv[1:])
else:
    print('usage: super-board-platform.sh detect [--root DIR] | lock <resource> [--wait S] -- <cmd…> | seed-unity-library <worktree>', file=sys.stderr)
    sys.exit(64)
PY
