#!/usr/bin/env python3
"""super-goal — the deterministic half of the goal loop: spec scaffold, trace, ledger, recap.

The goal loop drives a whole project to a written spec: requirements with ids (R1, R2 …),
acceptance tests tagged with those ids, the super-board run in between, and a recap of
everything that ended up different from what was asked. The agent does the judgement
(interview, tickets, decisions); this script does the counting, so "are we done?" is a
calculation over test results, never an opinion.

  init   [--dir docs/goal]                       scaffold the spec folder (never overwrites)
  trace  [--dir …] --results <file|glob> … [--board issues.json] [--out trace.json]
         per requirement: met | failing | untested | in-progress | manual, plus what needs tickets
  ledger [--dir …]                               validate deviations/*.md (fields, refs, the filter rule)
  recap  [--dir …] --trace trace.json [--out recap.md]

Spec folder (references/spec-format.md has the full format):
  vision.md        goal, users, out of scope, "How to try", `Status: draft|approved`
  requirements.md  `## R<n> — <title>` + Priority / Verify / Acceptance bullets
  decisions.md     `## D<n> — <title>` + Choice / Why  (every questionnaire answer)
  priorities.md    what to sacrifice first when two requirements collide
  deviations/      one file per deviation or autonomous choice, written by the lanes

Test results: JUnit XML (Playwright `junit` reporter, Vitest, Gradle test-results, Maestro
--format junit) and NUnit 3 XML (Unity -testResults). A test proves requirement R<n> when its
name carries the tag `[R<n>]` (several tags allowed: `[R3][R7]`).

Board: optional JSON array of issues as `gh issue list --json number,title,state,body,labels`
prints it. A ticket implements R<n> when its body has a line `Implements: R<n>[, R<m>]`.

Exit codes: trace — 0 every auto requirement met · 10 work remains · 20 only blocked/manual
remain. ledger — 0 valid · 1 problems listed. Any — 64 usage, 65 unreadable spec.
"""
import argparse
import glob
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

R_HEAD = re.compile(r"^##\s+(R\d+)\s*[—–:-]\s*(.+?)\s*$", re.M)
D_HEAD = re.compile(r"^##\s+(D\d+)\s*[—–:-]\s*(.+?)\s*$", re.M)
TAG = re.compile(r"\[(R\d+)\]")
IMPLEMENTS = re.compile(r"^\s*Implements:\s*(.+)$", re.M | re.I)
FIELD = re.compile(r"^(?P<key>[A-Z][A-Za-z ]+):\s*(?P<value>.*)$", re.M)
DV_FIELDS = ("Type", "Refs", "Prescribed", "Realized", "Why", "Reversible", "Evidence")


def die(message, code=65):
    print(f"super-goal: {message}", file=sys.stderr)
    sys.exit(code)


def sections(text, head):
    """[(id, title, body)] for every `## <id> — title` section."""
    found = list(head.finditer(text))
    out = []
    for i, match in enumerate(found):
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        out.append((match.group(1), match.group(2), text[match.end():end]))
    return out


def fields(body):
    return {m.group("key").strip(): m.group("value").strip() for m in FIELD.finditer(body)}


def requirements(spec):
    path = spec / "requirements.md"
    if not path.exists():
        die(f"{path} is missing — run `super-goal.py init` and write the requirements first")
    reqs = []
    for rid, title, body in sections(path.read_text(encoding="utf-8"), R_HEAD):
        f = fields(body)
        reqs.append(dict(id=rid, title=title, priority=(f.get("Priority") or "must").lower(),
                         verify=(f.get("Verify") or "auto").lower(),
                         acceptance=[l.strip()[5:].strip() for l in body.splitlines()
                                     if l.strip().startswith(("- [ ]", "- [x]"))]))
    if not reqs:
        die(f"{path} has no `## R<n> — title` sections")
    return reqs


def decisions(spec):
    path = spec / "decisions.md"
    return {did: title for did, title, _ in sections(path.read_text(encoding="utf-8"), D_HEAD)} if path.exists() else {}


