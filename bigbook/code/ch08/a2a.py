"""A minimal A2A v1.0 server and client, standard library only, for one machine.

What it implements, from the v1.0.1 specification (tag commit 3303592):
  - the Agent Card at GET /.well-known/agent-card.json (section 8.2), with Cache-Control and ETag (8.6)
  - the JSON-RPC binding (section 9) at POST /a2a: SendMessage (blocking, the default, 3.2.2) and GetTask
  - the A2A-Version header (3.6): 1.0 is served; an empty header means 0.3 and is refused with
    VersionNotSupportedError (-32009)
  - Task, TaskStatus, Message, Part and Artifact in ProtoJSON (camelCase fields, enum names, 5.5)
  - errors: -32700, -32600, -32601, -32602, TaskNotFoundError -32001, UnsupportedOperationError -32004
    for the streaming methods and for messages to a task (every task here is terminal; 3.1.1),
    PushNotificationNotSupportedError -32003 for push (3.3.4)
  - task references (3.4): an unknown taskId is TaskNotFoundError, a contextId that differs from
    the referenced task's is refused, and the request shape is checked before the worker runs

What it leaves out: streaming, push notifications, multi-turn (INPUT_REQUIRED), cancel, list,
authentication and card signing. It binds to 127.0.0.1 only and has no authentication, so it must
not be exposed to a network: on one machine it shows the protocol's shape, not its security.

The server wraps any function text -> work() dict (strategies.work); the client's sender() returns
the same kind of dict, so the orchestrator can use it in place of strategies.local().
"""
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = "1.0"
CARD_PATH = "/.well-known/agent-card.json"
RPC_PATH = "/a2a"
MAX_BODY = 1_000_000
ERRORS = {-32700: "Invalid JSON payload", -32600: "Request payload validation error", -32601: "Method not found",
          -32602: "Invalid parameters", -32603: "Internal error", -32001: "Task not found",
          -32003: "Push notifications are not supported", -32004: "Unsupported operation",
          -32009: "Protocol version not supported"}
STATE = {"completed": "TASK_STATE_COMPLETED", "failed": "TASK_STATE_FAILED"}
CONTENT = {"text", "raw", "url", "data"}                 # a Part's oneof (5.5)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int(time.time() * 1000) % 1000:03d}Z"


def card(url):
    """The worker's Agent Card. Every field the proto marks REQUIRED is present."""
    return {
        "name": "ACME handbook worker",
        "description": "Answers one bounded sub-task about the fictional ACME company handbook and returns a JSON result.",
        "supportedInterfaces": [{"url": url + RPC_PATH, "protocolBinding": "JSONRPC", "protocolVersion": VERSION}],
        "version": "0.1.0",
        "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/json"],
        "skills": [{"id": "handbook-subtask", "name": "Handbook sub-task",
                    "description": "Looks up handbook facts, computes with a calculator, and returns "
                                   '{"status", "result", "note"} as a data part.',
                    "tags": ["handbook", "lookup", "calculation"],
                    "examples": ["Objective: find the meals per-diem for trip TR0133 ..."]}],
    }


class RpcError(Exception):
    def __init__(self, code, detail=""):
        super().__init__(detail or ERRORS[code])
        self.code, self.detail = code, detail


def task_of(tid, ctx, r):
    """A Task in ProtoJSON from a work() dict: the result as a data artifact, the reason as a message."""
    status = {"state": STATE[r["state"]], "timestamp": now()}
    if r["state"] != "completed":
        status["message"] = {"messageId": str(uuid.uuid4()), "role": "ROLE_AGENT", "contextId": ctx, "taskId": tid,
                             "parts": [{"text": r["why"] or "failed"}]}
    t = {"id": tid, "contextId": ctx, "status": status,
         "metadata": {"steps": r["steps"], "tokens": r["tokens"]}}
    if r["result"] is not None:
        t["artifacts"] = [{"artifactId": str(uuid.uuid4()), "name": "result",
                           "parts": [{"data": r["result"], "mediaType": "application/json"}]}]
    return t


