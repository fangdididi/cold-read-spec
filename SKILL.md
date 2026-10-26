---
name: cold-read-spec
description: Write a feature spec before coding and prove it can be built by someone who was not in the conversation. Use when a feature is bigger than one sitting, when an AI agent or a new teammate will implement it, when the user says "write a spec / PRD / design doc first", or before handing work to another session. Produces a spec with numbered requirements and worked examples, a cold-read quiz answered by a fresh-context reader, a BUILD/REVISE verdict, and a spec-to-test trace before merge.
---

# Cold-Read Spec

[中文版](SKILL.zh-CN.md)

## What this is

A spec written by the person who just spent an hour discussing the feature always looks
complete to that person. Their head fills every gap. The first reader who was not in the
room, a teammate, a new agent session, or you next month, hits the gaps instead and fills
them with guesses. Those guesses become bugs that nobody can trace back to a decision.

This skill splits the work between two readers on purpose:

- **The author** has all the context. The author writes the spec, the questions an
  implementer will ask, and the expected answers.
- **The cold reader** has none. It is a fresh agent session, a subagent started with only
  the spec file, or a human who skipped the meeting. It answers the questions from the
  spec alone and must write `NOT IN SPEC` instead of guessing.

Where the two disagree, the spec has a hole. You fix the spec, not the reader, and repeat
until the cold reader gets it right. Only then does code start, written test-first against
numbered examples, and before merge every requirement is traced to a test.

## When to use it

- The feature will take more than one sitting, or more than one person or agent.
- An AI agent will implement it, especially in a new session that will not see this chat.
- The user asks for a spec, PRD, design doc or "plan before you code".
- A change keeps bouncing in review because people understood it differently.
- You inherit a half-written spec and need to know whether it is buildable.

Skip it for a one-line fix, a spike you will throw away, or work whose whole spec is the
failing test.

## The files

| File | Who writes it | Purpose |
| --- | --- | --- |
| `spec.md` | author | Problem, done-means, out of scope, glossary, requirements `R1..` with examples `R1.a..`, decisions `D1..`, open questions `Q1..` |
| `quiz-key.json` | author, **before** the cold read | 6 to 10 questions with the words a right answer must contain and the ids they test |
| `cold-answers.json` | cold reader | Answers from the spec only |
| tests | builder | Test names or comments carry the example id they prove (`test_R2_a_...` or `# R2.a`) |

Templates live in `templates/`. The helper `scripts/speccheck.py` (Python 3, standard
library only) checks each step: `lint`, `quiz`, `trace`.

## Steps

### 1. Pin the problem and the finish line

Before any requirement, write three short sections:

- **Problem**: who is stuck, doing what, how often, at what cost. Put a number in it
  ("40 minutes per client per month", "12% no-shows").
- **Done means**: one observable check that proves the feature works for that person.
- **Out of scope**: things a reasonable reader would expect that you are not doing now.
  This fence prevents the most common kind of scope creep: the builder being helpful.

If you cannot write the problem with a number, ask the user. Do not invent one.

### 2. Write numbered requirements, each with a worked example

- One behavior per line: `- R3: <actor> MUST <behavior> <bound>.`
- Say how firm it is: MUST / MUST NOT (non-negotiable), SHOULD (expected, may be traded
  with a reason), MAY (optional). In Chinese: 必须 / 不得 / 应当 / 可以.
- Every requirement gets at least one example with real values:
  `- ex R3.a: given <state>, when <action>, then <checkable result>.`
  Add a second example for the edge that worries you most (empty, maximum, time zone,
  permission, retry).
- Replace unmeasured words with numbers or checks. "Fast" becomes "under 2 s on a 4G
  phone"; "large files" becomes "up to 200 MB".
- Put every term that has a special meaning here in the glossary.
- Record choices that are already made as decisions (`D1: ... because ...`) so the builder
  does not reopen them.
- Anything you do not know yet goes in open questions with an owner. Do not hide unknowns
  inside vague wording.

### 3. Lint the spec

```bash
python3 scripts/speccheck.py lint spec.md
```

| Verdict | Meaning |
| --- | --- |
| `READY` | No blockers or major findings. Go to the cold read. |
| `REVISE` | Major findings: vague words, no MUST/SHOULD/MAY, example without a `then`, unowned question, "ready" with open questions. |
| `BLOCKED` | No requirements, a duplicate id, or a requirement with no example. |

The lint catches form, not meaning. A `READY` spec can still be wrong; that is what the
cold read is for.

### 4. Write the quiz and the answer key first

Write 6 to 10 questions that a builder will ask on the first day, and the answer you
expect. Write them before anyone reads the spec so you cannot fit the key to the answers.
Good questions:

