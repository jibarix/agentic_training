"""Offline tests for Chapter 10: the split, the worked examples, the reflection and its checks, the
offline numbers and the fine-tuning file, the experiment's plan, rows and halting, and the report.
No model: Chapter 1's ScriptedClient replays fixed replies, so the tests check the code around the
model, not the model.

Usage: python -m unittest -v test_ch10
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
sys.path.insert(1, str(HERE.parent / "ch04"))
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
import experiment                                        # noqa: E402
import offline as F                                      # noqa: E402
import optimise as O                                     # noqa: E402
from llm import ScriptedClient, call                     # noqa: E402  Chapter 1's

_spec = importlib.util.spec_from_file_location("ch10_report", HERE / "report.py")
report = importlib.util.module_from_spec(_spec)          # by path: Chapter 4's report.py is on the path too
_spec.loader.exec_module(report)
TASKS = json.loads((O.CH04 / "tasks_long.json").read_text(encoding="utf-8"))
BY_ID = {t["id"]: t for t in TASKS}
SPLIT = json.loads(O.SPLIT.read_text())


def say(text):
    return {"role": "assistant", "content": text}


class Broken:
    def chat(self, messages, tools=None):
        raise ConnectionError("server went away")


def run(tid, seed, ok, steps=3, cluster=None):
    trace = [{"type": "model", "content": "", "calls": [{"id": "c1", "name": "lookup", "arguments": '{"query":"x"}'}]},
             {"type": "tool", "id": "c1", "name": "lookup", "observation": "y" * 500},
             {"type": "model", "content": "Final answer: 5 USD", "calls": []}, {"type": "end"}]
    return {"id": tid, "seed": seed, "ok": ok, "steps": steps, "cluster": cluster or tid.split("_")[0],
            "trace": trace, "seconds": 20, "max_prompt": 1000}


class TestSplit(unittest.TestCase):
    def test_the_recorded_split_is_the_functions(self):
        right = O.successes(O.ch4_rows())
        self.assertEqual(O.split(TASKS, right), {"train": SPLIT["train"], "heldout": SPLIT["heldout"]})
        self.assertEqual(SPLIT["seed"], O.SPLIT_SEED)

    def test_halves_by_task_and_kind(self):
        tr, he = SPLIT["train"], SPLIT["heldout"]
        self.assertEqual((len(tr), len(he), set(tr) & set(he)), (15, 15, set()))
        self.assertEqual(set(tr) | set(he), set(BY_ID))
        for kind in {t["cluster"] for t in TASKS}:
            self.assertEqual(sum(BY_ID[t]["cluster"] == kind for t in tr), 3, kind)

    def test_balanced_on_chapter_4s_successes(self):
        right = O.successes(O.ch4_rows())
        self.assertLessEqual(abs(sum(right[t] for t in SPLIT["train"]) - sum(right[t] for t in SPLIT["heldout"])), 3)

    def test_pairs_are_neighbours(self):
        tasks = [{"id": f"k_{i}", "cluster": "k"} for i in range(4)]
        sp = O.split(tasks, {"k_0": 3, "k_1": 0, "k_2": 3, "k_3": 0}, seed=1)
        self.assertEqual(sorted(sp["train"] + sp["heldout"]), [f"k_{i}" for i in range(4)])
        # each side gets one of the two 0s and one of the two 3s
        self.assertEqual(sorted({"k_0": 3, "k_1": 0, "k_2": 3, "k_3": 0}[t] for t in sp["train"]), [0, 3])


class TestDemos(unittest.TestCase):
    def test_only_passing_training_runs_of_different_kinds(self):
        rows = [run("meals_a", 1, True, 5), run("meals_b", 1, True, 3), run("full_c", 2, True, 9),
                run("full_d", 1, False, 2), run("lodging_e", 1, True, 1)]
        got = O.bootstrap(rows, {"meals_a", "meals_b", "full_c", "full_d"}, 2)
        self.assertEqual([(r["id"], r["seed"]) for r in got], [("meals_b", 1), ("full_c", 2)])
        self.assertEqual(O.bootstrap(rows, {"full_d"}, 2), [])

    def test_no_demos(self):
        rows = [run("meals_a", 1, True, 5), run("full_c", 2, True, 9)]
        self.assertEqual(O.bootstrap(rows, {"meals_a", "full_c"}, 0), [])
        self.assertEqual(experiment.demos(O.ch4_rows(), BY_ID, SPLIT["train"], 0), ([], []))

    def test_no_held_out_task_in_arm_b(self):
        src = experiment.demos(O.ch4_rows(), BY_ID, SPLIT["train"], 2)[1]
        self.assertEqual(len(src), 2)
        self.assertTrue(all(s["id"] in SPLIT["train"] for s in src))
        prompt = O.with_demos(experiment.PROMPT, experiment.demos(O.ch4_rows(), BY_ID, SPLIT["train"], 2)[0])
        for t in SPLIT["heldout"]:
            self.assertNotIn(t.split("_")[1].upper(), prompt)

    def test_render_cuts_results(self):
        text = O.render_demo("Q?", run("meals_a", 1, True)["trace"])
        self.assertEqual(text.splitlines()[0], "Question: Q?")
        self.assertIn('Tool call: lookup({"query":"x"})', text)
        self.assertIn("y" * 300 + " [...]", text)
        self.assertNotIn("y" * 301, text)
        self.assertTrue(text.endswith("Reply: Final answer: 5 USD"))
        self.assertEqual(O.with_demos("P", []), "P")
        self.assertIn("=== Example 2 ===", O.with_demos("P", ["a", "b"]))


class TestReflect(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(O.parse_instruction("x <instructions> Read files. </instructions>"), ("Read files.", ""))
        self.assertEqual(O.parse_instruction("<instructions>a</instructions><instructions>b</instructions>")[0], "b")
        for text, why in (("no tags", "no <instructions> block"), ("<instructions> </instructions>", "no <instructions>"),
                          (f"<instructions>{'w' * 2001}</instructions>", "over 2000"),
                          ("<instructions>Check EMP0131 first.</instructions>", "names an employee"),
                          ("<instructions>See TR0099.</instructions>", "names an employee"), (None, "no <")):
            new, got = O.parse_instruction(text)
            self.assertIsNone(new)
            self.assertIn(why, got)

    def test_ids_in_any_case_are_refused(self):
        for text in ("<instructions>For emp0110 use 710 USD; see tr0099.</instructions>",
                     "<instructions>Check Emp0131 first.</instructions>"):
            new, why = O.parse_instruction(text)
            self.assertIsNone(new)
            self.assertIn("names an employee", why)

    def test_minibatch_is_fixed_by_the_step(self):
        failed = [f"t{i}" for i in range(10)]
        self.assertEqual(O.minibatch(failed, 1), O.minibatch(list(reversed(failed)), 1))
        self.assertEqual(len(O.minibatch(failed, 2)), 3)
        self.assertEqual(O.minibatch(["a", "b"], 3), ["a", "b"])
        self.assertEqual(O.minibatch([], 1), [])

    def test_reflect_shows_the_failures_and_the_answer(self):
        t = TASKS[0]
        client = ScriptedClient([say("Thinking.\n<instructions>Read every file.</instructions>")])
        fb = [O.failure(t, run(t["id"], 1, False)["trace"], "Final answer: 5 USD")]
        new, why, text, usage = O.reflect(client, "Old.", fb)
        self.assertEqual((new, why, usage), ("Read every file.", "", {"total_tokens": 100}))
        sent = client.seen[0]
        self.assertEqual(sent[0]["content"], O.REFLECT)
        self.assertIn("Current instructions:\nOld.", sent[1]["content"])
        self.assertIn(f"The expected answer was {t['answer']:g} USD", sent[1]["content"])

    def test_a_call_that_raises_is_not_caught(self):
        with self.assertRaises(ConnectionError):
            O.reflect(Broken(), "Old.", ["x"])


class TestOffline(unittest.TestCase):
    def test_degenerate(self):
        right = {"a": 0, "b": 3, "c": 1, "d": 2}
        self.assertEqual(F.degenerate(right, 3, 3), 0.5)
        self.assertAlmostEqual(F.degenerate(right, 3, 2), (1 + 1 + 5 / 9 + 5 / 9) / 4)

    def test_chapter_4s_numbers(self):
        nums = report.offline()
        self.assertEqual((nums["ChRuns"], nums["ChRight"], nums["DegenThree"], nums["DegenEight"]),
                         (90, 26, "60.0", "61.6"))
        self.assertEqual((nums["TrainRight"] + nums["HeldRight"], nums["MDETen"], nums["MDEFive"]), (26, "11.8", "16.7"))
        self.assertEqual((nums["PlannedRuns"], nums["PlannedRunsFive"]), (60 + 450, 60 + 225))

    def test_power_is_fixed_at_ten_and_five_seeds(self):
        saved = report.SEEDS
        try:
            report.SEEDS = 5
            nums = report.offline()
        finally:
            report.SEEDS = saved
        self.assertEqual((nums["MDETen"], nums["MDEFive"], nums["PlannedRuns"]), ("11.8", "16.7", 510))

    def test_bill(self):
        self.assertEqual(F.bill(3600, 2), 2.0)
        self.assertEqual(F.ROLLOUTS["A3"], 6400)

    def test_sft_messages(self):
        r = run("meals_a", 1, True)
        m = F.messages("S", "Q?", r["trace"])
        self.assertEqual([x["role"] for x in m], ["system", "user", "assistant", "tool", "assistant"])
        self.assertEqual([x["weight"] for x in m], [0, 0, 1, 0, 1])
        self.assertEqual(m[2]["tool_calls"][0]["function"], {"name": "lookup", "arguments": '{"query":"x"}'})
        self.assertEqual(m[3]["tool_call_id"], "c1")
        self.assertNotIn("tool_calls", m[4])

    def test_sft_rows_are_passing_training_runs(self):
        rows = [run("meals_a", 2, True), run("meals_a", 1, True), run("meals_b", 1, False), run("full_c", 1, True)]
        got = F.sft_rows(rows, {"meals_a": {"task": "Q"}, "meals_b": {"task": "Q"}}, {"meals_a", "meals_b"}, "S")
        self.assertEqual([(r["id"], r["seed"]) for r in got], [("meals_a", 1), ("meals_a", 2)])

    def test_the_exported_file(self):
        rows = [json.loads(line) for line in F.SFT.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), report.offline()["SFTExamples"])
        self.assertEqual({t["function"]["name"] for t in rows[0]["tools"]}, {"lookup", "read_file", "calculator"})
        self.assertTrue(all(r["id"] in SPLIT["train"] for r in rows))


class TestExperiment(unittest.TestCase):
    def test_settings_are_chapter_4s(self):
        self.assertEqual(experiment.AGENT_KW, experiment.ch04.AGENT_KW)
        self.assertEqual(experiment.PROMPT, experiment.SYSTEM + experiment.ch04.FINAL)
        self.assertEqual(experiment.THINK_OFF, {"reasoning_effort": "none"})
        self.assertEqual(experiment.REFLECT_KW["extra"], experiment.THINK_OFF)
        self.assertEqual((experiment.DEFAULTS["seeds"], experiment.DEFAULTS["candidates"], experiment.DEFAULTS["demos"]),
                         (report.SEEDS, report.CANDIDATES, report.DEMOS))
        self.assertIn("ch04/run/traces.jsonl", experiment.CODE)
        self.assertIn("ch10/split.json", experiment.CODE)

    def test_plan(self):
        p = experiment.held_plan(SPLIT["heldout"], 10)
        self.assertEqual(len(p), 450)
        self.assertEqual([a for *_, a in p[:4]], ["A", "B", "C", "A"])   # arms interleaved on each task
        reflects = [{"part": "reflect", "seed": s, "instruction": "x"} for s in range(1, 5)]
        want = report.planned(SPLIT["train"], SPLIT["heldout"], reflects)
        self.assertEqual(len(want), 4 + 60 + 450)
        self.assertEqual(set(p), {k for k in want if k[0] == "held"})
        reflects[1]["instruction"] = None                                # an invalid proposal is not run
        self.assertEqual(len(report.planned(SPLIT["train"], SPLIT["heldout"], reflects)), 4 + 45 + 450)

    def test_row(self):
        t = BY_ID["meals_emp0103"]
        client = ScriptedClient([{"role": "assistant", "content": "",
                                  "tool_calls": [call("calculator", {"expression": "700 + 10"}, "c1")]},
                                 say(f"It is 710.\nFinal answer: {t['answer']:g} USD")])
        row, trace = experiment.generate(t, client, experiment.PROMPT)
        self.assertEqual((row["ok"], row["status"], row["calls"], row["tokens"]), (True, "answered", 2, 200))
        self.assertIsNone(row["max_prompt"])                     # the scripted client gives no prompt count
        self.assertEqual(client.seen[0][0]["content"], experiment.PROMPT)
        self.assertEqual(trace[-1]["type"], "end")

    def test_server_failure_halts(self):
        with self.assertRaises(experiment.Halted):
            experiment.generate(TASKS[0], Broken(), experiment.PROMPT)

    def test_best_and_parent(self):
        self.assertEqual(experiment.best({1: 0.2, 2: 0.4, 3: 0.4}), 2)
        self.assertIsNone(experiment.best({}))
        base = ("S", [("t", {"ok": True}, []), ("u", {"ok": False}, [])])          # 0.5
        worse = {1: ("one", [("t", {"ok": False}, []), ("u", {"ok": False}, [])])}
        better = {1: ("one", [("t", {"ok": True}, []), ("u", {"ok": True}, [])])}
        self.assertEqual(experiment.parent_of(2, worse, base)[0], "S")
        self.assertEqual(experiment.parent_of(2, better, base)[0], "one")
        self.assertEqual(experiment.parent_of(1, better, base)[0], "S")           # only earlier steps count


def design(right_by_arm, refl_valid=(True, True, True, True)):
    """Rows of a complete design: right_by_arm[arm][s-1] says whether seed s of that arm was right."""
    rows = []
    for s, v in enumerate(refl_valid, 1):
        rows.append({"part": "reflect", "seed": s, "id": "-", "cond": "-", "instruction": "x" if v else None})
        if v:
            rows += [{"part": "search", "seed": s, "id": t, "cond": "C", "ok": s == 2, "status": "answered"}
                     for t in SPLIT["train"]]
    for arm, right in right_by_arm.items():
        for s in range(1, report.SEEDS + 1):
            for t in SPLIT["heldout"]:
                rows.append({"part": "held", "seed": s, "id": t, "cond": arm, "cluster": BY_ID[t]["cluster"],
                             "status": "answered", "ok": bool(right[s - 1]), "steps": 4, "tokens": 1000,
                             "seconds": 20, "max_prompt": 3000 if arm == "B" else 1000})
    return rows


class TestReport(unittest.TestCase):
    ALL = {"A": [1, 0, 0, 0, 0, 0, 0, 0, 0, 0], "B": [1, 1, 0, 0, 0, 0, 0, 0, 0, 0], "C": [1] * 5 + [0] * 5}

    def test_numbers(self):
        rows = design(self.ALL)
        table, nums = report.render(rows)
        self.assertEqual((nums["AMean"], nums["BMean"], nums["CMean"]), ("10.0", "20.0", "50.0"))
        self.assertEqual((nums["BADiff"], nums["CADiff"]), ("10.0", "40.0"))
        self.assertEqual((nums["ARuns"], nums["BRight"], nums["BMaxPrompt"]), (150, 30, "3,000"))
        self.assertEqual((nums["SearchValid"], nums["SearchBest"], nums["SearchBestTrain"], nums["SearchRuns"]),
                         ("4/4", 2, "100.0", 60))
        self.assertEqual(len(table), 3)
        self.assertEqual(len(report.MACROS), len(set(report.MACROS)))
        self.assertIsNone(report.rows_not_the_design(rows, report.planned(SPLIT["train"], SPLIT["heldout"], rows)))
        _, nums = report.numbers(rows)
        self.assertEqual(set(nums) - set(report.MACROS), set())

    def test_unknown_usage_is_not_zero_cost(self):
        rows = [{**r, "tokens": None, "max_prompt": None} if r.get("cond") == "A" else r for r in design(self.ALL)]
        _, nums = report.render(rows)
        self.assertEqual((nums["ATokens"], nums["AMaxPrompt"], nums["BTokens"]), ("--", "--", "1,000"))

    def test_labels_apply_to_held_out_runs_only(self):
        tmp = Path(tempfile.mkdtemp(dir=HERE))
        try:
            rows = design({a: [0] * 10 for a in "ABC"})
            t = SPLIT["heldout"][0]
            (tmp / "traces.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
            (tmp / "adjudication.json").write_text(json.dumps({"labels": [
                {"cond": "A", "id": t, "seed": 1, "label": True},
                {"cond": "C", "id": SPLIT["train"][0], "seed": 1, "label": True}]}))
            got = report.load(tmp.name)
            a = next(r for r in got if r["part"] == "held" and r["id"] == t and r["seed"] == 1 and r["cond"] == "A")
            self.assertEqual((a["ok"], a["raw"]), (True, {"ok": False}))
            self.assertFalse(any("raw" in r for r in got if r["part"] == "search"))
            _, nums = report.numbers(got)
            self.assertEqual((nums["LabelledHeld"], nums["RawAMean"]), (1, "0.0"))
            self.assertGreater(float(nums["AMean"]), 0.0)
        finally:
            shutil.rmtree(tmp)

    def test_completeness(self):
        rows = design(self.ALL)
        want = report.planned(SPLIT["train"], SPLIT["heldout"], rows)
        self.assertIn("duplicate", report.rows_not_the_design(rows + rows[-1:], want))
        swapped = rows[:-1] + [{**rows[-1], "seed": 99}]
        self.assertIn("lacks 1 planned runs and has 1 unplanned", report.rows_not_the_design(swapped, want))
        short = design(self.ALL, refl_valid=(True, False, True, True))
        self.assertIsNone(report.rows_not_the_design(short, report.planned(SPLIT["train"], SPLIT["heldout"], short)))

    def test_placeholders(self):
        files = report.files(*report.numbers([]))
        self.assertIn("has not been made yet", files["ch10_arms.tex"])
        run_macros = len(report.MACROS) - len(report.OFFLINE)
        self.assertEqual(files["ch10_numbers.tex"].count("{--}"), run_macros)
        self.assertIn("\\newcommand{\\ctenChRight}{26}", files["ch10_numbers.tex"])


if __name__ == "__main__":
    unittest.main()
