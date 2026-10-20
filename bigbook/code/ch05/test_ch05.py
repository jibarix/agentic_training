"""Offline tests for Chapter 5: crash and resume at every call, idempotent claims, retries, the
plan loop's stops, and the workflow's reading of the trip log. No model: a fake answers from the
handbook's own data, so every number it gives is right and the tests check only the machinery.

Usage: python -m unittest -v test_ch05
"""
import json
import re
import sys
import tempfile
import unittest
import urllib.error
from decimal import Decimal
from pathlib import Path

from run import TOOLS, durable_run                       # sets the path to Chapters 1 and 4
import make_handbook                                     # Chapter 4's
from durable import Crash, Diverged, Halted, Journal, Run
from faults import Flaky, RetryingClient, TransientError, retry, retrying_tools, waits
from ledger import Ledger
from strategies import EXTRACT, PLAN, final_amount, parse_plan, trip_rows, workflow
import strategies
from llm import call                                     # Chapter 1's
from tools import ToolError

HERE = Path(__file__).parent
TASKS = {t["id"]: t for t in json.loads((HERE.parent / "ch04" / "tasks_long.json").read_text(encoding="utf-8"))}
RATES, _, TRIPS = make_handbook.build()
TRIP = {t["id"]: t for t in TRIPS}
NO_SLEEP = {"sleep": lambda s: None}


def msg(text):
    return {"role": "assistant", "content": text}


class Fake:
    """A model that is always right. Stateless: each reply depends only on the messages, so a
    resumed run gets the same replies as an uninterrupted one. `stuck` lists plan steps it never
    finishes; `plans` are the plans it writes, first to last; `parts` overrides the extraction."""

    def __init__(self, plans=None, stuck=(), parts=None):
        self.plans = plans or [["Find the employee's trips", "Add up the amounts"]]
        self.stuck, self.parts, self.calls = set(stuck), parts, 0

    def chat(self, messages, tools=None):
        self.calls += 1
        system, user = messages[0]["content"], messages[1]["content"]
        if tools is None and system == EXTRACT:
            if self.parts is not None:
                return msg(self.parts), {"total_tokens": 10}
            parts = [p for p in ("meals", "lodging", "mileage") if p in user.lower()]
            return msg(json.dumps({"parts": parts})), {"total_tokens": 10}
        if tools is None and system == PLAN:
            k = min(user.count("This step failed"), len(self.plans) - 1) if "This step failed" in user else 0
            return msg(json.dumps(self.plans[k])), {"total_tokens": 10}
        turns = sum(m["role"] == "assistant" for m in messages)
        step = re.search(r"Your step: (.*)", user)
        if turns == 0 or (step and step.group(1) in self.stuck):
            return {"role": "assistant", "content": "",
                    "tool_calls": [call("lookup", {"query": "per diem"}, f"c{turns}")]}, {"total_tokens": 100}
        return msg(self.answer(user)), {"total_tokens": 100}

    def answer(self, user):
        m = re.match(r"For trip (TR\d{4})", user)
        if m:
            t, q = TRIP[m.group(1)], user.split("reimburse for")[1]
            v = ((Decimal(make_handbook.meals(t, RATES)) if "meals" in q else 0)
                 + (Decimal(make_handbook.lodging(t, RATES)) if "lodging" in q else 0)
                 + (make_handbook.mileage(t) if "mileage" in q else 0))
            return f"Final answer: {v} USD"
        task = next(t for t in TASKS.values() if t["task"] in user)
        if "Your step:" in user and "This is the last step" not in user:
            return "Result: done"
        return f"The total is {task['answer']}.\nFinal answer: {task['answer']} USD"


def go(tmp, strategy, task_id, client, crash=None, **kw):
    return durable_run(strategy, TASKS[task_id]["task"], client, Path(tmp) / "journal.jsonl",
                       Path(tmp) / "ledger.jsonl", f"1/{task_id}/{strategy}", crash=crash,
                       retry_kw=NO_SLEEP, **kw)


