"""Three ways to answer the same task: one agent, an orchestrator with workers, and a fixed pipeline.

  single       : Chapter 1's agent with all the tools and the whole task (as Chapter 5's agent)
  orchestrator : a lead agent that can't read the handbook; its tools are the calculator and
                 delegate, which hands a sub-task contract to a worker that starts fresh, sees only the contract, and
                 returns a JSON object. The lead decides what to delegate, in what order, and how
                 to combine the results (the plan is held by the model)
  pipeline     : code fixes the shape: a splitter agent lists independent sub-questions whose
                 amounts add up to the answer, a fresh worker answers each, and code adds them
                 (the plan is held by code; Anthropic's "sectioning")

Each takes the task, a chat client and Chapter 1's tools dict, and returns an Outcome whose
`traces` hold every agent's trace, so a failed run can be read and labelled afterwards.
Workers run one after another: on one local GPU there is no parallel speed-up to gain.
"""
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from agent import SYSTEM, Agent                         # Chapter 1's
from tools import ToolError, spec                       # Chapter 1's

FINAL = "\nEnd with one last line of the form: Final answer: <number> <unit>"   # as in Chapter 1
AGENT_KW = {"max_steps": 30, "max_tokens": 120_000, "max_obs_chars": 2_000, "hints": True}  # Chapters 4 and 5
LEAD_KW = {"max_steps": 16, "max_tokens": 120_000, "max_obs_chars": 2_000, "hints": True}
WORKER_KW = {"max_steps": 12, "max_tokens": 40_000, "max_obs_chars": 2_000, "hints": True}  # Chapter 5's step
SPLIT_KW = {"max_steps": 16, "max_tokens": 60_000, "max_obs_chars": 2_000, "hints": True}
MAX_WORKERS = 8                  # spawning limit per run (Harvard L6 p. 23)
MAX_TOKENS = 250_000             # whole run, lead and workers together, checked before each delegation
_NUM = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?"


@dataclass
class Outcome:
    status: str                  # "answered" | "split_error" | "part_failed" | an Agent status
    answer: str = ""
    detail: str = ""
    info: dict = field(default_factory=dict)
    traces: list = field(default_factory=list)    # [{"role": ..., "trace": [...]}], lead or splitter first


class Meter:
    """Counts calls and tokens across every agent in a run, and records calls that raised.
    A strategy given a Meter uses it as it is, so workers behind A2A count against the same budget.

    Chapter 1's agent turns an exception into a model_error, so a server that went away would look
    like a model that failed. The experiment checks `errors` and stops instead of writing that row."""

    def __init__(self, client):
        self.client, self.calls, self.tokens, self.errors = client, 0, 0, []

    def chat(self, messages, tools=None):
        try:
            msg, usage = self.client.chat(messages, tools)
        except Exception as e:
            self.errors.append(f"{type(e).__name__}: {e}")
            raise
        self.calls += 1
        self.tokens += (usage or {}).get("total_tokens") or 0
        return msg, usage


def metered(client):
    return client if isinstance(client, Meter) else Meter(client)


def json_in(text, kind):
    """The first JSON value of type `kind` (list or dict) in a reply, or None (as in Chapter 5)."""
    a, b = ("[", "]") if kind is list else ("{", "}")
    i, j = text.find(a), text.rfind(b)
    if i < 0 or j <= i:
        return None
    try:
        v = json.loads(text[i:j + 1])
    except ValueError:
        return None
    return v if isinstance(v, kind) else None


def tagged(text, tag, kind):
    """The JSON value after the last '<tag>:' line, or None."""
    m = list(re.finditer(rf"(?im)^[\s*_#>-]*{tag}[\s*_]*:", text or ""))
    return json_in(text[m[-1].end():], kind) if m else None


# ---- single ---------------------------------------------------------------------------------------
def single(task, client, tools):
    res = Agent(client, tools=tools, system=SYSTEM + FINAL, **AGENT_KW).run(task)
    return Outcome(res.status, res.answer, res.detail, {"steps": res.steps},
                   [{"role": "single", "trace": res.trace}])


# ---- workers --------------------------------------------------------------------------------------
WORKER = """You are one worker on a larger question about the ACME company handbook; another agent
will combine your result with others. You see only this sub-task.
Find facts with the tools; never guess a number. Do every calculation with the calculator.
Work on this sub-task only. End with one last line of the form:
Result: {"status": "done" or "failed", "result": <what the sub-task asks for>, "note": "<what you used, briefly>"}"""