def test_results(patterns):
    """{R-id: {"pass": n, "fail": n, "tests": [names]}} from JUnit / NUnit XML files."""
    files = sorted({f for p in patterns for f in (glob.glob(p, recursive=True) or ([p] if Path(p).exists() else []))})
    by_req, seen = {}, 0
    for name in files:
        try:
            root = ET.parse(name).getroot()
        except (ET.ParseError, OSError):
            continue
        cases = []
        for case in root.iter("testcase"):  # JUnit
            failed = case.find("failure") is not None or case.find("error") is not None
            skipped = case.find("skipped") is not None
            cases.append((f"{case.get('classname', '')} {case.get('name', '')}", None if skipped else not failed))
        for case in root.iter("test-case"):  # NUnit 3 (Unity)
            result = (case.get("result") or "").lower()
            label = f"{case.get('fullname', '')} {case.get('name', '')}"
            cases.append((label, None if result in ("skipped", "ignored", "inconclusive") else result == "passed"))
        for label, passed in cases:
            seen += 1
            for rid in set(TAG.findall(label)):
                slot = by_req.setdefault(rid, {"pass": 0, "fail": 0, "skipped": 0, "tests": []})
                slot["tests"].append(label.strip())
                slot["skipped" if passed is None else "pass" if passed else "fail"] += 1
    return by_req, files, seen


def board_tickets(path):
    """{R-id: [{number, state, title, blocked}]} from a gh issue list JSON file."""
    if not path:
        return {}
    try:
        issues = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        die(f"board file {path} is not a JSON array of issues")
    out = {}
    for issue in issues if isinstance(issues, list) else []:
        body = issue.get("body") or ""
        labels = {(l.get("name") if isinstance(l, dict) else str(l)).lower() for l in issue.get("labels") or []}
        for line in IMPLEMENTS.findall(body):
            for rid in re.findall(r"R\d+", line):
                out.setdefault(rid, []).append(dict(
                    number=issue.get("number"), title=issue.get("title"),
                    state=(issue.get("state") or "OPEN").upper(),
                    blocked=bool(labels & {"needs-you", "blocked"}) or issue.get("column") == "Blocked"))
    return out


def cmd_init(args):
    spec = Path(args.dir)
    (spec / "deviations").mkdir(parents=True, exist_ok=True)
    templates = {
        "vision.md": "# Vision\n\nStatus: draft\n\n## Goal\n\n## Users\n\n## Out of scope\n\n## How to try\n",
        "requirements.md": "# Requirements\n\n## R1 — <what the user can do>\nPriority: must\nVerify: auto\nAcceptance:\n- [ ] <observable outcome a test asserts>\n",
        "decisions.md": "# Decisions\n\n## D1 — <question asked>\nChoice: <the answer>\nWhy: <the reason given>\n",
        "priorities.md": "# Priorities\n\nWhen two requirements collide, keep the higher one:\n\n1. <e.g. works offline>\n2. <e.g. data is never lost>\n",
    }
    written = []
    for name, text in templates.items():
        target = spec / name
        if not target.exists():
            target.write_text(text, encoding="utf-8")
            written.append(name)
    keep = spec / "deviations" / ".gitkeep"
    if not keep.exists():
        keep.write_text("", encoding="utf-8")
    print(json.dumps({"dir": str(spec), "created": written}))


