"""Chat clients: one for an OpenAI-style /chat/completions endpoint, and a scripted fake for tests.

ChatClient was tested only against Ollama 0.40.1. Servers differ in how they handle tool calls
and extra options such as reasoning_effort, so check yours with a one-question smoke run."""
import json
import urllib.request


class ChatClient:
    """POST {base_url}/chat/completions with tools. Standard library only."""

    def __init__(self, model, base_url="http://localhost:11434/v1", api_key="none",
                 temperature=0.0, seed=None, extra=None, timeout=300):
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key
        self.temperature, self.seed, self.timeout = temperature, seed, timeout
        self.extra = extra or {}          # e.g. {"reasoning_effort": "none"} for Ollama

    def chat(self, messages, tools=None):
        body = {"model": self.model, "messages": messages, "temperature": self.temperature, **self.extra}
        if self.seed is not None:
            body["seed"] = self.seed
        if tools:
            body["tools"] = tools
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.load(r)
        return data["choices"][0]["message"], data.get("usage", {})


class ScriptedClient:
    """Replays a fixed list of assistant messages. Lets the tests run with no model."""

    def __init__(self, replies, tokens_per_call=100):
        self.replies, self.tokens_per_call, self.seen = list(replies), tokens_per_call, []

    def chat(self, messages, tools=None):
        self.seen.append(json.loads(json.dumps(messages)))
        done = {"role": "assistant", "content": "(script exhausted)"}
        reply = self.replies.pop(0) if self.replies else done
        return reply, {"total_tokens": self.tokens_per_call}


def call(name, arguments, id):
    """Build an assistant tool call the way the API returns it (arguments as a JSON string)."""
    args = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return {"id": id, "type": "function", "function": {"name": name, "arguments": args}}
