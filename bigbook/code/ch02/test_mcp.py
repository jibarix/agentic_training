"""Offline tests: the server message by message, the stdio transport with faults injected,
and the bridge, which must give Chapter 1's agent exactly the observations it had before."""
import json
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).parent
import bridge                                            # noqa: E402  (puts ../ch01 on the path)
from agent import Agent                                  # noqa: E402
from handbook_server import handbook_tools              # noqa: E402
from llm import ScriptedClient, call                     # noqa: E402
from mcp_client import McpError, McpTimeout, ServerExited, StdioClient  # noqa: E402
from mcp_server import Server                            # noqa: E402
from tools import TOOLS, ToolError                       # noqa: E402

META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {}}
SERVER = [sys.executable, str(HERE / "handbook_server.py")]


def req(method, rid=1, **params):
    return {"jsonrpc": "2.0", "id": rid, "method": method, "params": {**params, "_meta": dict(META)}}


class Quiet:
    def write(self, s):
        pass

    def flush(self):
        pass


class TestServer(unittest.TestCase):
    """Server.handle: one message in, one response out, no I/O."""

    def setUp(self):
        self.s = Server("handbook", "2.0", handbook_tools(), log=Quiet())

    def test_discover(self):
        r = self.s.handle(req("server/discover"))["result"]
        self.assertEqual(r["resultType"], "complete")
        self.assertEqual(r["supportedVersions"], ["2026-07-28"])
        self.assertIn("tools", r["capabilities"])
        self.assertEqual(r["_meta"]["io.modelcontextprotocol/serverInfo"]["name"], "handbook")
        self.assertIn(r["cacheScope"], ("public", "private"))

    def test_every_request_needs_meta(self):
        bare = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        self.assertEqual(self.s.handle(bare)["error"]["code"], -32602)
        no_caps = req("tools/list")
        del no_caps["params"]["_meta"]["io.modelcontextprotocol/clientCapabilities"]
        self.assertEqual(self.s.handle(no_caps)["error"]["code"], -32602)

    def test_unsupported_version_lists_supported(self):
        m = req("tools/list")
        m["params"]["_meta"] = {**META, "io.modelcontextprotocol/protocolVersion": "2099-01-01"}
        e = self.s.handle(m)["error"]
        self.assertEqual(e["code"], -32022)
        self.assertEqual(e["data"], {"supported": ["2026-07-28"], "requested": "2099-01-01"})

    def test_protocol_errors(self):
        self.assertEqual(self.s.handle(req("prompts/list"))["error"]["code"], -32601)
        self.assertEqual(self.s.handle({"id": 1, "method": "tools/list"})["error"]["code"], -32600)
        self.assertEqual(self.s.handle([req("tools/list")])["error"]["code"], -32600)  # no batches
        self.assertEqual(self.s.handle(req("tools/list", rid=True))["error"]["code"], -32600)

    def test_notification_gets_no_reply(self):
        n = {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}}
        self.assertIsNone(self.s.handle(n))

    def test_list_is_stable_and_pages(self):
        s = Server("handbook", "2.0", handbook_tools(), page_size=2, log=Quiet())
        first = s.handle(req("tools/list"))["result"]
        self.assertEqual([t["name"] for t in first["tools"]], ["lookup", "read_file"])
        rest = s.handle(req("tools/list", cursor=first["nextCursor"]))["result"]
        self.assertEqual([t["name"] for t in rest["tools"]], ["calculator"])
        self.assertNotIn("nextCursor", rest)
        for bad in ("x9", "²", "-1", "9", 2):                       # "²" passes str.isdigit
            self.assertEqual(s.handle(req("tools/list", cursor=bad))["error"]["code"], -32602)

    def test_tool_schema_is_chapter_1s(self):
        tools = self.s.handle(req("tools/list"))["result"]["tools"]
        for t in tools:
            self.assertEqual(t["inputSchema"], TOOLS[t["name"]][1]["function"]["parameters"])
            self.assertTrue(t["annotations"]["readOnlyHint"])

    def test_call_success(self):
        r = self.s.handle(req("tools/call", name="calculator", arguments={"expression": "4 * 68"}))
        self.assertEqual(r["result"]["content"], [{"type": "text", "text": "272"}])
        self.assertFalse(r["result"]["isError"])

    def test_unknown_tool_is_a_protocol_error(self):
        r = self.s.handle(req("tools/call", name="search", arguments={}))
        self.assertEqual(r["error"], {"code": -32602, "message": "Unknown tool: search"})

    def test_tool_failure_is_a_result_with_is_error(self):
        r = self.s.handle(req("tools/call", name="read_file", arguments={"path": "travel.md"}))["result"]
        self.assertTrue(r["isError"])
        self.assertEqual(r["structuredContent"]["error"]["kind"], "not_found")
        self.assertEqual(json.loads(r["content"][0]["text"]), r["structuredContent"])

    def test_server_validates_inputs_itself(self):
        for args in ({"expression": 7}, {}, {"expression": "1", "x": "2"}):
            r = self.s.handle(req("tools/call", name="calculator", arguments=args))["result"]
            self.assertTrue(r["isError"])
            self.assertEqual(r["structuredContent"]["error"]["kind"], "bad_arguments")

    def test_malformed_calls_are_protocol_errors(self):
        bad = req("tools/call", name="calculator")
        bad["params"] = [1]
        self.assertEqual(self.s.handle(bad)["error"]["code"], -32602)
        for name, args in (([], {}), ("calculator", [1])):
            r = self.s.handle(req("tools/call", name=name, arguments=args))
            self.assertEqual(r["error"]["code"], -32602)

    def test_a_server_bug_is_an_internal_error(self):
        self.s.list_tools = lambda params: 1 / 0
        self.assertEqual(self.s.handle(req("tools/list"))["error"]["code"], -32603)

    def test_a_tool_bug_does_not_kill_the_server(self):
        def broken(query):
            raise KeyError("index")
        s = Server("t", "1", [(broken, {"name": "lookup", "inputSchema": {
            "type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}}})],
            log=Quiet())
        r = s.handle(req("tools/call", name="lookup", arguments={"query": "x"}))["result"]
        self.assertEqual(r["structuredContent"]["error"]["kind"], "tool_failed")


class TestStdio(unittest.TestCase):
    """The real transport: a subprocess, pipes, and the faults that come with them."""

    def client(self, *flags, **kw):
        c = StdioClient("handbook", SERVER + list(flags), **kw).start()
        self.addCleanup(c.close)
        c.discover()
        c.list_tools()
        return c

    def test_parse_error_then_carry_on(self):
        c = self.client()
        c.proc.stdin.write(b"{not json\n")
        c.proc.stdin.flush()
        msg = c.inbox.get(timeout=5)
        self.assertEqual(msg["error"]["code"], -32700)
        self.assertNotIn("id", msg)
        self.assertEqual(c.call_tool("calculator", {"expression": "2 + 2"})["content"][0]["text"], "4")

    def test_logs_go_to_stderr_not_stdout(self):
        c = self.client()
        c.call_tool("lookup", {"query": "mileage"})
        c.close()
        self.assertEqual(c.junk, [])
        self.assertTrue(any("call lookup" in line for line in c.stderr))

    def test_junk_on_stdout_is_skipped_and_kept(self):
        c = self.client("--noise")
        self.assertEqual(c.junk, ["Loading handbook index... done"])
        self.assertIn("0.70 USD", c.call_tool("lookup", {"query": "reimbursed per mile"})["content"][0]["text"])

    def test_crash_restart_and_retry_when_trusted_and_read_only(self):
        c = self.client("--crash-on-call", "2", trusted=True)
        c.call_tool("calculator", {"expression": "1 + 1"})
        r = c.call_tool("calculator", {"expression": "2 + 2"})      # crashes, restarts, retries
        self.assertEqual(r["content"][0]["text"], "4")
        self.assertEqual(c.restarts, 1)

    def test_malformed_requests_get_errors_and_the_server_stays_up(self):
        c = self.client("--slow", "lookup=0.01", "--crash-on-call", "99")   # the fault paths are live
        meta = dict(META)
        msgs = [{"jsonrpc": "2.0", "id": "m1", "method": "tools/call", "params": [1]},
                {"jsonrpc": "2.0", "id": "m2", "method": "tools/call",
                 "params": {"name": [], "arguments": {}, "_meta": meta}},
                {"jsonrpc": "2.0", "id": "m3", "method": "tools/list", "params": {"cursor": "²", "_meta": meta}}]
        for m in msgs:
            c.send(m)
            self.assertEqual(c.inbox.get(timeout=5)["error"]["code"], -32602)
        self.assertEqual(c.call_tool("calculator", {"expression": "2 + 2"})["content"][0]["text"], "4")
        self.assertIsNone(c.proc.poll())

    def test_hints_say_what_the_client_did(self):
        c = self.client("--crash-on-call", "1", trusted=True)          # every new process crashes once
        with self.assertRaises(ToolError) as e:
            bridge.remote(c, "calculator")(expression="1 + 1")
        self.assertEqual(c.restarts, 2)
        self.assertIn("tried 2 times", e.exception.hint)

    def test_crash_is_not_retried_for_an_untrusted_server(self):
        c = self.client("--crash-on-call", "1")                       # annotations not believed
        with self.assertRaises(ServerExited):
            c.call_tool("calculator", {"expression": "1 + 1"})
        self.assertEqual(c.restarts, 1)
        fn = bridge.remote(c, "calculator")
        with self.assertRaises(ToolError) as e:                       # fresh process crashes again
            fn(expression="1 + 1")
        self.assertEqual(e.exception.kind, "server_unavailable")
        self.assertIn("not repeated", e.exception.hint)
        self.assertIn("may or may not have taken effect", e.exception.hint)

    def test_timeout_cancels_restarts_and_becomes_an_observation(self):
        c = self.client("--slow", "lookup=5", timeout=0.5)
        t0 = time.monotonic()
        with self.assertRaises(ToolError) as e:
            bridge.remote(c, "lookup")(query="mileage")
        self.assertEqual(e.exception.kind, "timeout")
        self.assertIn("not repeated", e.exception.hint)                # untrusted: no second attempt
        self.assertLess(time.monotonic() - t0, 3)
        self.assertEqual(c.restarts, 1)
        self.assertEqual(c.call_tool("calculator", {"expression": "3 * 3"})["content"][0]["text"], "9")

    def test_a_server_that_stops_reading_cannot_block_a_request(self):
        c = StdioClient("deaf", [sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.3).start()
        self.addCleanup(c.close)
        t0 = time.monotonic()
        with self.assertRaises(McpTimeout):                            # 1 MB fills the pipe; the write blocks
            c.request("tools/call", {"name": "lookup", "arguments": {"query": "x" * 1_000_000}})
        self.assertLess(time.monotonic() - t0, 1.5)

    def test_shutdown_by_closing_stdin(self):
        c = self.client()
        proc = c.proc
        t0 = time.monotonic()
        c.close()
        self.assertEqual(proc.returncode, 0)                          # exited by itself
        self.assertLess(time.monotonic() - t0, 2)

    def test_protocol_error_from_a_stale_tool_list(self):
        c = self.client()
        with self.assertRaises(McpError) as e:
            c.call_tool("search", {"query": "x"})
        self.assertEqual(e.exception.code, -32602)
        with self.assertRaises(ToolError) as e:
            bridge.remote(c, "search")(query="x")
        self.assertEqual(e.exception.kind, "server_error")

    def test_client_follows_cursors(self):
        c = StdioClient("x", [])
        pages = {None: {"tools": [{"name": "a"}], "nextCursor": "1"}, "1": {"tools": [{"name": "b"}]}}
        c.request = lambda method, params=None: pages[(params or {}).get("cursor")]
        self.assertEqual([t["name"] for t in c.list_tools()], ["a", "b"])

    def test_an_empty_cursor_is_still_a_cursor(self):
        c = StdioClient("x", [])
        pages = {None: {"tools": [{"name": "a"}], "nextCursor": ""}, "": {"tools": [{"name": "b"}]}}
        c.request = lambda method, params=None: pages[(params or {}).get("cursor")]
        self.assertEqual([t["name"] for t in c.list_tools()], ["a", "b"])


class TestBridge(unittest.TestCase):
    """Chapter 1's agent, unchanged, with its tools on the other side of a pipe."""

    def setUp(self):
        self.c = StdioClient("handbook", SERVER).start()
        self.addCleanup(self.c.close)

    def test_the_model_sees_the_same_tool_specs(self):
        reg = bridge.registry([self.c])
        self.assertEqual(json.dumps([s for _, s in reg.values()]),
                         json.dumps([s for _, s in TOOLS.values()]))

    def test_same_script_same_observations(self):
        script = [
            {"role": "assistant", "content": "", "tool_calls": [
                call("lookup", {"query": "per diem Denver"}, "a"),
                call("read_file", {"path": "travel.md"}, "b"),
                call("read_file", {"path": "../agent.py"}, "c"),
                call("calculator", {"expression": "2 ^ 3"}, "d"),
                call("calculator", {"expr": "1"}, "e"),
                call("search", {"query": "x"}, "f"),
                call("calculator", {"expression": 4}, "g")]},
            {"role": "assistant", "content": "Final answer: 272 USD"}]

        def run(tools):
            client = ScriptedClient([json.loads(json.dumps(m)) for m in script])
            res = Agent(client, tools=tools).run("q")
            return client.seen, [{k: v for k, v in t.items() if k != "seconds"} for t in res.trace]

        local, remote = run(TOOLS), run(bridge.registry([self.c]))
        self.assertEqual(local, remote)
        kinds = [m["content"].split(":")[0] for m in local[0][-1] if m["role"] == "tool"]
        self.assertEqual(kinds, ["per_diem.md", "ERROR not_found", "ERROR permission_denied",
                                 "ERROR bad_expression", "ERROR bad_arguments", "ERROR unknown_tool", "4"])

    def test_names_collide_without_a_prefix(self):
        archive = StdioClient("archive", SERVER + ["--name", "archive", "--dir", str(HERE / "archive")]).start()
        self.addCleanup(archive.close)
        with self.assertRaises(ValueError):
            bridge.registry([self.c, archive])
        reg = bridge.registry([self.c, archive], prefix=True)
        self.assertEqual(list(reg), ["handbook__lookup", "handbook__read_file", "handbook__calculator",
                                     "archive__lookup", "archive__read_file", "archive__calculator"])
        self.assertIn("0.655", reg["archive__lookup"][0](query="reimbursed per mile"))
        self.assertIn("0.70", reg["handbook__lookup"][0](query="reimbursed per mile"))

    def test_exposed_names_fit_the_model_api(self):
        self.assertEqual(bridge.exposed_name("acme.files", "get.file", True), "acme_files__get_file")
        with self.assertRaises(ValueError):
            bridge.exposed_name("s" * 40, "t" * 40, True)

    def test_other_results(self):
        self.assertEqual(bridge.result_text({"content": [{"type": "image", "data": "..."}]}),
                         "[image content omitted]")
        with self.assertRaises(ToolError) as e:
            bridge.result_text({"isError": True, "content": [{"type": "text", "text": "API down"}]})
        self.assertEqual((e.exception.kind, str(e.exception)), ("tool_error", "API down"))
        with self.assertRaises(ToolError) as e:                       # structuredContent can be any JSON
            bridge.result_text({"isError": True, "structuredContent": ["retry later"],
                                "content": [{"type": "text", "text": "retry later"}]})
        self.assertEqual((e.exception.kind, str(e.exception)), ("tool_error", "retry later"))
        with self.assertRaises(ToolError) as e:
            bridge.result_text({"resultType": "input_required"})
        self.assertEqual(e.exception.kind, "unsupported")


if __name__ == "__main__":
    unittest.main()
