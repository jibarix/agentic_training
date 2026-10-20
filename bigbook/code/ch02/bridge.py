"""MCP tools as a Chapter 1 registry {name: (function, spec)}, so the agent loop is unchanged.

Every failure on the far side of the process boundary comes back as Chapter 1's ToolError,
which the dispatcher already turns into an observation the model can act on."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "ch01"))
from tools import ToolError                              # noqa: E402
from mcp_client import CallFailed, McpError, McpTimeout   # noqa: E402


def exposed_name(server, tool, prefix):
    """The name the model sees. Model APIs allow [A-Za-z0-9_-], up to 64 characters."""
    name = f"{server}__{tool}" if prefix else tool
    name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    if len(name) > 64:
        raise ValueError(f"tool name too long for the model API: {name}")
    return name


def registry(clients, prefix=False):
    """One registry from several started clients. Without a prefix, a duplicate name is an error:
    silently letting one server's tool shadow another's is how calls go to the wrong place."""
    out = {}
    for client in clients:
        client.discover()
        for tool in client.list_tools():
            name = exposed_name(client.name, tool["name"], prefix)
            if name in out:
                raise ValueError(f"two servers offer '{name}'; use prefix=True")
            spec = {"type": "function", "function": {
                "name": name, "description": tool.get("description", ""),
                "parameters": tool["inputSchema"]}}
            out[name] = (remote(client, tool["name"]), spec)
    return out


def remote(client, tool):
    def call(**args):
        try:
            res = client.call_tool(tool, args)
        except McpTimeout as e:
            raise ToolError("timeout", f"'{tool}' did not answer within {client.timeout:g} s", next_step(e))
        except CallFailed as e:                     # the server exited during the call
            raise ToolError("server_unavailable", f"the '{client.name}' server stopped during '{tool}'",
                            next_step(e))
        except McpError as e:                       # unknown tool, bad request: a protocol error
            raise ToolError("server_error", str(e), "The tool list may be out of date.")
        return result_text(res)
    return call


def next_step(e):
    """The hint says what the client already did, so the model doesn't repeat it blindly."""
    if e.retry_safe:
        return f"The server was restarted and the call was tried {e.attempts} times. Use another tool."
    return ("The server was restarted. The call was not repeated: this tool is not known to be safe to "
            "repeat, and it may or may not have taken effect. Check that before calling it again.")


def result_text(res):
    if res.get("resultType", "complete") != "complete":
        raise ToolError("unsupported", f"the server asked for more input ({res.get('resultType')})",
                        "This client cannot provide it.")
    texts = [b.get("text", "") if b.get("type") == "text" else f"[{b.get('type')} content omitted]"
             for b in res.get("content", []) if isinstance(b, dict)]
    if res.get("isError"):
        data = res.get("structuredContent")        # any JSON value; only an object can hold our envelope
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict) and isinstance(err.get("kind"), str):
            raise ToolError(err["kind"], err.get("message", ""), err.get("hint", ""))
        raise ToolError("tool_error", " ".join(texts) or "the tool reported an error", "")
    return "\n".join(texts)
