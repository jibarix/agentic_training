"""Offline tests for Chapter 8: the three strategies' machinery, the A2A server and client, the tasks,
and the experiment's plan and halting. No model: Chapter 1's ScriptedClient replays fixed replies,
so the tests check the code around the model, not the model.

Usage: python -m unittest -v test_ch08
"""
import importlib.util
import json
import re
import sys
import unittest
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
sys.path.insert(1, str(HERE.parent / "ch04"))
sys.path.insert(0, str(HERE))
import a2a                                               # noqa: E402
import experiment                                        # noqa: E402
import make_handbook as hb                               # noqa: E402  Chapter 4's
import make_tasks                                        # noqa: E402
import strategies as S                                   # noqa: E402
from handbook_tools import TOOLS                         # noqa: E402
from llm import ScriptedClient, call                     # noqa: E402  Chapter 1's

_spec = importlib.util.spec_from_file_location("ch08_report", HERE / "report.py")
report = importlib.util.module_from_spec(_spec)          # by path: Chapter 4's report.py is on the path too
_spec.loader.exec_module(report)
TASKS = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))


def say(text):
    return {"role": "assistant", "content": text}


def use(name, args, i=1):
    return {"role": "assistant", "content": "", "tool_calls": [call(name, args, f"c{i}")]}


def result(status="done", **kw):
    return say("Worked it out.\nResult: " + json.dumps({"status": status, **kw}))


CONTRACT = {"objective": "find the meals per-diem of TR0133", "inputs": "trip TR0133",
            "output": "the amount in USD", "done_when": "you have the number"}


class TestParsing(unittest.TestCase):
    def test_tagged_takes_the_last_line(self):
        text = 'Result: {"status": "failed"}\nThinking again.\n**Result:** {"status": "done", "result": 5}'
        self.assertEqual(S.tagged(text, "result", dict), {"status": "done", "result": 5})
        self.assertIsNone(S.tagged("no tag here {}", "result", dict))
        self.assertIsNone(S.tagged("Result: [1, 2]", "result", dict))

    def test_amount_of(self):
        ok = {216: "216", 12.5: "12.5", "1,234.50": "1234.50", "$80": "80", " 0 ": "0"}
        for given, want in ok.items():
            self.assertEqual(S.amount_of({"amount": given}), Decimal(want), given)
        for bad in (True, None, "about 80", "-5", -5, [80], "80 USD", "", "1,2", "1$2", "1,,234", "12,34", "$"):
            self.assertIsNone(S.amount_of({"amount": bad}), bad)
        self.assertIsNone(S.amount_of(None))

    def test_parse_parts(self):
        good = 'Parts: [{"trip": "TR0133", "question": " Meals for TR0133? "}, {"question": "Meals for TR0134?"}]'
        self.assertEqual(S.parse_parts(good), [{"trip": "TR0133", "question": "Meals for TR0133?"},
                                               {"trip": "", "question": "Meals for TR0134?"}])
        too_many = "Parts: " + json.dumps([{"question": f"q{i}"} for i in range(S.MAX_WORKERS + 1)])
        for bad in ("Parts: []", 'Parts: [{"trip": "TR0133"}]', 'Parts: [{"question": " "}]', too_many,
                    "no parts line", 'Parts: ["Meals for TR0133?"]'):
            self.assertIsNone(S.parse_parts(bad), bad)


class TestWork(unittest.TestCase):
    def run_one(self, *replies):
        return S.work("sub-task", ScriptedClient(list(replies)), TOOLS)

    def test_done(self):
        r = self.run_one(use("calculator", {"expression": "2+2"}), result(result=4, note="calc"))
        self.assertEqual((r["state"], r["result"]["result"], r["why"], r["steps"]), ("completed", 4, None, 2))

    def test_reported_failure(self):
        r = self.run_one(result("failed", note="no such trip"))
        self.assertEqual(r["state"], "failed")
        self.assertIn("no such trip", r["why"])

    def test_no_result_line_or_bad_status(self):
        self.assertIn("no 'Result:' line", self.run_one(say("It is 4."))["why"])
        r = self.run_one(say('Result: {"status": "ok", "result": 4}'))
        self.assertEqual((r["state"], r["result"]), ("failed", None))
        r = self.run_one(say('Result: {"status": "done"}'))
        self.assertEqual((r["state"], r["result"]), ("failed", None))
        self.assertIn('no "result"', r["why"])

    def test_worker_that_stops(self):
        r = S.work("x", ScriptedClient([use("calculator", {"expression": "1"}, i) for i in range(20)]), TOOLS)
        self.assertEqual(r["state"], "failed")
        self.assertIn("step_limit", r["why"])


