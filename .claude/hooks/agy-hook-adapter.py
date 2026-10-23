#!/usr/bin/env python3
"""Run super-board's Claude Code guard hooks under Google Antigravity (agy CLI / 2.0 / IDE).

Antigravity hooks (antigravity.google/docs/hooks) live in `.agents/hooks.json` and speak a
different dialect from Claude Code:

    in   {"toolCall": {"name": "run_command", "args": {...}}, "workspacePaths": [...], ...}
    out  {"decision": "allow" | "deny" | "ask" | "force_ask" | "deny_unless_prior_grant",
          "reason": "..."}

The guards (guard-*.py next to this file) read Claude's
`{"hook_event_name", "tool_name", "tool_input"}` and answer with
`hookSpecificOutput.permissionDecision = "deny"`. This adapter translates the call, runs the
guards that Claude's settings-snippet.json would run for that tool, and translates the
verdict back. The guards stay the single copy of every rule.

Tool mapping. The docs name `run_command` and `view_file`; argument names are not
documented, so the adapter reads the first non-empty value among the usual spellings
(CommandLine / command / cmd …, AbsolutePath / TargetFile / file_path / path …) and maps a
tool by its name: command/shell/terminal → Bash, view/read/open → Read, grep/search/find →
Grep, write/create → Write, replace/edit/patch/modify → Edit. Anything else passes.

No objection is not the same as "allow": `allow` would skip Antigravity's own permission
check. The adapter answers
  - shell commands:            SB_AGY_HOOK_PASS_COMMAND (default "ask": the normal
                               allowlist / Always Allow flow; headless soft-denies
                               anything not allowed);
  - files inside the workspace: SB_AGY_HOOK_PASS_FILE (default "allow": Antigravity
                               auto-allows workspace reads and writes anyway);
  - files outside it:          "ask".
Verify these defaults against your agy version (super-board spike, docs/antigravity.md).

PostToolUse returns {} (the event takes no decision); the Pre check already saw the write.
Like every guard, the adapter's own errors never block a tool call: it falls back to the
pass decision above.

Usage (from .agents/hooks.json):
  python3 .claude/hooks/agy-hook-adapter.py --event PreToolUse [--protect-push]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMAND_KEYS = ("CommandLine", "commandLine", "command", "Command", "cmd")
PATH_KEYS = ("AbsolutePath", "absolutePath", "TargetFile", "targetFile", "file_path", "filePath",
             "FilePath", "path", "Path", "SearchPath", "searchPath", "DirectoryPath")
GLOB_KEYS = ("Includes", "includes", "glob", "Glob", "pattern", "Pattern", "Query", "query")
# Claude's settings-snippet.json matchers, per mapped tool.
GUARDS = {
    "Bash": ["guard-worktree-path.py", "guard-delete-outside.py", "guard-secrets.py", "guard-key-literals.py"],
    "Read": ["guard-secrets.py"],
    "Grep": ["guard-secrets.py"],
    "Write": ["guard-key-literals.py"],
    "Edit": ["guard-key-literals.py"],
}


def first(args, keys):
    for key in keys:
        value = args.get(key)
        if isinstance(value, list):
            value = " ".join(str(v) for v in value)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def other_text(args, skip):
    """Every string an edit could write: all values except the path ones."""
    parts = []
    def walk(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key not in skip:
                    walk(item)
    for key, value in args.items():
        if key not in skip:
            walk(value)
    return "\n".join(parts)


def to_claude(name, args):
    """(tool_name, tool_input) in Claude Code terms, or (None, None) to pass."""
    lowered = name.lower()
    command = first(args, COMMAND_KEYS)
    path = first(args, PATH_KEYS)
    if command or re.search(r"command|shell|terminal|exec", lowered):
        return "Bash", {"command": command}
    if re.search(r"grep|search|find", lowered):
        return "Grep", {"path": path, "glob": first(args, GLOB_KEYS)}
    if re.search(r"view|read|open", lowered):
        return "Read", {"file_path": path}
    if re.search(r"write|create", lowered):
        return "Write", {"file_path": path, "content": other_text(args, set(PATH_KEYS))}
    if re.search(r"replace|edit|patch|modify", lowered):
        return "Edit", {"file_path": path, "new_string": other_text(args, set(PATH_KEYS))}
    return None, None


def inside(path, root):
    if not path:
        return True
    try:
        target = Path(path)
        target = (target if target.is_absolute() else root / target).resolve()
        return target == root or root in target.parents
    except (OSError, ValueError):
        return False


def run_guard(guard, payload, root):
    script = HERE / guard
    if not script.exists():
        return None
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
    proc = subprocess.run([sys.executable, str(script)], input=json.dumps(payload), text=True,
                          capture_output=True, cwd=str(root), env=env, timeout=25)
    if proc.returncode == 2:  # Claude's "block" exit, reason on stderr
        return proc.stderr.strip() or f"blocked by {guard}"
    try:
        out = json.loads(proc.stdout or "{}").get("hookSpecificOutput") or {}
    except ValueError:
        return None
    if out.get("permissionDecision") == "deny":
        return out.get("permissionDecisionReason") or f"blocked by {guard}"
    return None


def main():
    argv = sys.argv[1:]
    event = argv[argv.index("--event") + 1] if "--event" in argv else "PreToolUse"
    if event != "PreToolUse":
        print("{}")
        return
    pass_command = os.environ.get("SB_AGY_HOOK_PASS_COMMAND", "ask")
    pass_file = os.environ.get("SB_AGY_HOOK_PASS_FILE", "allow")
    decision = {"decision": pass_command}
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        call = payload.get("toolCall") or {}
        args = call.get("args") or {}
        if isinstance(args, str):
            args = json.loads(args)
        roots = payload.get("workspacePaths") or []
        root = Path(roots[0] if roots else os.getcwd()).resolve()
        tool, tool_input = to_claude(str(call.get("name") or ""), args if isinstance(args, dict) else {})
        if tool is None:
            print(json.dumps(decision))
            return
        if tool != "Bash":
            decision = {"decision": pass_file if inside(tool_input.get("file_path") or tool_input.get("path"), root) else "ask"}
        guards = list(GUARDS[tool])
        if tool == "Bash" and "--protect-push" in argv:
            guards.append("guard-protected-push.py")
        claude_payload = {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
                          "cwd": str(root)}
        for guard in guards:
            reason = run_guard(guard, claude_payload, root)
            if reason:
                decision = {"decision": "deny", "reason": reason}
                break
    except Exception:
        pass
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