CONTRACT = """Objective: {objective}
Inputs: {inputs}
Return as "result": {output}
Done when: {done_when}"""


def work(text, client, tools, system=WORKER, key="result"):
    """One worker on one sub-task, in a fresh context. Returns a dict the caller can check:
    state "completed" with the parsed Result object (marked done, with `key` present), or "failed"
    with why. This is also what the
    A2A server (a2a.py) runs for each task it is sent."""
    res = Agent(client, tools=tools, system=system, **WORKER_KW).run(text)
    out = tagged(res.answer, "result", dict) if res.status == "answered" else None
    if res.status != "answered":
        why = f"the worker stopped: {res.status} ({res.detail})"
    elif out is None:
        why = "the worker gave no 'Result:' line with a JSON object"
    elif out.get("status") not in ("done", "failed"):
        why = "the worker's Result has no status 'done' or 'failed'"
        out = None
    elif out["status"] == "done" and out.get(key) is None:
        why = f"the worker's Result is marked done but has no \"{key}\""
        out = None
    else:
        why = None
    state = "completed" if out is not None and out["status"] == "done" else "failed"
    if out is not None and out["status"] == "failed":
        why = "the worker reported failure: " + str(out.get("note", ""))[:300]
    return {"state": state, "result": out, "why": why, "answer": res.answer, "steps": res.steps,
            "tokens": res.tokens, "trace": res.trace}


def local(client, tools):
    """Send a sub-task to a worker in this process (no protocol): the default transport."""
    return lambda text: work(text, client, tools)


# ---- orchestrator ---------------------------------------------------------------------------------
LEAD = """You lead a team that answers questions about the ACME company handbook. You can't read the
handbook yourself: you give sub-tasks to workers with the delegate tool. Each worker starts fresh,
sees only the sub-task you write, can search and read the handbook and use a calculator, and returns
a JSON object. Write each sub-task as a contract: the objective, the inputs the worker needs (names,
ids and values found so far), what to return, and how the worker knows it is done. Delegate
independent sub-tasks separately; when a sub-task needs an earlier result, wait for it and put it in
the inputs. Do every calculation with the calculator. You can delegate at most {n} sub-tasks.
When you have the answer, reply in plain text with the final number and its unit.""" + FINAL

DELEGATE = spec("delegate", "Give one sub-task to a fresh worker and get back its JSON result.",
                objective="what the worker must find or compute, in one or two sentences",
                inputs="everything the worker needs to know: names, ids, values found so far",
                output="what to return as the result, e.g. 'the trip's meals per-diem in USD, as a number'",
                done_when="how the worker can tell it has finished")


def orchestrator(task, client, tools, send=None):
    """The lead's tools are delegate and the calculator. `send` carries a sub-task to a worker and
    returns work()'s dict: local() by default, a2a.Client.sender() to go through the protocol."""
    client = metered(client)
    send = send or local(client, tools)
    calls, traces = [], []

    def delegate(objective, inputs, output, done_when):
        if len(calls) >= MAX_WORKERS:
            raise ToolError("limit", f"all {MAX_WORKERS} sub-tasks are used",
                            "Answer with what you have, or say what is missing.")
        if client.tokens >= MAX_TOKENS:
            raise ToolError("budget", f"the run's token budget ({MAX_TOKENS:,}) is spent",
                            "Answer with what you have, or say what is missing.")
        text = CONTRACT.format(objective=objective, inputs=inputs, output=output, done_when=done_when)
        r = send(text)
        calls.append({"contract": {"objective": objective, "inputs": inputs, "output": output,
                                   "done_when": done_when},
                      "state": r["state"], "result": r["result"], "why": r["why"], "steps": r["steps"],
                      "tokens": r["tokens"]})
        traces.append({"role": f"worker {len(calls)}", "trace": r.get("trace", [])})
        if r["state"] != "completed":
            raise ToolError("worker_failed", r["why"] or "the worker failed",
                            "Rewrite the sub-task more precisely, give it the inputs it lacked, or split it.")
        return json.dumps(r["result"])

    lead_tools = {"delegate": (delegate, DELEGATE), "calculator": tools["calculator"]}
    res = Agent(client, tools=lead_tools, system=LEAD.format(n=MAX_WORKERS), **LEAD_KW).run(task)
    info = {"steps": res.steps, "delegations": calls, "calls": client.calls, "tokens": client.tokens,
            "errors": client.errors}
    return Outcome(res.status, res.answer, res.detail, info, [{"role": "lead", "trace": res.trace}] + traces)