class TestOrchestrator(unittest.TestCase):
    def test_delegates_and_answers(self):
        client = ScriptedClient([use("delegate", CONTRACT), result(result=216, note="table"),
                                 say("The meals per-diem is 216.\nFinal answer: 216 USD")])
        out = S.orchestrator("q", client, TOOLS)
        self.assertEqual(out.status, "answered")
        d = out.info["delegations"]
        self.assertEqual((len(d), d[0]["state"], d[0]["result"]["result"]), (1, "completed", 216))
        self.assertEqual(d[0]["contract"], CONTRACT)
        self.assertEqual([t["role"] for t in out.traces], ["lead", "worker 1"])
        self.assertEqual(out.info["calls"], 3)
        worker_saw = client.seen[1]
        self.assertEqual(worker_saw[0]["content"], S.WORKER)
        self.assertEqual(worker_saw[1]["content"], S.CONTRACT.format(**CONTRACT))
        self.assertEqual(len(worker_saw), 2, "the worker starts fresh: system and contract only")
        self.assertIn('"result": 216', client.seen[2][-1]["content"])

    def test_lead_tools(self):
        client = ScriptedClient([say("Final answer: 1 USD")])
        S.orchestrator("q", client, TOOLS)
        self.assertNotIn("lookup", client.seen[0][0]["content"])

    def test_worker_failure_is_an_error_observation(self):
        client = ScriptedClient([use("delegate", CONTRACT), say("I could not."), say("Final answer: 0 USD")])
        out = S.orchestrator("q", client, TOOLS)
        self.assertIn("ERROR worker_failed", client.seen[2][-1]["content"])
        self.assertEqual(out.info["delegations"][0]["state"], "failed")

    def test_spawn_limit(self):
        n = S.MAX_WORKERS
        replies = []
        for i in range(n):
            replies += [use("delegate", CONTRACT, i), result(result=i)]
        replies += [use("delegate", CONTRACT, n), say("Final answer: 1 USD")]
        client = ScriptedClient(replies)
        out = S.orchestrator("q", client, TOOLS)
        self.assertEqual(len(out.info["delegations"]), n)
        self.assertIn("ERROR limit", client.seen[-1][-1]["content"])

    def test_token_budget(self):
        client = ScriptedClient([use("delegate", CONTRACT), result(result=1), use("delegate", CONTRACT, 2),
                                 say("Final answer: 1 USD")])
        was, S.MAX_TOKENS = S.MAX_TOKENS, 150             # the lead and one worker call spend 200
        try:
            out = S.orchestrator("q", client, TOOLS)
        finally:
            S.MAX_TOKENS = was
        self.assertEqual(len(out.info["delegations"]), 1)
        self.assertIn("ERROR budget", client.seen[-1][-1]["content"])


def split(*parts):
    return say("Parts: " + json.dumps([{"trip": t, "question": f"Meals for {t}?"} for t in parts]))


def part(amount, trip=""):
    return say("Result: " + json.dumps({"status": "done", "trip": trip, "amount": amount, "note": ""}))


class TestPipeline(unittest.TestCase):
    def test_sums_in_code(self):
        out = S.pipeline("q", ScriptedClient([split("TR0133", "TR0134"), part(216), part("270.50")]), TOOLS)
        self.assertEqual(out.status, "answered")
        self.assertTrue(out.answer.endswith("Final answer: 486.50 USD"))
        self.assertEqual([(r["trip"], r["amount"]) for r in out.info["results"]],
                         [("TR0133", "216"), ("TR0134", "270.50")])
        self.assertEqual([t["role"] for t in out.traces], ["splitter", "part 1", "part 2"])

    def test_split_asked_again_once(self):
        out = S.pipeline("q", ScriptedClient([say("two trips"), split("TR0133"), part(5)]), TOOLS)
        self.assertEqual(out.status, "answered")
        self.assertEqual(out.traces[1]["role"], "splitter (again)")
        out = S.pipeline("q", ScriptedClient([say("two trips"), say("still no list")]), TOOLS)
        self.assertEqual(out.status, "split_error")
        self.assertEqual(out.answer, "")

    def test_part_retried_once(self):
        client = ScriptedClient([split("TR0133"), say("about 200"), part(216)])
        out = S.pipeline("q", client, TOOLS)
        self.assertEqual((out.status, out.info["retried"]), ("answered", [1]))
        self.assertIn("as a number", client.seen[2][1]["content"])
        self.assertEqual(client.seen[2][0]["content"], S.PART_WORKER)

    def test_failed_part_gives_no_number(self):
        out = S.pipeline("q", ScriptedClient([split("TR0133", "TR0134"), part(216),
                                              part("lots"), part("still lots")]), TOOLS)
        self.assertEqual(out.status, "part_failed")
        self.assertEqual(out.answer, "")
        self.assertIn("part 2", out.detail)
        self.assertEqual(out.info["results"][-1]["amount"], None)


