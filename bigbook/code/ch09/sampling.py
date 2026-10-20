"""Spending more inference on one question: sample several runs, then pick one answer.

  Recorder  : wraps a chat client; logs each call's tokens and the length of any thinking it
              returned, and the errors of calls that raised
  amount    : the number on a run's last 'Final answer:' line, in the shape Chapter 3's scorer
              accepts (no word before it but a unit, so "not 710 USD" gives none), or None
  vote_k    : the expected score of a majority vote over k runs drawn from n, averaged exactly
              over every subset, with ties broken at random
  agreement : the share of runs that gave the winning amount, a confidence signal
  judge     : the same model shown the question and k candidate runs, asked for one number
The oracle that picks a right run whenever there is one is Chapter 3's pass@k.

Every choice is scored on the runs it picks, so a vote or a judge can't be right on a run that was
wrong: it can only choose among them. Standard library only.
"""
import json
import re
from decimal import Decimal, InvalidOperation
from itertools import combinations
from statistics import fmean

FINAL_LINE = re.compile(r"(?im)^[\s*_#>-]*final answer[\s*_]*:(.*)$")       # as Chapter 3's scorer
NUM = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?"


class Recorder:
    """A chat client that remembers what each call cost. Pass it to Chapter 1's Agent."""

    def __init__(self, client):
        self.client, self.calls, self.errors, self.thoughts = client, [], [], []

    def chat(self, messages, tools=None):
        try:
            msg, usage = self.client.chat(messages, tools)
        except Exception as e:                   # Chapter 1's agent stops the run; the experiment stops too
            self.errors.append(f"{type(e).__name__}: {e}")
            raise
        usage = usage or {}
        thought = (msg.get("reasoning") or msg.get("reasoning_content") or "") if isinstance(msg, dict) else ""
        thought = thought if isinstance(thought, str) else ""
        self.thoughts.append(thought)            # Chapter 1's trace keeps only the reply, so keep it here
        self.calls.append({"prompt": usage.get("prompt_tokens"), "completion": usage.get("completion_tokens"),
                           "total": usage.get("total_tokens"),
                           "thinking_chars": len(thought)})
        return msg, usage


def amount(answer, units=()):
    """The number on the last 'Final answer:' line, as a Decimal, or None.

    The line must have the shape Chapter 3's scorer accepts: one number, at most a currency unit or
    '$' before it, and at most two words after it. A word before the number that isn't one of the
    task's units (as in "not 710 USD" or "about 710") gives None, as the scorer would refuse it. The
    words after it are not checked, so two runs with the same number and different units vote
    together, and the vote scores them separately."""
    lines = FINAL_LINE.findall(answer or "")
    if not lines:
        return None
    line = re.sub(r"[*_]", "", lines[-1]).strip().rstrip(".").strip()
    m = re.fullmatch(rf"(\$|[A-Za-z]+)?\s*({NUM})\s*(?:[A-Za-z]+\s+)?(?:[A-Za-z]+)?", line)
    names = {u.lower() for u in units}
    if not m or (m.group(1) and m.group(1) != "$" and m.group(1).lower() not in names
                 and m.group(1).lower().rstrip("s") not in names):
        return None
    try:
        return Decimal(m.group(2).replace(",", ""))
    except InvalidOperation:
        return None


def vote(runs):
    """Expected score of a majority vote over runs [(amount, ok)], ties broken at random.

    Runs with no amount don't vote. The vote returns one of the runs that gave the winning amount,
    chosen at random, so its score is the share of those runs that were right (runs with the same
    number can differ in their unit). No amount at all scores 0."""
    groups = {}
    for a, ok in runs:
        if a is not None:
            groups.setdefault(a, []).append(1 if ok is True else 0)
    if not groups:
        return 0.0
    top = max(map(len, groups.values()))
    winners = [g for g in groups.values() if len(g) == top]
    return fmean(fmean(g) for g in winners)


def vote_k(runs, k):
    """The vote's expected score over every k of the n runs, each subset equally likely."""
    return fmean(vote(c) for c in combinations(runs, k))


def agreement(runs):
    """Share of the runs that gave the winning amount (Wang et al.'s consistency), or 0."""
    counts = {}
    for a, _ in runs:
        if a is not None:
            counts[a] = counts.get(a, 0) + 1
    return max(counts.values()) / len(runs) if counts else 0.0


JUDGE = """You check answers to questions about the ACME company handbook.
Below are a question and several attempts at it, each with the tool results it used and its
final answer. The attempts may disagree, and any of them may be wrong. Pick the one whose final
answer is most likely correct, judging by whether its numbers come from its tool results and its
arithmetic is right, not by how long or confident it is.
Reply with one last line of the form: Choice: <number>"""
CHOICE_LINE = re.compile(r"(?im)^[\s*_#>-]*choice[\s*_]*:(.*)$")
CHOICE = re.compile(r"\s*(?:attempt\s*)?(\d+)\s*\.?\s*", re.I)  # the whole value: "2", "**2**", "Attempt 2."


def evidence(trace, max_obs=400, max_chars=3_000):
    """A run as the judge sees it: each tool call with a cut of its result, then the last reply."""
    lines, last = [], ""
    for t in trace:
        if t["type"] == "tool":
            obs = t["observation"]
            obs = obs if len(obs) <= max_obs else obs[:max_obs] + " [...]"
            lines.append(f"- {t['name']}: {obs}")
        elif t["type"] == "model" and t.get("content"):
            last = t["content"]
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n[... more tool results omitted ...]"
    return f"Tool results:\n{text or '(none)'}\nReply:\n{last.strip() or '(no reply)'}"


def judge_prompt(question, candidates):
    parts = [f"Question: {question}"]
    for i, c in enumerate(candidates, 1):
        parts.append(f"=== Attempt {i} ===\n{c}")
    return "\n\n".join(parts)


def judge(client, question, candidates):
    """Ask the model which candidate is right. Returns (index from 0 or None, reply, usage).

    A model call that raises is not caught: the experiment stops with nothing written."""
    msg, usage = client.chat([{"role": "system", "content": JUDGE},
                              {"role": "user", "content": judge_prompt(question, candidates)}])
    text = msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), str) else ""
    lines = CHOICE_LINE.findall(text)                     # the last declaration counts, and all of it:
    m = CHOICE.fullmatch(re.sub(r"[*_]", "", lines[-1])) if lines else None   # "1 or 2", "1.5", "-1" give none
    n = int(m.group(1)) if m else 0
    return (n - 1 if 1 <= n <= len(candidates) else None), text, usage or {}
