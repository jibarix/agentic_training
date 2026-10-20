"""Tests for Chapter 11's code. No model is called: the runs are made up, or Chapter 4's and 5's own."""
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import analysis as A                                     # noqa: E402
import native as N                                       # noqa: E402
import otel_shape as O                                   # noqa: E402
import probe as P                                        # noqa: E402
import ratelimit as R                                    # noqa: E402
import report as REP                                     # noqa: E402

HAVE_RUNS = (A.CODE / "ch04" / A.CH04_RUN / "traces.jsonl").exists() and \
            (A.CODE / "ch05" / A.CH05_RUN / "traces.jsonl").exists()


def model(tokens, seconds, calls=(), content=""):
    return {"type": "model", "tokens": tokens, "seconds": seconds, "estimated": False, "content": content,
            "calls": [{"id": c, "name": "lookup", "arguments": "{}"} for c in calls]}


def tool(cid):
    return {"type": "tool", "id": cid, "name": "lookup", "observation": "secret text"}


def run(cond="full", prompts=(600, 900), tokens=(650, 980), seconds=(2.0, 3.0), summary=(0, 0), ok=True,
        status="answered", total=6.0):
    trace = [model(tokens[0], seconds[0], ["c1"]), tool("c1"), model(tokens[1], seconds[1], content="done"),
             {"type": "end"}]
    return {"cond": cond, "seed": 1, "id": "t1", "cluster": "meals", "status": status, "ok": ok, "steps": 2,
            "tokens": sum(tokens), "seconds": total, "calls": 2, "max_prompt": max(prompts), "answer": "42 USD",
            "trace": trace,
            "call_log": [{"prompt_tokens": p, "summary_tokens": s} for p, s in zip(prompts, summary)]}


