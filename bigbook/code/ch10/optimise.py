"""Improving the agent's prompt without touching its weights: the split, bootstrapped demos and a
reflected instruction. Standard library only; nothing here calls a model except reflect().

  split     : Chapter 4's 30 long tasks into training and held-out halves, by task, three of each
              per kind, pairing tasks with similar success in Chapter 4's run
  bootstrap : the passing runs of training tasks in Chapter 4's run, kept as worked examples (the
              prompt-level form of keeping what passes, as in ReST-EM and DSPy's bootstrap)
  reflect   : the same model reads failed training runs with the scorer's feedback and writes a
              new instruction (one step of GEPA's loop, with one module and no Pareto pool)

The held-out tasks are never shown to either method: demos come from training tasks, and the
instruction is chosen on training tasks before any held-out run.
"""
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).parent
CH04 = HERE.parent / "ch04"
CH4_RUN = CH04 / "results" / "2026-10-17-run1"
SPLIT = HERE / "split.json"
SPLIT_SEED = 10
CH4_COND = "full"                        # Chapter 4's full-context agent: arm A's own agent


def ch4_rows(run=CH4_RUN, cond=CH4_COND):
    """Chapter 4's runs of its full-context agent, as recorded (the scorer's ok, not the labels)."""
    rows = [json.loads(line) for line in (run / "traces.jsonl").read_text(encoding="utf-8").splitlines()]
    return [r for r in rows if r["cond"] == cond]


def successes(rows):
    """{task: runs right} over Chapter 4's seeds."""
    out = {}
    for r in rows:
        out[r["id"]] = out.get(r["id"], 0) + (r["ok"] is True)
    return out


def split(tasks, right, seed=SPLIT_SEED):
    """{"train": [ids], "heldout": [ids]}: per kind, sort by (successes, id), pair neighbours, and
    send one of each pair to each side at random. All runs of a task stay on one side."""
    rng = random.Random(seed)
    out = {"train": [], "heldout": []}
    for kind in sorted({t["cluster"] for t in tasks}):
        ids = sorted((t["id"] for t in tasks if t["cluster"] == kind), key=lambda i: (right.get(i, 0), i))
        for a, b in zip(ids[::2], ids[1::2]):
            first, second = (a, b) if rng.random() < 0.5 else (b, a)
            out["train"].append(first)
            out["heldout"].append(second)
    return out


def bootstrap(rows, train, n=2):
    """Up to n passing runs of training tasks, from different kinds, fewest steps first."""
    if n <= 0:
        return []
    ok = sorted((r for r in rows if r["ok"] is True and r["id"] in train),
                key=lambda r: (r["steps"], r["id"], r["seed"]))
    picked, kinds = [], set()
    for r in ok:
        if r["cluster"] not in kinds:
            picked.append(r)
            kinds.add(r["cluster"])
        if len(picked) == n:
            break
    return picked


def render_demo(question, trace, max_obs=300):
    """One worked example: the question, each tool call with a cut of its result, the last reply."""
    lines = [f"Question: {question}"]
    for t in trace:
        if t["type"] == "model":
            for c in t.get("calls", []):
                lines.append(f"Tool call: {c['name']}({c['arguments']})")
            if not t.get("calls") and t.get("content"):
                lines.append("Reply: " + t["content"].strip())
        elif t["type"] == "tool":
            obs = t["observation"]
            lines.append("Result: " + (obs if len(obs) <= max_obs else obs[:max_obs] + " [...]"))
    return "\n".join(lines)


DEMOS_HEAD = "\n\nWorked examples of other questions, answered correctly with the tools:"


def with_demos(prompt, demos):
    """Arm B's system prompt: arm A's, then the worked examples."""
    if not demos:
        return prompt
    return prompt + DEMOS_HEAD + "".join(f"\n\n=== Example {i} ===\n{d}" for i, d in enumerate(demos, 1))


REFLECT = """You improve the instructions of an assistant that answers questions about the ACME
company handbook with three tools: lookup (search the handbook), read_file (read one file) and
calculator. Below are its current instructions and some questions it answered wrongly, each with
the tool calls it made, a cut of their results, its final reply and the expected answer.
Work out what general habits or rules would have avoided these mistakes, then write improved
instructions. Keep what still helps. Keep them general: do not mention these employees, trips,
cities or amounts. Use at most 250 words. Do not describe the answer format; it is added for you.
Reply with the new instructions between <instructions> and </instructions>."""
TAG = re.compile(r"<instructions>(.*?)</instructions>", re.S | re.I)
LEAK = re.compile(r"\b(?:EMP|TR)\d{4}\b", re.I)    # recognised IDs only, in any case
MAX_CHARS = 2_000


def failure(task, trace, answer):
    """A failed training run as the reflection reads it, with the scorer's feedback."""
    return (render_demo(task["task"], trace) + f"\nFinal reply: {(answer or '(none)').strip()}\n"
            f"Feedback: wrong. The expected answer was {task['answer']:g} USD.")


def minibatch(failed, step, size=3):
    """Up to size failed runs, drawn with the step as the seed, in a fixed order."""
    failed = sorted(failed)
    return sorted(random.Random(step).sample(failed, min(size, len(failed))))


def parse_instruction(text):
    """The proposed instruction, or (None, why) if it is missing, too long or names task data."""
    m = TAG.findall(text or "")
    if not m or not m[-1].strip():
        return None, "no <instructions> block"
    s = m[-1].strip()
    if len(s) > MAX_CHARS:
        return None, f"{len(s)} characters, over {MAX_CHARS}"
    if LEAK.search(s):
        return None, "names an employee or trip"
    return s, ""


def reflect(client, instruction, failures):
    """One reflection call. Returns (instruction or None, why, reply, usage).

    A model call that raises is not caught: the experiment stops with nothing written."""
    user = (f"Current instructions:\n{instruction}\n\n"
            + "\n\n".join(f"=== Wrong answer {i} ===\n{f}" for i, f in enumerate(failures, 1)))
    msg, usage = client.chat([{"role": "system", "content": REFLECT}, {"role": "user", "content": user}])
    text = msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), str) else ""
    new, why = parse_instruction(text)
    return new, why, text, usage or {}
