import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import speccheck as sc  # noqa: E402

GOOD = """# Spec: tiny
status: draft
## Problem
People wait.
## Out of scope
- Nothing else.
## Requirements
- R1: The page MUST load in under 2 seconds on a 4G phone.
  - ex R1.a: given a cold cache, when the page opens, then it is usable within 2 s.
"""


def codes(result):
    return [f["code"] for f in result["findings"]]


class ParseTests(unittest.TestCase):
    def test_reads_status(self):
        self.assertEqual(sc.parse_spec(GOOD)["status"], "draft")

    def test_reads_chinese_status(self):
        self.assertEqual(sc.parse_spec("状态: ready\n")["status"], "ready")

    def test_finds_requirement_and_example(self):
        s = sc.parse_spec(GOOD)
        self.assertIn("R1", s["reqs"])
        self.assertIn("R1.a", s["examples"])

    def test_chinese_example_marker(self):
        s = sc.parse_spec("## 需求\n- R1: 必须发送。\n  - 例 R1.a: 假设 A，那么 B。\n")
        self.assertIn("R1.a", s["examples"])

    def test_fullwidth_colon(self):
        s = sc.parse_spec("- R2：必须记录。\n")
        self.assertIn("R2", s["reqs"])

    def test_sections_detected(self):
        s = sc.parse_spec(GOOD)
        self.assertIn("fence", s["sections"])
        self.assertIn("problem", s["sections"])

    def test_questions_and_decisions(self):
        s = sc.parse_spec("- Q1: which? owner: ann\n- D1: use UTF-8 because Excel.\n")
        self.assertIn("Q1", s["questions"])
        self.assertIn("D1", s["decisions"])

    def test_duplicate_recorded(self):
        s = sc.parse_spec("- R1: MUST a\n- R1: MUST b\n")
        self.assertEqual(s["dupes"], ["R1"])


class VagueTests(unittest.TestCase):
    def test_flags_english(self):
        self.assertIn("fast", sc.vague_words("It MUST be fast."))

    def test_number_suppresses(self):
        self.assertEqual(sc.vague_words("fast: under 200 ms"), [])

    def test_flags_chinese(self):
        self.assertIn("友好", sc.vague_words("界面要友好"))

    def test_word_boundary(self):
        self.assertEqual(sc.vague_words("breakfast menu"), [])

    def test_hyphenated(self):
        self.assertIn("user-friendly", sc.vague_words("a user-friendly form"))


class LintTests(unittest.TestCase):
    def test_good_spec_ready(self):
        self.assertEqual(sc.lint(GOOD)["verdict"], "READY")

    def test_empty_blocked(self):
        r = sc.lint("# nothing\n")
        self.assertEqual(r["verdict"], "BLOCKED")
        self.assertIn("NO_REQUIREMENTS", codes(r))

    def test_missing_example_blocks(self):
        r = sc.lint("## Out of scope\n- x\n## Problem\ny\n- R1: It MUST work in 1 s.\n")
        self.assertIn("NO_EXAMPLE", codes(r))
        self.assertEqual(r["verdict"], "BLOCKED")

    def test_duplicate_blocks(self):
        r = sc.lint(GOOD + "- R1: It MUST also log 1 line.\n")
        self.assertIn("DUPLICATE_ID", codes(r))

    def test_no_strength_major(self):
        r = sc.lint(GOOD.replace("MUST load", "loads"))
        self.assertIn("NO_STRENGTH", codes(r))
        self.assertEqual(r["verdict"], "REVISE")

    def test_vague_requirement(self):
        r = sc.lint(GOOD.replace("in under 2 seconds on a 4G phone", "quickly"))
        self.assertIn("VAGUE", codes(r))

    def test_example_without_outcome(self):
        r = sc.lint(GOOD.replace("then it is usable within 2 s", "it opens in 2 s"))
        self.assertIn("NO_OUTCOME", codes(r))

    def test_orphan_example(self):
        r = sc.lint(GOOD + "  - ex R9.a: given x, then y in 1 s.\n")
        self.assertIn("ORPHAN_EXAMPLE", codes(r))

    def test_unowned_question(self):
        r = sc.lint(GOOD + "## Open questions\n- Q1: which browser?\n")
        self.assertIn("UNOWNED_QUESTION", codes(r))

    def test_owned_question_ok(self):
        r = sc.lint(GOOD + "## Open questions\n- Q1: which browser? owner: ann\n")
        self.assertNotIn("UNOWNED_QUESTION", codes(r))
        self.assertEqual(r["verdict"], "READY")

    def test_at_handle_counts_as_owner(self):
        r = sc.lint(GOOD + "- Q1: which browser? (@lin)\n")
        self.assertNotIn("UNOWNED_QUESTION", codes(r))

    def test_ready_with_open_questions(self):
        r = sc.lint(GOOD.replace("status: draft", "status: ready") + "- Q1: which? owner: ann\n")
        self.assertIn("READY_WITH_OPEN", codes(r))

    def test_missing_fence_is_minor(self):
        r = sc.lint(GOOD.replace("## Out of scope\n- Nothing else.\n", ""))
        self.assertIn("NO_FENCE", codes(r))
        self.assertEqual(r["verdict"], "READY")

    def test_counts(self):
        c = sc.lint(GOOD)["counts"]
        self.assertEqual((c["requirements"], c["examples"]), (1, 1))


