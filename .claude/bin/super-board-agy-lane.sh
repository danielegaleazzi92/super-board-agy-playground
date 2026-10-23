#!/usr/bin/env bash
# One headless lane on Google Antigravity (`agy -p`). Mirrors super-board-codex-lane.sh:
# --agy is the run owner's explicit opt-in; without it, usage fallback may build/test
# but must never own a review or merge. Without --agy the board config must say
# "usage_fallback": "agy" (exit 78 otherwise).
# Usage: --config f --card '<JSON>' --lane build|qa|review [--agy[=model]]
#        [--tier low|medium|high] [--complexity low|medium|high]
# Model:  --agy=<model>, else agy.model, else agy.ladder[tier][complexity], else the CLI default.
# Effort: agy.effort, else AGY_EFFORT[tier][complexity] (review: high), passed as --effort.
#
# HOW agy IS CALLED (antigravity.google/docs/cli/headless):
#   agy -p <prompt> --output-format json --json-schema <file> --print-timeout <agy.timeout>
#   [--model <slug>] [--effort low|medium|high]
# The lane result is the run's `structured_output`; status other than SUCCESS fails closed.
# agy has no working-directory flag: this script chdirs to the repo root first.
# Headless agy soft-denies un-allowed shell commands and still exits 0, with a warning
# on stderr. The lane counts those warnings and names them in `detail`, so a lane that
# "advanced" without being allowed to run gh/git/tests is visible in the wave report.
# Allow the board's commands once with super-board-agy-permissions.py.
set -euo pipefail
exec python3 - "${BASH_SOURCE[0]}" "$@" <<'PY'
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

def fail(message, code=64):
    print(message, file=sys.stderr)
    sys.exit(code)

parser = argparse.ArgumentParser(description='Run one Antigravity board lane (agy -p).')
parser.add_argument('--config', required=True)
parser.add_argument('--card', required=True, help='card JSON or a JSON file')
parser.add_argument('--lane', required=True, choices=['build', 'qa', 'review'])
parser.add_argument('--tier', choices=['low', 'medium', 'high'], help='run ladder (--low / default / --high)')
parser.add_argument('--complexity', choices=['low', 'medium', 'high'], help="router's grade for this card")
parser.add_argument('--autonomy', choices=['ask', 'decide', 'full'],
                    help='run --autonomous[=full]; default: config autonomy, else ask')
raw = sys.argv[2:]
explicit = False
model = None
rest = []
for arg in raw:
    if arg == '--agy':
        explicit = True
    elif arg.startswith('--agy='):
        explicit = True
        model = arg.partition('=')[2]
        if not model.strip():
            fail('--agy=<model> requires a non-empty model')
    else:
        rest.append(arg)
args = parser.parse_args(rest)
script_path = Path(sys.argv[1]).resolve()
if args.lane == 'review' and not explicit:
    fail('Antigravity review refused: run must be started with explicit --agy; usage fallback cannot review.', 78)

# Effort ladder: run tier x card grade -> --effort. Mirrors the Claude LADDERS in
# workflows/super-board-wave.js in spirit: cheap for easy cards, high for hard ones.
AGY_EFFORT = {
    'low': {'low': 'low', 'medium': 'low', 'high': 'medium'},
    'medium': {'low': 'medium', 'medium': 'medium', 'high': 'high'},
    'high': {'low': 'high', 'medium': 'high', 'high': 'high'},
}
try:
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text())
    card = json.loads(args.card if args.card.lstrip().startswith('{') else Path(args.card).read_text())
    if not isinstance(config, dict) or not isinstance(card, dict):
        raise ValueError('config/card must be objects')
    if type(card.get('number')) is not int or card['number'] < 1 or not isinstance(card.get('status'), str):
        raise ValueError('card needs a positive issue number and status')
    agy = config.get('agy') or {}
    if not isinstance(agy, dict):
        raise ValueError('agy must be an object')
    configured = agy.get('model')
    if configured is not None and not isinstance(configured, str):
        raise ValueError('agy.model must be a string')
    ladder = agy.get('ladder') or {}
    if not isinstance(ladder, dict):
        raise ValueError('agy.ladder must be an object {tier: {complexity: model}}')
    if model is None and configured and configured.strip():
        model = configured
    if model is None and args.tier:
        cell = (ladder.get(args.tier) or {}).get(args.complexity or 'medium')
        model = cell if isinstance(cell, str) and cell.strip() else None
    effort = agy.get('effort')
    if effort is not None and effort not in ['low', 'medium', 'high']:
        raise ValueError('agy.effort must be low, medium or high')
    if effort is None:
        effort = 'high' if args.lane == 'review' else AGY_EFFORT[args.tier or 'medium'][args.complexity or 'medium']
    timeout = str(agy.get('timeout') or '120m')
    if not re.fullmatch(r'\d+[smh]', timeout):
        raise ValueError('agy.timeout must look like 90m, 2h or 600s')
