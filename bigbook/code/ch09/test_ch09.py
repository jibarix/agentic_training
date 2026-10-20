"""Offline tests for Chapter 9: reading amounts, the vote and its exact average, the judge, the
experiment's plan, rows and halting, and the report. No model: Chapter 1's ScriptedClient replays
fixed replies, so the tests check the code around the model, not the model.

Usage: python -m unittest -v test_ch09
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
sys.path.insert(1, str(HERE.parent / "ch04"))
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
import experiment                                        # noqa: E402
import sampling as S                                     # noqa: E402
import stats                                             # noqa: E402
from llm import ScriptedClient, call                     # noqa: E402  Chapter 1's

_spec = importlib.util.spec_from_file_location("ch09_report", HERE / "report.py")
report = importlib.util.module_from_spec(_spec)          # by path: Chapter 4's report.py is on the path too
_spec.loader.exec_module(report)
TASKS = json.loads((HERE.parent / "ch04" / "tasks_long.json").read_text(encoding="utf-8"))
D = Decimal


def say(text):
    return {"role": "assistant", "content": text}


class Broken:
    def chat(self, messages, tools=None):
        raise ConnectionError("server went away")


class TestAmount(unittest.TestCase):
    def test_reads_the_last_final_line(self):
        self.assertEqual(S.amount("Final answer: 5 USD\nNo, wait.\n**Final answer:** $1,234.50"), D("1234.50"))
        self.assertEqual(S.amount("Final answer: 710 USD."), D("710"))

    def test_none_without_one_number(self):
        for text in ("710 USD", "Final answer: 3 trips, 710 USD", "Final answer: unknown", "", None):
            self.assertIsNone(S.amount(text), text)

    def test_the_scorers_shape(self):
        # a word before the number must be a unit: a refusal or a hedge doesn't vote
        for text in ("Final answer: not 710 USD", "Final answer: about 710 USD", "Final answer: 710 or 720"):
            self.assertIsNone(S.amount(text, ["USD"]), text)
        self.assertEqual(S.amount("Final answer: USD 710", ["USD"]), D("710"))
        self.assertEqual(S.amount("Final answer: 710 dollars"), D("710"))        # the unit is scored, not parsed


class TestVote(unittest.TestCase):
    def test_majority_wins(self):
        self.assertEqual(S.vote([(D(5), True), (D(5), True), (D(7), False)]), 1.0)
        self.assertEqual(S.vote([(D(7), False), (D(7), False), (D(5), True)]), 0.0)

    def test_ties_break_at_random(self):
        self.assertEqual(S.vote([(D(5), True), (D(7), False)]), 0.5)
        self.assertAlmostEqual(S.vote([(D(5), True), (D(7), False), (D(9), False)]), 1 / 3)

    def test_runs_without_an_amount_abstain(self):
        self.assertEqual(S.vote([(None, False), (None, False), (D(5), True)]), 1.0)
        self.assertEqual(S.vote([(None, False), (None, None)]), 0.0)
        self.assertEqual(S.vote([]), 0.0)

    def test_a_winning_amount_scores_its_runs(self):
        # same number, one with a unit the scorer refused: the vote returns one of the two at random
        self.assertEqual(S.vote([(D(5), True), (D(5), False), (D(7), False)]), 0.5)

    def test_vote_k_is_the_average_over_every_subset(self):
        runs = [(D(5), True), (D(5), True), (D(7), False), (D(7), False), (None, False), (D(9), False)]
        want = fmean(S.vote(c) for c in combinations(runs, 3))
        self.assertAlmostEqual(S.vote_k(runs, 3), want)
        self.assertEqual(S.vote_k(runs, len(runs)), S.vote(runs))
        self.assertAlmostEqual(S.vote_k(runs, 1), 2 / 6)        # one run: pass@1

    def test_agreement(self):
        self.assertEqual(S.agreement([(D(5), True), (D(5), True), (D(7), False), (None, False)]), 0.5)
        self.assertEqual(S.agreement([(None, False)]), 0.0)


class TestJudge(unittest.TestCase):
    def test_choice_is_parsed_from_the_last_line(self):
        client = ScriptedClient([say("Attempt 1 looks off.\nChoice: 1\nOn reflection:\n**Choice:** 2")])
        i, reply, _ = S.judge(client, "Q?", ["a", "b", "c"])
        self.assertEqual(i, 1)
        self.assertEqual(S.judge(ScriptedClient([say("Choice: Attempt 3.")]), "Q?", ["a", "b", "c"])[0], 2)
        prompt = client.seen[0][1]["content"]
        self.assertLess(prompt.index("=== Attempt 1 ===\na"), prompt.index("=== Attempt 3 ===\nc"))
        self.assertEqual(client.seen[0][0]["content"], S.JUDGE)

    def test_no_or_out_of_range_choice_is_none(self):
        for text in ("I can't tell.", "Choice: 0", "Choice: 4", "Choice: 1 or 2", "Choice: 1.5",
                     "Choice: 1\nChoice: none", "Choice: 1\nChoice: -1"):
            self.assertIsNone(S.judge(ScriptedClient([say(text)]), "Q?", ["a", "b", "c"])[0], text)

    def test_a_call_that_raises_is_not_caught(self):
        with self.assertRaises(ConnectionError):
            S.judge(Broken(), "Q?", ["a"])

    def test_evidence(self):
        trace = [{"type": "model", "content": "", "calls": []},
                 {"type": "tool", "name": "lookup", "observation": "x" * 500},
                 {"type": "model", "content": "Final answer: 5 USD"}]
        e = S.evidence(trace, max_obs=100)
        self.assertIn("- lookup: " + "x" * 100 + " [...]", e)
        self.assertTrue(e.endswith("Reply:\nFinal answer: 5 USD"))
        self.assertIn("(no reply)", S.evidence([]))
        long = [{"type": "tool", "name": "lookup", "observation": "y" * 300}] * 30
        self.assertIn("[... more tool results omitted ...]", S.evidence(long))


class TestRecorder(unittest.TestCase):
    def test_counts_thinking_and_errors(self):
        class Thinker:
            def chat(self, messages, tools=None):
                return ({"role": "assistant", "content": "hi", "reasoning": "abcd"},
                        {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10})
        rec = S.Recorder(Thinker())
        rec.chat([])
        self.assertEqual(rec.calls, [{"prompt": 7, "completion": 3, "total": 10, "thinking_chars": 4}])
        self.assertEqual(rec.thoughts, ["abcd"])                 # kept: Chapter 1's trace drops it
        rec = S.Recorder(Broken())
        with self.assertRaises(ConnectionError):
            rec.chat([])
        self.assertEqual(rec.errors, ["ConnectionError: server went away"])


class TestExperiment(unittest.TestCase):
    def test_settings_are_chapter_4s(self):
        self.assertEqual(experiment.AGENT_KW, experiment.ch04.AGENT_KW)
        self.assertTrue(experiment.PROMPT.endswith(experiment.ch04.FINAL))
        self.assertEqual(experiment.THINK, {"off": {"reasoning_effort": "none"}, "on": {"reasoning_effort": "high"}})
        self.assertEqual(experiment.JUDGE_KW["extra"], experiment.THINK["off"])

    def test_groups(self):
        self.assertEqual(experiment.groups(10, 5), [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]])
        self.assertEqual(experiment.groups(7, 3), [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(experiment.groups(10, 5), report.groups())

    def test_plan(self):
        p = experiment.plan(TASKS, 10, 3, 5)
        gen = [x for x in p if x[0] == "gen"]
        self.assertEqual((len(gen), len(p) - len(gen)), (30 * 13, 30 * 2 * 2))
        self.assertEqual([x[0] for x in p[len(gen):]], ["judge"] * 120)    # every judge after every run
        self.assertEqual([(s, c) for _, s, _, c in gen[:3]], [(1, "off"), (1, "on"), (1, "off")])
        keys = {(x, s, t["id"], c) for x, s, t, c in p}
        self.assertEqual(keys, report.planned({t["id"]: t for t in TASKS}))

    def test_row(self):
        t = next(x for x in TASKS if x["id"] == "meals_emp0103")
        client = ScriptedClient([{"role": "assistant", "content": "",
                                  "tool_calls": [call("calculator", {"expression": "700 + 10"}, "c1")]},
                                 say(f"It is 710.\nFinal answer: {t['answer']:g} USD")])
        row, trace, thoughts = experiment.generate(t, client)
        self.assertEqual((row["ok"], row["status"], row["amount"], row["calls"], row["tokens"]),
                         (True, "answered", "710", 2, 200))
        self.assertIsNone(row["completion"])                     # the scripted client gives no completion count
        self.assertEqual((trace[-1]["type"], thoughts), ("end", ["", ""]))
        row, _, _ = experiment.generate(t, ScriptedClient([say("about seven hundred")]))
        self.assertEqual((row["ok"], row["amount"]), (None, None))

    def test_server_failure_halts(self):
        with self.assertRaises(experiment.Halted):
            experiment.generate(TASKS[0], Broken())
        with self.assertRaises(experiment.Halted):
            experiment.pick(TASKS[0], [1, 2], "forward", {1: [], 2: []}, Broken())

    def test_pick_maps_the_choice_back_to_a_seed(self):
        traces = {s: [{"type": "model", "content": f"Final answer: {s} USD"}] for s in (1, 2, 3)}
        fwd = experiment.pick(TASKS[0], [1, 2, 3], "forward", traces, ScriptedClient([say("Choice: 1")]))
        rev = experiment.pick(TASKS[0], [1, 2, 3], "reverse", traces, ScriptedClient([say("Choice: 1")]))
        self.assertEqual((fwd["shown"], fwd["pick"], rev["shown"], rev["pick"]), ([1, 2, 3], 1, [3, 2, 1], 3))
        bad = experiment.pick(TASKS[0], [1, 2, 3], "forward", traces, ScriptedClient([say("not sure")]))
        self.assertIsNone(bad["pick"])


def design(off_right, on_right=(), picks=None, amounts=None):
    """Rows of a complete design on every task: off_right[s-1] says whether seed s was right.

    Wrong runs give 1 more than the answer. amounts, if given, sets each thinking-off seed instead:
    "r" the answer, "w" one more, None no amount (all but "r" wrong)."""
    rows = []
    for t in TASKS:
        for c, right, n in (("off", off_right, report.OFF), ("on", on_right, report.ON)):
            for s in range(1, n + 1):
                ok = bool(right[s - 1]) if s <= len(right) else False
                a = t["answer"] if ok else t["answer"] + 1
                if amounts and c == "off":
                    ok = amounts[s - 1] == "r"
                    a = {"r": t["answer"], "w": t["answer"] + 1, None: None}[amounts[s - 1]]
                rows.append({"part": "gen", "seed": s, "cond": c, "id": t["id"], "cluster": t["cluster"],
                             "status": "answered", "ok": ok, "amount": None if a is None else f"{a:g}",
                             "steps": 3, "tokens": 1000 if c == "off" else 3000, "completion": 100,
                             "thinking_chars": 0 if c == "off" else 500, "seconds": 10 if c == "off" else 40})
        for g, grp in enumerate(report.groups(), 1):
            for o in ("forward", "reverse"):
                shown = grp if o == "forward" else grp[::-1]
                rows.append({"part": "judge", "seed": g, "cond": o, "id": t["id"], "cluster": t["cluster"],
                             "shown": shown, "pick": (picks or {}).get((g, o), shown[0]), "reply": "",
                             "tokens": 500, "seconds": 5})
    return rows


class TestReport(unittest.TestCase):
    def test_numbers(self):
        right = [1, 1, 0, 0, 0, 1, 0, 0, 0, 0]               # three of ten
        rows = design(right, on_right=[1, 1, 0], picks={(1, "forward"): 1, (1, "reverse"): 2,
                                                        (2, "forward"): 7, (2, "reverse"): 6})
        table, nums = report.render(rows)
        runs = [(D(1) if r else D(2), bool(r)) for r in right]   # every wrong run gives the same wrong amount
        self.assertEqual(nums["OffMean"], "30.0")
        self.assertEqual(nums["OnMean"], "66.7")
        self.assertEqual(nums["VoteMean"], report.pct(S.vote_k(runs, 5)))
        self.assertEqual(nums["OracleMean"], report.pct(stats.pass_at_k(10, 3, 5)))
        self.assertEqual(nums["HatK"], "0.0")
        self.assertEqual(nums["JudgeMean"], "75.0")             # picks 1, 2 and 6 were right, 7 wrong
        self.assertEqual(nums["VoteSameMean"], report.pct(fmean([S.vote(runs[:5]), S.vote(runs[5:])])))
        self.assertEqual(nums["GapVote"], report.pct(stats.pass_at_k(10, 3, 5) - S.vote_k(runs, 5)))
        self.assertEqual(nums["JudgeSamePick"], "0/60")
        self.assertEqual((nums["OffTokens"], nums["VoteTokens"], nums["JudgeTokens"], nums["JudgeCallTokens"]),
                         ("1,000", "5,000", "5,500", "500"))   # five runs, plus the judge's call
        self.assertEqual(len(report.MACROS), len(set(report.MACROS)))
        self.assertEqual(len(table), 5)
        self.assertEqual({k for k in nums if not k.startswith("_")} - set(report.MACROS), set())   # _fig feeds the figure
        self.assertIsNone(report.rows_not_the_design(rows, report.planned(report.tasks())))

    def test_the_vote_can_lose_what_the_oracle_finds(self):
        # two runs share a wrong amount and outvote the one right run (Chapter 4's mileage_emp0146)
        rows = design([], amounts=["w", "w", None, None, None, "r", None, None, None, None])
        _, nums = report.render(rows)
        self.assertEqual(nums["OracleMean"], "50.0")
        self.assertLess(float(nums["VoteMean"]), 50.0)

    def test_the_judges_gap_uses_its_own_groups(self):
        # one right run in each group and a judge that always finds it: no gap, though pass@5 is 77.8
        rows = design([1, 0, 0, 0, 0, 1, 0, 0, 0, 0], picks={(1, "forward"): 1, (1, "reverse"): 1,
                                                             (2, "forward"): 6, (2, "reverse"): 6})
        _, nums = report.render(rows)
        self.assertEqual((nums["JudgeMean"], nums["OracleSameMean"], nums["GapJudge"]), ("100.0", "100.0", "0.0"))
        self.assertEqual(nums["OracleMean"], "77.8")

    def test_unknown_usage_is_not_zero_cost(self):
        rows = [{**r, "tokens": None} if r["part"] == "judge" else r for r in design([1] * 10)]
        table, nums = report.render(rows)
        self.assertEqual((nums["JudgeTokens"], nums["JudgeCallTokens"], nums["VoteTokens"]), ("--", "--", "5,000"))
        rows = [{**r, "completion": None} for r in design([1] * 10)]
        self.assertEqual(report.render(rows)[1]["OffCompletion"], "--")

    def test_labels_override_ok_and_amount(self):
        tmp = Path(tempfile.mkdtemp(dir=HERE))
        try:
            rows = design([0] * 10)
            t = TASKS[0]
            (tmp / "traces.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            (tmp / "adjudication.json").write_text(json.dumps({"labels": [
                {"cond": "off", "id": t["id"], "seed": 1, "label": True, "amount": f"{t['answer']:g}"}]}))
            got = [r for r in report.load(tmp.name) if r["id"] == t["id"] and r["seed"] == 1 and r["part"] == "gen"]
            off = next(r for r in got if r["cond"] == "off")
            on = next(r for r in got if r["cond"] == "on")
            self.assertEqual((off["ok"], off["amount"], on["ok"]), (True, f"{t['answer']:g}", False))
            self.assertEqual(off["raw"], {"ok": False, "amount": f"{t['answer'] + 1:g}"})
            _, nums = report.numbers(report.load(tmp.name))
            self.assertEqual((nums["LabelledOff"], nums["LabelledOn"], nums["RawOffMean"]), (1, 0, "0.0"))
            self.assertGreater(float(nums["OffMean"]), 0.0)       # the label counts; the raw mean ignores it
            self.assertEqual({k for k in nums if not k.startswith("_")} - set(report.MACROS), set())   # _fig feeds the figure
        finally:
            shutil.rmtree(tmp)

    def test_completeness(self):
        want = report.planned(report.tasks())
        rows = design([1] * 10)
        self.assertIsNone(report.rows_not_the_design(rows, want))
        self.assertIn("duplicate", report.rows_not_the_design(rows + rows[:1], want))
        swapped = rows[1:] + [{**rows[0], "seed": 99}]
        self.assertIn("lacks 1 planned runs and has 1 unplanned", report.rows_not_the_design(swapped, want))

    def test_placeholders(self):
        files = report.files([], {})
        self.assertIn("has not been made yet", files["ch09_ways.tex"])
        self.assertEqual(files["ch09_numbers.tex"].count("{--}"), len(report.MACROS))


if __name__ == "__main__":
    unittest.main()
