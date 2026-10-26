#!/usr/bin/env python3
"""speccheck: lint a feature spec, score a cold read of it, and trace it to tests.

Standard library only. Usage:
  python3 speccheck.py lint  SPEC.md            [--json]
  python3 speccheck.py quiz  KEY.json ANSWERS.json [--json]
  python3 speccheck.py trace SPEC.md PATH [PATH ...] [--json]
Exit code: 0 when the verdict is good (READY / PASS / TRACED), 1 otherwise, 2 on bad input.
"""
import json
import os
import re
import sys

REQ_RE = re.compile(r"^\s*[-*]\s*(R\d+)\s*[:：]\s*(.+)$")
EX_RE = re.compile(r"^\s*[-*]\s*(?:[Ee]x|例)\s+(R\d+\.(?:[a-z]|\d+))\s*[:：]\s*(.+)$")
Q_RE = re.compile(r"^\s*[-*]\s*(Q\d+)\s*[:：]\s*(.+)$")
D_RE = re.compile(r"^\s*[-*]\s*(D\d+)\s*[:：]\s*(.+)$")
STATUS_RE = re.compile(r"^\s*(?:status|状态)\s*[:：]\s*(\w+)", re.I)
HEAD_RE = re.compile(r"^\s*#{2,6}\s*(.+?)\s*$")
ID_IN_TEXT = re.compile(r"(?<![A-Za-z0-9])R(\d+)(?:[._]([a-z]|\d+))?(?![A-Za-z0-9])")

STRENGTH = re.compile(r"\b(MUST|SHOULD|MAY|SHALL)\b|必须|应当|应该|可以|不得", re.I)
VAGUE_EN = ["fast", "quickly", "quick", "easy", "easily", "intuitive", "user-friendly",
            "robust", "seamless", "seamlessly", "appropriate", "appropriately", "as needed",
            "reasonable", "etc", "and so on", "various", "some", "soon", "efficient",
            "properly", "nice", "simple", "flexible", "scalable", "large", "small", "many"]
VAGUE_ZH = ["快速", "迅速", "友好", "简单", "方便", "合适", "适当", "等等", "尽量", "稳定",
            "流畅", "大量", "一些", "若干", "合理", "灵活", "及时", "高效"]
HAS_NUMBER = re.compile(r"\d")
OUTCOME = re.compile(r"\bthen\b|那么|则|结果", re.I)
OWNER = re.compile(r"(?:owner|负责人)\s*[:：=]\s*\S+|@\w+", re.I)

SECTION_KEYS = {
    "problem": ["problem", "问题", "背景"],
    "fence": ["out of scope", "not doing", "不做", "范围外", "不在范围"],
    "requirements": ["requirement", "需求", "要求"],
    "questions": ["open question", "待定", "未决", "开放问题"],
    "decisions": ["decision", "决定", "决策"],
    "glossary": ["glossary", "术语"],
}

GAP_MARKERS = ["not in spec", "不在规格", "规格未说明", "规格没有"]


def _section_of(title):
    t = title.lower()
    for key, words in SECTION_KEYS.items():
        if any(w in t for w in words):
            return key
    return None


def parse_spec(text):
    spec = {"status": None, "sections": {}, "reqs": {}, "examples": {}, "questions": {},
            "decisions": {}, "dupes": [], "order": []}
    current = None
    for lineno, line in enumerate(text.splitlines(), 1):
        m = STATUS_RE.match(line)
        if m and spec["status"] is None:
            spec["status"] = m.group(1).lower()
            continue
        h = HEAD_RE.match(line)
        if h:
            current = _section_of(h.group(1))
            if current:
                spec["sections"].setdefault(current, [])
            continue
        if current and line.strip():
            spec["sections"][current].append(line.strip())
        m = EX_RE.match(line)
        if m:
            eid, body = m.group(1), m.group(2).strip()
            if eid in spec["examples"]:
                spec["dupes"].append(eid)
            spec["examples"][eid] = {"text": body, "line": lineno}
            continue
        m = REQ_RE.match(line)
        if m:
            rid, body = m.group(1), m.group(2).strip()
            if rid in spec["reqs"]:
                spec["dupes"].append(rid)
            spec["reqs"][rid] = {"text": body, "line": lineno}
            spec["order"].append(rid)
            continue
        m = Q_RE.match(line)
        if m:
            spec["questions"][m.group(1)] = {"text": m.group(2).strip(), "line": lineno}
            continue
        m = D_RE.match(line)
        if m:
            spec["decisions"][m.group(1)] = {"text": m.group(2).strip(), "line": lineno}
    return spec