class Server:
    """Serve one worker function on 127.0.0.1. port=0 picks a free port. One request at a time:
    the model runs one call at a time on this machine anyway."""

    def __init__(self, worker, port=0):
        self.worker, self.tasks, self.traces, self.log = worker, {}, {}, []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):              # keep the console for the experiment
                pass

            def send(self, code, body, headers=()):
                data = json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in headers:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path != CARD_PATH:
                    return self.send(404, {"error": "not found"})
                body = card(outer.url)
                etag = '"' + hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16] + '"'
                fresh = self.headers.get("If-None-Match") != etag
                outer.log.append({"method": "GET agent card", "error": None, "bytes_in": 0,
                                  "bytes_out": len(json.dumps(body)) if fresh else 0})
                if not fresh:
                    self.send_response(304)
                    self.send_header("ETag", etag)
                    return self.end_headers()
                self.send(200, body, [("Cache-Control", "max-age=300"), ("ETag", etag)])

            def do_POST(self):
                if self.path != RPC_PATH:
                    return self.send(404, {"error": "not found"})
                n = int(self.headers.get("Content-Length") or 0)
                rid = req = None
                try:
                    if n > MAX_BODY:
                        raise RpcError(-32600, f"body over {MAX_BODY} bytes")
                    try:
                        req = json.loads(self.rfile.read(n))
                    except ValueError:
                        raise RpcError(-32700)
                    if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
                        raise RpcError(-32600)
                    rid = req.get("id")
                    version = (self.headers.get("A2A-Version") or "").strip() or "0.3"
                    if version != VERSION:
                        raise RpcError(-32009, f"version {version} is not supported; this agent serves {VERSION}")
                    result = outer.handle(req["method"], req.get("params"))
                    body = {"jsonrpc": "2.0", "id": rid, "result": result}
                except RpcError as e:
                    body = {"jsonrpc": "2.0", "id": rid, "error": {"code": e.code, "message": ERRORS[e.code],
                            "data": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                      "reason": str(e), "domain": "a2a"}]}}
                except Exception as e:                 # a bug or a model failure inside the worker
                    body = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32603, "message": ERRORS[-32603],
                            "data": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                      "reason": f"{type(e).__name__}: {e}", "domain": "a2a"}]}}
                outer.log.append({"method": req.get("method") if isinstance(req, dict) else None,
                                  "error": body.get("error", {}).get("code"), "bytes_in": n,
                                  "bytes_out": len(json.dumps(body))})
                self.send(200, body)

        self.httpd = HTTPServer(("127.0.0.1", port), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = None

    def handle(self, method, params):
        if method == "SendMessage":
            msg = params.get("message") if isinstance(params, dict) else None
            if not isinstance(msg, dict) or msg.get("role") != "ROLE_USER" or not isinstance(msg.get("messageId"), str):
                raise RpcError(-32602, "params.message needs a messageId and role ROLE_USER")
            for k in ("contextId", "taskId"):
                if k in msg and not isinstance(msg[k], str):
                    raise RpcError(-32602, f"params.message.{k} must be a string")
            parts = msg.get("parts")
            if (not isinstance(parts, list) or not parts
                    or not all(isinstance(p, dict) and isinstance(p.get("text"), str) and not set(p) & (CONTENT - {"text"})
                               for p in parts)):
                raise RpcError(-32602, "params.message.parts must hold at least one part, each a text part only")
            config = params.get("configuration")
            if config is not None and not isinstance(config, dict):
                raise RpcError(-32602, "params.configuration must be an object")
            if (config or {}).get("returnImmediately"):
                raise RpcError(-32004, "this agent answers blocking requests only")
            if "taskId" in msg:                          # a message to an existing task (3.4)
                old = self.tasks.get(msg["taskId"])
                if old is None:
                    raise RpcError(-32001, f"no task {msg['taskId']!r}")
                if "contextId" in msg and msg["contextId"] != old["contextId"]:
                    raise RpcError(-32602, "params.message.contextId differs from the task's")
                raise RpcError(-32004, f"task {msg['taskId']!r} is {old['status']['state']}, a terminal state, "
                                       "and takes no more messages")
            texts = [p["text"] for p in parts]
            tid, ctx = str(uuid.uuid4()), msg.get("contextId") or str(uuid.uuid4())
            r = self.worker("\n".join(texts))
            self.traces[tid] = r.get("trace", [])
            self.tasks[tid] = task_of(tid, ctx, r)
            return {"task": self.tasks[tid]}
        if method == "GetTask":
            tid = params.get("id") if isinstance(params, dict) else None
            if not isinstance(tid, str):
                raise RpcError(-32602, "params.id must be a string")
            if tid not in self.tasks:
                raise RpcError(-32001, f"no task {tid!r}")
            return self.tasks[tid]
        if method in ("SendStreamingMessage", "SubscribeToTask", "GetExtendedAgentCard"):
            raise RpcError(-32004, f"{method} is not supported (see the Agent Card's capabilities)")
        if "PushNotificationConfig" in method:
            raise RpcError(-32003)
        raise RpcError(-32601, f"no method {method!r}")

    def start(self):
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class Client:
    """Find an agent by its card, then send it messages over the JSON-RPC binding."""

    def __init__(self, base, timeout=900):
        self.base, self.timeout, self.n = base.rstrip("/"), timeout, 0
        with urllib.request.urlopen(self.base + CARD_PATH, timeout=30) as r:
            self.card = json.load(r)
        iface = [i for i in self.card.get("supportedInterfaces", [])
                 if i.get("protocolBinding") == "JSONRPC" and i.get("protocolVersion") == VERSION]
        if not iface:
            raise ValueError(f"the agent offers no JSON-RPC interface at A2A {VERSION}")
        self.url = iface[0]["url"]                      # the first supported one (8.3.2)

    def rpc(self, method, params, version=VERSION):
        self.n += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}).encode()
        headers = {"Content-Type": "application/json"}
        if version is not None:
            headers["A2A-Version"] = version
        req = urllib.request.Request(self.url, body, headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.load(r)

    def send_text(self, text):
        """SendMessage with one text part; the Task, or raises RpcError with the server's code."""
        out = self.rpc("SendMessage", {"message": {"messageId": str(uuid.uuid4()), "role": "ROLE_USER",
                                                   "parts": [{"text": text}]}})
        if "error" in out:
            raise RpcError(out["error"]["code"], out["error"].get("data", [{}])[0].get("reason", ""))
        return out["result"]["task"]

    def sender(self, traces=None):
        """A function text -> work()-style dict, for strategies.orchestrator(send=...). The worker's
        trace stays with the server (A2A's opaque execution); pass the server's `traces` dict to
        keep it for labelling on one machine."""
        def send(text):
            t = self.send_text(text)
            data = [p["data"] for a in t.get("artifacts", []) for p in a["parts"] if "data" in p]
            why = None
            if t["status"]["state"] != "TASK_STATE_COMPLETED":
                why = " ".join(p.get("text", "") for p in t["status"].get("message", {}).get("parts", []))
            meta = t.get("metadata", {})
            return {"state": "completed" if t["status"]["state"] == "TASK_STATE_COMPLETED" else "failed",
                    "result": data[0] if data else None, "why": why, "steps": meta.get("steps"),
                    "tokens": meta.get("tokens"), "trace": (traces or {}).get(t["id"], []), "task": t["id"]}
        return send
