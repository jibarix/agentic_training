"""A minimal MCP client for the stdio transport (protocol 2026-07-28), standard library only.

The client launches the server as a subprocess and owns its lifecycle: it restarts the
process after a crash or a timeout, and retries a call once only when that cannot do harm."""
import itertools
import json
import queue
import subprocess
import threading
import time

VERSION = "2026-07-28"
META = "io.modelcontextprotocol/"
EOF = object()                                      # the reader thread's end-of-output marker


class McpError(Exception):
    """A JSON-RPC error response from the server."""

    def __init__(self, code, message, data=None):
        super().__init__(f"{message} (code {code})")
        self.code, self.data = code, data


class CallFailed(Exception):
    """The call got no reply. attempts: how many times it was sent; retry_safe: whether the client
    was allowed to send it again (only then does a second attempt happen)."""
    attempts, retry_safe = 1, False


class McpTimeout(CallFailed):
    pass


class ServerExited(CallFailed):
    pass


class StdioClient:
    def __init__(self, name, command, timeout=10.0, trusted=False):
        """name: the id this client uses for the server (never the server's own serverInfo).
        trusted: whether to believe the server's annotations (readOnlyHint, idempotentHint)."""
        self.name, self.command, self.timeout, self.trusted = name, command, timeout, trusted
        self.ids = itertools.count(1)
        self.proc, self.tools = None, {}
        self.junk, self.stderr, self.dropped = [], [], []   # what did not belong on the wire
        self.restarts, self.log = 0, []                     # log: (method, name, seconds, outcome)

    # -- process lifecycle ------------------------------------------------------------
    def start(self):
        self.proc = subprocess.Popen(self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        self.inbox, self.outbox = queue.Queue(), queue.Queue()
        threading.Thread(target=self._read, args=(self.proc.stdout, self.inbox), daemon=True).start()
        threading.Thread(target=self._write, args=(self.proc.stdin, self.outbox), daemon=True).start()
        threading.Thread(target=self._drain, args=(self.proc.stderr,), daemon=True).start()
        return self

    def _read(self, stream, inbox):
        with stream:                                # each reader closes its pipe at end of output
            for raw in stream:
                try:
                    inbox.put(json.loads(raw))
                except ValueError:                  # not an MCP message: keep it, skip it
                    self.junk.append(raw.decode("utf-8", "replace").rstrip())
        inbox.put(EOF)

    def _write(self, stream, outbox):
        """Writes run here, so a server that stops reading blocks this thread, not the request."""
        with stream:
            for data, written in iter(outbox.get, EOF):
                try:
                    stream.write(data)
                    stream.flush()
                except (OSError, ValueError):       # the pipe is gone; the read will say why
                    return
                written.set()

    def _drain(self, stream):
        with stream:
            for raw in stream:
                self.stderr.append(raw.decode("utf-8", "replace").rstrip())
                del self.stderr[:-200]

    def close(self, wait=2.0):
        """The spec's shutdown: close stdin, wait, then terminate."""
        if self.proc is None:
            return
        try:
            self.outbox.put(EOF)                    # the writer closes stdin after what is queued
            self.proc.wait(timeout=wait)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()
            self.proc.wait()
        self.proc = None

    def restart(self):
        if self.proc is not None:
            self.proc.kill()
            self.proc.wait()
            self.outbox.put(EOF)
        self.restarts += 1
        self.start()

    # -- one request, one response --------------------------------------------------------
    def request(self, method, params=None, timeout=None):
        rid = f"{self.name}-{next(self.ids)}"
        meta = {META + "protocolVersion": VERSION, META + "clientCapabilities": {},
                META + "clientInfo": {"name": "bigbook-ch02", "version": "1.0"}}
        deadline = time.monotonic() + (timeout or self.timeout)   # the write counts too
        written = self.send({"jsonrpc": "2.0", "id": rid, "method": method,
                             "params": {**(params or {}), "_meta": meta}})
        while True:
            try:
                if not written.wait(max(0.0, deadline - time.monotonic())):
                    raise queue.Empty
                msg = self.inbox.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:                     # the cancellation is queued, not waited for
                self.notify("notifications/cancelled", {"requestId": rid, "reason": "timeout"})
                raise McpTimeout(f"no reply to {method} within {timeout or self.timeout} s")
            if msg is EOF:
                raise ServerExited(f"server exited (code {self.proc.poll()}) during {method}")
            if not isinstance(msg, dict) or msg.get("id") != rid:
                self.dropped.append(msg)            # a late reply, or a notification we did not ask for
                continue
            if "error" in msg:
                e = msg["error"] if isinstance(msg["error"], dict) else {}
                raise McpError(e.get("code"), e.get("message", ""), e.get("data"))
            return msg.get("result") or {}

    def send(self, msg):
        """Queue one message for the writer thread; the returned event is set once it is written."""
        written = threading.Event()
        self.outbox.put((json.dumps(msg).encode("utf-8") + b"\n", written))
        return written

    def notify(self, method, params):
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    # -- the protocol ------------------------------------------------------------------------
    def discover(self):
        res = self.request("server/discover")
        if VERSION not in res.get("supportedVersions", []):
            raise McpError(-32022, f"server does not support {VERSION}", res.get("supportedVersions"))
        return res

    def list_tools(self):
        tools, cursor = [], None
        while True:
            res = self.request("tools/list", {} if cursor is None else {"cursor": cursor})
            tools += res.get("tools", [])
            cursor = res.get("nextCursor")         # "" is a valid cursor; only absence ends the list
            if cursor is None:
                break
        self.tools = {t["name"]: t for t in tools}
        return tools

    def safe_to_retry(self, name):
        hints = self.tools.get(name, {}).get("annotations", {}) if self.trusted else {}
        return bool(hints.get("readOnlyHint") or hints.get("idempotentHint"))

    def call_tool(self, name, arguments):
        for attempt in (1, 2):
            t0 = time.monotonic()
            try:
                res = self.request("tools/call", {"name": name, "arguments": arguments})
                self.log.append(("tools/call", name, time.monotonic() - t0, "ok"))
                return res
            except CallFailed as e:
                self.log.append(("tools/call", name, time.monotonic() - t0, type(e).__name__))
                self.restart()                      # one request at a time: a hung server blocks all
                e.attempts, e.retry_safe = attempt, self.safe_to_retry(name)
                if attempt == 2 or not e.retry_safe:
                    raise
