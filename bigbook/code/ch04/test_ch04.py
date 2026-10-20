"""Offline tests for Chapter 4: the context policies on a scripted run, BM25 against the formula,
the passages, and the long tasks' answers recomputed from the handbook files.

Usage: python -m unittest -v test_ch04
"""
import json
import math
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

import make_handbook
from bm25 import BM25, passages, words
from context import POLICIES, Compact, ContextClient, Estimate, coverage, kept, turn_starts
from handbook_tools import TOOLS

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
from agent import Agent                                      # noqa: E402
from llm import call                                         # noqa: E402


class Router:
    """Agent calls (with tools) replay a script; summary calls (no tools) get a fixed summary."""

    def __init__(self, replies, summary="Objective: test.\nFacts found: TR0101 is Dallas.", fail=False):
        self.replies, self.summary, self.fail = list(replies), summary, fail
        self.sent, self.summaries = [], 0

    def chat(self, messages, tools=None):
        if tools is None:
            self.summaries += 1
            if self.fail:
                raise TimeoutError("summariser timed out")
            return {"role": "assistant", "content": self.summary}, {"total_tokens": 300}
        self.sent.append(json.loads(json.dumps(messages)))
        reply = self.replies.pop(0) if self.replies else {"role": "assistant", "content": "Final answer: 1 USD"}
        return reply, {"total_tokens": 100}


def long_script(n=6):
    """n turns, each reading the large trip log (a 2,000-character observation), then an answer."""
    turns = [{"role": "assistant", "content": f"step {i}",
              "tool_calls": [call("read_file", {"path": "trips_2026q1.md"}, f"c{i}")]} for i in range(n)]
    return turns + [{"role": "assistant", "content": "Final answer: 1 USD"}]


def run(policy, script=None, **kw):
    client = Router(script or long_script(), **kw)
    agent = Agent(ContextClient(client, policy), tools=TOOLS, max_steps=12, max_tokens=10 ** 6)
    return agent.run("How much does ACME owe EMP0101?"), client, policy


def well_formed(view):
    """System, then the task, and every tool message answers a call made earlier in the view."""
    ids = set()
    for m in view:
        ids |= {c["id"] for c in m.get("tool_calls") or []}
        if m["role"] == "tool" and m["tool_call_id"] not in ids:
            return False
    return view[0]["role"] == "system" and view[1] == {"role": "user", "content": "How much does ACME owe EMP0101?"}