class Analysis(unittest.TestCase):
    def test_percentile_interpolates_between_ranks(self):
        self.assertEqual(A.percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertAlmostEqual(A.percentile(list(range(1, 21)), 0.95), 19.05)

    def test_the_reuse_proxy_counts_the_last_prompt_and_reply_as_reused(self):
        cs = A.calls(run())
        self.assertEqual([(c["new"], c["reused"], c["completion"]) for c in cs], [(600, 0, 50), (250, 650, 80)])

    def test_a_hosted_cache_can_read_only_the_last_prompt_not_its_reply(self):
        cs = A.calls(run())
        self.assertEqual([c["cached"] for c in cs], [0, 600])
        self.assertEqual([c["cached"] for c in A.calls(run("drop"))], [0, 0])

    def test_drop_and_compact_calls_are_all_new_and_the_summary_is_kept_apart(self):
        cs = A.calls(run("compact", summary=(0, 30), tokens=(650, 1010)))
        self.assertEqual([c["reused"] for c in cs], [0, 0])
        self.assertEqual((cs[1]["completion"], cs[1]["summary"]), (80, 30))

    def test_a_trace_that_does_not_line_up_gives_no_calls(self):
        r = run()
        r["call_log"].pop()
        self.assertEqual(A.calls(r), [])

    def test_the_ideal_cache_needs_the_minimum_and_a_written_call_before(self):
        A.PRICES["test"] = ("x", 1.0, 1.25, 0.1, 5.0, 700)
        try:
            cs = A.calls(run(prompts=(600, 900)))
            plain = (600 + 900) * 1.0 + (50 + 80) * 5.0
            self.assertAlmostEqual(A.price(cs, "test", False) * 1e6, plain)
            # the first prompt is below the minimum, so nothing was written for the second to read
            self.assertAlmostEqual(A.price(cs, "test", True) * 1e6, 600 + 900 * 1.25 + 130 * 5.0)
            A.PRICES["test"] = ("x", 1.0, 1.25, 0.1, 5.0, 500)
            # the second call reads the first prompt (600), not its reply, and writes the other 300
            self.assertAlmostEqual(A.price(cs, "test", True) * 1e6, 600 * 1.25 + 600 * 0.1 + 300 * 1.25 + 650)
        finally:
            del A.PRICES["test"]

    def test_ols_recovers_a_known_line(self):
        X = [(1.0, x, x * x % 7) for x in range(10)]
        beta, r2 = A.ols(X, [2 + 3 * a + 0.5 * b for _, a, b in X])
        self.assertEqual([round(b, 6) for b in beta], [2, 3, 0.5])
        self.assertAlmostEqual(r2, 1.0)

    def test_golden_signals_and_cost_per_solved_task(self):
        rows = [run(), run(ok=False, status="step_limit", total=4.0)]
        g = A.golden(rows)["full"]
        self.assertEqual((g["runs"], g["right"], g["errors"]), (2, 1, 0.5))
        self.assertAlmostEqual(g["per_minute"], 60 * 4 / 10)
        self.assertEqual(A.per_solved(rows, "full"), {"tokens": 2 * 1630, "seconds": 10.0})
        self.assertIsNone(A.per_solved([run(ok=False)], "full"))

    def test_only_pairs_every_condition_reached_are_compared(self):
        rows = [{"part": "compare", "id": "a", "seed": 1, "cond": c} for c in ("agent", "plan", "workflow")] + \
               [{"part": "compare", "id": "b", "seed": 1, "cond": "agent"}]
        kept, pairs = A.common(rows)
        self.assertEqual((len(kept), pairs), (3, 1))

    def test_other_parts_are_left_out_and_duplicates_or_strange_conditions_refused(self):
        rows = [{"part": "compare", "id": "a", "seed": 1, "cond": c} for c in ("agent", "plan", "workflow")]
        crash = [{"part": "crash", "id": "a", "seed": 1, "cond": c} for c in ("agent", "plan", "workflow")]
        kept, pairs = A.common(rows + crash)
        self.assertEqual((len(kept), pairs), (3, 1))
        self.assertTrue(all(r["part"] == "compare" for r in kept))
        with self.assertRaises(ValueError):
            A.common(rows + rows[:1])
        with self.assertRaises(ValueError):
            A.common(rows + [{"part": "compare", "id": "a", "seed": 1, "cond": "react"}])
        # two conditions only: no pair has all three, so nothing is compared
        self.assertEqual(A.common(rows[:2])[1], 0)

    @unittest.skipUnless(HAVE_RUNS, "Chapter 4's and 5's runs are not here")
    def test_the_fit_on_chapter_4s_run(self):
        f = A.fit(A.ch04_rows())
        self.assertEqual(f["calls"], 614)
        self.assertGreater(f["r2"], 0.99)
        self.assertGreater(f["new_ms"], f["reused_ms"])


class RateLimit(unittest.TestCase):
    def test_a_bucket_refills_and_says_how_long_to_wait(self):
        b = R.Bucket(60, 1.0)
        b.level = 0
        b.refill(10)
        self.assertEqual((b.level, b.wait(15)), (10, 5))
        self.assertEqual(b.wait(61), float("inf"))

    def test_cache_aware_counting_leaves_out_what_is_read(self):
        cs = A.calls(run())
        self.assertEqual(R.counted(cs, 512, True), [600, 300])
        self.assertEqual(R.counted(cs, 700, True), [600, 900])
        self.assertEqual(R.counted(cs, 512, False), [600, 900])

    def test_generous_limits_refuse_nothing(self):
        work = [([(1000, 50, 1.0, 0.5)] * 3, 4.5)]
        out = R.replay(work, (1000, 10 ** 7, 10 ** 6))
        self.assertEqual((out["calls"], out["refused"], out["slowdown_p50"]), (3, 0, 1.0))

    def test_a_tight_limit_makes_agents_wait_and_backoff_can_stop_them(self):
        work = [([(30_000, 10, 0.1, 0.0)] * 4, 0.4)] * 3
        wait = R.replay(work, (1000, 60_000, 10 ** 6))
        self.assertEqual((wait["calls"], wait["stopped"]), (12, 0))
        self.assertGreater(wait["refused"], 0)
        self.assertGreater(wait["slowdown_p50"], 1)
        back = R.replay(work, (1000, 60_000, 10 ** 6), mode="backoff")
        self.assertGreater(back["stopped"], 0)

    def test_a_call_larger_than_a_bucket_stops_its_agent(self):
        out = R.replay([([(20_000, 10, 1.0, 0.0)], 1.0)], (1000, 600_000, 10 ** 6), per=1)
        self.assertEqual((out["calls"], out["too_large"], out["stopped"]), (0, 1, 1))

    def test_oversized_counts_every_large_call_not_only_the_first_an_agent_reaches(self):
        work = [([(20_000, 10, 1.0, 0.0), (20_000, 10, 1.0, 0.0), (100, 10, 1.0, 0.0)], 3.0)]
        out = R.replay(work, (1000, 600_000, 10 ** 6), per=1)
        self.assertEqual((out["too_large"], out["oversized"]), (1, 2))
        both = R.replay([([(20_000, 10, 1.0, 0.0), (100, 50_000, 1.0, 0.0)], 2.0)], (1000, 600_000, 600_000), per=1)
        self.assertEqual((both["oversized"], both["oversized_in"], both["oversized_out"]), (2, 1, 1))

    def test_honouring_retry_after_waits_at_least_the_header_within_a_budget(self):
        work = [([(30_000, 10, 0.1, 0.0)] * 4, 0.4)] * 3
        told = R.replay(work, (1000, 150_000, 10 ** 6))
        honour = R.replay(work, (1000, 150_000, 10 ** 6), mode="honour")
        self.assertGreater(honour["refused"], 0)
        self.assertEqual((honour["calls"], honour["stopped"]), (12, 0))
        self.assertGreaterEqual(honour["waited"], told["waited"])
        # a wait longer than the 60-second budget stops the agent instead
        slow = R.replay([([(30_000, 10, 0.1, 0.0)] * 2, 0.2)], (1000, 30_000, 10 ** 6), mode="honour")
        self.assertEqual((slow["calls"], slow["stopped"], slow["out_of_time"], slow["out_of_tries"]), (1, 1, 1, 0))
        # contention: many agents on a small bucket run out of tries while each wait is short
        busy = R.replay([([(5_000, 10, 0.1, 0.0)] * 3, 0.3)] * 40, (1000, 60_000, 10 ** 6), mode="honour")
        self.assertGreater(busy["out_of_tries"], 0)
        self.assertEqual(busy["out_of_time"], 0)
        self.assertEqual(busy["time_left"], busy["out_of_tries"])
        self.assertEqual(slow["time_left"], 0)
        self.assertEqual(busy["stopped"], busy["out_of_tries"] + busy["too_large"])


class Otel(unittest.TestCase):
    def test_a_run_becomes_an_agent_span_with_chat_and_tool_children(self):
        s = O.spans(run(), "m", start=100.0)
        self.assertEqual([x["name"] for x in s], ["invoke_agent handbook-agent", "chat m", "execute_tool lookup",
                                                  "chat m"])
        root = s[0]["span_id"]
        self.assertTrue(all(x["parent_span_id"] == root for x in s[1:]))
        self.assertEqual(s[1]["attributes"]["gen_ai.usage.input_tokens"], 600)
        self.assertEqual(s[1]["attributes"]["gen_ai.usage.output_tokens"], 50)
        self.assertEqual(s[1]["kind"], "CLIENT")
        self.assertEqual(s[0]["end_time_unix_nano"], round(106.0 * 1e9))

    def test_content_is_left_out_unless_asked_for(self):
        text = json.dumps(O.spans(run(), "m"))
        self.assertNotIn("secret text", text)
        self.assertNotIn("42 USD", text)
        self.assertIn("secret text", json.dumps(O.spans(run(), "m", content=True)))

    def test_every_attribute_is_a_genai_or_error_name(self):
        for x in O.spans(run(status="token_limit"), "m", content=True):
            for k in x["attributes"]:
                self.assertRegex(k, r"^(gen_ai\.[a-z_.]+|error\.type)$")
        self.assertEqual(O.spans(run(status="token_limit"), "m")[0]["status"]["code"], "ERROR")

    def test_no_stopping_reason_is_invented_and_messages_have_parts(self):
        s = O.spans(run(), "m", content=True)
        self.assertTrue(all("gen_ai.response.finish_reasons" not in x["attributes"] for x in s))
        first = s[1]["attributes"]["gen_ai.output.messages"]
        self.assertEqual(first, [{"role": "assistant", "parts": [
            {"type": "tool_call", "id": "c1", "name": "lookup", "arguments": {}}]}])
        self.assertEqual(s[3]["attributes"]["gen_ai.output.messages"][0]["parts"],
                         [{"type": "text", "content": "done"}])
        self.assertEqual(s[0]["attributes"]["gen_ai.output.messages"][0]["parts"],
                         [{"type": "text", "content": "42 USD"}])

    def test_provider_usage_maps_to_the_conventions_input_count(self):
        a = O.anthropic_usage({"input_tokens": 50, "output_tokens": 9, "cache_read_input_tokens": 900,
                               "cache_creation_input_tokens": 100})
        self.assertEqual(a["gen_ai.usage.input_tokens"], 1050)
        self.assertEqual(a["gen_ai.usage.cache_read.input_tokens"], 900)
        o = O.openai_usage({"prompt_tokens": 1000, "completion_tokens": 9,
                            "prompt_tokens_details": {"cached_tokens": 896}})
        self.assertEqual((o["gen_ai.usage.input_tokens"], o["gen_ai.usage.cache_read.input_tokens"]), (1000, 896))


class Native(unittest.TestCase):
    MSGS = [{"role": "system", "content": "s"}, {"role": "user", "content": "q"},
            {"role": "assistant", "content": "", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "lookup", "arguments": '{"query": "x"}'}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "found"}]

    def test_messages_go_out_with_argument_objects_and_named_tool_results(self):
        out = N.to_native(self.MSGS)
        self.assertEqual(out[2]["tool_calls"][0]["function"]["arguments"], {"query": "x"})
        self.assertEqual(out[3], {"role": "tool", "content": "found", "tool_name": "lookup"})
        self.assertEqual(self.MSGS[2]["tool_calls"][0]["function"]["arguments"], '{"query": "x"}')

    def test_replies_come_back_in_the_v1_shape(self):
        m = N.from_native({"content": None, "tool_calls": [{"function": {"name": "calc", "arguments": {"a": 1}}}]})
        self.assertEqual(m["tool_calls"][0]["function"]["arguments"], '{"a": 1}')
        self.assertEqual(m["tool_calls"][0]["id"], "call_0")
        self.assertEqual(m["content"], "")

    def test_a_missing_cached_count_is_unknown_not_zero(self):
        v1, rec = N.usage({"prompt_eval_count": 10, "eval_count": 2, "prompt_eval_duration": 5e8})
        self.assertEqual(v1["total_tokens"], 12)
        self.assertIsNone(rec["cached"])
        self.assertEqual(rec["prompt_seconds"], 0.5)
        self.assertIsNone(rec["eval_seconds"])                  # no eval_duration: unknown, not 0 s

    def test_the_client_sends_the_window_and_no_thinking_and_logs_the_counts(self):
        sent = []

        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def opener(req, timeout):
            sent.append(json.loads(req.data))
            return Reply(json.dumps({"message": {"content": "hi"}, "prompt_eval_count": 7,
                                     "prompt_eval_cached_count": 4, "eval_count": 1}).encode())
        c = N.NativeClient("m", seed=3, opener=opener)
        msg, usage = c.chat(self.MSGS[:2], tools=[{"type": "function"}])
        b = sent[0]
        self.assertEqual((b["think"], b["stream"], b["options"]["num_ctx"], b["options"]["seed"]), (False, False,
                                                                                                    32768, 3))
        self.assertEqual((msg["content"], usage["prompt_tokens"], c.log[0]["cached"]), ("hi", 7, 4))


