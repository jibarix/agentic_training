"""A bounded tool-using agent: one loop, explicit budgets, tool failures become observations."""
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
    detail: str = ""            # why a run that did not answer stopped
    trace: list = field(default_factory=list)


def tidy(call, fallback_id):
    """Any tool call, however malformed, as a well-formed one: string name, string arguments, id."""
    call = call if isinstance(call, dict) else {}
    fn = call.get("function") if isinstance(call.get("function"), dict) else {}
    name, args, cid = fn.get("name"), fn.get("arguments"), call.get("id")
    return {"id": cid if isinstance(cid, str) and cid else fallback_id, "type": "function",
            "function": {"name": name if isinstance(name, str) else "",
                         "arguments": args if isinstance(args, str) else json.dumps(args or {})}}


class Agent:
    def __init__(self, client, tools=TOOLS, system=SYSTEM, max_steps=8, max_tokens=20_000,
                 max_obs_chars=2_000, hints=True):
        self.client, self.tools, self.system = client, tools, system
        self.max_steps, self.max_tokens, self.max_obs_chars = max_steps, max_tokens, max_obs_chars
        self.hints = hints      # False = bare error messages, without the hint

    # -- one tool call -> one observation string; never raises ----------------
    def dispatch(self, call):
        call = tidy(call, "")
        name, raw = call["function"]["name"], call["function"]["arguments"]
        if name not in self.tools:
            return self.error("unknown_tool", f"no tool named '{name}'",
                              "Available tools: " + ", ".join(self.tools))
        fn, spec = self.tools[name]
        params = spec["function"]["parameters"]
        try:
            args = json.loads(raw)
        except (ValueError, RecursionError) as e:   # bad JSON, a 5,000-digit number, deep nesting
            why = e.msg if isinstance(e, json.JSONDecodeError) else type(e).__name__
            return self.error("bad_arguments", f"arguments are not valid JSON ({why})",
                              "Send a JSON object, e.g. "
                              + json.dumps({k: "..." for k in params["required"]}))
        if not isinstance(args, dict):
            return self.error("bad_arguments", "arguments must be a JSON object", "")
        missing = [k for k in params["required"] if k not in args]
        extra = [k for k in args if k not in params["properties"]]
        if missing or extra:
            return self.error("bad_arguments", f"missing {missing}, unexpected {extra}",
                              f"'{name}' takes exactly: " + ", ".join(params["properties"]))
        wrong = [k for k, v in args.items()
                 if isinstance(v, bool) or not isinstance(v, (str, int, float))]
        if wrong:
            return self.error("bad_arguments", f"{wrong} must be text",
                              f"Pass each argument of '{name}' as a string.")
        args = {k: v if isinstance(v, str) else str(v) for k, v in args.items()}  # 7 -> "7"
        try:
            out = fn(**args)
            out = out if isinstance(out, str) else json.dumps(out, default=str)
        except ToolError as e:
            return self.error(e.kind, str(e), e.hint)
        except Exception as e:  # a bug in the tool, or output that is not text, must not kill the run
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
        res = Result(status="step_limit", detail=f"{self.max_steps} model calls")
        for step in range(1, self.max_steps + 1):
            if res.tokens >= self.max_tokens:    # a threshold between calls, not a hard cap
                res.status, res.detail = "token_limit", f"{res.tokens} >= {self.max_tokens}"
                break
            t0 = time.time()
            try:
                msg, usage = self.client.chat(messages, specs)
                if not isinstance(msg, dict):
                    raise TypeError("the reply is not a message")
            except Exception as e:               # the failed attempt is traced, then the run stops
                res.status, res.detail = "model_error", f"{type(e).__name__}: {e}"
                res.trace.append({"step": step, "type": "model", "error": res.detail,
                                  "seconds": round(time.time() - t0, 2)})
                break
            res.steps = step
            used = (usage or {}).get("total_tokens")
            estimated = not isinstance(used, int)
            if estimated:                        # rough: 4 characters per token, all text sent
                used = len(json.dumps([messages, specs, msg])) // 4
            res.tokens += used
            raw = msg.get("tool_calls") or []
            calls, ids = [], set()
            for i, c in enumerate(raw if isinstance(raw, list) else [raw]):
                c = tidy(c, f"call_{step}_{i}")
                while c["id"] in ids:            # ids must be unique within the turn
                    c["id"] += f"_{i}"
                ids.add(c["id"])
                calls.append(c)
            text = msg.get("content") if isinstance(msg.get("content"), str) else ""
            turn = {"role": "assistant", "content": text}
            if calls:
                turn["tool_calls"] = calls
            messages.append(turn)
            res.trace.append({"step": step, "type": "model", "content": text,
                              "calls": [{"id": c["id"], "name": c["function"]["name"],
                                         "arguments": c["function"]["arguments"]} for c in calls],
                              "tokens": used, "estimated": estimated, "total": res.tokens,
                              "seconds": round(time.time() - t0, 2)})
            if not calls:                        # no tool call = the model's final answer
                if text.strip():
                    res.status, res.answer, res.detail = "answered", text, ""
                else:
                    res.status, res.detail = "model_error", "empty reply"
                break
            for c in calls:                      # one observation per call, linked by id
                obs = self.dispatch(c)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": obs})
                res.trace.append({"step": step, "type": "tool", "id": c["id"],
                                  "name": c["function"]["name"], "observation": obs})
        res.trace.append({"type": "end", "status": res.status, "detail": res.detail,
                          "steps": res.steps, "tokens": res.tokens})
        return res
