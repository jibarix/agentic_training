"""Three ways to answer the same long task, from the model deciding everything to code deciding it.

  agent    : Chapter 1's agent with the whole task (the model chooses every step as it goes)
  plan     : the model writes a plan; a fresh agent runs each step; a failed step is replanned
  workflow : code fixes the steps; the model fills two kinds of slot (what the question asks
             for, and one trip's reimbursement), and code does the rest

Each takes the task, a chat client and Chapter 1's tools dict, and returns an Outcome. None of
them files the claim: that is left to the caller (run.py), so that the one action with an effect
goes through code that checks it, whichever strategy produced the number.
"""
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from agent import SYSTEM, Agent                         # Chapter 1's
from tools import ToolError                             # Chapter 1's

FINAL = "\nEnd with one last line of the form: Final answer: <number> <unit>"   # as in Chapter 1
AGENT_KW = {"max_steps": 30, "max_tokens": 120_000, "max_obs_chars": 2_000, "hints": True}  # Chapter 4's
STEP_KW = {"max_steps": 12, "max_tokens": 40_000, "max_obs_chars": 2_000, "hints": True}   # one plan step
PARTS = ("meals", "lodging", "mileage")
_NUM = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?"


@dataclass
class Outcome:
    status: str                  # "answered" | "gave_up" | "plan_error" | "step_failed" | an Agent status
    answer: str = ""
    amount: str = None           # the final number, as text, for the claim; None if there isn't one
    detail: str = ""
    info: dict = field(default_factory=dict)


class Meter:
    """Counts the calls and tokens a strategy spends, whether they are made or replayed."""

    def __init__(self, client):
        self.client, self.calls, self.tokens = client, 0, 0

    def chat(self, messages, tools=None):
        msg, usage = self.client.chat(messages, tools)
        self.calls += 1
        self.tokens += (usage or {}).get("total_tokens") or 0
        return msg, usage


_MONEY = re.compile(rf"\s*(\$)?\s*({_NUM})\s*(USD|dollars?)?\s*\.?\s*", re.I)


def final_amount(text):
    """The amount on the last 'Final answer:' line, as a Decimal, or None.

    Strict, because a claim is filed from it: the line must hold one unsigned number marked as
    money ($, USD or dollars) and nothing else. 'not 500 USD', '500 or 700 USD' and '91 miles' are
    None, not 500 or 91. This decides what may be claimed; whether the answer is right is the
    scorer's job (Chapter 3), which reads the same line differently."""
    lines = re.findall(r"(?im)^[\s*_#>-]*final answer[\s*_]*:(.*)$", text or "")
    m = _MONEY.fullmatch(re.sub(r"[*_`]", "", lines[-1])) if lines else None
    if not m or not (m.group(1) or m.group(3)) or m.group(2).startswith("-"):
        return None
    try:
        return Decimal(m.group(2).replace(",", ""))
    except InvalidOperation:
        return None


def employee_of(task):
    m = re.search(r"\bEMP\d{4}\b", task)
    return m.group(0) if m else None


def ask(client, system, user):
    """One call without tools; the reply's text ('' if there is none)."""
    msg, _ = client.chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    return msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), str) else ""


def json_in(text, kind):
    """The first JSON value of type `kind` (list or dict) in a reply, or None."""
    a, b = ("[", "]") if kind is list else ("{", "}")
    i, j = text.find(a), text.rfind(b)
    if i < 0 or j <= i:
        return None
    try:
        v = json.loads(text[i:j + 1])
    except ValueError:
        return None
    return v if isinstance(v, kind) else None


# ---- agent --------------------------------------------------------------------------------------
def agent(task, client, tools):
    res = Agent(client, tools=tools, system=SYSTEM + FINAL, **AGENT_KW).run(task)
    amount = final_amount(res.answer) if res.status == "answered" else None
    return Outcome(res.status, res.answer, None if amount is None else str(amount), res.detail,
                   {"steps": res.steps})


# ---- plan, execute, replan ------------------------------------------------------------------------
PLAN = """You plan how to answer a question about the ACME company handbook. A helper will carry out
the plan one step at a time. The helper can search the handbook, read a handbook file and use a
calculator, and sees the question and the results of the earlier steps. Reply with only a JSON list
of steps, each one short instruction, at most 8 steps. The last step must answer the question."""

