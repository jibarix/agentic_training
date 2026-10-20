"""A chat client for Ollama's native /api/chat, which says how much of each prompt came from its cache.

Chapter 1's ChatClient speaks the OpenAI-compatible /v1 endpoint, whose usage block gives the prompt
and completion tokens but not the cached ones. /api/chat's reply also gives prompt_eval_cached_count
(prompt tokens read from the cache), prompt_eval_duration (the time spent on the others) and
eval_duration, all in nanoseconds. NativeClient takes and returns messages in the /v1 shape, so
Chapter 1's agent runs on it unchanged, and keeps each call's counts in `log`.

The window is set on every request (options.num_ctx), so the server can't fall back to a smaller
one. Ollama's documentation doesn't say whether it leaves out a cached count of zero; a missing
count or duration is recorded as None, not as 0, and the pilot shows which it is. The tool result's tool_name
field is from Ollama's tool-calling guide, not its API reference; the pilot checks that tool
results reach the model. Tested only by the unit tests: the night run will be the first real use.
"""
import json
import time
import urllib.request


def to_native(messages):
    """/v1 messages -> /api/chat messages: tool-call arguments as objects, tool results named."""
    out, names = [], {}
    for m in messages:
        m = dict(m)
        if m.get("tool_calls"):
            calls = []
            for c in m["tool_calls"]:
                f = c["function"]
                names[c.get("id")] = f["name"]
                try:
                    args = json.loads(f["arguments"]) if isinstance(f["arguments"], str) else f["arguments"]
                except ValueError:
                    args = {}
                calls.append({"function": {"name": f["name"], "arguments": args if isinstance(args, dict) else {}}})
            m["tool_calls"] = calls
        if m.get("role") == "tool":
            m = {"role": "tool", "content": m.get("content", ""), "tool_name": names.get(m.get("tool_call_id"), "")}
        out.append(m)
    return out


def from_native(msg):
    """/api/chat's message -> the /v1 shape Chapter 1's agent reads (arguments as a JSON string)."""
    out = {"role": "assistant", "content": msg.get("content") or ""}
    calls = []
    for i, c in enumerate(msg.get("tool_calls") or []):
        f = c.get("function") or {}
        args = f.get("arguments")
        calls.append({"id": c.get("id") or f"call_{i}", "type": "function",
                      "function": {"name": f.get("name") or "",
                                   "arguments": args if isinstance(args, str) else json.dumps(args or {})}})
    if calls:
        out["tool_calls"] = calls
    return out


def usage(data):
    """The reply's counts: the /v1 usage block, and the record kept in NativeClient.log. What the
    server didn't report is None: unknown, never zero."""
    p, c = data.get("prompt_eval_count"), data.get("eval_count")
    secs = {k: v / 1e9 if isinstance(v := data.get(k), (int, float)) else None
            for k in ("prompt_eval_duration", "eval_duration")}
    v1 = {}
    if isinstance(p, int) and isinstance(c, int):
        v1 = {"prompt_tokens": p, "completion_tokens": c, "total_tokens": p + c}
    rec = {"prompt": p, "cached": data.get("prompt_eval_cached_count"), "completion": c,
           "prompt_seconds": secs["prompt_eval_duration"], "eval_seconds": secs["eval_duration"],
           "thinking_chars": len((data.get("message") or {}).get("thinking") or "")}
    return v1, rec


class NativeClient:
    """POST {root}/api/chat with tools, thinking off, the window and the sampling options."""

    def __init__(self, model, root="http://localhost:11434", temperature=0.7, seed=None, num_ctx=32_768,
                 timeout=300, opener=urllib.request.urlopen):
        self.model, self.root, self.timeout, self.opener = model, root.rstrip("/"), timeout, opener
        self.options = {"temperature": temperature, "num_ctx": num_ctx} | ({"seed": seed} if seed is not None else {})
        self.log = []

    def body(self, messages, tools=None):
        b = {"model": self.model, "messages": to_native(messages), "stream": False, "think": False,
             "options": self.options}
        if tools:
            b["tools"] = tools
        return b

    def chat(self, messages, tools=None):
        req = urllib.request.Request(self.root + "/api/chat", data=json.dumps(self.body(messages, tools)).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        with self.opener(req, timeout=self.timeout) as r:
            data = json.load(r)
        v1, rec = usage(data)
        self.log.append(rec | {"seconds": round(time.time() - t0, 3)})
        return from_native(data.get("message") or {}), v1