KEY = [
    {"id": "C1", "q": "max days?", "expect": ["366"], "refs": ["R2"]},
    {"id": "C2", "q": "zone?", "expect": ["client", "time zone"], "refs": ["R3"]},
    {"id": "C3", "q": "decimals?", "expect": "2", "refs": ["R4"]},
]


class QuizTests(unittest.TestCase):
    def test_all_match_passes(self):
        r = sc.quiz(KEY, {"C1": "366 days", "C2": "The client's time zone", "C3": "2"})
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["score"], 1.0)

    def test_gap_marker_english(self):
        r = sc.quiz(KEY, {"C1": "NOT IN SPEC", "C2": "client time zone", "C3": "2"})
        self.assertEqual(r["rows"][0]["result"], "GAP")
        self.assertEqual(r["verdict"], "FIX_SPEC")

    def test_gap_marker_chinese(self):
        r = sc.quiz(KEY, {"C1": "不在规格中", "C2": "client time zone", "C3": "2"})
        self.assertEqual(r["rows"][0]["result"], "GAP")

    def test_one_gap_fails_even_with_high_score(self):
        key = KEY + [{"id": "C%d" % i, "expect": ["x"]} for i in range(4, 12)]
        ans = {"C%d" % i: "x" for i in range(4, 12)}
        ans.update({"C1": "366", "C2": "client time zone", "C3": "not in spec"})
        r = sc.quiz(key, ans)
        self.assertGreaterEqual(r["score"], 0.8)
        self.assertEqual(r["verdict"], "FIX_SPEC")

    def test_partial_terms_is_misread(self):
        r = sc.quiz(KEY, {"C1": "366", "C2": "client", "C3": "2"})
        self.assertEqual(r["rows"][1]["result"], "MISREAD")
        self.assertEqual(r["rows"][1]["missing"], ["time zone"])

    def test_unanswered(self):
        r = sc.quiz(KEY, {"C1": "366", "C2": "client time zone"})
        self.assertEqual(r["rows"][2]["result"], "UNANSWERED")

    def test_fix_refs_collected(self):
        r = sc.quiz(KEY, {"C1": "a year", "C2": "not in spec", "C3": "2"})
        self.assertEqual(r["fix_refs"], ["R2", "R3"])

    def test_case_and_space_insensitive(self):
        r = sc.quiz(KEY, {"C1": "366", "C2": "CLIENT   Time   Zone", "C3": "2"})
        self.assertEqual(r["rows"][1]["result"], "MATCH")

    def test_unknown_answers_reported(self):
        r = sc.quiz(KEY, {"C1": "366", "C2": "client time zone", "C3": "2", "C9": "?"})
        self.assertEqual(r["unknown_answers"], ["C9"])

    def test_bad_key_raises(self):
        with self.assertRaises(ValueError):
            sc.quiz([], {})
        with self.assertRaises(ValueError):
            sc.quiz([{"q": "no id"}], {})