- a boundary ("What is the longest range allowed?"),
- a format ("How is 1234.5 written in the file?"),
- a permission or failure ("What does a viewer get from the URL?"),
- a fence ("Can one export cover two clients?"),
- a decision ("Which encoding, and why?").

In `quiz-key.json`, `expect` lists the words or numbers a correct answer must contain, and
`refs` lists the spec ids that should answer it.

### 5. Run the cold read

Start a reader with no history: a subagent or a new session, given only `spec.md` (plus
read-only code access for the builder lens) and the brief in
`templates/cold-reader-brief.md`. Never paste your summary or the answer key. If you cannot
start a fresh context, ask a human who was not involved, or at least clear the conversation
and load only the file.

Use one or more lenses, each in its own fresh reader:

- **Builder**: could I start coding tomorrow? What would I have to guess?
- **Tester**: can every example become a test with a clear pass or fail?
- **Newcomer**: which words, systems or steps are assumed and never explained?
- **Skeptic**: what happens at zero, at the maximum, on retry, on a second click, across
  time zones, with the wrong role?

Save the answers as JSON and score them:

```bash
python3 scripts/speccheck.py quiz quiz-key.json cold-answers.json
```

Each question comes back as `MATCH`, `MISREAD` (answered but missing an expected term),
`GAP` (the reader said `NOT IN SPEC`), or `UNANSWERED`. The verdict is `PASS` when at
least 80% match and there is no gap; otherwise `FIX_SPEC`, with the spec ids to fix.

### 6. Fix the spec, not the reader

- A `GAP` means the spec is silent: add a requirement, example, glossary entry or decision.
- A `MISREAD` means the spec is ambiguous: reword it, usually by adding an example with
  numbers.
- If the reader was right and your key was wrong, you just found a hidden disagreement in
  your own thinking. Decide, write the decision down, and fix the key.
- Also act on the reader's "would stop and ask" list.

Then run the lint and a cold read again with a **new** reader (the old one now has context).
If a third round still fails, the feature is probably too big or not yet decided: split it,
or take the open questions back to the user.

Set `status: ready` only after `lint` says `READY` and `quiz` says `PASS`.

### 7. Build against the examples

- Work in small pieces, one requirement at a time.
- For each example, write the failing test first, named after it (`test_R3_a_...`), watch
  it fail for the expected reason, then make the smallest change that passes.
- Get it working, then clean it up while the tests stay green.
- If the code needs behavior the spec does not describe, stop and add it to the spec first
  (new id, example, decision). The spec stays the single source of truth.

### 8. Trace before merge

```bash
python3 scripts/speccheck.py trace spec.md tests/
```

| Verdict | Meaning |
| --- | --- |
| `TRACED` | Every requirement is named by at least one test, and no test names an id the spec lacks. |
| `PARTIAL` | Some requirements have no test. Write the test or explain why in the spec. |
| `DRIFT` | A test names an id that is not in the spec. Code moved without the spec: update the spec or remove the id. |

Put the trace output in the pull request description. Later changes start by editing the
spec, then the tests, then the code.

## Example

`examples/csv-export/` shows a full round trip:

- `spec.draft.md` lints `BLOCKED`: "quickly", a requirement with no example, an example
  with no outcome, a "ready" status with an unowned question, no out-of-scope section.
- The first cold read (`cold-answers.round1.json`) scores 3/7 with two `NOT IN SPEC`
  answers: nobody said which time zone sets the date or which file encoding to use.
- `spec.md` adds a glossary, the 366-day limit, the client-time-zone example, and decision
  D1 (UTF-8 with a byte-order mark for Excel). It lints `READY`.
- A new reader (`cold-answers.round2.json`) scores 7/7, `PASS`.
- `tests/test_export.py` traces every requirement: `TRACED`.

`examples/booking-reminder/` is a Chinese spec for appointment reminder texts. It lints
`REVISE` (vague "简单友好", an example with no outcome, an unowned question) and its tests
show `DRIFT`: a retry test names `R6`, which the spec never defined.

## Tips

- Keep the spec short enough to read in ten minutes. If it is not, it is probably two
  features.
- Examples beat adjectives. When two people argue about a sentence, add an example with
  numbers and the argument usually ends.
- The cold reader must be truly cold. A subagent that inherits your conversation is not a
  cold reader.
- Never let the cold reader edit the spec. Its job is to find holes, yours is to decide.
- An open question with an owner is honest. A vague requirement that hides the question is
  a bug waiting to happen.
- The lint messages are in English for every spec language; the Chinese markers
  (状态, 需求, 例, 必须, 不做, 待定问题, 负责人, 不在规格中) are all recognized.
- Example ids use a single lowercase letter or a number after the dot (`R2.a`, `R2.3`) so the
  trace can tell `test_R2_a` from `test_R2_happy_path`.