STEP = """Question: {task}

Results of the earlier steps:
{done}

Your step: {step}
Do this step only, using the tools. {end}"""
MID = "End with one last line of the form: Result: <what you found>"
LAST = "This is the last step: answer the question. End with one last line of the form: Final answer: <number> <unit>"

REPLAN = """Question: {task}

Steps done, with their results:
{done}

This step failed: {step}
Why: {why}

The plan still to do was:
{rest}

Write the steps still to do as a new JSON list (not the ones already done), at most 8. Change the
plan; don't repeat the failed step as it was. The last step must answer the question."""


def parse_plan(text):
    steps = json_in(text, list)
    if not steps or len(steps) > 8 or not all(isinstance(s, str) and s.strip() for s in steps):
        return None
    return [s.strip() for s in steps]


def get_plan(client, user):
    """A valid plan in at most two tries (the second is told what was wrong), or None."""
    reply = ask(client, PLAN, user)
    steps = parse_plan(reply)
    if steps is None:
        reply = ask(client, PLAN, user + "\n\nYour last reply was not a JSON list of 1 to 8 strings. "
                    "Reply with only the list.")
        steps = parse_plan(reply)
    return steps


def result_of(text):
    lines = re.findall(r"(?im)^[\s*_#>-]*result[\s*_]*:(.*)$", text)
    return lines[-1].strip() if lines else text.strip().splitlines()[-1].strip()


def plan(task, client, tools, max_replans=2, max_tokens=250_000):
    """Plan, then run each step with a fresh agent that sees the earlier results.

    A step fails if its agent stops without answering, or if the last step gives no number. Then
    the planner rewrites the rest of the plan, up to max_replans times; it stops sooner if the new
    plan is the old one (no new work to try). A run that stops says what it could not finish.

    max_tokens is checked before each step and each replan and counts every call, the planner's
    too. It is a threshold, not a cap: it is checked only before a step or a replan, so a run can
    pass it by whatever the step or replan then spends. A step's own 40,000 is a threshold of the
    same kind (Chapter 1's agent checks it between calls), and a replan can make two calls."""
    client = Meter(client)                       # this run's spending, planner and steps together
    steps = get_plan(client, f"Question: {task}")
    if steps is None:
        return Outcome("plan_error", detail="no valid plan in two tries")
    info = {"plans": [list(steps)], "replans": 0, "failures": []}
    done, i = [], 0
    show = lambda: "\n".join(f"{k + 1}. {s}\n   -> {r}" for k, (s, r) in enumerate(done)) or "(none yet)"
    over = lambda: f"the token budget ({max_tokens:,}) is spent: {client.tokens:,} tokens so far"
    while i < len(steps):
        if client.tokens >= max_tokens:
            why = over()
            info["failures"].append({"step": steps[i], "why": why})
            break
        last = i == len(steps) - 1
        res = Agent(client, tools=tools, system=SYSTEM, **STEP_KW).run(
            STEP.format(task=task, done=show(), step=steps[i], end=LAST if last else MID))
        why = None
        if res.status != "answered":
            why = f"the helper stopped: {res.status} ({res.detail})"
        elif last and final_amount(res.answer) is None:
            why = "the last step gave no 'Final answer:' line with one amount in USD"
        if why is None:
            done.append((steps[i], result_of(res.answer)))
            i += 1
            if last:
                return Outcome("answered", res.answer, str(final_amount(res.answer)), "", info)
            continue
        info["failures"].append({"step": steps[i], "why": why})
        if info["replans"] >= max_replans:
            break
        if client.tokens >= max_tokens:
            why += f"; and {over()}"
            break
        rest = steps[i:]
        new = get_plan(client, REPLAN.format(task=task, done=show(), step=steps[i], why=why,
                                             rest="\n".join(f"- {s}" for s in rest)))
        info["replans"] += 1
        if new is None or new == rest:
            info["failures"].append({"step": "(replan)", "why": "no new plan"})
            break
        steps = steps[:i] + new
        info["plans"].append(list(steps))
    found = show()
    gave_up = (f"I could not finish this. The step '{steps[i]}' failed: {why}.\n"
               f"What I found before stopping:\n{found}\nI have not confirmed the total, so I give no final answer.")
    return Outcome("gave_up", gave_up, None, why, info)