def vague_words(text):
    """Return vague words in text, ignoring the line if it also carries a number."""
    if HAS_NUMBER.search(text):
        return []
    low = text.lower()
    hits = []
    for w in VAGUE_EN:
        if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", low):
            hits.append(w)
    for w in VAGUE_ZH:
        if w in text:
            hits.append(w)
    return hits


def lint(text):
    spec = parse_spec(text)
    findings = []

    def add(sev, code, where, msg):
        findings.append({"severity": sev, "code": code, "where": where, "message": msg})

    if not spec["reqs"]:
        add("blocker", "NO_REQUIREMENTS", "-", "No lines like '- R1: ...' were found.")
    for d in sorted(set(spec["dupes"])):
        add("blocker", "DUPLICATE_ID", d, "The same id is used twice; ids must be unique.")
    for rid in spec["order"]:
        r = spec["reqs"][rid]
        exs = [e for e in spec["examples"] if e.split(".")[0] == rid]
        if not exs:
            add("blocker", "NO_EXAMPLE", rid, "Requirement has no worked example (ex %s.a: ...)." % rid)
        if not STRENGTH.search(r["text"]):
            add("major", "NO_STRENGTH", rid, "Say MUST, SHOULD or MAY so a reader knows what is negotiable.")
        vw = vague_words(r["text"])
        if vw:
            add("major", "VAGUE", rid, "Unmeasured words: %s. Replace with a number or a check." % ", ".join(vw))
    for eid, e in spec["examples"].items():
        parent = eid.split(".")[0]
        if parent not in spec["reqs"]:
            add("major", "ORPHAN_EXAMPLE", eid, "Example points at a requirement that does not exist.")
        if not OUTCOME.search(e["text"]):
            add("major", "NO_OUTCOME", eid, "Example has no 'then ...' outcome a test could check.")
        vw = vague_words(e["text"])
        if vw:
            add("major", "VAGUE", eid, "Example uses unmeasured words: %s." % ", ".join(vw))
    for qid, q in spec["questions"].items():
        if not OWNER.search(q["text"]):
            add("major", "UNOWNED_QUESTION", qid, "Open question has no owner (owner: name).")
    if spec["status"] == "ready" and spec["questions"]:
        add("major", "READY_WITH_OPEN", "status", "Status says ready but %d open question(s) remain." % len(spec["questions"]))
    if not spec["sections"].get("fence"):
        add("minor", "NO_FENCE", "-", "No 'Out of scope' section; readers will guess the edges.")
    if not spec["sections"].get("problem"):
        add("minor", "NO_PROBLEM", "-", "No 'Problem' section; reviewers cannot judge if the spec solves it.")

    sev = {f["severity"] for f in findings}
    verdict = "BLOCKED" if "blocker" in sev else ("REVISE" if "major" in sev else "READY")
    return {
        "verdict": verdict,
        "counts": {"requirements": len(spec["reqs"]), "examples": len(spec["examples"]),
                   "open_questions": len(spec["questions"]), "decisions": len(spec["decisions"])},
        "findings": findings,
    }


def _norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def quiz(key, answers, pass_ratio=0.8):
    if not isinstance(key, list) or not key:
        raise ValueError("key must be a non-empty list of questions")
    rows = []
    for item in key:
        qid = item.get("id")
        if not qid or "expect" not in item:
            raise ValueError("every key item needs 'id' and 'expect'")
        expect = item["expect"] if isinstance(item["expect"], list) else [item["expect"]]
        ans = answers.get(qid)
        refs = item.get("refs", [])
        if ans is None or not str(ans).strip():
            rows.append({"id": qid, "result": "UNANSWERED", "missing": expect, "refs": refs})
            continue
        a = _norm(ans)
        if any(m in a for m in GAP_MARKERS):
            rows.append({"id": qid, "result": "GAP", "missing": expect, "refs": refs})
            continue
        missing = [t for t in expect if _norm(t) not in a]
        rows.append({"id": qid, "result": "MATCH" if not missing else "MISREAD",
                     "missing": missing, "refs": refs})
    total = len(rows)
    matched = sum(r["result"] == "MATCH" for r in rows)
    gaps = [r for r in rows if r["result"] == "GAP"]
    misreads = [r for r in rows if r["result"] in ("MISREAD", "UNANSWERED")]
    ratio = matched / total
    verdict = "PASS" if ratio >= pass_ratio and not gaps else "FIX_SPEC"
    to_fix = sorted({ref for r in gaps + misreads for ref in r["refs"]})
    extra = sorted(set(answers) - {i["id"] for i in key})
    return {"verdict": verdict, "score": round(ratio, 2), "matched": matched, "total": total,
            "gaps": len(gaps), "misreads": len(misreads), "fix_refs": to_fix,
            "unknown_answers": extra, "rows": rows}