class Probe(unittest.TestCase):
    def test_the_plan_is_120_runs_with_the_arms_alternating(self):
        p = P.plan(list(range(30)), 2)
        self.assertEqual(len(p), 120)
        self.assertEqual(len(set(p)), 120)
        firsts = [p[i][2] for i in range(0, len(p), 2)]
        self.assertEqual(firsts.count("stable"), 30)

    def test_the_stamp_goes_before_the_system_prompt_on_a_copy(self):
        seen = []
        inner = SimpleNamespace(chat=lambda m, t=None: seen.append(m) or ({}, {}))
        msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "q"}]
        P.Stamped(inner, clock=lambda: "T").chat(msgs)
        self.assertEqual(seen[0][0]["content"], "Time of this request: T\n\nS")
        self.assertEqual(msgs[0]["content"], "S")

    def test_a_row_adds_up_the_servers_counts_and_keeps_unknowns_unknown(self):
        log = [{"prompt": 100, "cached": 0, "prompt_seconds": 1.0, "eval_seconds": 0.5, "thinking_chars": 0},
               {"prompt": 300, "cached": 250, "prompt_seconds": 0.2, "eval_seconds": None, "thinking_chars": 0}]
        res = SimpleNamespace(status="answered", answer="Final answer: 5 USD", steps=2, tokens=420, detail="")
        task = {"id": "t", "cluster": "c", "answer": "5", "units": "USD"}
        r = P.row(1, task, "stable", res, SimpleNamespace(log=log), 3.0)
        self.assertEqual((r["prompt_tokens"], r["cached_tokens"], r["cached_missing"], r["prompt_seconds"],
                          r["eval_seconds"]), (400, 250, 0, 1.2, None))
        log[1]["cached"] = None                                  # one call without a count: the run's is unknown
        r = P.row(1, task, "stable", res, SimpleNamespace(log=log), 3.0)
        self.assertEqual((r["cached_tokens"], r["cached_missing"]), (None, 1))

    def test_a_torn_last_row_is_dropped_on_resume_and_the_manifest_is_replaced_whole(self):
        d = Path(tempfile.mkdtemp())
        try:
            path = d / "traces.jsonl"
            path.write_text('{"seed": 1, "id": "a", "arm": "stable"}\n{"seed": 1, "id": "a", "ar', encoding="utf-8")
            self.assertEqual(P.recover(path), [{"seed": 1, "id": "a", "arm": "stable"}])
            self.assertEqual(path.read_text(encoding="utf-8"), '{"seed": 1, "id": "a", "arm": "stable"}\n')
            bad = '{"seed": 1}\n{"seed": 1, "id": "a", "ar\n{"seed": 2}\n'
            path.write_text(bad, encoding="utf-8")       # a bad line in the middle: refused, not repaired
            with self.assertRaises(ValueError):
                P.recover(path)
            self.assertEqual(path.read_text(encoding="utf-8"), bad)
            path.write_text('{"seed": 1}\n{"seed": 2}', encoding="utf-8")   # killed after "}", before the newline
            self.assertEqual(P.recover(path), [{"seed": 1}, {"seed": 2}])
            with open(path, "a", encoding="utf-8") as f:                     # the next run appends as main() does
                f.write(json.dumps({"seed": 3}) + "\n")
            self.assertEqual(P.recover(path), [{"seed": 1}, {"seed": 2}, {"seed": 3}])
            P.write_atomic(d / "manifest.json", '{"run": "x"}')
            self.assertEqual([p.name for p in d.iterdir() if p.name.endswith(".tmp")], [])
            self.assertEqual(json.loads((d / "manifest.json").read_text()), {"run": "x"})
        finally:
            shutil.rmtree(d)

    def test_the_probe_does_not_check_the_window_by_loading_the_model(self):
        self.assertNotIn("check_window(", (HERE / "probe.py").read_text(encoding="utf-8"))