class FakeWorker:
    def __init__(self, state="completed"):
        self.state, self.seen = state, []

    def __call__(self, text):
        self.seen.append(text)
        ok = self.state == "completed"
        return {"state": self.state, "result": {"status": "done", "result": 42} if ok else None,
                "why": None if ok else "no such trip", "steps": 3, "tokens": 300, "trace": [{"step": 1}]}


class TestA2A(unittest.TestCase):
    def setUp(self):
        self.worker = FakeWorker()
        self.server = a2a.Server(self.worker).start()
        self.client = a2a.Client(self.server.url)

    def tearDown(self):
        self.server.stop()

    def post(self, body, version=a2a.VERSION):
        headers = {"Content-Type": "application/json"}
        if version is not None:
            headers["A2A-Version"] = version
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        with urllib.request.urlopen(urllib.request.Request(self.client.url, data, headers)) as r:
            return json.load(r)

    def code(self, out):
        return out.get("error", {}).get("code")

    def test_binds_to_loopback(self):
        self.assertTrue(self.server.url.startswith("http://127.0.0.1:"))

    def test_card(self):
        c = self.client.card
        for k in ("name", "description", "supportedInterfaces", "version", "capabilities",
                  "defaultInputModes", "defaultOutputModes", "skills"):
            self.assertIn(k, c)
        self.assertEqual(c["supportedInterfaces"][0],
                         {"url": self.server.url + "/a2a", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"})
        for k in ("id", "name", "description", "tags"):
            self.assertIn(k, c["skills"][0])
        self.assertFalse(c["capabilities"]["streaming"])

    def test_card_etag(self):
        with urllib.request.urlopen(self.server.url + a2a.CARD_PATH) as r:
            etag = r.headers["ETag"]
            self.assertIn("max-age", r.headers["Cache-Control"])
        req = urllib.request.Request(self.server.url + a2a.CARD_PATH, headers={"If-None-Match": etag})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code, 304)

    def test_send_message(self):
        t = self.client.send_text("Objective: x")
        self.assertEqual(t["status"]["state"], "TASK_STATE_COMPLETED")
        self.assertEqual(t["artifacts"][0]["parts"][0], {"data": {"status": "done", "result": 42},
                                                         "mediaType": "application/json"})
        self.assertEqual(self.worker.seen, ["Objective: x"])
        self.assertEqual(self.client.rpc("GetTask", {"id": t["id"]})["result"], t)

    def test_version(self):
        msg = {"messageId": "m1", "role": "ROLE_USER", "parts": [{"text": "x"}]}
        body = {"jsonrpc": "2.0", "id": 1, "method": "SendMessage", "params": {"message": msg}}
        self.assertEqual(self.code(self.post(body, version=None)), -32009)
        self.assertEqual(self.code(self.post(body, version="0.3")), -32009)
        self.assertEqual(self.worker.seen, [])
        self.assertIn("result", self.post(body))

    def test_errors(self):
        rpc = self.client.rpc
        msg = {"messageId": "m1", "role": "ROLE_USER", "parts": [{"text": "x"}]}
        self.assertEqual(self.code(rpc("SendMessage", {"message": {"role": "ROLE_USER", "parts": [{"text": "x"}]}})), -32602)
        self.assertEqual(self.code(rpc("SendMessage", {"message": msg | {"role": "ROLE_AGENT"}})), -32602)
        self.assertEqual(self.code(rpc("SendMessage", {"message": msg | {"parts": [{"url": "file:///x"}]}})), -32602)
        self.assertEqual(self.code(rpc("SendMessage", {"message": msg, "configuration": {"returnImmediately": True}})), -32004)
        self.assertEqual(self.code(rpc("GetTask", {"id": "nope"})), -32001)
        self.assertEqual(self.code(rpc("SendStreamingMessage", {"message": msg})), -32004)
        self.assertEqual(self.code(rpc("CreateTaskPushNotificationConfig", {})), -32003)
        self.assertEqual(self.code(rpc("Fly", {})), -32601)
        self.assertEqual(self.code(self.post(b"{not json")), -32700)
        self.assertEqual(self.code(self.post({"jsonrpc": "1.0", "method": "SendMessage"})), -32600)
        self.assertEqual(self.worker.seen, [])
        self.assertEqual([w["error"] for w in self.server.log],
                         [None, -32602, -32602, -32602, -32004, -32001, -32004, -32003, -32601, -32700, -32600])
        self.assertEqual(self.server.log[0]["method"], "GET agent card")

    def test_worker_exception_is_internal_error(self):
        self.server.worker = lambda text: 1 / 0
        out = self.client.rpc("SendMessage", {"message": {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]}})
        self.assertEqual(self.code(out), -32603)
        self.assertIn("ZeroDivisionError", out["error"]["data"][0]["reason"])

    def test_sender_maps_back(self):
        r = self.client.sender(self.server.traces)("x")
        self.assertEqual((r["state"], r["result"], r["why"], r["steps"], r["tokens"], r["trace"]),
                         ("completed", {"status": "done", "result": 42}, None, 3, 300, [{"step": 1}]))
        self.server.worker = FakeWorker("failed")
        r = self.client.sender()("x")
        self.assertEqual((r["state"], r["result"], r["why"], r["trace"]), ("failed", None, "no such trip", []))

    def test_task_references(self):
        t = self.client.send_text("first")
        msg = {"messageId": "m2", "role": "ROLE_USER", "parts": [{"text": "more"}]}
        rpc = self.client.rpc
        self.assertEqual(self.code(rpc("SendMessage", {"message": msg | {"taskId": "nope"}})), -32001)
        self.assertEqual(self.code(rpc("SendMessage", {"message": msg | {"taskId": t["id"]}})), -32004)
        self.assertEqual(self.code(rpc("SendMessage", {"message": msg | {"taskId": t["id"], "contextId": "other"}})),
                         -32602)
        self.assertEqual(self.worker.seen, ["first"], "no message reached the worker")
        ctx = self.client.rpc("SendMessage", {"message": msg | {"contextId": t["contextId"]}})["result"]["task"]
        self.assertEqual((ctx["contextId"], ctx["id"] != t["id"]), (t["contextId"], True))

    def test_malformed_fields(self):
        msg = {"messageId": "m", "role": "ROLE_USER", "parts": [{"text": "x"}]}
        rpc = self.client.rpc
        for params in ({"message": msg | {"contextId": {"a": 1}}}, {"message": msg | {"taskId": 7}},
                       {"message": msg | {"parts": [{"text": "x", "data": {}}]}},
                       {"message": msg | {"parts": "x"}}, {"message": msg, "configuration": []}, []):
            self.assertEqual(self.code(rpc("SendMessage", params)), -32602, params)
        self.assertEqual(self.code(rpc("GetTask", {"id": 5})), -32602)
        self.assertEqual(self.worker.seen, [])

    def test_budget_is_the_same_through_a2a(self):
        def run(through_a2a):
            client = ScriptedClient([use("delegate", CONTRACT), result(result=1), use("delegate", CONTRACT, 2),
                                     say("Final answer: 1 USD")])
            meter = S.Meter(client)
            send = None
            if through_a2a:
                self.server.worker = lambda text: S.work(text, meter, TOOLS)
                send = self.client.sender(self.server.traces)
            was, S.MAX_TOKENS = S.MAX_TOKENS, 150         # the lead and one worker call spend 200
            try:
                out = S.orchestrator("q", meter, TOOLS, send=send)
            finally:
                S.MAX_TOKENS = was
            return len(out.info["delegations"]), out.info["tokens"], meter.tokens, client.seen[-1][-1]["content"]
        for r in (run(False), run(True)):
            self.assertEqual(r[:3], (1, 400, 400))   # lead, worker, lead, lead
            self.assertIn("ERROR budget", r[3])

    def test_orchestrator_through_a2a(self):
        client = ScriptedClient([use("delegate", CONTRACT), result(result=216),
                                 say("Final answer: 216 USD")])
        self.server.worker = lambda text: S.work(text, client, TOOLS)
        out = S.orchestrator("q", client, TOOLS, send=self.client.sender(self.server.traces))
        self.assertEqual(out.status, "answered")
        self.assertEqual(out.info["delegations"][0]["result"], {"status": "done", "result": 216})
        self.assertEqual(client.seen[1][1]["content"], S.CONTRACT.format(**CONTRACT))
        self.assertEqual(out.traces[1]["trace"][-1]["type"], "end")