class TestPolicies(unittest.TestCase):
    BUDGET = 1_500

    def test_full_sends_everything(self):
        res, client, _ = run(POLICIES["full"]())
        self.assertEqual(res.status, "answered")
        self.assertEqual(len(client.sent[-1]), 2 + 6 * 2)

    def test_every_view_is_well_formed_and_keeps_the_latest_turn(self):
        for name in ("drop", "mask", "compact"):
            with self.subTest(name):
                res, client, policy = run(POLICIES[name](self.BUDGET))
                self.assertEqual(res.status, "answered")
                self.assertTrue(policy.events, "the policy never triggered")
                for view in client.sent:
                    self.assertTrue(well_formed(view))
                last = client.sent[-1]
                self.assertEqual(last[-1]["role"], "tool")
                self.assertNotIn("removed", last[-1]["content"])        # the newest observation is intact
                self.assertLess(len(json.dumps(last)), len(json.dumps(run(POLICIES["full"]())[1].sent[-1])))

    def test_drop_fits_the_budget(self):
        _, client, policy = run(POLICIES["drop"](self.BUDGET))
        self.assertTrue(all(e["tokens"] <= self.BUDGET for e in policy.events))
        self.assertIn("earlier messages were removed", client.sent[-1][2]["content"])

    def test_compaction_replaces_old_turns_and_counts_its_tokens(self):
        res, client, policy = run(Compact(self.BUDGET))
        last = client.sent[-1]
        self.assertIn("TR0101 is Dallas", last[2]["content"])
        self.assertLess(len(last), 2 + 6 * 2)
        self.assertEqual(last[3]["role"], "assistant")      # after the summary, whole turns only
        self.assertTrue(all(e["tokens"] <= self.BUDGET for e in policy.events))
        self.assertEqual(client.summaries, len([e for e in policy.events if "summary" in e]))
        self.assertEqual(res.tokens, 100 * res.steps + 300 * client.summaries)
        # the agent's own history is untouched: every observation is in its trace
        self.assertEqual(sum(t["type"] == "tool" for t in res.trace), 6)

    def test_a_failed_summary_sends_the_full_history(self):
        res, client, policy = run(Compact(self.BUDGET), fail=True)
        self.assertEqual(res.status, "answered")
        self.assertTrue(all("error" in e for e in policy.events))
        self.assertEqual(len(client.sent[-1]), 2 + 6 * 2)

    def test_nothing_to_compact_with_one_turn(self):
        policy = Compact(10)
        msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "t"},
                {"role": "assistant", "content": "", "tool_calls": [call("lookup", {"query": "x"}, "a")]},
                {"role": "tool", "tool_call_id": "a", "content": "x" * 400}]
        self.assertEqual(policy.view(msgs, None, None), msgs)
        self.assertEqual(policy.events[-1]["error"], "nothing old enough to compact")
        self.assertEqual(turn_starts(msgs), [2])

    def test_estimate_calibrates_from_the_server(self):
        est = Estimate()
        msgs = [{"role": "user", "content": "x" * 400}]
        est.calibrate(msgs, None, {"prompt_tokens": est(msgs) * 2})
        self.assertAlmostEqual(est.chars_per_token, 2.0, delta=0.05)

    def test_kept_matches_whole_values_only(self):
        self.assertEqual(kept("Trip TR0004: 14 days, rate 4.5", ["4", "14", "TR0004", "TR0040"]), ["14", "TR0004"])

    def test_coverage_counts_only_what_was_given_and_links_values(self):
        facts = [{"value": "TR0010", "keys": []}, {"value": "4", "keys": ["TR0010"]},
                 {"value": "TR0011", "keys": []}, {"value": "4", "keys": ["TR0011"]},
                 {"value": "TR0012", "keys": []}, {"value": "6", "keys": ["TR0012"]}]
        given = "| TR0010 | Denver | 4 |\n| TR0011 | Boston | 4 |"          # TR0012 not read yet
        loose = coverage("Trips: TR0010, TR0011\nDays: 4", given, facts)
        self.assertEqual(loose, {"given": 4, "values": 4, "linked": 2})     # one "4" passes for both
        tight = coverage("TR0010: 4 days\nTR0011: 4 days", given, facts)
        self.assertEqual(tight, {"given": 4, "values": 4, "linked": 4})

    def test_a_fact_is_given_only_with_one_of_its_names(self):
        facts = [{"value": "4", "keys": ["TR0010"]},                   # given only as TR0011's value
                 {"value": "72", "keys": ["Denver", "TR0010"]}]        # an earlier summary names the trip
        given = "Earlier summary:\nTR0010: meals rate 72\n\n| TR0010 | Denver | 3 |\n| TR0011 | Boston | 4 |"
        self.assertEqual(coverage("TR0010: 72", given, facts), {"given": 1, "values": 1, "linked": 1})

    def test_an_empty_summary_still_costs_its_tokens(self):
        res, client, policy = run(Compact(self.BUDGET), summary="")
        self.assertGreater(client.summaries, 0)
        self.assertTrue(all(e["error"] == "empty summary" for e in policy.events if "input" in e))
        self.assertEqual(res.tokens, 100 * res.steps + 300 * client.summaries)

    def test_summary_tokens_survive_a_failed_main_call(self):
        class Breaks(Router):                                   # the summary works, the next call fails
            def chat(self, messages, tools=None):
                if tools is not None and self.summaries:
                    raise TimeoutError("server went away")
                return super().chat(messages, tools)
        policy = Compact(self.BUDGET)
        client = ContextClient(Breaks(long_script()), policy)
        res = Agent(client, tools=TOOLS, max_steps=12, max_tokens=10 ** 6).run("How much does ACME owe EMP0101?")
        self.assertEqual(res.status, "model_error")
        self.assertEqual(client.unbilled, 300)
        self.assertEqual(client.calls[-1]["summary_tokens"], 300)
        self.assertIn("error", client.calls[-1])

    def test_a_transport_error_leaves_the_summary_cost_unknown(self):
        _, _, policy = run(Compact(self.BUDGET), fail=True)
        self.assertTrue(all(e["summary_tokens"] == "unknown" for e in policy.events if "input" in e))

    def test_a_summary_that_does_not_shrink_the_view_is_rejected(self):
        res, client, policy = run(Compact(self.BUDGET), summary="TR0101 " * 3000)
        self.assertEqual(res.status, "answered")
        self.assertTrue(all(e["error"] == "summary did not shrink the view" for e in policy.events if "input" in e))
        self.assertEqual(len(client.sent[-1]), 2 + 6 * 2)             # the uncompacted view was sent
        self.assertEqual(res.tokens, 100 * res.steps + 300 * client.summaries)

    def test_a_view_over_the_budget_is_recorded(self):
        # a summary that shrinks the view, but not under a budget this small
        res, client, policy = run(Compact(900), summary="Facts found: " + "TR0101 Dallas 4 days. " * 60)
        accepted = [e for e in policy.events if "summary" in e]
        self.assertTrue(accepted and all(e["over"] for e in accepted))
        self.assertTrue(all(len(json.dumps(e["summary"])) < 2000 for e in accepted))