def probe_rows(tasks, seeds=(1, 2)):
    rows = []
    for t in tasks:
        for s in seeds:
            for arm, cached, ps in (("stable", 800, 2.0), ("stamped", 0, 9.0)):
                rows.append({"seed": s, "arm": arm, "id": t, "ok": arm == "stable", "prompt_tokens": 1000,
                             "cached_tokens": cached, "cached_missing": 0, "prompt_seconds": ps + s,
                             "seconds": 30.0 + ps, "calls": 6})
    return rows


class Report(unittest.TestCase):
    def test_macro_names_are_letters_and_unique(self):
        self.assertEqual(len(REP.MACROS), len(set(REP.MACROS)))
        self.assertTrue(all(re.fullmatch(r"[A-Za-z]+", m) for m in REP.MACROS))

    def test_the_probe_numbers_from_made_up_rows(self):
        T = list(REP.tasks())[:3]
        table, nums = REP.probe_numbers(probe_rows(T))
        self.assertEqual(len(table), 2)
        self.assertEqual((nums["StableHit"], nums["StampedHit"], nums["ProbeHitDiff"]), ("80.0", "0.0", "-80.0"))
        self.assertEqual(nums["ProbePromptDiff"], "7.0")
        self.assertEqual(nums["ProbeRightDiff"], "-100.0")

    def test_an_unknown_count_is_never_published_as_zero(self):
        T = list(REP.tasks())[:3]
        rows = probe_rows(T)
        rows[1]["cached_tokens"] = None                  # one stamped run without its cached count
        rows[2]["prompt_seconds"] = None                 # one stable run without its prompt seconds
        table, nums = REP.probe_numbers(rows)
        self.assertEqual((nums["StampedHit"], nums["StableHit"], nums["StablePrompt"]), ("--", "80.0", "--"))
        self.assertEqual((nums["StampedUnknown"], nums["StableUnknown"]), (1, 1))
        self.assertNotIn("ProbeHitDiff", nums)
        self.assertNotIn("ProbePromptDiff", nums)
        self.assertIn("ProbeSecondsDiff", nums)

    def test_without_a_probe_run_its_table_is_a_placeholder_and_its_numbers_dashes(self):
        f = REP.files({"probe": []}, {})
        self.assertEqual(f["ch11_probe.tex"], REP.PLACEHOLDER)
        self.assertIn("\\newcommand{\\celevenStableHit}{--}", f["ch11_numbers.tex"])

    def test_a_partial_or_pilot_probe_is_not_the_design(self):
        d = Path(tempfile.mkdtemp(dir=HERE))
        try:
            T = list(REP.tasks())
            settings = {"pilot": False, "seeds": [1, 2], "tasks": T}
            (d / "manifest.json").write_text(json.dumps({"settings": settings}))
            name = d.name
            self.assertIsNone(REP.not_the_design(name, probe_rows(T)))
            self.assertIn("lacks 4", REP.not_the_design(name, probe_rows(T)[4:]))
            (d / "manifest.json").write_text(json.dumps({"settings": settings | {"pilot": True}}))
            self.assertIn("pilot", REP.not_the_design(name, probe_rows(T)))
        finally:
            shutil.rmtree(d)

    @unittest.skipUnless(HAVE_RUNS, "Chapter 4's and 5's runs are not here")
    def test_the_analysis_numbers_are_all_there(self):
        tables, nums = REP.numbers([])
        missing = [m for m in REP.MACROS if m not in nums and not m.startswith(("Stable", "Stamped", "Probe"))]
        self.assertEqual(missing, [])
        self.assertEqual(nums["FullRight"], 27)


if __name__ == "__main__":
    unittest.main()
