"""What the model sees on each call once the history grows: four context policies.

Chapter 1's agent keeps its whole history in `messages` and sends all of it on every call. Here a
policy sits between the agent and the model client and decides the view that is sent. The agent's
own history is never changed, so every run can be audited against what the model actually saw.

  full   : send everything (Chapter 1)
  drop   : over budget, drop the oldest turns
  mask   : over budget, replace the oldest tool observations with a short placeholder
  compact: over budget, have the model summarise the oldest turns, and send the summary instead

Every policy keeps the system prompt and the task word for word, keeps at least the latest turn
(an assistant message with all of its tool observations), and cuts only between turns, so a tool
observation is never sent without the call it answers.

The budget is a trigger, not a bound: over it, a policy shrinks the view as far as its rules allow,
and that can still be over the budget when the protected part alone is too large. Every event and
every call records whether the view sent was over.
"""
import json
import re

SUMMARY_PROMPT = """You compress the earlier steps of an agent's task so that it can continue.
Write a checkpoint with these headings, and write "None" under a heading that has nothing:
Objective: the task, in one line.
Constraints: every condition the task or the handbook puts on the answer.
Facts found: every value found so far, with what it is and where it came from (file, row, trip id).
Calculations: every calculation done so far and its exact result.
Failed attempts: calls that failed or found nothing, so they are not repeated.
Next step: what the agent was about to do.
Copy numbers, names and identifiers exactly. Do not round. Do not answer the task. At most 250 words."""


class Estimate:
    """Prompt tokens from characters, calibrated by the server's last reported prompt_tokens."""

    def __init__(self, chars_per_token=4.0):
        self.chars_per_token = chars_per_token

    def __call__(self, messages, tools=None):
        return int(len(json.dumps([messages, tools or []])) / self.chars_per_token)

    def calibrate(self, messages, tools, usage):
        sent = (usage or {}).get("prompt_tokens")
        if isinstance(sent, int) and sent > 0:
            self.chars_per_token = len(json.dumps([messages, tools or []])) / sent


def turn_starts(messages):
    """Where each turn begins: every assistant message after the system prompt and the task."""
    return [i for i, m in enumerate(messages) if i >= 2 and m.get("role") == "assistant"]


def note(text):
    return {"role": "user", "content": text}


class Full:
    name = "full"

    def __init__(self, budget=None, estimate=None):
        self.estimate, self.events, self.extra_tokens = estimate or Estimate(), [], 0
        self.budget = budget

    def view(self, messages, tools, client):
        return messages

    def over(self, tokens):
        return self.budget is not None and tokens > self.budget


class Drop(Full):
    """Over budget: drop whole turns, oldest first, until the view fits or one turn is left."""
    name = "drop"

    def view(self, messages, tools, client):
        if self.estimate(messages, tools) <= self.budget:
            return messages
        starts = turn_starts(messages)
        if len(starts) < 2:                         # only the latest turn: nothing may go
            self.events.append({"at": len(messages), "error": "nothing old enough to drop", "over": True})
            return messages
        for cut in starts[1:]:
            v = messages[:2] + [note(f"[{cut - 2} earlier messages were removed to save space.]")] + messages[cut:]
            if self.estimate(v, tools) <= self.budget:
                break
        tokens = self.estimate(v, tools)
        self.events.append({"at": len(messages), "dropped": cut - 2, "tokens": tokens, "over": self.over(tokens)})
        return v


class Mask(Full):
    """Over budget: replace tool observations, oldest first, with a placeholder; keep the calls."""
    name = "mask"

    def __init__(self, budget, estimate=None, keep_turns=1):
        super().__init__(budget, estimate)
        self.keep_turns = keep_turns

    def view(self, messages, tools, client):
        if self.estimate(messages, tools) <= self.budget:
            return messages
        starts = turn_starts(messages)
        protect = starts[-self.keep_turns] if len(starts) >= self.keep_turns else len(messages)
        v, masked = list(messages), 0
        for i in range(2, protect):
            if v[i].get("role") == "tool":
                v[i] = {**v[i], "content": "[Observation removed to save space; repeat the call if you need it.]"}
                masked += 1
                if self.estimate(v, tools) <= self.budget:
                    break
        tokens = self.estimate(v, tools)
        self.events.append({"at": len(messages), "masked": masked, "tokens": tokens, "over": self.over(tokens)})
        return v


def render(messages):
    """Turns as plain text for the summariser: each call with its arguments, each observation."""
    names, out = {}, []
    for m in messages:
        if m.get("role") == "assistant":
            if m.get("content"):
                out.append(f"Agent: {m['content']}")
            for c in m.get("tool_calls") or []:
                names[c["id"]] = c["function"]["name"]
                out.append(f"Call {c['function']['name']}({c['function']['arguments']})")
        elif m.get("role") == "tool":
            out.append(f"Result of {names.get(m.get('tool_call_id'), 'tool')}: {m['content']}")
        else:
            out.append(f"{m.get('role', 'note').capitalize()}: {m.get('content', '')}")
    return "\n".join(out)