class TestBM25(unittest.TestCase):
    DOCS = ["denver lodging cap", "denver denver denver meals rate per day in denver", "boston meals",
            "austin hotel", "chicago office", "miami beach"]

    def test_against_the_formula(self):
        # Equation 3.15 with the IDF of Equation 3.3 for the query "denver meals". Both words are in
        # 2 of 6 passages, so IDF = log(4.5 / 2.5) = 0.5878. The lengths are 3, 9, 2, 2, 2, 2 (mean
        # 10/3), so the passages test the count (4 "denver"), its saturation and the length scaling.
        k1, b = 1.2, 0.75
        bm = BM25(self.DOCS, k1, b)
        N, avg = 6, 10 / 3
        idf = lambda n: max(0.0, math.log((N - n + 0.5) / (n + 0.5)))
        def w(tf, dl, n):
            return tf / (k1 * ((1 - b) + b * dl / avg) + tf) * idf(n)
        want = [w(1, 3, 2), w(4, 9, 2) + w(1, 9, 2), w(1, 2, 2), 0, 0, 0]
        by_hand = [0.2786, 0.5069, 0.3194, 0, 0, 0]          # computed on paper, to 4 places
        for got, exp, hand in zip(bm.score("denver meals"), want, by_hand):
            self.assertAlmostEqual(got, exp)
            self.assertAlmostEqual(got, hand, places=4)
        self.assertGreater(bm.score("denver meals")[2], bm.score("denver meals")[0])   # shorter wins

    def test_common_words_weigh_nothing(self):
        bm = BM25(self.DOCS[:3])
        self.assertEqual(bm.idf["denver"], 0.0)                 # in two of three passages
        self.assertGreater(bm.idf["boston"], 0.0)

    def test_count_saturates(self):
        bm = BM25(["x y"] * 10 + ["rare " * n + "pad " * (10 - n) for n in (1, 2, 4, 8)])
        s = bm.score("rare")[-4:]
        gains = [q - p for p, q in zip(s, s[1:])]
        self.assertTrue(all(g > 0 for g in gains) and gains[-1] < gains[0] * 2)


class TestPassages(unittest.TestCase):
    def test_rows_carry_their_header(self):
        rows = [t for f, t in passages(HERE / "handbook", 1) if f == "mileage.md" and "| van |" in t]
        self.assertEqual(rows, ["| Vehicle | Rate (USD/mile) |\n| van | 0.85 |"])

    def test_every_phrase_fits_in_one_line(self):
        # otherwise line search could never find it, and the comparison would be unfair to it
        lines = passages(HERE / "handbook", 1)
        flat = lambda s: re.sub(r"\s+", " ", s).lower()
        for q in json.loads((HERE / "queries.json").read_text(encoding="utf-8")):
            if "needle" in q:
                self.assertTrue(any(f == q["file"] and flat(q["needle"]) in flat(t) for f, t in lines), q["id"])

    def test_larger_passages_stay_within_a_section(self):
        for f, t in passages(HERE / "handbook", 1500):
            self.assertLessEqual(t.count("[") - t.count("[Trip"), 1, t[:80])


class TestTasks(unittest.TestCase):
    def test_answers_from_the_files(self):
        """Recompute every answer from the Markdown the agent reads, not from the generator's data."""
        book = HERE / "handbook"
        rows = lambda name: [[c.strip() for c in l.strip().strip("|").split("|")]
                             for l in (book / name).read_text(encoding="utf-8").splitlines()
                             if l.startswith("|") and not l.startswith("|-")][1:]
        rates = {r[0]: (Decimal(r[1]), Decimal(r[2])) for r in rows("per_diem.md")}
        per_mile = {r[0]: Decimal(r[1]) for r in rows("mileage.md")} | {"none": Decimal(0)}
        trips = {r[0]: r for r in rows("trips_2026q1.md")}
        for t in json.loads((HERE / "tasks_long.json").read_text(encoding="utf-8")):
            emp = re.search(r"EMP\d{4}", t["task"]).group()
            mine = [r for r in trips.values() if r[1] == emp]
            self.assertLessEqual(len(mine), 5, "lookup returns at most five lines")
            total = Decimal(0)
            for r in mine:
                city, days, nights, cost, vehicle, miles, billed = r[2], int(r[4]), int(r[5]), Decimal(r[6]), r[7], int(r[8]), r[9]
                if billed != "ACME":
                    continue
                if t["cluster"] in ("meals", "full", "billed"):
                    total += rates[city][0] * days
                if t["cluster"] in ("lodging", "full", "billed"):
                    total += min(cost, rates[city][1]) * nights
                if t["cluster"] in ("mileage", "full"):
                    total += per_mile[vehicle] * miles
            self.assertEqual(total, Decimal(str(t["answer"])), t["id"])

    def test_the_generator_reproduces_the_tasks(self):
        rates, staff, trips = make_handbook.build()
        self.assertEqual(make_handbook.tasks(rates, staff, trips),
                         json.loads((HERE / "tasks_long.json").read_text(encoding="utf-8")))