class TestTasks(unittest.TestCase):
    def test_file_is_what_make_tasks_builds(self):
        self.assertEqual(make_tasks.build(), TASKS)

    def test_counts_and_ids(self):
        clusters = [t["cluster"] for t in TASKS]
        self.assertEqual({c: clusters.count(c) for c in set(clusters)},
                         dict.fromkeys(["meals", "mileage", "full", "billed", "chain_meals", "chain_lodging"], 6))
        self.assertEqual(len({t["id"] for t in TASKS}), 36)

    def test_answers_from_the_handbook(self):
        rates, staff, trips = hb.build()
        trip = {t["id"]: t for t in trips}
        for t in TASKS:
            if t["set"] == "decomposable":
                self.assertEqual(Decimal(str(t["answer"])), sum(Decimal(v) for v in t["per_trip"].values()), t["id"])
                self.assertTrue(all(trip[x]["emp"] == t["employee"] and trip[x]["billed"] == "ACME"
                                    for x in t["trips"]), t["id"])
            else:
                c = t["chain"]
                self.assertEqual(trip[c["trip"]]["emp"], c["employee"])
                self.assertEqual(staff[c["employee"]], c["office"])
                self.assertNotEqual(trip[c["trip"]]["city"], c["office"])
                self.assertEqual(trip[c["trip"]]["billed"], "ACME", t["id"])     # else ACME pays no lodging
                moved = dict(trip[c["trip"]], city=c["office"])                  # the trip, at the office city
                if t["cluster"] == "chain_meals":
                    days = int(re.search(r"a (\d+)-day trip", t["task"])[1])
                    want = hb.meals(dict(moved, days=days), rates)
                else:
                    want = hb.lodging(moved, rates)
                self.assertEqual(Decimal(str(t["answer"])), Decimal(str(want)), t["id"])

    def test_no_chapter_4_employee(self):
        used = {t["id"].split("_")[1].upper() for t in json.loads(
            (HERE.parent / "ch04" / "tasks_long.json").read_text(encoding="utf-8"))}
        emps = {t.get("employee") or t["chain"]["employee"] for t in TASKS}
        self.assertFalse(emps & used)


