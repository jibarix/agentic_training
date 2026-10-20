"""Chapter 1's three tools behind an MCP server on stdio.

  python handbook_server.py                         the current handbook (../ch01/handbook)
  python handbook_server.py --name archive --dir archive --label "ARCHIVE (2024 edition, superseded)"

Fault switches, for the tests and the chapter's demonstrations:
  --crash-on-call N   exit without replying when the N-th tools/call arrives
  --slow NAME=S       sleep S seconds before running tool NAME
  --noise             print a line that is not JSON to stdout (a common server bug)
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ch01"))
import tools as ch01                                   # noqa: E402
from mcp_server import Server, ToolFailure             # noqa: E402

READ_ONLY = {"readOnlyHint": True, "openWorldHint": False}


def wrap(fn):
    """Chapter 1's ToolError becomes the server's tool execution error, kind and hint kept."""
    def call(**args):
        try:
            return fn(**args)
        except ch01.ToolError as e:
            raise ToolFailure(e.kind, str(e), e.hint)
    return call


def handbook_tools(label=""):
    """(fn, Tool) pairs from Chapter 1's registry; the JSON schema is passed on unchanged."""
    out = []
    for name, (fn, spec) in ch01.TOOLS.items():
        f = spec["function"]
        desc = f"{label}: {f['description']}" if label and name != "calculator" else f["description"]
        out.append((wrap(fn), {"name": name, "description": desc, "inputSchema": f["parameters"],
                               "annotations": READ_ONLY}))
    return out


class FaultyServer(Server):
    def __init__(self, *a, crash_on_call=0, slow=None, **kw):
        super().__init__(*a, **kw)
        self.crash_on_call, self.slow, self.calls = crash_on_call, slow or {}, 0

    def call_tool(self, params):
        """The faults act only on a request that got this far: handle has checked it and its _meta."""
        self.calls += 1
        if self.calls == self.crash_on_call:
            self.log_line("crashing on purpose")
            os._exit(3)
        name = params.get("name")
        if isinstance(name, str) and name in self.slow:
            time.sleep(self.slow[name])
        return super().call_tool(params)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--name", default="handbook")
    ap.add_argument("--dir", default=str(ch01.HANDBOOK))
    ap.add_argument("--label", default="")
    ap.add_argument("--crash-on-call", type=int, default=0)
    ap.add_argument("--slow", action="append", default=[])
    ap.add_argument("--noise", action="store_true")
    a = ap.parse_args()
    ch01.HANDBOOK = Path(a.dir).resolve()               # each server process serves one folder
    slow = {k: float(v) for k, v in (s.split("=") for s in a.slow)}
    if a.noise:
        sys.stdout.buffer.write(b"Loading handbook index... done\n")
        sys.stdout.buffer.flush()
    note = f"{a.label}. " if a.label else ""
    FaultyServer(a.name, "2.0", handbook_tools(a.label), crash_on_call=a.crash_on_call, slow=slow,
                 instructions=note + "Read-only tools over the ACME handbook in " + ch01.HANDBOOK.name + "/."
                 ).serve()


if __name__ == "__main__":
    main()
