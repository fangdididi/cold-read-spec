# Cold-Read Spec

**English** | [简体中文](README.zh-CN.md)

An agent skill for writing a feature spec **before** coding and proving it can be built by
someone who was not in the conversation.

The author of a spec cannot see its holes, because their memory fills them. So this skill
has a second reader with zero context, a fresh agent session or subagent given only the
spec file, answer a quiz the author wrote in advance. Every answer that comes back wrong or
`NOT IN SPEC` points at a sentence to fix. Code starts only when the cold reader passes,
it is written test-first against numbered examples, and before merge every requirement is
traced to a test.

## Why

- AI agents implement exactly what is written, and guess the rest with confidence.
- New sessions, teammates and future you do not share the conversation that produced the spec.
- Reviewing your own spec feels thorough and finds almost nothing.
- Code that quietly grows past its spec leaves nothing to check the next change against.

## Features

- **A spec shape that can be checked**: problem with a number, a "done means" check,
  out-of-scope fence, glossary, requirements `R1..` with MUST/SHOULD/MAY, worked examples
  `R1.a..` in given/when/then form, decisions `D1..`, open questions `Q1..` with owners.
- **Lint** for form: missing examples, duplicate ids, vague words such as "fast",
  "intuitive", "快速" or "友好" without a number, examples with no checkable outcome,
  unowned questions, "ready" while questions remain.
- **Cold-read quiz**: answer key written first, a fresh reader through one of four lenses
  (Builder, Tester, Newcomer, Skeptic), automatic scoring into MATCH / MISREAD / GAP and the
  list of spec ids to fix.
- **Fix loop rules**: fix the spec, never coach the reader; use a new reader each round;
  split the feature if round three still fails.
- **Test-first build** against example ids, then a **trace** that flags untested
  requirements and `DRIFT` (tests naming ids the spec never had).
- English and Chinese specs both work; one Python file, standard library only, 51 tests.

## Install

Copy the folder into your agent's skills directory.

| Agent | Where |
| --- | --- |
| Claude Code | `~/.claude/skills/cold-read-spec/` (personal) or `.claude/skills/cold-read-spec/` (project) |
| Codex | `~/.codex/skills/cold-read-spec/` or the skills folder your setup uses |
| Cursor | `.cursor/skills/cold-read-spec/`, or reference `SKILL.md` from a project rule |
| Other agents | Put `SKILL.md` where the agent reads instructions, or paste it into the system prompt |

```bash
git clone https://github.com/fangdididi/cold-read-spec ~/.claude/skills/cold-read-spec
```

Then ask: "Write a spec for the CSV export first and cold-read it before we build."

## Usage

```bash
# 1. form check
python3 scripts/speccheck.py lint spec.md

# 2. score a cold read (key written before the reader saw the spec)
python3 scripts/speccheck.py quiz quiz-key.json cold-answers.json

# 3. before merge: every requirement has a test, no test cites a missing id
python3 scripts/speccheck.py trace spec.md tests/

# any command: --json for machine-readable output
```

Exit code is `0` for `READY` / `PASS` / `TRACED`, `1` for anything else, `2` for bad input,
so the commands can gate a CI step.

## Example

```text
$ python3 scripts/speccheck.py lint examples/csv-export/spec.draft.md
verdict: BLOCKED  (3 requirements, 2 examples, 1 open questions)
  [major] VAGUE R1 - Unmeasured words: quickly. Replace with a number or a check.
  [blocker] NO_EXAMPLE R2 - Requirement has no worked example (ex R2.a: ...).
  ...

$ python3 scripts/speccheck.py quiz examples/csv-export/quiz-key.json examples/csv-export/cold-answers.round1.json
verdict: FIX_SPEC  score 3/7, gaps 2, misreads 2
  C2 GAP  missing: client
  C5 GAP  missing: utf-8, byte-order mark
  ...
  fix these parts of the spec: D1, R1, R2, R3

$ python3 scripts/speccheck.py quiz examples/csv-export/quiz-key.json examples/csv-export/cold-answers.round2.json
verdict: PASS  score 7/7, gaps 0, misreads 0

$ python3 scripts/speccheck.py trace examples/booking-reminder/spec.md examples/booking-reminder/tests
verdict: DRIFT
  ...
  ORPHAN R6 in .../test_reminder.py (not in the spec: update the spec or remove the id)
```

## File structure

```text
cold-read-spec/
├── SKILL.md                    # skill instructions (English)
├── SKILL.zh-CN.md              # skill instructions (Chinese)
├── README.md / README.zh-CN.md
├── LICENSE
├── scripts/speccheck.py        # lint / quiz / trace
├── templates/
│   ├── spec.md / spec.zh-CN.md # empty spec skeletons
│   ├── quiz-key.json           # answer key skeleton
│   └── cold-reader-brief.md    # prompt for the fresh-context reader (EN + ZH)
├── examples/
│   ├── csv-export/             # draft -> cold read round 1 -> fixed spec -> round 2 -> trace
│   └── booking-reminder/       # Chinese spec with REVISE findings and a DRIFT trace
└── tests/test_speccheck.py     # 51 tests: python3 -m unittest discover -s tests
```

## License

MIT
