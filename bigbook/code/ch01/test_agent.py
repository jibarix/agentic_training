"""Offline tests: a scripted client drives the loop through every failure path."""
import unittest

from agent import Agent
from llm import ScriptedClient, call
import json
import tempfile
from pathlib import Path

import report
from experiment import run_no_tools, score
from tools import TOOLS, ToolError, calculator, lookup, lookup_v1, read_file

say = lambda text: {"role": "assistant", "content": text}
act = lambda *calls: {"role": "assistant", "content": "", "tool_calls": list(calls)}


def run(*replies, **kw):
    client = ScriptedClient(replies)
    res = Agent(client, **kw).run("q")
    return res, client


class TestLoop(unittest.TestCase):
    def test_success_links_observation_to_call(self):
        res, client = run(act(call("calculator", {"expression": "4 * 68"}, "c1")), say("272 USD"))
        self.assertEqual((res.status, res.answer, res.steps), ("answered", "272 USD", 2))
        tool_msg = client.seen[1][-1]
        self.assertEqual((tool_msg["role"], tool_msg["tool_call_id"], tool_msg["content"]), ("tool", "c1", "272"))

    def test_parallel_calls_each_get_an_observation_in_order(self):
        res, client = run(act(call("calculator", {"expression": "1+1"}, "a"),
                              call("calculator", {"expression": "2+2"}, "b")), say("done"))
        tail = client.seen[1][-2:]
        self.assertEqual([(m["tool_call_id"], m["content"]) for m in tail], [("a", "2"), ("b", "4")])

    def test_missing_id_is_filled(self):
        c = call("calculator", {"expression": "1"}, None)
        res, client = run(act(c), say("1"))
        self.assertEqual(client.seen[1][-1]["tool_call_id"], "call_1_0")

    def test_unknown_tool_is_recoverable(self):
        res, client = run(act(call("search_web", {"q": "x"}, "c1")), say("ok"))
        obs = client.seen[1][-1]["content"]
        self.assertTrue(obs.startswith("ERROR unknown_tool"))
        self.assertIn("lookup, read_file, calculator", obs)
        self.assertEqual(res.status, "answered")

    def test_malformed_json(self):
        res, client = run(act(call("calculator", '{"expression": "1+', "c1")), say("ok"))
        self.assertIn("ERROR bad_arguments: arguments are not valid JSON", client.seen[1][-1]["content"])

    def test_missing_and_unexpected_arguments(self):
        res, client = run(act(call("read_file", {"file": "x.md"}, "c1")), say("ok"))
        obs = client.seen[1][-1]["content"]
        self.assertIn("missing ['path'], unexpected ['file']", obs)

    def test_numeric_argument_is_coerced(self):
        res, client = run(act(call("calculator", {"expression": 7}, "c1")), say("7"))
        self.assertEqual(client.seen[1][-1]["content"], "7")

    def test_other_non_text_arguments_are_rejected(self):
        for bad in ([1, 2], {"a": 1}, True, None):
            res, client = run(act(call("calculator", {"expression": bad}, "c1")), say("ok"))
            self.assertIn("ERROR bad_arguments: ['expression'] must be text", client.seen[1][-1]["content"])

    def test_dispatch_never_raises_on_a_malformed_call(self):
        agent = Agent(ScriptedClient([]))
        for bad in ({}, None, "lookup", {"function": None}, {"function": {"name": 7}},
                    {"function": {"name": "lookup", "arguments": 5}}):
            self.assertTrue(agent.dispatch(bad).startswith("ERROR "), bad)

    def test_malformed_call_in_a_reply_becomes_an_observation(self):
        res, client = run({"role": "assistant", "tool_calls": [{"id": "c1"}, "junk"]}, say("ok"))
        turn, obs = client.seen[1][-3], client.seen[1][-2:]
        self.assertEqual([c["id"] for c in turn["tool_calls"]], ["c1", "call_1_1"])
        self.assertTrue(all(m["content"].startswith("ERROR unknown_tool") for m in obs))
        self.assertEqual(res.status, "answered")

    def test_duplicate_ids_in_one_turn_are_made_unique(self):
        res, client = run(act(call("calculator", {"expression": "1"}, "a"),
                              call("calculator", {"expression": "2"}, "a")), say("ok"))
        self.assertEqual([m["tool_call_id"] for m in client.seen[1][-2:]], ["a", "a_1"])

    def test_tool_exception_does_not_crash(self):
        def broken(path):
            raise RuntimeError("disk on fire")
        tools = {"read_file": (broken, TOOLS["read_file"][1])}
        res, client = run(act(call("read_file", {"path": "a.md"}, "c1")), say("ok"), tools=tools)
        self.assertIn("ERROR tool_failed: RuntimeError: disk on fire", client.seen[1][-1]["content"])

    def test_arguments_json_cannot_raise(self):
        agent = Agent(ScriptedClient([]))
        for raw in ('{"expression": ' + "9" * 5000 + "}", "[" * 100_000):
            obs = agent.dispatch({"function": {"name": "calculator", "arguments": raw}})
            self.assertTrue(obs.startswith("ERROR bad_arguments: arguments are not valid JSON"), obs[:80])

    def test_unserialisable_tool_output_becomes_an_observation(self):
        loop = []
        loop.append(loop)
        tools = {"read_file": (lambda path: loop, TOOLS["read_file"][1])}
        res, client = run(act(call("read_file", {"path": "a.md"}, "c1")), say("ok"), tools=tools)
        self.assertIn("ERROR tool_failed: ValueError", client.seen[1][-1]["content"])

    def test_non_text_tool_output_is_converted(self):
        tools = {"read_file": (lambda path: {"lines": 3}, TOOLS["read_file"][1])}
        res, client = run(act(call("read_file", {"path": "a.md"}, "c1")), say("ok"), tools=tools)
        self.assertEqual(client.seen[1][-1]["content"], '{"lines": 3}')

    def test_step_limit(self):
        loop = [act(call("lookup", {"query": "mileage"}, f"c{i}")) for i in range(5)]
        res, _ = run(*loop, max_steps=3)
        self.assertEqual((res.status, res.steps), ("step_limit", 3))

    def test_token_threshold_can_overshoot_by_one_call(self):
        loop = [act(call("lookup", {"query": "mileage"}, f"c{i}")) for i in range(5)]
        res, _ = run(*loop, max_tokens=250)          # 100 tokens per scripted call
        self.assertEqual((res.status, res.steps, res.tokens), ("token_limit", 3, 300))
        res, _ = run(say("done"), max_tokens=50)     # one call already exceeds the budget
        self.assertEqual((res.status, res.tokens), ("answered", 100))

    def test_tokens_are_estimated_and_flagged_when_usage_is_missing(self):
        class NoUsage(ScriptedClient):
            def chat(self, messages, tools=None):
                return super().chat(messages, tools)[0], {}
        res = Agent(NoUsage([say("done")])).run("q")
        model = res.trace[0]
        self.assertTrue(model["estimated"] and model["tokens"] > 0)

    def test_model_errors_and_empty_replies_are_not_answers(self):
        class Down:
            def chat(self, messages, tools=None):
                raise ConnectionError("server down")
        res = Agent(Down()).run("q")
        self.assertEqual((res.status, res.detail), ("model_error", "ConnectionError: server down"))
        res, _ = run(say(""))
        self.assertEqual((res.status, res.answer, res.detail), ("model_error", "", "empty reply"))
        res, _ = run("not a message")
        self.assertEqual(res.status, "model_error")
        self.assertEqual(res.trace[0]["error"], "TypeError: the reply is not a message")

    def test_no_tools_runner_checks_replies_and_estimates_tokens(self):
        res = run_no_tools(ScriptedClient(["junk"]), "q")
        self.assertEqual((res.status, res.trace[0]["type"]), ("model_error", "model"))
        class NoUsage(ScriptedClient):
            def chat(self, messages, tools=None):
                return super().chat(messages, tools)[0], None
        res = run_no_tools(NoUsage([say("Final answer: 1 USD")]), "q")
        self.assertTrue(res.trace[0]["estimated"] and res.tokens > 0)

    def test_trace_links_both_sides_and_records_the_end(self):
        res, _ = run(act(call("calculator", {"expression": "4 * 68"}, "c1")), say("272 USD"))
        model, tool, end = res.trace[0], res.trace[1], res.trace[-1]
        self.assertEqual((model["calls"][0]["id"], tool["id"]), ("c1", "c1"))
        self.assertEqual((end["type"], end["status"], end["tokens"]), ("end", "answered", 200))

    def test_bare_errors_drop_the_hint(self):
        res, client = run(act(call("read_file", {"path": "travel.md"}, "c1")), say("ok"), hints=False)
        self.assertEqual(client.seen[1][-1]["content"], "Error: no file named 'travel.md'")

    def test_truncation_keeps_both_ends(self):
        out = Agent(ScriptedClient([]), max_obs_chars=200).truncate("A" * 150 + "B" * 150)
        self.assertTrue(out.startswith("A") and out.endswith("B") and "omitted" in out)