class Broken:
    def chat(self, messages, tools=None):
        raise urllib.error.URLError("connection refused")


class TestExperiment(unittest.TestCase):
    def test_plan(self):
        p = experiment.plan(TASKS, 5, ["compare", "a2a"])
        self.assertEqual(len(p), 36 * 3 * 5 + 12)
        self.assertEqual([c for _, _, _, c in p[:3]], experiment.CONDS)
        a = [t["cluster"] for part, _, t, _ in p if part == "a2a"]
        self.assertEqual(sorted(set(a.count(c) for c in a)), [2])
        self.assertEqual(len({(x, s, t["id"], c) for x, s, t, c in p}), len(p))

    def test_server_failure_halts(self):
        for part, cond in (("compare", "single"), ("compare", "orchestrator"), ("compare", "pipeline"),
                           ("a2a", "orchestrator")):
            with self.assertRaises(experiment.Halted, msg=(part, cond)):
                experiment.one(part, 1, TASKS[0], cond, Broken())

    def test_row(self):
        client = ScriptedClient([split("TR0133", "TR0134", "TR0132"), part(216), part(270), part(118)])
        row, traces = experiment.one("compare", 1, TASKS[0], "pipeline", client)
        self.assertEqual((row["ok"], row["status"], row["calls"], row["agents"]), (True, "answered", 4, 4))
        self.assertNotIn("errors", row["info"])
        client = ScriptedClient([use("delegate", CONTRACT), result(result=604), say("Final answer: 604 USD")])
        row, _ = experiment.one("a2a", 1, TASKS[0], "orchestrator", client)
        self.assertEqual((row["ok"], row["wire"]["requests"], row["wire"]["posts"], row["wire"]["errors"]),
                         (True, 2, 1, 0))                     # the card, then one SendMessage
        self.assertEqual(row["info"]["tokens"], row["tokens"])