def cmd_trace(args):
    spec = Path(args.dir)
    reqs = requirements(spec)
    results, files, seen = test_results(args.results)
    tickets = board_tickets(args.board)
    rows, needs, blocked_only = [], [], True
    for r in reqs:
        res = results.get(r["id"], {"pass": 0, "fail": 0, "skipped": 0, "tests": []})
        open_tickets = [t for t in tickets.get(r["id"], []) if t["state"] == "OPEN"]
        if r["verify"] == "manual":
            status = "manual"
        elif res["fail"]:
            status = "failing"
        elif res["pass"]:
            status = "met"
        else:
            status = "untested"
        if status in ("failing", "untested") and open_tickets:
            status = "in-progress"
        row = dict(id=r["id"], title=r["title"], priority=r["priority"], status=status,
                   passed=res["pass"], failed=res["fail"], skipped=res["skipped"],
                   tickets=[t["number"] for t in tickets.get(r["id"], [])],
                   open=[t["number"] for t in open_tickets],
                   blocked=[t["number"] for t in open_tickets if t["blocked"]])
        rows.append(row)
        if status in ("failing", "untested"):
            needs.append(r["id"])
        if status in ("failing", "untested") or (status == "in-progress" and len(row["blocked"]) < len(row["open"])):
            blocked_only = False
    auto = [r for r in rows if r["status"] != "manual"]
    summary = {s: sum(1 for r in rows if r["status"] == s) for s in ("met", "failing", "untested", "in-progress", "manual")}
    out = dict(spec=str(spec), result_files=files, tests_seen=seen, summary=summary,
               needs_tickets=needs, requirements=rows,
               done=all(r["status"] == "met" for r in auto))
    text = json.dumps(out, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    if out["done"]:
        return 0
    return 20 if blocked_only else 10


def parse_deviation(path):
    text = path.read_text(encoding="utf-8")
    head = re.search(r"^#\s+(DV-[\w-]+)\s*[—–:-]\s*(.+)$", text, re.M)
    f = fields(text)
    return dict(file=path.name, id=head.group(1) if head else None, title=head.group(2).strip() if head else None,
                **{k.lower(): f.get(k, "") for k in DV_FIELDS})


def norm(text):
    return re.sub(r"[\W_]+", " ", text.lower()).strip()


def cmd_ledger(args):
    spec = Path(args.dir)
    rids = {r["id"] for r in requirements(spec)}
    dids = set(decisions(spec))
    problems, entries = [], []
    for path in sorted((spec / "deviations").glob("*.md")):
        d = parse_deviation(path)
        entries.append(d)
        where = path.name
        if not d["id"]:
            problems.append(f"{where}: first line must be `# DV-<issue>-<n> — <title>`")
        for key in DV_FIELDS:
            if not d[key.lower()]:
                problems.append(f"{where}: missing `{key}:`")
        if d["type"] and d["type"].lower() not in ("deviation", "autonomous"):
            problems.append(f"{where}: Type must be deviation or autonomous, got {d['type']!r}")
        refs = re.findall(r"[RD]\d+", d["refs"])
        if not refs:
            problems.append(f"{where}: Refs must name at least one R<n> or D<n>")
        for ref in refs:
            if (ref.startswith("R") and ref not in rids) or (ref.startswith("D") and ref not in dids):
                problems.append(f"{where}: Refs names {ref}, which is not in the spec")
        # The filter rule: an entry exists only when the result differs from what was asked.
        if d["type"].lower() == "deviation" and d["prescribed"] and norm(d["prescribed"]) == norm(d["realized"]):
            problems.append(f"{where}: Prescribed and Realized say the same — not a deviation, delete the file")
        if d["type"].lower() == "autonomous" and not d["prescribed"].lower().startswith(("nothing", "silent", "-", "n/a")):
            problems.append(f"{where}: an autonomous choice has `Prescribed: nothing (spec silent)`; a choice that "
                            "overrides the spec is Type: deviation")
    ids = [e["id"] for e in entries if e["id"]]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"duplicate id {dup}")
    print(json.dumps({"entries": len(entries), "problems": problems}, indent=2))
    return 1 if problems else 0


def robot_line(path):
    """One line for the recap from super-board-decisions.py's trail (its second line holds the counts)."""
    counts = next((l for l in path.read_text(encoding="utf-8").splitlines() if " decisions · " in l), "")
    return f"{counts or 'Decision trail'} — see [{path.name}]({path.name}); review the 🔴 ones first.\n"


def table(rows, cols):
    head = "| " + " | ".join(c for c, _ in cols) + " |\n|" + "---|" * len(cols) + "\n"
    return head + "".join("| " + " | ".join(str(fn(r)).replace("|", "\\|") for _, fn in cols) + " |\n" for r in rows)