# ---- pipeline -------------------------------------------------------------------------------------
SPLIT = """You split a question about the ACME company handbook into independent sub-questions. Use the
tools to find what the sub-questions need, for example which trips count. Each sub-question must be
answerable alone by a helper who sees only it, and must have one amount in USD as its answer; the
answer to the whole question must be the sum of those amounts. Put into each sub-question every name,
id and value the helper needs. If the question can't be split that way, give one sub-question: the
whole question, with what you found put into it. Don't compute the amounts yourself.
End with one last line of the form:
Parts: [{"trip": "<trip id, or empty>", "question": "<the sub-question>"}, ...]   (at most %d)""" % MAX_WORKERS

PART = """{question}
End with one last line of the form:
Result: {{"status": "done" or "failed", "trip": "<trip id, or empty>", "amount": <the amount in USD, as a number>, "note": "<what you used, briefly>"}}"""

PART_WORKER = """You answer one question about the ACME company handbook. Find facts with the tools;
never guess a number. Do every calculation with the calculator."""


def parse_parts(text):
    parts = tagged(text, "parts", list)
    if (not parts or len(parts) > MAX_WORKERS
            or not all(isinstance(p, dict) and isinstance(p.get("question"), str) and p["question"].strip()
                       for p in parts)):
        return None
    return [{"trip": str(p.get("trip") or ""), "question": p["question"].strip()} for p in parts]


def amount_of(result):
    """The Result's amount as a Decimal, or None: a number, or a string holding only one, written
    with an optional '$' and correctly grouped thousands ("1,234.50"; not "1,2" or "1$2")."""
    a = (result or {}).get("amount")
    if isinstance(a, bool) or not isinstance(a, (int, float, str)):
        return None
    m = re.fullmatch(rf"\$?\s*({_NUM})", str(a).strip())
    if not m:
        return None
    try:
        v = Decimal(m[1].replace(",", ""))
    except InvalidOperation:
        return None
    return v if v >= 0 else None


def pipeline(task, client, tools):
    """Split (one agent, tools allowed), then one fresh worker per part, then code adds. A split
    that isn't a valid list is asked for once more; a part with no amount is retried once, told what
    was missing; a part that still fails stops the run with no number, so nothing wrong is added."""
    client = metered(client)
    splitter = Agent(client, tools=tools, system=SPLIT, **SPLIT_KW)
    res = splitter.run(f"Question: {task}")
    traces = [{"role": "splitter", "trace": res.trace}]
    parts = parse_parts(res.answer) if res.status == "answered" else None
    if parts is None and res.status == "answered":
        res = splitter.run(f"Question: {task}\n\nEnd with the 'Parts:' line: a JSON list of 1 to {MAX_WORKERS} "
                           "objects, each with a \"question\".")
        traces.append({"role": "splitter (again)", "trace": res.trace})
        parts = parse_parts(res.answer) if res.status == "answered" else None
    info = {"parts": parts, "results": [], "retried": [], "calls": client.calls, "tokens": client.tokens,
            "errors": client.errors}
    if parts is None:
        return Outcome("split_error", "", f"no valid split ({res.status})", info, traces)
    total = Decimal(0)
    for k, p in enumerate(parts, 1):
        q = PART.format(question=p["question"])
        r = work(q, client, tools, PART_WORKER, "amount")
        traces.append({"role": f"part {k}", "trace": r["trace"]})
        amount = amount_of(r["result"]) if r["state"] == "completed" else None
        if amount is None:
            info["retried"].append(k)
            r = work(q + "\nGive the amount on the 'Result:' line, as a number.", client, tools, PART_WORKER, "amount")
            traces.append({"role": f"part {k} (again)", "trace": r["trace"]})
            amount = amount_of(r["result"]) if r["state"] == "completed" else None
        info["results"].append({"part": k, "trip": p["trip"], "state": r["state"], "why": r["why"],
                                "result": r["result"], "amount": None if amount is None else str(amount)})
        if amount is None:
            info |= {"calls": client.calls, "tokens": client.tokens}
            return Outcome("part_failed", "", f"part {k}: {r['why'] or 'no amount'}", info, traces)
        total += amount
    lines = "\n".join(f"{r['trip'] or 'part ' + str(r['part'])}: {r['amount']} USD" for r in info["results"])
    info |= {"calls": client.calls, "tokens": client.tokens}
    return Outcome("answered", f"By part:\n{lines}\nFinal answer: {total} USD", "", info, traces)


STRATEGIES = {"single": single, "orchestrator": orchestrator, "pipeline": pipeline}
