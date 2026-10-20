"""Pin an MCP server's tool definitions, and refuse a registry whose tools have changed since.

A tool's name, description, input schema and annotations all reach the model, so all of them are
input the server's author controls. A person reads them once, when the server is approved; the
pin keeps that approval tied to exactly what was read. The MCP documents call a change after
approval a rug pull: the server is the same, and its tools now say something else.

  pins = pin(clients)                 # after a person has read the tools: store this
  tools = pinned_registry(clients, pins)   # every later start: Chapter 2's registry, or ValueError

Chapter 2's client restarts a server that dies during a call and may send the call again. The
restarted server is a new start, so pinned_registry makes the client list its tools and check the
pins before anything more is sent. The server is refused from the moment the restart begins until
the check passes; if the restart or the listing fails, or the tools differ, the call fails with
not_permitted and every later call to that server is refused.

A pin says the definitions are the ones approved; it says nothing about what the code behind them
does. That needs the other half of the MCP guidance: run the server with as little as it needs.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ch02"))
from bridge import exposed_name, registry                              # noqa: E402  Chapter 2's
from tools import ToolError                              # noqa: E402  Chapter 1's (bridge put it on the path)

FIELDS = ("name", "title", "description", "inputSchema", "outputSchema", "annotations")


def fingerprint(tool):
    """sha256 of the parts of a tool definition the model or the client acts on."""
    body = json.dumps({k: tool.get(k) for k in FIELDS}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def pin(clients):
    """{server: {tool: fingerprint}} for started clients."""
    out = {}
    for c in clients:
        c.discover()
        out[c.name] = {t["name"]: fingerprint(t) for t in c.list_tools()}
    return out


def changes(client, pins):
    """What differs from the pins for one client whose tools have been listed: a list of strings."""
    want, have = pins.get(client.name), {n: fingerprint(t) for n, t in client.tools.items()}
    if want is None:
        return [f"server '{client.name}' was never approved"]
    out = [f"{client.name}: new tool '{n}'" for n in have if n not in want]
    out += [f"{client.name}: tool '{n}' is gone" for n in want if n not in have]
    out += [f"{client.name}: tool '{n}' has changed since it was approved" for n in have
            if n in want and have[n] != want[n]]
    return out


def pinned_registry(clients, pins, prefix=False):
    """Chapter 2's registry, only if every tool of every server is the one approved, with each
    client's restart checking the pins again before the client sends anything more."""
    clients = list(clients)                      # an iterator would be used up by registry()
    tools = registry(clients, prefix)            # lists each server's tools
    problems = [p for c in clients for p in changes(c, pins)]
    if problems:
        raise ValueError("tool definitions differ from the approved ones: " + "; ".join(problems))
    broken = set()
    for c in clients:
        c.restart = recheck(c, c.restart, pins, broken)
    owner = {exposed_name(c.name, t, prefix): c.name for c in clients for t in c.tools}
    return {name: (refusing(fn, owner[name], broken), spec) for name, (fn, spec) in tools.items()}


def recheck(client, restart, pins, broken):
    def again():
        broken.add(client.name)                  # refused until the new start is verified
        client.tools = {}                        # and no annotation of it is trusted meanwhile
        try:
            restart()
            client.discover()
            client.list_tools()
        except Exception as e:
            client.tools = {}
            raise ToolError("not_permitted", f"the server was restarted and its tools could not be checked "
                            f"({type(e).__name__}: {e})", "Do not use this server's tools; tell the user.")
        problems = changes(client, pins)
        if problems:
            client.tools = {}
            raise ToolError("not_permitted", "the server was restarted and its tools are not the approved ones: "
                            + "; ".join(problems), "Do not use this server's tools; tell the user.")
        broken.discard(client.name)              # verified: the same tools as approved
    return again


def refusing(fn, server, broken):
    def call(**args):
        if server in broken:
            raise ToolError("not_permitted", f"the '{server}' server changed after approval",
                            "Do not use this server's tools; tell the user.")
        return fn(**args)
    return call