except (OSError, ValueError, AttributeError) as error:
    fail(f'Invalid Antigravity lane input: {error}')
# Without --agy this is the usage fallback, and that is opt-in per board.
if not explicit and config.get('usage_fallback', 'none') != 'agy':
    fail(f'Antigravity fallback refused: usage_fallback is not "agy" in {config_path}; pass --agy for an explicit Antigravity run.', 78)

column = card['status']
def result(status, detail):
    print(json.dumps({'status': status, 'column': column, 'detail': detail}))

readiness = script_path.with_name('super-board-verification-ready.py')
def require_verification_ready():
    if subprocess.run([sys.executable, str(readiness), '--config', str(config_path)]).returncode:
        result('halted', 'verification-readiness: repair verify_commands; preserve claims, worktrees and card state, then restart explicitly')
        sys.exit(9)
require_verification_ready()

try:
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
except (subprocess.CalledProcessError, OSError):
    fail('Antigravity lane must start inside the target git repository')
os.chdir(root)
helper = script_path.with_name('super-board-github-read.py')
if not helper.exists() or subprocess.run([sys.executable, str(helper), '--check']).returncode:
    result('halted', 'required GitHub reads halted or helper missing; preserve claims and worktrees')
    sys.exit(79)

# Antigravity finds skills in .agents/skills/ and reads .claude/skills/ files on instruction
# (host "agy" in the resolver). The same readiness contract as Codex: exit 10 halts the lane.
resolver_path = script_path.with_name('super-board-skills-ready.py')
try:
    spec = importlib.util.spec_from_file_location('skills_ready', resolver_path)
    resolver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resolver)
    resolver.hydrate([card], root)
    skills = resolver.report(root, 'agy', [card], lane=args.lane,
                             home=os.environ.get('SUPER_BOARD_SKILLS_HOME'), catalog=os.environ.get('SUPER_BOARD_SKILLS_CATALOG'))
except SystemExit as error:
    result('halted', 'required GitHub reads halted while hydrating skills; preserve claims and worktrees')
    sys.exit(error.code)
except (OSError, ValueError, TypeError, KeyError) as error:
    result('halted', 'skills-readiness: ' + str(error))
    sys.exit(64)
if not skills['ready']:
    result('halted', 'skills-readiness: missing ' + ', '.join(dict.fromkeys(e['name'] for e in skills['entries'] if e['status'] == 'missing')))
    sys.exit(10)

def autonomy_rules(mode):
    """Prompt lines for run --autonomous[=full]; [] for ask. Mirrors AUTONOMY_RULES in super-board-wave.js."""
    if mode == 'ask':
        return ''
    decided = 'merge policy money/auth/schema/spec' if mode == 'full' else 'merge policy size/default'
    kept = '' if mode == 'full' else ', merge policy money/auth/schema/spec'
    return (f"AUTONOMOUS MODE ({mode}): the run owner chose not to be asked. Read "
            ".claude/skills/super-board/references/block-template.md → \"Autonomous mode\" and follow it EXACTLY: "
            "where you would move this card to Blocked for a decision a person could make (❓ 🧑 🎨 👯, too big, "
            f"🛡 truth-check inconclusive, rebuild cap, {decided}), decide instead with the decision ladder, act on it, "
            "label the issue and PR auto-decided, and post ONE decision record (marker <!-- super-board:decision -->) "
            "on the issue. Still Blocked 🙋, never decided: missing credentials 🔐, billing 💳, permissions 🔑, "
            f"merge-gate exit 8 steps (live DB, human_steps), destructive production actions{kept}. "
            f"Merge through the gate with --autonomy {mode}.\n")