class TestTools(unittest.TestCase):
    def test_calculator_is_exact(self):
        self.assertEqual(calculator("1,800 * 1.04 ** 3"), "2024.7552")
        self.assertEqual(calculator("1000000.01"), "1000000.01")
        self.assertEqual(calculator("1234567.89 + 0.01"), "1234567.9")
        self.assertEqual(calculator("1 / 3"), "0.3333333333 (rounded)")
        self.assertEqual(calculator("9007199254740993.0"), "9007199254740993")  # not via float
        self.assertEqual(calculator("1 / 2 ** 10"), "0.0009765625")             # terminates
        self.assertTrue(calculator("1 / (2 ** 100)").startswith("0.000000000000000000000000000000788"))
        self.assertEqual(calculator("1 / (3 * 10 ** 20)"), "0.000000000000000000003333333333 (rounded)")

    def test_calculator_refuses(self):
        for expr, why in [("2 ^ 3", "'^'"), ("__import__('os')", "unsupported"),
                          ("True + 1", "unsupported"), ("1e309", "too large"),
                          ("9 ** 9 ** 9", "too large"), ("2 ** 0.5", "whole numbers"),
                          ("1 / 0", "division by zero"), ("1+" * 150 + "1", "longer than")]:
            with self.assertRaises(ToolError) as e:
                calculator(expr)
            self.assertIn(why, str(e.exception), expr)

    def test_lookup_fix_surfaces_the_row(self):
        self.assertNotIn("Denver", lookup_v1("per diem Denver meals"))
        self.assertIn("| Meals per-diem (USD/day) | Lodging cap (USD/night) | / | Denver | 68 | 195 |",
                      lookup("per diem Denver meals"))

    def test_read_file_suggests_and_sandboxes(self):
        with self.assertRaises(Exception) as e:
            read_file("per_diem")
        self.assertIn("per_diem.md", e.exception.hint)
        with self.assertRaises(Exception) as e:
            read_file("../agent.py")
        self.assertEqual(e.exception.kind, "permission_denied")


