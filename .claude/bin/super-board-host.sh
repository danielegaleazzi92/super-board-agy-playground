#!/usr/bin/env bash
# super-board-host.sh — which agent host is this shell inside: `claude`, `codex` or `agy`.
#
# WHY. `/super-board run` launched from a Codex CLI or Antigravity session has no Claude
# Workflow tool, so the workflow backend cannot start. The orchestrator checks its own
# tool list first; this is the check a script can make, and the tie-breaker when the
# tool list is unclear.
#
# CODEX. Codex CLI sets CODEX_THREAD_ID (and CODEX_SESSION_ID, the same value) in every
# shell it runs. Observed 2026-10-04 on codex-cli 0.160.0 with `codex exec -s read-only`:
# CODEX_THREAD_ID, CODEX_SESSION_ID, CODEX_VERSION, CODEX_SANDBOX=seatbelt, CODEX_CI=1.
# Not used: CODEX_HOME (people export it in their own profile), CODEX_SANDBOX (absent when
# the sandbox is off). A Codex lane started from a Claude session also carries CLAUDECODE; the
# Codex ids still win there, because the innermost host is the one running this shell.
#
# ANTIGRAVITY. The docs (antigravity.google/docs) name no environment variable that the
# agy CLI or Antigravity 2.0 exports to the shells it runs, so this script does not guess
# one. Ways to answer `agy`, in order:
#   1. SUPER_BOARD_HOST=agy (export it in the shell profile agy uses, or in the
#      orchestrator's environment);
#   2. SB_AGY_HOST_VAR=<NAME>: a variable you observed agy setting
#      (`agy -p 'run env | sort'`); NAME set and non-empty means agy;
#   3. the orchestrator's own tool list: invoke_subagent / run_command / view_file are
#      Antigravity tools (run-workflow.md → "Antigravity runs").
#
# Usage: super-board-host.sh          prints `claude`, `codex` or `agy`, exit 0
# SUPER_BOARD_HOST=claude|codex|agy forces the answer (tests, or a host the check misreads).
set -euo pipefail

case "${SUPER_BOARD_HOST:-}" in
  claude|codex|agy) echo "$SUPER_BOARD_HOST"; exit 0 ;;
  '') ;;
  *) echo "super-board-host.sh: SUPER_BOARD_HOST must be claude, codex or agy" >&2; exit 64 ;;
esac

if [ -n "${CODEX_THREAD_ID:-}" ] || [ -n "${CODEX_SESSION_ID:-}" ]; then
  echo codex
elif printf '%s' "${SB_AGY_HOST_VAR:-}" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$' \
     && [ -n "$(printenv "$SB_AGY_HOST_VAR" 2>/dev/null || true)" ]; then
  echo agy
else
  echo claude
fi
