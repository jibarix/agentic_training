"""A minimal MCP server: protocol 2026-07-28, tools only, stdio transport, standard library only.

`Server.handle` turns one parsed JSON-RPC message into one response (or None for a
notification) and does no I/O, so the tests can drive it directly. `Server.serve` is the
stdio loop: one message per line in, one per line out, logs to stderr, exit on end of input."""
import json
import sys

VERSION = "2026-07-28"
SUPPORTED = [VERSION]
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = -32700, -32600, -32601, -32602
INTERNAL_ERROR = -32603
UNSUPPORTED_VERSION = -32022
META = "io.modelcontextprotocol/"


class ToolFailure(Exception):
    """A tool execution error: goes back to the model as a result with isError: true."""

    def __init__(self, kind, message, hint=""):
        super().__init__(message)
        self.kind, self.hint = kind, hint


class RpcError(Exception):
    """A protocol error: goes back as a JSON-RPC error response."""

    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code, self.data = code, data


class Server:
    def __init__(self, name, version, tools, instructions="", page_size=50, log=sys.stderr):
        """tools: list of (fn, Tool dict). The Tool dict is sent as is in tools/list."""
        self.info = {"name": name, "version": version}
        self.tools = {t["name"]: (fn, t) for fn, t in tools}
        self.instructions, self.page_size, self.log = instructions, page_size, log

    # -- one message in, one response (or None) out ------------------------------
    def handle(self, msg):
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            rid = msg.get("id") if isinstance(msg, dict) else None
            return self.reply(rid if _valid_id(rid) else None, error=(INVALID_REQUEST, "not a JSON-RPC 2.0 request"))
        if "id" not in msg:                        # a notification: never answered
            self.log_line(f"notification {msg['method']}")
            return None
        rid = msg["id"]
        if not _valid_id(rid):
            return self.reply(None, error=(INVALID_REQUEST, "id must be a string or an integer"))
        try:
            params = msg.get("params")
            self.check_meta(params)
            method = {"server/discover": self.discover, "tools/list": self.list_tools,
                      "tools/call": self.call_tool}.get(msg["method"])
            if method is None:
                raise RpcError(METHOD_NOT_FOUND, f"Method not found: {msg['method']}")
            return self.reply(rid, result=method(params))
        except RpcError as e:
            return self.reply(rid, error=(e.code, str(e), e.data))
        except Exception as e:                     # a bug in the server: answer, and stay up
            self.log_line(f"internal error on {msg['method']}: {type(e).__name__}: {e}")
            return self.reply(rid, error=(INTERNAL_ERROR, "Internal error"))

    def check_meta(self, params):
        meta = params.get("_meta") if isinstance(params, dict) else None
        if not isinstance(meta, dict):
            raise RpcError(INVALID_PARAMS, "params._meta is required")
        version = meta.get(META + "protocolVersion")
        if not isinstance(version, str) or not isinstance(meta.get(META + "clientCapabilities"), dict):
            raise RpcError(INVALID_PARAMS, "_meta needs protocolVersion and clientCapabilities")
        if version not in SUPPORTED:
            raise RpcError(UNSUPPORTED_VERSION, f"Unsupported protocol version: {version}",
                           {"supported": SUPPORTED, "requested": version})

    def reply(self, rid, result=None, error=None):
        out = {"jsonrpc": "2.0"}
        if rid is not None:
            out["id"] = rid
        if error:
            out["error"] = {"code": error[0], "message": error[1]}
            if len(error) > 2 and error[2] is not None:
                out["error"]["data"] = error[2]
        else:
            out["result"] = {"resultType": "complete", **result,
                             "_meta": {META + "serverInfo": self.info}}
        return out

    # -- the three methods ----------------------------------------------------------
    def discover(self, params):
        out = {"supportedVersions": SUPPORTED, "capabilities": {"tools": {}},
               "ttlMs": 3_600_000, "cacheScope": "public"}
        return {**out, "instructions": self.instructions} if self.instructions else out

    def list_tools(self, params):
        cursor = params.get("cursor", "0")         # opaque to the client; here, an offset
        ok = isinstance(cursor, str) and cursor.isascii() and cursor.isdigit()   # "²" is a digit too
        start = int(cursor) if ok else -1
        if not 0 <= start <= len(self.tools):
            raise RpcError(INVALID_PARAMS, "invalid cursor")
        names = list(self.tools)[start:start + self.page_size]   # always the same order
        out = {"tools": [self.tools[n][1] for n in names], "ttlMs": 3_600_000, "cacheScope": "public"}
        if start + self.page_size < len(self.tools):
            out["nextCursor"] = str(start + self.page_size)
        return out

    def call_tool(self, params):
        name, args = params.get("name"), params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(args, dict):
            raise RpcError(INVALID_PARAMS, "tools/call needs a string name and an object of arguments")
        if name not in self.tools:
            raise RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        fn, tool = self.tools[name]
        self.log_line(f"call {name} {json.dumps(args)}")
        try:
            check_args(tool, args)                 # servers MUST validate inputs
            out = fn(**args)
        except ToolFailure as e:
            return failure(e.kind, str(e), e.hint)
        except Exception as e:                     # a bug in the tool is still the tool's result
            return failure("tool_failed", f"{type(e).__name__}: {e}", "Try a different call or tool.")
        return {"content": [{"type": "text", "text": out if isinstance(out, str) else json.dumps(out)}],
                "isError": False}

    # -- stdio -----------------------------------------------------------------------
    def serve(self, stdin=None, stdout=None):
        stdin, stdout = stdin or sys.stdin.buffer, stdout or sys.stdout.buffer
        self.log_line(f"{self.info['name']} ready, {len(self.tools)} tools")
        for raw in stdin:                          # ends when the client closes our stdin
            if not raw.strip():
                continue
            try:
                msg = json.loads(raw)
            except (ValueError, RecursionError):
                out = self.reply(None, error=(PARSE_ERROR, "Parse error"))
            else:
                out = self.handle(msg)
            if out is not None:                    # json.dumps never emits a raw newline
                stdout.write(json.dumps(out, ensure_ascii=False).encode("utf-8") + b"\n")
                stdout.flush()
        self.log_line("stdin closed, exiting")

    def log_line(self, text):
        print(f"[{self.info['name']}] {text}", file=self.log, flush=True)


def failure(kind, message, hint=""):
    """A tool execution error. The text block carries the same JSON as structuredContent."""
    data = {"error": {"kind": kind, "message": message, "hint": hint}}
    return {"content": [{"type": "text", "text": json.dumps(data)}], "structuredContent": data,
            "isError": True}


def check_args(tool, args):
    """The subset of JSON Schema our tools use: an object of required string properties."""
    schema = tool["inputSchema"]
    props, required = schema.get("properties", {}), schema.get("required", [])
    missing = [k for k in required if k not in args]
    extra = [k for k in args if k not in props]
    if missing or extra:
        raise ToolFailure("bad_arguments", f"missing {missing}, unexpected {extra}",
                          f"'{tool['name']}' takes exactly: " + ", ".join(props))
    wrong = [k for k, v in args.items() if props[k].get("type") == "string" and not isinstance(v, str)]
    if wrong:
        raise ToolFailure("bad_arguments", f"{wrong} must be text",
                          f"Pass each argument of '{tool['name']}' as a string.")


def _valid_id(rid):
    return isinstance(rid, str) or (isinstance(rid, int) and not isinstance(rid, bool))