class TestScore(unittest.TestCase):
    def test_reads_only_an_explicit_final_answer(self):
        usd = ["USD", "$", "dollar"]
        self.assertTrue(score("68 * 4 = 272\nFinal answer: 272 USD", 272, usd))
        self.assertTrue(score("**Final answer:** $2,024.76", 2024.76, usd))
        self.assertIsNone(score("The answer is not 272; it is 140 USD.", 272, usd))
        self.assertFalse(score("Final answer: 272 miles", 272, usd))
        self.assertFalse(score("Final answer: not 272 but 140 USD", 272, usd))
        self.assertFalse(score("Final answer: 272 USD\nFinal answer: 140 USD", 272, usd))
        self.assertFalse(score("Final answer: 272.02 USD", 272, usd))
        self.assertTrue(score("Final answer: 2300.01 USD", 2300, usd))      # decimal, not float
        self.assertFalse(score("Final answer: not 272 USD", 272, usd))
        self.assertFalse(score("Final answer: 272 USDollarsPerMile", 272, usd))
        self.assertFalse(score("Final answer: 272", 272, usd))
        self.assertTrue(score("Final answer: 25 days.", 25, ["day", "holiday"]))


class TestReport(unittest.TestCase):
    def test_a_run_with_one_condition_renders(self):
        res, _ = run(say("Final answer: 272 USD"))
        row = {"seed": 1, "cond": "v2", "id": "denver", "status": res.status, "ok": True,
               "steps": res.steps, "tokens": res.tokens, "answer": res.answer, "detail": ""}
        with tempfile.TemporaryDirectory() as d:
            Path(d, "traces.jsonl").write_text(json.dumps({**row, "trace": res.trace}) + "\n")
            rows, files = report.render(d, ["v2:denver:1"])
        self.assertIn("v2 & 1/1 &", files["results_table.tex"])
        self.assertIn("model answers: Final answer: 272 USD", files["trace_1.txt"])


if __name__ == "__main__":
    unittest.main()
