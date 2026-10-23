#!/usr/bin/env python3
"""Give headless Antigravity lanes the same command allowlist Claude Code lanes have.

Headless `agy -p` soft-denies every shell command that is not allowed up front and still
exits 0 (antigravity.google/docs/cli/headless). A board lane needs gh, git, the board
scripts and the project's test runner, so without this step a lane "succeeds" without
having run anything. The docs put the allowlist in
~/.gemini/antigravity-cli/settings.json → permissions.allow, as `action(target)` rules:
`command(git)`, `write_file(src/)`.

This script reads the Claude Code allowlist the board already maintains
(<repo>/.claude/settings.json → permissions.allow, written by onboard) and converts every
`Bash(<prefix>:*)` / `Bash(<exact>)` rule to `command(<prefix>)`. Other Claude rules have
no Antigravity twin and are skipped (listed with --verbose). `--add RULE` appends any
extra Antigravity rule as written (platform tools: `command(./gradlew)`, `command(maestro)`).

Default is a dry run: it prints the rules it would add. `--apply` merges them into the
settings file (other keys untouched, no duplicates), after copying the old file to
<file>.bak-<timestamp>. An invalid settings file is left untouched (exit 2).

Usage:
  super-board-agy-permissions.py [--repo .] [--settings ~/.gemini/antigravity-cli/settings.json]
                                 [--add RULE ...] [--apply] [--verbose]
Exit: 0 ok · 2 settings file is not valid JSON · 64 usage.
"""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

BASH_RULE = re.compile(r"^Bash\((?P<body>.+)\)$")


def convert(rule):
    """`Bash(gh pr view:*)` -> `command(gh pr view)`; None for rules with no agy twin."""
    match = BASH_RULE.match(rule.strip())
    if not match:
        return None
    body = match.group("body").strip()
    body = re.sub(r"(:\*|\s\*|\*)$", "", body).strip()
    return f"command({body})" if body else None


def main():
    parser = argparse.ArgumentParser(description="Convert the board's Claude allowlist to Antigravity rules.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--settings", default=str(Path.home() / ".gemini/antigravity-cli/settings.json"))
    parser.add_argument("--add", action="append", default=[], help="extra Antigravity rule, e.g. command(./gradlew)")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    claude = Path(args.repo) / ".claude/settings.json"
    try:
        allow = (json.loads(claude.read_text()).get("permissions") or {}).get("allow") or [] if claude.exists() else []
    except ValueError:
        print(f"✋ {claude} is not valid JSON; fix it first", file=sys.stderr)
        return 2
    wanted, skipped = [], []
    for rule in allow:
        converted = convert(rule) if isinstance(rule, str) else None
        (wanted if converted else skipped).append(converted or rule)
    for rule in args.add:
        if not re.match(r"^[a-z_]+\(.+\)$", rule):
            print(f"--add takes an Antigravity rule like command(./gradlew), got {rule!r}", file=sys.stderr)
            return 64
        wanted.append(rule)

    target = Path(args.settings).expanduser()
    try:
        current = json.loads(target.read_text()) if target.exists() else {}
        if not isinstance(current, dict):
            raise ValueError
    except ValueError:
        print(f"✋ {target} is not valid JSON; left untouched", file=sys.stderr)
        return 2
    existing = ((current.get("permissions") or {}).get("allow")) or []
    new = []
    for rule in wanted:
        if rule not in existing and rule not in new:
            new.append(rule)

    for rule in new:
        print(f"+ {rule}")
    if args.verbose:
        for rule in skipped:
            print(f"  skipped (no Antigravity twin): {rule}")
    if not new:
        print(f"✓ {target}: every board rule already present")
        return 0
    if not args.apply:
        print(f"dry run: {len(new)} rule(s) for {target} — re-run with --apply to write them")
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.copy2(target, target.with_name(target.name + time.strftime(".bak-%Y%m%d%H%M%S")))
    current.setdefault("permissions", {}).setdefault("allow", [])
    current["permissions"]["allow"] = existing + new
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(current, indent=2) + "\n")
    temporary.replace(target)
    print(f"✓ {len(new)} rule(s) added to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