skill = {'build': 'super-build', 'qa': 'super-qa', 'review': 'super-review'}[args.lane]
section = {'build': 'Builder', 'qa': 'Tester', 'review': 'Reviewer'}[args.lane]
platform = config.get('platform') if isinstance(config.get('platform'), dict) else {}
kind = platform.get('kind') or 'web'
prompt = f'''Run {skill} for issue #{card['number']} as an Antigravity lane worker.
First operation: recheck .claude/bin/super-board-skills-ready.py --root {root} --host agy --cards - --lane {args.lane} with the Card JSON below as a one-element stdin array, before worktree creation, classification or lifecycle writes. Exit 10 means status=halted, detail=skills-readiness:, preserve all state. Load resolved_path files and only declared fallback IDs from the report. Before activating any conditional helper, repeat with --require <exact-name>.
Resolved skill report: {json.dumps(skills)}
Config: {config_path}
Card: {json.dumps(card)}
Platform: {kind}
Read .claude/skills/{skill}/SKILL.md and .claude/skills/super-board/references/run.md → {section} lifecycle; follow all its board, branch, worktree, comments, test and merge requirements.
Read .claude/skills/super-board/references/platforms.md → "{kind}" for this project's build, test layers, devices, evidence capture and shared-resource locks; use the config's platform.commands when set.
Source .claude/bin/super-board-gh-guard.sh and use its quota checks. Required GitHub reads go through .claude/bin/super-board-github-read.py; a read that misses its --kind shape exits 64 for that call only and prints the valid form, so fix the read. Check --check before new writes, migrations and merges; exit 79 means status=halted, no more GitHub calls, preserve claims/worktree/card/approval. Never retry a mutation.
Use .claude/bin/super-board-card.sh for board reads/moves and .claude/bin/super-board-pr-body.sh for owned PR blocks; follow writing-standard.md and pr-author-notes.md.
Use your own worktree under .claude/worktrees/; never edit the main checkout. Clean up on ordinary exit, preserve work on halt/interruption.
Antigravity adaptation: do not call invoke_subagent or define_subagent. Perform preflight, classification, independent review and truth-check duties inline. Run shell commands with run_command from inside your worktree. If a command is denied by permissions, do not work around it: report status=failed with the denied command in detail. This changes the execution host, never the evidence requirements, confidence threshold or merge policy.
{autonomy_rules(args.autonomy or config.get('autonomy') or 'ask')}Return JSON: status=advanced|bounced|blocked|human-gate|failed|halted; column=current board column; detail=one line; prUrl/branch when known, otherwise null; priorFindings=review counts or null. A non-advanced exit ends this card's lane chain. On merge-gate exit 9, return status=halted with detail starting exactly "verification-readiness:"; preserve work and never bounce/retry.
'''
if args.lane == 'build':
    prompt += '''Before creating any worktree or changing code, perform run.md's Builder pre-flight inline: call super-board-preflight.sh, judge its candidates semantically, and act on proceed/hold/sequence/skipped. Blind preflight leaves Ready and returns failed. Your own issue branch PR is not a duplicate. Read the issue and all comments; preserve qa/bug/feature labels. Existing docs/ux/tests/refactor/tech-debt rows keep their label chain: classify complexity without adding feature/bug. If truly untyped, classify feature or bug, re-run skills-ready on the proposed labelled card before adding that label, never qa. Then follow the Builder lifecycle.
'''
elif args.lane == 'qa' and card['status'] == 'Ready':
    prompt += 'This qa-labelled Ready card skips Building: move Ready → QA and create the issue branch from the base; test the existing product per run.md qa cards.\n'
elif args.lane == 'review':
    prompt += '''The owner explicitly chose run --agy: you may review and own the merge. First load the latest <!-- super-review:report -->; grade prior R-ids fixed/not fixed/no longer applies, bounce any not fixed and edit the same report in place. Form hypotheses from the issue AC and diff before reading the Builder narrative.
Rerun the Tester's tests. When truth_gate triggers, apply super-review's fixed Adversarial mode brief inline in two distinct passes (code-grounder and historian); collect evidence and aggregate confidence against truth_threshold. Over-engineering is Should fix, never Blocker alone and never lowers confidence. Missing evidence fails closed.
When config interrogate.trigger fires (.claude/skills/super-review/references/interrogate.md), run its reviewer brief inline as two separate passes (correctness, then quality), each written to its own scratch file before the next starts, then the lead judgment; report `reviewers: inline`. Act-on findings join the report like any finding; quality-lens findings are Should fix at most. Never apply a reviewer's suggestion yourself.
Merge ONLY through the unchanged .claude/bin/super-board-merge-gate.sh, pinning the exact head you reviewed at review pass using --expect-head "$HEAD" --config <config> --pr <N> --subject <title> --body-file <msg.md>. Never run bare gh pr merge or bypass the gate. Follow run.md Merge protocol and route every gate exit exactly: 2/5 rebase pass, 3 Blocked, 4 stay Review, 6 fresh review, 7/8 human gate with pinned approval-request; 9 verification-readiness means halt and preserve card/worktree/approval/claims until config repair and explicit restart, never a Build bounce or rebase retry. Respect human_approves_merge and merge_policy. Confirm MERGED <sha>, fetch base and prove merge-base --is-ancestor <sha> origin/<base> before closing issue or moving Done.
'''