class Compact(Full):
    """Over budget: summarise the old turns with the model; send task, summary, latest turns.

    The summary replaces turns that were already summarised too, so a fact can drift through
    repeated summaries. If the summariser fails, or its summary doesn't make the view smaller, the
    uncompacted view is sent and the event logged. Every summary call's tokens are counted, even
    when the summary is rejected; after a transport error they are unknown, and logged as such.
    """
    name = "compact"

    def __init__(self, budget, estimate=None, keep_turns=1, prompt=SUMMARY_PROMPT):
        super().__init__(budget, estimate)
        self.keep_turns, self.prompt = keep_turns, prompt
        self.summary, self.cut = None, 2            # messages[2:cut] are covered by the summary

    def current(self, messages):
        if self.summary is None:
            return messages
        return messages[:2] + [note("Summary of your earlier steps on this task (the older messages were "
                                    "removed to save space):\n" + self.summary)] + messages[self.cut:]

    def view(self, messages, tools, client):
        v = self.current(messages)
        before = self.estimate(v, tools)
        if before <= self.budget:
            return v
        starts = [i for i in turn_starts(messages) if i >= self.cut]
        if len(starts) <= self.keep_turns:
            self.events.append({"at": len(messages), "error": "nothing old enough to compact", "over": True})
            return v
        cut = starts[-self.keep_turns]
        old = ("Earlier summary:\n" + self.summary + "\n\n" if self.summary else "") + render(messages[self.cut:cut])
        ask = [{"role": "system", "content": self.prompt},
               {"role": "user", "content": f"Task: {messages[1]['content']}\n\nSteps to compress:\n{old}"}]
        event = {"at": len(messages), "input": old}
        try:
            msg, usage = client.chat(ask)
        except Exception as e:                      # recover: send the full view, keep going
            self.events.append(event | {"error": f"{type(e).__name__}: {e}", "summary_tokens": "unknown",
                                        "over": True})
            return v
        used = (usage or {}).get("total_tokens")    # counted whether or not the summary is used
        used = used if isinstance(used, int) else self.estimate(ask) + len(json.dumps(msg)) // 4
        self.extra_tokens += used
        event["summary_tokens"] = used
        text = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(text, str) or not text.strip():
            self.events.append(event | {"error": "empty summary", "over": True})
            return v
        old_state = self.summary, self.cut
        self.summary, self.cut = text.strip(), cut
        after = self.estimate(self.current(messages), tools)
        if after >= before:                         # a summary longer than what it replaces
            self.summary, self.cut = old_state
            self.events.append(event | {"error": "summary did not shrink the view", "rejected": text,
                                        "over": True})
            return v
        self.events.append(event | {"covered": cut - 2, "summary": self.summary, "tokens": after,
                                    "over": self.over(after)})
        return self.current(messages)


POLICIES = {p.name: p for p in (Full, Drop, Mask, Compact)}


class ContextClient:
    """A chat client that sends a policy's view of the history. The agent loop doesn't change.

    The tokens a summary costs are added to the next call's usage, so the agent's budget and the
    run's token count include them. If that call fails, they stay in `unbilled`, and the run's
    record adds them.
    """

    def __init__(self, client, policy):
        self.client, self.policy, self.calls = client, policy, []

    @property
    def unbilled(self):
        return self.policy.extra_tokens

    def chat(self, messages, tools=None):
        view = self.policy.view(messages, tools, self.client)
        sent = self.policy.estimate(view, tools)
        record = {"history": len(messages), "sent": len(view), "estimated": sent,
                  "over": self.policy.over(sent), "summary_tokens": self.policy.extra_tokens}
        try:
            msg, usage = self.client.chat(view, tools)
        except Exception as e:
            self.calls.append(record | {"prompt_tokens": None, "error": f"{type(e).__name__}: {e}"})
            raise
        self.policy.estimate.calibrate(view, tools, usage)
        usage = dict(usage or {})
        if not isinstance(usage.get("total_tokens"), int):
            usage["total_tokens"] = sent + len(json.dumps(msg)) // 4
        usage["total_tokens"] += self.policy.extra_tokens
        self.calls.append(record | {"prompt_tokens": usage.get("prompt_tokens")})
        self.policy.extra_tokens = 0
        return msg, usage


def kept(summary, facts):
    """The facts that appear in a summary as whole values: '4' is not found in 'TR0004', '14' or '4.5'."""
    return [f for f in facts if re.search(rf"(?<![\w.]){re.escape(f)}(?!\w|\.\d)", summary or "")]


def together(text, fact):
    """Is the fact's value on a line of `text` that also names one of its keys? A fact with no keys
    (a trip id) needs only its value. This is co-occurrence, not meaning: "TR0010: 4 USD" passes
    for "TR0010 lasted 4 days"."""
    if not fact["keys"]:
        return bool(kept(text, [fact["value"]]))
    return any(kept(line, [fact["value"]]) and kept(line, fact["keys"]) for line in (text or "").splitlines())


def coverage(summary, given, facts):
    """How much of what the summariser was given survives, measured two ways.

    `facts` are a task's facts, each a value with the names it belongs to (a trip id, a city, a
    vehicle). Only the facts whose value was in `given`, the text the summariser was asked to
    compress, on a line with one of their names, are counted. `values`: how many of those values
    appear anywhere in the summary, which an unordered list of numbers would pass. `linked`: how
    many appear on a summary line that also names one of their names, so "TR0010: 4 days" counts
    for TR0010 and not for TR0011.
    """
    have = [f for f in facts if together(given, f)]
    values = [f for f in have if kept(summary, [f["value"]])]
    linked = [f for f in values if together(summary, f)]
    return {"given": len(have), "values": len(values), "linked": len(linked)}