def _iter_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__")]
                for f in sorted(files):
                    yield os.path.join(root, f)
        elif os.path.isfile(p):
            yield p


def trace(text, paths):
    spec = parse_spec(text)
    known = set(spec["reqs"]) | set(spec["examples"])
    seen = {}
    for path in _iter_files(paths):
        try:
            with open(path, encoding="utf-8") as fh:
                body = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        for num, sub in set(ID_IN_TEXT.findall(body)):
            tok = "R" + num + ("." + sub if sub else "")
            seen.setdefault(tok, set()).add(path)
    covered_req = {}
    for rid in spec["order"]:
        hits = set(seen.get(rid, set()))
        for eid in spec["examples"]:
            if eid.split(".")[0] == rid:
                hits |= seen.get(eid, set())
        covered_req[rid] = sorted(hits)
    untested_req = [r for r, h in covered_req.items() if not h]
    untested_ex = sorted(e for e in spec["examples"] if e not in seen)
    orphans = sorted(t for t in seen if t not in known)
    verdict = "TRACED" if not untested_req and not orphans else ("DRIFT" if orphans else "PARTIAL")
    return {"verdict": verdict, "requirements": covered_req, "untested_requirements": untested_req,
            "untested_examples": untested_ex,
            "orphans": {o: sorted(seen[o]) for o in orphans}}


def _print_lint(r):
    c = r["counts"]
    print("verdict: %s  (%d requirements, %d examples, %d open questions)" % (
        r["verdict"], c["requirements"], c["examples"], c["open_questions"]))
    for f in r["findings"]:
        print("  [%s] %s %s - %s" % (f["severity"], f["code"], f["where"], f["message"]))


def _print_quiz(r):
    print("verdict: %s  score %d/%d, gaps %d, misreads %d" % (
        r["verdict"], r["matched"], r["total"], r["gaps"], r["misreads"]))
    for row in r["rows"]:
        extra = "" if row["result"] == "MATCH" else "  missing: %s" % ", ".join(map(str, row["missing"]))
        print("  %s %s%s" % (row["id"], row["result"], extra))
    if r["fix_refs"]:
        print("  fix these parts of the spec: %s" % ", ".join(r["fix_refs"]))


def _print_trace(r):
    print("verdict: %s" % r["verdict"])
    for rid, files in r["requirements"].items():
        print("  %s %s" % (rid, ", ".join(files) if files else "UNTESTED"))
    if r["untested_examples"]:
        print("  examples with no test: %s" % ", ".join(r["untested_examples"]))
    for o, files in r["orphans"].items():
        print("  ORPHAN %s in %s (not in the spec: update the spec or remove the id)" % (o, ", ".join(files)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv or argv[0] not in ("lint", "quiz", "trace"):
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    try:
        if cmd == "lint" and len(args) == 1:
            with open(args[0], encoding="utf-8") as fh:
                r = lint(fh.read())
            ok, printer = r["verdict"] == "READY", _print_lint
        elif cmd == "quiz" and len(args) == 2:
            with open(args[0], encoding="utf-8") as fh:
                key = json.load(fh)
            with open(args[1], encoding="utf-8") as fh:
                answers = json.load(fh)
            r = quiz(key, answers)
            ok, printer = r["verdict"] == "PASS", _print_quiz
        elif cmd == "trace" and len(args) >= 2:
            with open(args[0], encoding="utf-8") as fh:
                r = trace(fh.read(), args[1:])
            ok, printer = r["verdict"] == "TRACED", _print_trace
        else:
            print(__doc__)
            return 2
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        printer(r)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