SPEC_T = """## Requirements
- R1: MUST a in 1 s.
  - ex R1.a: given x, then y.
  - ex R1.b: given z, then w.
- R2: MUST b in 1 s.
  - ex R2.a: given x, then y.
"""


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def write(self, name, body):
        p = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        return p

    def test_all_traced(self):
        self.write("t.py", "def test_R1_a(): pass\ndef test_R2_a(): pass\n")
        r = sc.trace(SPEC_T, [self.tmp])
        self.assertEqual(r["verdict"], "TRACED")
        self.assertEqual(r["untested_examples"], ["R1.b"])

    def test_untested_requirement_partial(self):
        self.write("t.py", "# covers R1.a\n")
        r = sc.trace(SPEC_T, [self.tmp])
        self.assertEqual(r["verdict"], "PARTIAL")
        self.assertEqual(r["untested_requirements"], ["R2"])

    def test_orphan_is_drift(self):
        self.write("t.py", "# R1.a R2.a R7\n")
        r = sc.trace(SPEC_T, [self.tmp])
        self.assertEqual(r["verdict"], "DRIFT")
        self.assertIn("R7", r["orphans"])

    def test_unknown_example_is_orphan(self):
        self.write("t.py", "# R1.a R2.a R2.z\n")
        self.assertIn("R2.z", sc.trace(SPEC_T, [self.tmp])["orphans"])

    def test_underscore_word_not_example(self):
        self.write("t.py", "def test_R1_happy_path(): pass  # R2.a\n")
        r = sc.trace(SPEC_T, [self.tmp])
        self.assertEqual(r["orphans"], {})
        self.assertEqual(r["verdict"], "TRACED")

    def test_ignores_words_like_ror3(self):
        self.write("t.py", "ROR3 HR12 # R1 R2\n")
        self.assertEqual(sc.trace(SPEC_T, [self.tmp])["orphans"], {})

    def test_skips_hidden_dirs_and_binary(self):
        self.write(".git/x.py", "# R9\n")
        with open(os.path.join(self.tmp, "b.bin"), "wb") as fh:
            fh.write(b"\xff\xfe R8 \x00")
        self.write("t.py", "# R1 R2\n")
        self.assertEqual(sc.trace(SPEC_T, [self.tmp])["orphans"], {})

    def test_single_file_path(self):
        p = self.write("t.py", "# R1 R2\n")
        self.assertEqual(sc.trace(SPEC_T, [p])["verdict"], "TRACED")


class CliTests(unittest.TestCase):
    EX = os.path.join(ROOT, "examples")

    def run_cli(self, *args):
        from io import StringIO
        old = sys.stdout
        sys.stdout = StringIO()
        try:
            code = sc.main(list(args))
            out = sys.stdout.getvalue()
        finally:
            sys.stdout = old
        return code, out

    def test_example_spec_ready(self):
        code, out = self.run_cli("lint", os.path.join(self.EX, "csv-export", "spec.md"))
        self.assertEqual(code, 0)
        self.assertIn("READY", out)

    def test_draft_spec_blocked(self):
        code, out = self.run_cli("lint", os.path.join(self.EX, "csv-export", "spec.draft.md"))
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED", out)

    def test_chinese_spec_revise_json(self):
        code, out = self.run_cli("lint", os.path.join(self.EX, "booking-reminder", "spec.md"), "--json")
        self.assertEqual(json.loads(out)["verdict"], "REVISE")

    def test_quiz_rounds(self):
        d = os.path.join(self.EX, "csv-export")
        c1, _ = self.run_cli("quiz", os.path.join(d, "quiz-key.json"), os.path.join(d, "cold-answers.round1.json"))
        c2, _ = self.run_cli("quiz", os.path.join(d, "quiz-key.json"), os.path.join(d, "cold-answers.round2.json"))
        self.assertEqual((c1, c2), (1, 0))

    def test_trace_drift_example(self):
        d = os.path.join(self.EX, "booking-reminder")
        code, out = self.run_cli("trace", os.path.join(d, "spec.md"), os.path.join(d, "tests"))
        self.assertEqual(code, 1)
        self.assertIn("ORPHAN R6", out)

    def test_usage_and_bad_file(self):
        self.assertEqual(self.run_cli()[0], 2)
        self.assertEqual(self.run_cli("lint", "/no/such/file.md")[0], 2)


if __name__ == "__main__":
    unittest.main()
