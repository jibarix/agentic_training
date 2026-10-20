"""A bounded tool-using agent: one loop, explicit budgets, every failure becomes an observation."""
import json
import time
from dataclasses import dataclass, field

from tools import TOOLS, ToolError

SYSTEM = """You answer questions about the ACME company handbook.
Find facts with the tools; never guess a number. Do every calculation with the calculator.
When you have the answer, reply in plain text with the final number and its unit."""


@dataclass
class Result:
    status: str                 # "answered" | "step_limit" | "token_limit" | "model_error"
    answer: str = ""
    steps: int = 0
    tokens: int = 0
    trace: list = field(default_factory=list)


class Agent:
    def __init__(self, client, tools=TOOLS, system=SYSTEM, max_steps=8, max_tokens=20_000,
                 max_obs_chars=2_000, hints=True):
        self.client, self.tools, self.system = client, tools, system
        self.max_steps, self.max_tokens, self.max_obs_chars = max_steps, max_tokens, max_obs_chars
        self.hints = hints      # False = bare error messages (the baseline in the experiment)

    # -- one tool call -> one observation string; never raises ----------------
    def dispatch(self, call):
        name, raw = call["function"]["name"], call["function"].get("arguments") or "{}"
        if name not in self.tools:
            return self.error("unknown_tool", f"no tool named '{name}'",
                              "Available tools: " + ", ".join(self.tools))
        fn, spec = self.tools[name]
        params = spec["function"]["parameters"]
        try:
            args = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError as e:
            return self.error("bad_arguments", f"arguments are not valid JSON ({e.msg})",
                              "Send a JSON object, e.g. "
                              + json.dumps({k: "..." for k in params["required"]}))
        if not isinstance(args, dict):
            return self.error("bad_arguments", "arguments must be a JSON object", "")
        missing = [k for k in params["required"] if k not in args]
        extra = [k for k in args if k not in params["properties"]]
        if missing or extra:
            return self.error("bad_arguments", f"missing {missing}, unexpected {extra}",
                              f"'{name}' takes exactly: " + ", ".join(params["properties"]))
        args = {k: v if isinstance(v, str) else json.dumps(v) for k, v in args.items()}
        try:
            out = fn(**args)
        except ToolError as e:
            return self.error(e.kind, str(e), e.hint)
        except Exception as e:  # a bug in the tool must not kill the run
            return self.error("tool_failed", f"{type(e).__name__}: {e}",
                              "Try a different call or tool.")
        return self.truncate(out)

    def error(self, kind, message, hint):
        text = f"ERROR {kind}: {message}."
        return f"{text} {hint}".strip() if self.hints else f"Error: {message}"

    def truncate(self, text):
        n = self.max_obs_chars
        if len(text) <= n:
            return text
        half = (n - 60) // 2
        return f"{text[:half]}\n[... {len(text) - 2 * half} characters omitted ...]\n{text[-half:]}"

    # -- the loop ---------------------------------------------------------------
    def run(self, task):
        messages = [{"role": "system", "content": self.system}, {"role": "user", "content": task}]
        specs = [spec for _, spec in self.tools.values()]
        res = Result(status="step_limit")
        for step in range(1, self.max_steps + 1):
            if res.tokens >= self.max_tokens:
                res.status = "token_limit"
                break
            t0 = time.time()
            try:
                msg, usage = self.client.chat(messages, specs)
            except Exception as e:
                res.status, res.answer = "model_error", f"{type(e).__name__}: {e}"
                break
            res.steps = step
            res.tokens += usage.get("total_tokens") or len(json.dumps(messages)) // 4
            calls = msg.get("tool_calls") or []
            for i, c in enumerate(calls):       # some servers omit ids; the link must exist
                c["id"] = c.get("id") or f"call_{step}_{i}"
            turn = {"role": "assistant", "content": msg.get("content") or ""}
            if calls:
                turn["tool_calls"] = calls
            messages.append(turn)
            res.trace.append({"step": step, "type": "model", "content": msg.get("content") or "",
                              "calls": [(c["function"]["name"], c["function"].get("arguments"))
                                        for c in calls],
                              "tokens": res.tokens, "seconds": round(time.time() - t0, 2)})
            if not calls:                       # no tool call = the model's final answer
                res.status, res.answer = "answered", msg.get("content") or ""
                break
            for c in calls:                     # one observation per call, linked by id
                obs = self.dispatch(c)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": obs})
                res.trace.append({"step": step, "type": "tool", "id": c["id"],
                                  "name": c["function"]["name"], "observation": obs})
        return res