def cmd_recap(args):
    spec = Path(args.dir)
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    entries = [parse_deviation(p) for p in sorted((spec / "deviations").glob("*.md"))]
    deviations = [e for e in entries if e["type"].lower() == "deviation"]
    autonomous = [e for e in entries if e["type"].lower() == "autonomous"]
    rows = trace["requirements"]
    icon = {"met": "✅", "failing": "❌", "untested": "⚪", "in-progress": "🔄", "manual": "👀"}
    deviated = {ref for e in deviations for ref in re.findall(r"R\d+", e["refs"])}
    blocked = [(r["id"], n) for r in rows for n in r["blocked"]]
    vision = (spec / "vision.md").read_text(encoding="utf-8") if (spec / "vision.md").exists() else ""
    how = re.search(r"^## How to try\s*\n(.*?)(?=^## |\Z)", vision, re.M | re.S)
    s = trace["summary"]
    out = [f"# Recap\n",
           f"{s['met']} met · {s['failing']} failing · {s['untested']} untested · {s['in-progress']} in progress · "
           f"{s['manual']} to judge by hand · {len(deviations)} deviations · {len(autonomous)} autonomous choices\n",
           "## 1 · Requirements\n",
           table(rows, [("Req", lambda r: r["id"]), ("Title", lambda r: r["title"]),
                        ("Status", lambda r: icon.get(r["status"], "") + " " + r["status"]
                         + (" · ⚠️ deviated" if r["id"] in deviated else "")),
                        ("Tests", lambda r: f"{r['passed']}✓ {r['failed']}✗"),
                        ("Tickets", lambda r: " ".join(f"#{n}" for n in r["tickets"]) or "—")]),
           "\n## 2 · Deviations — the result differs from the spec\n",
           table(deviations, [("Id", lambda e: e["id"]), ("Refs", lambda e: e["refs"]),
                              ("Asked", lambda e: e["prescribed"]), ("Built", lambda e: e["realized"]),
                              ("Why", lambda e: e["why"]), ("Undo", lambda e: e["reversible"]),
                              ("Evidence", lambda e: e["evidence"])]) if deviations else "None.\n",
           "\n## 3 · Choices made where the spec was silent\n",
           table(autonomous, [("Id", lambda e: e["id"]), ("Refs", lambda e: e["refs"]),
                              ("Chose", lambda e: e["realized"]), ("Why", lambda e: e["why"]),
                              ("Undo", lambda e: e["reversible"])]) if autonomous else "None.\n",
           "\n## 4 · Waiting for you\n",
           ("".join(f"- {rid}: #{n}\n" for rid, n in blocked) if blocked else "Nothing blocked.\n"),
           "\n## 5 · Judge by hand\n",
           ("".join(f"- {r['id']} — {r['title']}\n" for r in rows if r["status"] == "manual") or "Nothing.\n"),
           "\n## 6 · Decisions the robot took instead of asking\n",
           (robot_line(spec / "robot-decisions.md") if (spec / "robot-decisions.md").exists()
            else "None recorded (run without --autonomous, or no doubt needed one).\n"),
           "\n## 7 · How to try it\n",
           (how.group(1).strip() + "\n") if how and how.group(1).strip() else "See vision.md.\n"]
    text = "".join(out)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


def main():
    parser = argparse.ArgumentParser(description="super-goal spec, trace, ledger and recap.")
    sub = parser.add_subparsers(dest="verb", required=True)
    for name in ("init", "trace", "ledger", "recap"):
        p = sub.add_parser(name)
        p.add_argument("--dir", default="docs/goal")
        if name == "trace":
            p.add_argument("--results", nargs="+", default=[], help="JUnit/NUnit XML files or globs")
            p.add_argument("--board")
            p.add_argument("--out")
        if name == "recap":
            p.add_argument("--trace", required=True)
            p.add_argument("--out")
    args = parser.parse_args()
    return {"init": cmd_init, "trace": cmd_trace, "ledger": cmd_ledger, "recap": cmd_recap}[args.verb](args) or 0


if __name__ == "__main__":
    sys.exit(main())