# ---- workflow ---------------------------------------------------------------------------------------
EXTRACT = """Read a question about travel reimbursement. Reply with only a JSON object
{"parts": [...]}, listing which of "meals", "lodging" and "mileage" the question asks about."""

TRIP = ("For trip {Trip} to {City} ({Days} travel days, {Nights} nights, hotel {Lodging} USD per "
        "night, vehicle: {Vehicle}, {Miles} miles driven), how much does ACME reimburse for {what}?")
TRIP_COLUMNS = ("Trip", "Employee", "City", "Days", "Nights", "Lodging", "Vehicle", "Miles", "Billed")


def parse_parts(text):
    v = json_in(text, dict)
    parts = v.get("parts") if v else None
    if not isinstance(parts, list) or not parts or not all(p in PARTS for p in parts):
        return None
    return sorted(set(parts), key=PARTS.index)


def trip_rows(text, employee):
    """The employee's rows of the trip log, as dicts keyed by the first word of each header.

    ValueError if the text holds no table with the columns the workflow reads: a log that can't be
    read must not look like an employee with no trips."""
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in text.splitlines() if line.strip().startswith("|")]
    if len(rows) < 2:
        raise ValueError("no table in the trip log")
    head = [h.split()[0] if h.split() else "" for h in rows[0]]
    missing = [h for h in TRIP_COLUMNS if h not in head]
    if missing:
        raise ValueError(f"the trip log's table has no column {', '.join(missing)}")
    return [dict(zip(head, r)) for r in rows[2:] if len(r) == len(head) and r[head.index("Employee")] == employee]


def workflow(task, client, tools, fallback=agent):
    """Code decides the steps: (1) the model says which parts the question asks for, checked by
    code; (2) code reads the trip log and keeps the employee's trips billed to ACME (the travel
    policy's section 5, written as code); (3) a fresh agent works out each trip; (4) code adds.
    A question the workflow can't read goes to `fallback` instead; a step that fails stops the run
    with no number, so nothing is claimed."""
    employee = employee_of(task)
    reply = ask(client, EXTRACT, task)
    parts = parse_parts(reply)
    if parts is None:
        parts = parse_parts(ask(client, EXTRACT, task + '\n\nReply with only the JSON object, e.g. {"parts": ["meals"]}.'))
    if employee is None or parts is None:
        out = fallback(task, client, tools)
        out.info["routed"] = "employee" if employee is None else "parts"
        return out
    try:
        log = tools["read_file"][0](path="trips_2026q1.md")
    except ToolError as e:                       # the code's own read failed: stop and say so
        return Outcome("step_failed", "", None, f"trip log: {e}", {"parts": parts})
    try:
        rows = [r for r in trip_rows(log, employee) if r["Billed"] == "ACME"]
    except ValueError as e:                      # unreadable, not empty: stop with no number
        return Outcome("step_failed", "", None, f"trip log unreadable: {e}", {"parts": parts})
    info = {"parts": parts, "trips": [r["Trip"] for r in rows], "per_trip": {}, "retried": []}
    if not rows:
        return Outcome("answered", f"{employee} has no trips billed to ACME.\nFinal answer: 0 USD", "0", "", info)
    what = " and ".join({"meals": "meals per-diem", "lodging": "lodging", "mileage": "mileage"}[p] for p in parts)
    total = Decimal(0)
    for r in rows:
        q = TRIP.format(what=what, **r) + FINAL
        res = Agent(client, tools=tools, system=SYSTEM + FINAL, **STEP_KW).run(q)
        amount = final_amount(res.answer) if res.status == "answered" else None
        if amount is None:                       # one more try, told what was missing
            info["retried"].append(r["Trip"])
            res = Agent(client, tools=tools, system=SYSTEM + FINAL, **STEP_KW).run(
                q + "\nGive the amount for this one trip on a 'Final answer:' line.")
            amount = final_amount(res.answer) if res.status == "answered" else None
        if amount is None:
            return Outcome("step_failed", "", None, f"trip {r['Trip']}: no amount ({res.status})", info)
        info["per_trip"][r["Trip"]] = str(amount)
        total += amount
    lines = "\n".join(f"{t}: {a} USD" for t, a in info["per_trip"].items())
    return Outcome("answered", f"{what.capitalize()} for {employee}, by trip:\n{lines}\nFinal answer: {total} USD",
                   str(total), "", info)


STRATEGIES = {"agent": agent, "plan": plan, "workflow": workflow}