class TestJournal(unittest.TestCase):
    def test_torn_last_line_is_dropped_and_cut(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "j.jsonl"
            j = Journal(p)
            j.append({"n": 0})
            j.append({"n": 1})
            with self.assertRaises(Crash):
                j.append({"n": 2, "result": "x" * 50}, crash_mid_write=True)
            j = Journal(p)
            self.assertEqual([e["n"] for e in j.entries], [0, 1])
            self.assertTrue(j.torn)
            self.assertTrue(p.read_bytes().endswith(b"\n"))
            j.append({"n": 2})
            self.assertEqual([e["n"] for e in Journal(p).entries], [0, 1, 2])
            self.assertFalse(Journal(p).torn)

    def test_divergence_stops_the_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            go(tmp, "workflow", "meals_emp0103", Fake())
            with self.assertRaises(Diverged):
                durable_run("workflow", TASKS["lodging_emp0122"]["task"], Fake(), Path(tmp) / "journal.jsonl",
                            Path(tmp) / "ledger.jsonl", "1/meals_emp0103/workflow", retry_kw=NO_SLEEP)

    def test_crash_is_not_caught_by_the_agent(self):
        run = Run(Journal(Path(tempfile.mkdtemp()) / "j.jsonl"), "r", crash=(1, "before"))
        from durable import DurableClient, durable_tools
        from agent import Agent
        agent = Agent(DurableClient(Fake(), run), tools=durable_tools(TOOLS, run))
        with self.assertRaises(Crash):           # call 0 is the model, call 1 its lookup
            agent.run(TASKS["meals_emp0103"]["task"])


class TestHalt(unittest.TestCase):
    """A call that fails for good stops the run with nothing recorded for it, so no gap is left."""

    class Breaks:
        """Fake's replies, but model call number `at` times out every time."""

        def __init__(self, at):
            self.fake, self.at, self.n = Fake(), at, 0

        def chat(self, messages, tools=None):
            self.n += 1
            if self.n - 1 >= self.at:
                raise TimeoutError("timed out")
            return self.fake.chat(messages, tools)

    def test_a_failing_model_call_halts_and_the_resume_finishes(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean, _, run, _ = go(tmp, "workflow", "billed_emp0101", Fake())
            total = run.seq
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Halted):                          # 4 tries, all time out
                go(tmp, "workflow", "billed_emp0101", self.Breaks(at=2))
            es = Journal(Path(tmp) / "journal.jsonl").entries
            self.assertEqual([e["n"] for e in es], list(range(len(es))))   # no gap
            self.assertGreater(len(es), 2)
            out, receipt, run, _ = go(tmp, "workflow", "billed_emp0101", Fake())
            self.assertEqual((out.answer, run.seq), (clean.answer, total))
            self.assertEqual(len(Ledger(Path(tmp) / "ledger.jsonl").claims()), 1)

    def test_a_result_that_cannot_be_recorded_halts(self):
        import durable
        real, n = durable.append_jsonl, {"k": 0}

        def failing(path, entry, crash_mid_write=False):
            n["k"] += 1
            if n["k"] == 2:                                          # the first tool result
                raise OSError("disk full")
            return real(path, entry, crash_mid_write)
        with tempfile.TemporaryDirectory() as tmp:
            durable.append_jsonl = failing
            try:
                with self.assertRaises(Halted):
                    go(tmp, "agent", "lodging_emp0122", Fake())
            finally:
                durable.append_jsonl = real
            self.assertEqual([e["n"] for e in Journal(Path(tmp) / "journal.jsonl").entries], [0])
            out, _, run, _ = go(tmp, "agent", "lodging_emp0122", Fake())
            self.assertEqual(out.status, "answered")
            self.assertEqual(run.replayed, 1)

    def test_a_bug_in_a_tool_is_recorded_and_replayed(self):
        def broken(**args):
            raise KeyError("rates")
        tools = {**TOOLS, "lookup": (broken, TOOLS["lookup"][1])}
        with tempfile.TemporaryDirectory() as tmp:
            first, _, _, _ = go(tmp, "agent", "lodging_emp0122", Fake(), tools=tools)
            es = Journal(Path(tmp) / "journal.jsonl").entries
            self.assertTrue(any("raised" in e["result"] for e in es if e["kind"] == "tool"))
            again, _, run, _ = go(tmp, "agent", "lodging_emp0122", Fake(), tools=tools)
            self.assertEqual(again.answer, first.answer)
            self.assertEqual(run.live, 0)


class TestResume(unittest.TestCase):
    """Kill each strategy at every call and every point, resume, and compare with a clean run."""

    def check(self, strategy, task_id, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            clean, receipt, run, _ = go(tmp, strategy, task_id, Fake(**kw))
            total = run.seq
        self.assertEqual(clean.status, "answered")
        self.assertEqual(Decimal(clean.amount), Decimal(str(TASKS[task_id]["answer"])))
        self.assertIn("filed", receipt)
        for n in range(total):
            for point in Run.POINTS:
                with self.subTest(call=n, point=point), tempfile.TemporaryDirectory() as tmp:
                    fake = Fake(**kw)
                    with self.assertRaises(Crash):
                        go(tmp, strategy, task_id, fake, crash=(n, point))
                    out, _, run, _ = go(tmp, strategy, task_id, fake)
                    self.assertEqual((out.status, out.answer, out.amount), (clean.status, clean.answer, clean.amount))
                    self.assertEqual(run.seq, total)
                    self.assertEqual(run.replayed + run.live, total)
                    self.assertEqual(run.replayed, n + (point == "after_record"))
                    claims = Ledger(Path(tmp) / "ledger.jsonl").claims()
                    self.assertEqual(len(claims), 1, claims)           # keyed: never a second claim
                    self.assertEqual(Decimal(claims[0]["amount"]), Decimal(clean.amount))
        return total

    def test_workflow(self):
        self.assertGreater(self.check("workflow", "billed_emp0101"), 10)

    def test_plan(self):
        self.check("plan", "meals_emp0103")

    def test_agent(self):
        self.check("agent", "lodging_emp0122")

    def test_plan_with_a_replan(self):
        self.check("plan", "mileage_emp0143", plans=[["Look it up", "Answer"], ["Search again", "Answer"]],
                   stuck={"Look it up"})


class TestIdempotency(unittest.TestCase):
    def claims_after_crash_in_claim(self, keyed):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, run, _ = go(tmp, "workflow", "meals_emp0103", Fake())
            last = run.seq - 1                                       # the claim is the last call
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Crash):
                go(tmp, "workflow", "meals_emp0103", Fake(), crash=(last, "after_effect"), keyed=keyed)
            _, receipt, _, _ = go(tmp, "workflow", "meals_emp0103", Fake(), keyed=keyed)
            return Ledger(Path(tmp) / "ledger.jsonl").claims(), receipt

    def test_without_a_key_the_claim_is_filed_twice(self):
        claims, receipt = self.claims_after_crash_in_claim(keyed=False)
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0]["amount"], claims[1]["amount"])
        self.assertIn("CL0002 filed", receipt)

    def test_with_a_key_the_second_is_dropped(self):
        claims, receipt = self.claims_after_crash_in_claim(keyed=True)
        self.assertEqual(len(claims), 1)
        self.assertIn("already filed", receipt)

    def test_a_ledger_line_cut_off_by_a_kill_is_not_a_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Ledger(Path(tmp) / "l.jsonl")
            book.post("EMP0101", "10.00", key="k0")
            with self.assertRaises(Crash):
                book.post("EMP0101", "20.00", key="k1", crash_mid_write=True)
            self.assertEqual([c["key"] for c in book.claims()], ["k0"])
            self.assertIn("CL0002 filed", book.post("EMP0101", "20.00", key="k1"))
            self.assertIn("already filed", book.post("EMP0101", "20.00", key="k1"))
            self.assertEqual(len(book.claims()), 2)

    def test_a_kill_inside_the_ledger_then_a_resume_is_one_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, run, _ = go(tmp, "workflow", "meals_emp0103", Fake())
            last = run.seq - 1
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Crash):                           # stands in for the receiver dying mid-append
                go(tmp, "workflow", "meals_emp0103", Fake(), crash=(last, "before"))
            with open(Path(tmp) / "ledger.jsonl", "ab") as f:
                f.write(b'{"id": "CL0001", "key": "1/meals_emp0103/workflow/')
            _, receipt, _, _ = go(tmp, "workflow", "meals_emp0103", Fake())
            self.assertIn("CL0001 filed", receipt)
            self.assertEqual(len(Ledger(Path(tmp) / "ledger.jsonl").claims()), 1)

    def test_the_ledger_takes_only_positive_amounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = Ledger(Path(tmp) / "l.jsonl")
            for bad in ("NaN", "Infinity", "0", "-5", "abc"):
                with self.subTest(amount=bad), self.assertRaises(ToolError):
                    book.post("EMP0101", bad, key=bad)
            self.assertEqual(book.claims(), [])

    def test_a_second_run_is_a_second_claim(self):
        """The key names one run's call. A new run (a new id) is a new claim: the run-level key
        protects against replays, not against running the whole job twice."""
        with tempfile.TemporaryDirectory() as tmp:
            for rid in ("a", "b"):
                durable_run("workflow", TASKS["meals_emp0103"]["task"], Fake(), Path(tmp) / f"{rid}.jsonl",
                            Path(tmp) / "ledger.jsonl", rid, retry_kw=NO_SLEEP)
            self.assertEqual(len(Ledger(Path(tmp) / "ledger.jsonl").claims()), 2)