class TestReport(unittest.TestCase):
    def rows(self):
        t, chain = TASKS[0], next(x for x in TASKS if x["set"] == "sequential")
        trips = t["trips"]
        good = [split(*trips)] + [part(t["per_trip"][x]) for x in trips]
        bad_part = [split(*trips)] + [part(t["per_trip"][x]) for x in trips[:-1]] + [part(1)]
        bad_split = [split(*trips[:-1])] + [part(t["per_trip"][x]) for x in trips[:-1]]
        out = []
        for seed, script in ((1, good), (2, bad_part), (3, bad_split)):
            for task in (t, chain):
                runs = {"pipeline": script if task is t else [split(""), part(chain["answer"])],
                        "single": [say(f"Final answer: {task['answer']} USD")],
                        "orchestrator": [use("delegate", CONTRACT), result(result=1),
                                         say(f"Final answer: {task['answer'] + seed - 1} USD")]}
                for cond in experiment.CONDS:
                    row, _ = experiment.one("compare", seed, task, cond, ScriptedClient(list(runs[cond])))
                    out.append(row)
        return out

    def test_numbers(self):
        table, nums = report.render(self.rows())
        self.assertEqual(len(table), 3)
        self.assertEqual((nums["SingleMean"], nums["OrchMean"], nums["PipeMean"]), ("100.0", "33.3", "66.7"))
        self.assertEqual((nums["PipeDecMean"], nums["PipeSeqMean"]), ("33.3", "100.0"))
        self.assertEqual(nums["SingleTokensX"], "1.0")
        self.assertEqual((nums["PipeWrong"], nums["PipeWrongSplit"], nums["PipeWrongPart"], nums["PipeWrongOther"]),
                         (2, 1, 1, 0))
        self.assertEqual(nums["PipeRightTrips"], 2)
        self.assertEqual(nums["OrchDelegations"], "1.0")
        self.assertEqual(nums["Tasks"], 2)
        self.assertIn("OrchSingleDiff", nums)
        self.assertEqual(set(nums) - set(report.MACROS), set())

    def test_parts_check_groups_by_trip(self):
        t = next(x for x in TASKS if x["cluster"] == "full")
        a, b = t["trips"][:2]
        half = {x: Decimal(t["per_trip"][x]) / 2 for x in t["per_trip"]}
        parts = [{"trip": x, "question": "q"} for x in t["trips"] for _ in (1, 2)]
        results = [{"trip": x, "amount": str(half[x])} for x in t["trips"] for _ in (1, 2)]
        row = {"info": {"parts": parts, "results": results}}
        self.assertEqual(report.parts_check(row, t), (True, dict.fromkeys(t["trips"], True)))
        row["info"]["results"][0]["amount"] = "0"
        self.assertEqual(report.parts_check(row, t)[1][a], False)
        row["info"]["parts"] = [p for p in parts if p["trip"] != b]
        self.assertFalse(report.parts_check(row, t)[0])

    def test_parts_check_counts_failed_parts(self):
        t = next(x for x in TASKS if x["cluster"] == "full")
        a, b = t["trips"][:2]
        parts = [{"trip": a, "question": "q"}, {"trip": b, "question": "q"}]
        failed = {"info": {"parts": parts, "results": [{"trip": a, "amount": t["per_trip"][a]},
                                                         {"trip": b, "amount": None}]}}
        self.assertEqual(report.parts_check(failed, t)[1], {a: True, b: False})
        unrun = {"info": {"parts": parts, "results": [{"trip": a, "amount": t["per_trip"][a]}]}}
        self.assertEqual(report.parts_check(unrun, t)[1], {a: True, b: False})

    def test_completeness(self):
        want = report.planned(report.tasks())
        self.assertEqual(len(want), 36 * 3 * 5 + 12)
        self.assertEqual(want, {(x, s, t["id"], c) for x, s, t, c in experiment.plan(TASKS, 5, ["compare", "a2a"])})
        rows = [{"part": x, "seed": s, "id": i, "cond": c} for x, s, i, c in sorted(want)]
        self.assertIsNone(report.rows_not_the_design(rows, want))
        self.assertIn("duplicate", report.rows_not_the_design(rows + rows[:1], want))
        swapped = rows[1:] + [dict(rows[0], seed=999)]
        self.assertIn("lacks 1", report.rows_not_the_design(swapped, want))

    def test_placeholders(self):
        f = report.files([], {})
        self.assertIn("has not been made", f["ch08_compare.tex"])
        self.assertEqual(f["ch08_numbers.tex"].count("{--}"), len(report.MACROS))


if __name__ == "__main__":
    unittest.main()
