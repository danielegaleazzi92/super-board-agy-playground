#!/usr/bin/env python3
"""The trail of decisions the robot took in autonomous mode, for a human to review.

`run --autonomous[=full]` lets lanes decide where they would otherwise park a card in
Blocked. Each decision is one issue comment that starts with `<!-- super-board:decision -->`
(format: references/block-template.md → "Autonomous mode"), and the issue and PR carry the
label `auto-decided`. This script checks a record before it is posted and gathers every
record into one review document at the end of a run.

  check  --body-file <f>                     exit 0 valid · 1 problems (listed on stdout)
  report [--repo owner/name] [--input f]     markdown trail, highest risk first, one review
         [--since YYYY-MM-DD] [--out f]      checkbox per decision
  --input reads a JSON array of issues/PRs `{number, title, url, comments:[{body, url,
  createdAt}]}` instead of calling gh (tests, or an export you made yourself).

Without --input, report reads `gh issue list` and `gh pr list` with `--label auto-decided
--state all --json number,title,url,comments`: two calls, REST-cheap.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MARKER = "<!-- super-board:decision -->"
FIELDS = ("Would block", "Options", "Chose", "Why", "Risk", "Undo", "Evidence")
HEAD = re.compile(r"^\[(?P<role>[\w-]+)\]\s*\[decision\]\s*🤖\s*decided\s*·\s*(?P<summary>.+)$", re.M)
RISK_ORDER = {"🔴": 0, "🟡": 1, "🟢": 2}


def parse(body):
    head = HEAD.search(body)
    out = {"role": head.group("role") if head else "", "summary": head.group("summary").strip() if head else ""}
    for key in FIELDS:
        match = re.search(rf"^{re.escape(key)}:\s*(.+)$", body, re.M)
        out[key] = match.group(1).strip() if match else ""
    return out


def problems(body):
    found = []
    if MARKER not in body:
        found.append(f"first line must be {MARKER}")
    record = parse(body)
    if not record["summary"]:
        found.append("second line must be `[<role>] [decision] 🤖 decided · <emoji> <summary>`")
    for key in FIELDS:
        if not record[key]:
            found.append(f"missing `{key}:`")
    if record["Risk"] and record["Risk"][:1] not in RISK_ORDER:
        found.append("Risk must start with 🟢, 🟡 or 🔴")
    if record["Options"] and not re.search(r"\bB\)", record["Options"]):
        found.append("Options needs at least two (A) … · B) …): a decision with one option was not a decision")
    if record["Chose"] and not re.match(r"^[A-Z]\b", record["Chose"]):
        found.append("Chose must start with the option letter")
    return found


def gh_items(repo):
    items = []
    for kind in ("issue", "pr"):
        cmd = ["gh", kind, "list", "--label", "auto-decided", "--state", "all", "--limit", "500",
               "--json", "number,title,url,comments"] + (["--repo", repo] if repo else [])
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"super-board-decisions: {' '.join(cmd[:3])} failed: {error}", file=sys.stderr)
            sys.exit(2)
        for item in json.loads(out or "[]"):
            item["kind"] = kind
            items.append(item)
    return items


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def report(items, since):
    records, seen = [], set()
    for item in items:
        for comment in item.get("comments") or []:
            body = comment.get("body") or ""
            when = (comment.get("createdAt") or "")[:10]
            if MARKER not in body or (since and when and when < since):
                continue
            key = comment.get("url") or (item.get("number"), body)
            if key in seen:
                continue
            seen.add(key)
            rec = parse(body)
            rec.update(number=item.get("number"), title=item.get("title"), url=comment.get("url") or item.get("url"),
                       when=when, invalid=problems(body))
            records.append(rec)
    records.sort(key=lambda r: (RISK_ORDER.get(r["Risk"][:1], 3), r["when"], r["number"] or 0))
    counts = {k: sum(1 for r in records if r["Risk"][:1] == k) for k in RISK_ORDER}
    lines = ["# Decisions taken in autonomous mode\n",
             f"{len(records)} decisions · 🔴 {counts['🔴']} · 🟡 {counts['🟡']} · 🟢 {counts['🟢']}"
             + (f" · since {since}" if since else "") + "\n",
             "Review each one: tick it when you accept it, or follow its Undo line.\n",
             "| ✔ | Risk | Card | Decision | Would have blocked on | Chose | Undo |",
             "|---|---|---|---|---|---|---|"]
    for r in records:
        lines.append(f"| ☐ | {cell(r['Risk'][:1] or '?')} | [#{r['number']}]({r['url']}) | {cell(r['summary'])} | "
                     f"{cell(r['Would block'])} | {cell(r['Chose'])} | {cell(r['Undo'])} |")
    lines.append("")
    for r in records:
        lines += [f"## #{r['number']} — {r['summary']}", "",
                  f"- **Card:** [{cell(r['title'])}]({r['url']}) · {r['role']} · {r['when']}",
                  f"- **Would have blocked on:** {r['Would block']}",
                  f"- **Options:** {r['Options']}",
                  f"- **Chose:** {r['Chose']}",
                  f"- **Why:** {r['Why']}",
                  f"- **Risk:** {r['Risk']}",
                  f"- **Undo:** {r['Undo']}",
                  f"- **Evidence:** {r['Evidence']}"]
        if r["invalid"]:
            lines.append(f"- ⚠️ **Incomplete record:** {'; '.join(r['invalid'])}")
        lines.append("")
    if not records:
        lines.append("No decision records found.\n")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Check and gather autonomous-mode decision records.")
    sub = parser.add_subparsers(dest="verb", required=True)
    c = sub.add_parser("check")
    c.add_argument("--body-file", required=True)
    r = sub.add_parser("report")
    r.add_argument("--repo")
    r.add_argument("--input")
    r.add_argument("--since")
    r.add_argument("--out")
    args = parser.parse_args()
    if args.verb == "check":
        found = problems(Path(args.body_file).read_text(encoding="utf-8"))
        print(json.dumps({"problems": found}, indent=2, ensure_ascii=False))
        return 1 if found else 0
    items = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else gh_items(args.repo)
    text = report(items, args.since)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