class TestRetries(unittest.TestCase):
    def test_waits_are_capped_and_jittered(self):
        import random
        w = waits(8, base=1.0, cap=5.0, rng=random.Random(0))
        self.assertEqual(len(w), 7)
        for i, x in enumerate(w):
            self.assertTrue(0 <= x <= min(5.0, 2 ** i))
        self.assertNotEqual(w, waits(8, base=1.0, cap=5.0, rng=random.Random(1)))

    def test_only_transient_errors_are_retried(self):
        n = {"calls": 0}

        def failing(exc):
            def f():
                n["calls"] += 1
                raise exc
            return f
        for exc, tries in [(TransientError("x"), 4), (TimeoutError("x"), 4), (ConnectionResetError("x"), 4),
                           (urllib.error.HTTPError("u", 503, "busy", {}, None), 4),
                           (urllib.error.HTTPError("u", 429, "slow", {}, None), 4),
                           (urllib.error.HTTPError("u", 400, "bad", {}, None), 1),
                           (urllib.error.URLError(ConnectionRefusedError("x")), 4),
                           (urllib.error.URLError(TimeoutError("x")), 4),
                           (urllib.error.URLError("unknown url type: htp"), 1),
                           (urllib.error.URLError(ValueError("certificate verify failed")), 1),
                           (ToolError("not_found", "x"), 1), (ValueError("x"), 1)]:
            n["calls"] = 0
            with self.subTest(exc=repr(exc)), self.assertRaises(type(exc)):
                retry(failing(exc), attempts=4, sleep=lambda s: None)
            self.assertEqual(n["calls"], tries)

    def test_budget_stops_the_waiting(self):
        slept = []
        with self.assertRaises(TransientError):
            retry(lambda: (_ for _ in ()).throw(TransientError("x")), attempts=10, base=10, cap=10,
                  budget=15, sleep=slept.append)
        self.assertLessEqual(sum(slept), 15)

    def test_an_empty_result_is_a_result(self):
        n = {"calls": 0}

        def empty():
            n["calls"] += 1
            return "No matches. Files: a.md"
        self.assertEqual(retry(empty, sleep=lambda s: None), "No matches. Files: a.md")
        self.assertEqual(n["calls"], 1)

    def test_flaky_tools_give_the_clean_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            clean, _, _, _ = go(tmp, "workflow", "full_emp0104", Fake())
        with tempfile.TemporaryDirectory() as tmp:
            log, flaky = [], Flaky(0.4, seed=3)
            out, _, _, _ = go(tmp, "workflow", "full_emp0104", Fake(), flaky=flaky, retry_log=log)
        self.assertGreater(flaky.failures, 0)
        self.assertEqual(len(log), flaky.failures)
        self.assertEqual(out.amount, clean.amount)

    def test_retries_running_out_is_an_error_the_model_reads(self):
        tools = retrying_tools({k: (Flaky(1.0, 0).tool(fn), s) for k, (fn, s) in TOOLS.items()}, sleep=lambda s: None)
        with self.assertRaises(ToolError) as e:
            tools["lookup"][0](query="per diem")
        self.assertEqual(e.exception.kind, "unavailable")

    def test_retries_cut_short_by_the_budget_say_so(self):
        tools = retrying_tools({k: (Flaky(1.0, 0).tool(fn), s) for k, (fn, s) in TOOLS.items()},
                               attempts=4, budget=0, sleep=lambda s: None)
        with self.assertRaises(ToolError) as e:
            tools["lookup"][0](query="per diem")
        self.assertIn("failed 1 time ", str(e.exception))

    def test_a_resumed_run_meets_the_same_faults(self):
        once = {**NO_SLEEP, "attempts": 1}
        task = TASKS["full_emp0104"]["task"]

        def failed(tmp):
            es = Journal(Path(tmp) / "journal.jsonl").entries
            return [e["n"] for e in es if e["kind"] == "tool" and "tool_error" in e["result"]]

        def run(tmp, crash=None):
            return durable_run("workflow", task, Fake(), Path(tmp) / "journal.jsonl", Path(tmp) / "ledger.jsonl",
                               "r", crash=crash, flaky=Flaky(0.3, seed=5), retry_kw=once)
        with tempfile.TemporaryDirectory() as tmp:
            run(tmp)
            clean = failed(tmp)
            total = len(Journal(Path(tmp) / "journal.jsonl").entries)
        self.assertTrue(clean)
        for n in (1, total // 2, total - 2):
            with self.subTest(cut=n), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(Crash):
                    run(tmp, crash=(n, "before"))
                run(tmp)
                self.assertEqual(failed(tmp), clean)

    def test_client_retries(self):
        class Down:
            def __init__(self):
                self.n = 0

            def chat(self, messages, tools=None):
                self.n += 1
                if self.n < 3:
                    raise urllib.error.URLError(ConnectionRefusedError("refused"))
                return msg("ok"), {}
        down = Down()
        self.assertEqual(RetryingClient(down, sleep=lambda s: None).chat([])[0]["content"], "ok")
        self.assertEqual(down.n, 3)


class TestPlan(unittest.TestCase):
    def test_parse_plan(self):
        self.assertEqual(parse_plan('Here: ["a", " b "]'), ["a", "b"])
        self.assertEqual(parse_plan('{"steps": ["a"]}'), ["a"])      # a list inside an object is accepted
        for bad in ["no list", "[]", '["a", 3]', json.dumps(["s"] * 9)]:
            self.assertIsNone(parse_plan(bad), bad)

    def test_replans_are_capped(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, receipt, _, _ = go(tmp, "plan", "meals_emp0103",
                                    Fake(plans=[["A", "Z"], ["B", "Z"], ["C", "Z"], ["D", "Z"]], stuck={"A", "B", "C", "D"}))
            self.assertEqual(out.status, "gave_up")
            self.assertEqual(out.info["replans"], 2)
            self.assertIsNone(final_amount(out.answer))              # no number to score or to claim
            self.assertIsNone(receipt)
            self.assertFalse((Path(tmp) / "ledger.jsonl").exists())

    def test_the_token_budget_counts_the_planner_and_is_checked_before_each_step(self):
        fake = Fake()
        out = strategies.plan(TASKS["meals_emp0103"]["task"], fake, TOOLS, max_tokens=0)
        self.assertEqual(out.status, "gave_up")
        self.assertIn("token budget", out.detail)
        self.assertEqual(fake.calls, 1)                             # the plan, then no step
        out = strategies.plan(TASKS["meals_emp0103"]["task"], Fake(), TOOLS, max_tokens=150)
        self.assertEqual(out.status, "gave_up")                     # 10 + 200 for step 1: no step 2
        self.assertIn("token budget", out.detail)

    def test_the_same_plan_again_stops_the_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _, _, _ = go(tmp, "plan", "meals_emp0103", Fake(plans=[["A", "Z"]], stuck={"A"}))
            self.assertEqual(out.status, "gave_up")
            self.assertEqual(out.info["replans"], 1)
            self.assertEqual(out.info["failures"][-1]["why"], "no new plan")

    def test_a_replan_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _, _, _ = go(tmp, "plan", "meals_emp0103", Fake(plans=[["A", "Z"], ["B", "Z"]], stuck={"A"}))
            self.assertEqual(out.status, "answered")
            self.assertEqual(out.info["plans"], [["A", "Z"], ["B", "Z"]])


class TestWorkflow(unittest.TestCase):
    def test_trip_rows_match_the_generator(self):
        text = (HERE.parent / "ch04" / "handbook" / "trips_2026q1.md").read_text(encoding="utf-8")
        for t in TASKS.values():
            emp = t["id"].split("_")[1].upper()
            rows = [r["Trip"] for r in trip_rows(text, emp) if r["Billed"] == "ACME"]
            self.assertEqual(sorted(rows), sorted(t["trips"]), t["id"])

    def test_every_task_right_with_a_right_model(self):
        for tid, t in TASKS.items():
            with self.subTest(task=tid), tempfile.TemporaryDirectory() as tmp:
                out, _, _, _ = go(tmp, "workflow", tid, Fake())
                self.assertEqual(Decimal(out.amount), Decimal(str(t["answer"])))
                self.assertEqual(sorted(out.info["trips"]), sorted(t["trips"]))

    def test_unreadable_question_goes_to_the_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, _, _, _ = go(tmp, "workflow", "meals_emp0103", Fake(parts='{"parts": ["taxis"]}'))
            self.assertEqual(out.info["routed"], "parts")
            self.assertEqual(Decimal(out.amount), Decimal(str(TASKS["meals_emp0103"]["answer"])))

    def test_a_failed_read_of_the_trip_log_stops_the_workflow(self):
        def down(**args):
            raise TransientError("service unavailable")
        tools = {**TOOLS, "read_file": (down, TOOLS["read_file"][1])}
        with tempfile.TemporaryDirectory() as tmp:
            out, receipt, _, _ = go(tmp, "workflow", "meals_emp0103", Fake(), tools=tools)
            self.assertEqual(out.status, "step_failed")
            self.assertIn("unavailable", out.detail)
            self.assertIsNone(receipt)                                # no number, no claim
            self.assertEqual(Ledger(Path(tmp) / "ledger.jsonl").claims(), [])

    def test_final_amount(self):
        self.assertEqual(final_amount("x\n**Final answer:** $1,234.50 USD"), Decimal("1234.50"))
        self.assertEqual(final_amount("Final answer: 3\nFinal answer: 4 USD"), Decimal("4"))
        self.assertIsNone(final_amount("The total is 12 USD."))
        self.assertEqual(final_amount("Final answer: 500 dollars."), Decimal("500"))
        for bad in ["Final answer: not 500 USD", "Final answer: 500 or 700 USD", "Final answer: 91 miles",
                    "Final answer: 500", "Final answer: -5 USD", "Final answer: 500 USD (meals only)"]:
            self.assertIsNone(final_amount(bad), bad)

    def test_a_trip_log_without_its_table_is_not_an_empty_one(self):
        with self.assertRaises(ValueError):
            trip_rows("corrupt file", "EMP0103")
        with self.assertRaises(ValueError):
            trip_rows("| Trip | City |\n|---|---|\n| TR0001 | Oslo |", "EMP0103")
        tools = {**TOOLS, "read_file": (lambda **a: "corrupt file", TOOLS["read_file"][1])}
        with tempfile.TemporaryDirectory() as tmp:
            out, receipt, _, _ = go(tmp, "workflow", "meals_emp0103", Fake(), tools=tools)
            self.assertEqual(out.status, "step_failed")
            self.assertIn("unreadable", out.detail)
            self.assertIsNone(receipt)


class TestExperiment(unittest.TestCase):
    def test_parts_with_a_right_model(self):
        import experiment
        ts = [TASKS["billed_emp0102"], TASKS["full_emp0104"]]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journals").mkdir()
            rows = {}
            for part, seed, t, cond in experiment.plan(ts, 1, ["compare", "crash", "faults"]):
                clean = rows.get(("compare", 1, t["id"], cond))
                rows[(part, seed, t["id"], cond)] = experiment.one(out, part, seed, t, cond, Fake(), clean)
            self.assertEqual(len(rows), 2 * (3 + 3 + 2))
            for k, r in rows.items():
                if k[0] != "faults":                 # with faults, a run may fail; see the faults lines
                    self.assertTrue(r["ok"], (k, r["answer"]))
                if k[0] == "crash":
                    self.assertTrue(r["same_answer"])
                    self.assertEqual(r["replayed"], r["cut_at"])
                    self.assertEqual(r["journal_calls"], r["clean_calls"])
                    self.assertLess(r["live_tokens"], r["clean_tokens"])
                    self.assertEqual(r["recovery_tokens"], r["live_tokens"])   # not interrupted again
                    self.assertFalse(r["interrupted"])
            self.assertEqual(len(Ledger(out / "ledger.jsonl").claims()), 6)
            self.assertEqual(len(Ledger(out / "ledger_crash.jsonl").claims()), 6)
            self.assertGreater(sum(r.get("injected", 0) for r in rows.values()), 0)
            import report
            (out / "traces.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows.values()))
            table, nums = report.render(report.load(out), out)
            self.assertEqual(len(table), 3)
            self.assertEqual((nums["AgentRight"], nums["PlanRight"], nums["WorkflowRight"]), (2, 2, 2))
            self.assertEqual((nums["Claims"], nums["RepeatedKeys"], nums["ClaimsExpected"]), (6, 0, 6))
            self.assertEqual((nums["CrashSame"], nums["CrashRuns"]), (6, 6))
            self.assertIn("FaultWorkflowDiff", nums)
            self.assertEqual(nums["Injected"], sum(r.get("injected", 0) for r in rows.values()))
            self.assertFalse(set(nums) - set(report.MACROS))
            torn = (out / "ledger.jsonl").read_bytes() + b'{"id": "CL00'
            (out / "ledger.jsonl").write_bytes(torn)
            report.render(report.load(out), out)
            self.assertEqual((out / "ledger.jsonl").read_bytes(), torn)    # the report changes no evidence

    def test_report_with_one_task(self):
        import experiment
        import report
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "journals").mkdir()
            rows = {}
            for part, seed, t, cond in experiment.plan([TASKS["meals_emp0103"]], 1, ["compare", "crash", "faults"]):
                rows[(part, seed, t["id"], cond)] = experiment.one(out, part, seed, t, cond, Fake(),
                                                                   rows.get(("compare", 1, t["id"], cond)))
            (out / "traces.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows.values()))
            table, nums = report.render(report.load(out), out)
            self.assertEqual(len(table), 3)
            self.assertEqual(nums["AgentSE"], "--")
            self.assertNotIn("PlanAgentDiff", nums)
            self.assertEqual(nums["FaultAgentRight"], 1)

    def test_cut_is_seeded_and_in_range(self):
        import experiment
        for total in (2, 5, 40):
            n = experiment.cut_at("x", "plan", total)
            self.assertTrue(1 <= n < total)
            self.assertEqual(n, experiment.cut_at("x", "plan", total))


if __name__ == "__main__":
    unittest.main()