class TestReport(unittest.TestCase):
    def test_tables_from_fake_rows(self):
        import importlib.util                               # Chapter 1 has a report.py too
        spec = importlib.util.spec_from_file_location("ch04_report", HERE / "report.py")
        report = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(report)
        rows = [{"cond": c, "id": f"t{i}", "seed": s, "ok": (c != "drop" or i % 2 == 0), "tokens": 1000,
                 "steps": 5, "triggers": 1 if c != "full" else 0, "max_sent": 900, "budget": 3000,
                 "summary_tokens": 300 if c == "compact" else 0, "facts": 10, "calls": 10,
                 "over_calls": 2 if c == "drop" else 0, "summary_failures": 0, "summary_unknown": 0,
                 "coverage": [{"given": 10, "values": 8, "linked": 6}] if c == "compact" else [],
                 "cluster": f"k{i % 2}",
                 "call_log": [{"history": h, "sent": h - (2 if c == "drop" and h > 4 else 0)} for h in (2, 4, 6, 9)],
                 "events": [{"at": 6, "summary": "s", "tokens": 1200}, {"at": 9, "summary": "s", "tokens": 1400},
                            {"at": 4, "error": "summary did not shrink the view"}] if c == "compact" else []}
                for c in ("full", "drop", "compact") for i in range(4) for s in (1, 2)]
        table, nums = report.render(rows)
        self.assertEqual(len(table), 3)
        self.assertEqual(nums["DropMean"], "50.0")
        self.assertEqual(nums["CompactDropDiff"], "50.0")
        self.assertEqual((nums["ValuesKept"], nums["LinkedKept"]), ("80.0", "60.0"))
        self.assertEqual(nums["DropOver"], "20.0")
        self.assertEqual(nums["SummaryShare"], "30.0")
        self.assertEqual((nums["DropMoves"], nums["DropLater"]), (8, 24))       # one new cut a run
        self.assertEqual((nums["CompactMoves"], nums["CompactLater"]), (16, 24))  # two accepted summaries
        self.assertEqual((nums["SummaryView"], nums["AgainNext"], nums["AgainOf"]), ("1,300", 8, 8))    # 6 -> 9: two tool results in a turn
        self.assertEqual(nums["Clusters"], 2)
        self.assertIn("CompactDropClusterLo", nums)
        self.assertTrue(set(nums) <= set(report.MACROS))
        files = report.files(table, nums)
        self.assertEqual(files["ch04_long.tex"].count("\\\\"), 3)
        self.assertEqual(report.files([], {})["ch04_long.tex"], report.PLACEHOLDER)

    def test_a_resume_refuses_other_settings(self):
        import argparse
        import importlib.util
        spec = importlib.util.spec_from_file_location("ch04_experiment", HERE / "experiment.py")
        exp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exp)
        manifest = {"model": {"tag": "m"}, "server": {"base_url": "u"},
                    "settings": {"budget": 3000, "conds": ["full", "drop"], "extra": {}, "seeds": [1, 2],
                                 "temperature": 0.7, "tasks": ["a", "b"]}}
        blank = dict.fromkeys(["budget", "conds", "model", "base_url", "extra", "seeds", "temperature", "tasks"])
        a = argparse.Namespace(**blank)
        exp.from_manifest(a, manifest)                          # nothing given: the run's own settings
        self.assertEqual((a.budget, a.conds, a.seeds, a.tasks), (3000, "full,drop", 2, "a,b"))
        with self.assertRaises(SystemExit):
            exp.from_manifest(argparse.Namespace(**(blank | {"budget": 2000})), manifest)
        with self.assertRaises(SystemExit):
            exp.from_manifest(argparse.Namespace(**(blank | {"temperature": 0.0})), manifest)


if __name__ == "__main__":
    unittest.main()