counts = {key: {'type': 'integer'} for key in ['fixed', 'notFixed', 'noLongerApplies']}
properties = {
    'status': {'type': 'string', 'enum': ['advanced', 'bounced', 'blocked', 'human-gate', 'failed', 'halted']},
    'column': {'type': 'string'}, 'detail': {'type': 'string'},
    'prUrl': {'type': ['string', 'null']}, 'branch': {'type': ['string', 'null']},
    'priorFindings': {'anyOf': [{'type': 'null'}, {'type': 'object', 'properties': counts,
                      'required': list(counts), 'additionalProperties': False}]},
}
schema = {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}
# A warning line agy prints when it soft-denies a tool call in headless mode. The
# exact wording is not documented; match the words any such line must carry.
DENIED = re.compile(r'(?i)\b(soft[- ]?denied|permission denied|denied by|not allowed|requires? (approval|permission))\b')
AGY = shlex.split(os.environ.get('SB_AGY_BIN', '')) or [shutil.which('agy') or 'agy']
child = None
def interrupted(signum, frame):
    if child is not None:
        child.terminate()
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    result('halted', 'lane interrupted; preserve claims and worktrees')
    sys.exit(128 + signum)
signal.signal(signal.SIGTERM, interrupted)
signal.signal(signal.SIGINT, interrupted)
# The full brief goes in a file inside the repo (agy reads workspace files without
# asking) and argv carries one line. A multi-line argv breaks when `agy` resolves to a
# .cmd shim on Windows, and a short line keeps the process list readable.
brief = root / '.claude/super-board/inflight' / f"agy-{card['number']}-{args.lane}.prompt.md"
brief.parent.mkdir(parents=True, exist_ok=True)
brief.write_text(prompt, encoding='utf-8')
pointer = (f"Read {brief.relative_to(root).as_posix()} and follow it exactly; it is your whole task. "
           'Answer only with the JSON object it asks for.')
with tempfile.TemporaryDirectory(prefix='super-board-agy-') as temporary:
    schema_path = Path(temporary) / 'schema.json'
    schema_path.write_text(json.dumps(schema))
    command = AGY + ['-p', pointer, '--output-format', 'json', '--json-schema', str(schema_path),
                     '--print-timeout', timeout, '--effort', effort]
    if model and model.strip():
        command += ['--model', model]
    if agy.get('skip_permissions') is True:
        # Explicit, per-board, discouraged: approves every tool call. The guard hooks
        # (.agents/hooks.json) still run; the permission allowlist does not.
        command += ['--dangerously-skip-permissions']
    try:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 encoding='utf-8', errors='replace')
        stdout, stderr = child.communicate()
        sys.stderr.write(stderr)
        denied = [line.strip() for line in stderr.splitlines() if DENIED.search(line)]
        require_verification_ready()
        if child.returncode:
            result('halted' if child.returncode in (9, 10, 79) else 'failed',
                   'verification-readiness: repair verify_commands and restart explicitly; preserve work'
                   if child.returncode == 9 else 'skills-readiness: required skills became unavailable; preserve work' if child.returncode == 10 else f'agy exited {child.returncode}')
            sys.exit(child.returncode if child.returncode in (9, 10, 79) else 1)
        run = json.loads(stdout)
        if not isinstance(run, dict) or run.get('status') != 'SUCCESS':
            raise ValueError(f"agy run status {run.get('status') if isinstance(run, dict) else '?'}: "
                             f"{(run.get('error') if isinstance(run, dict) else '') or 'no error text'}")
        parsed = run.get('structured_output')
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        if (not isinstance(parsed, dict) or parsed.get('status') not in properties['status']['enum']
                or not all(isinstance(parsed.get(key), str) for key in ['column', 'detail'])):
            raise ValueError('lane result needs status, column and detail')
        if denied:
            parsed['detail'] += f' · ⚠️ {len(denied)} tool call(s) denied by agy permissions: {denied[0][:160]}'
        print(json.dumps(parsed))
        sys.exit(10 if parsed['status'] == 'halted' and parsed['detail'].startswith('skills-readiness:')
                 else 9 if parsed['status'] == 'halted' and parsed['detail'].startswith('verification-readiness:')
                 else 79 if parsed['status'] == 'halted' else 0)
    except (OSError, ValueError) as error:
        result('failed', f'Antigravity returned no valid lane result: {error}')
        sys.exit(1)
    finally:
        brief.unlink(missing_ok=True)
PY
