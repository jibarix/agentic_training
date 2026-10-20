"""Durable runs: a journal of every model call and tool call, replayed on resume.

A run's code is ordinary Python that calls the model and the tools through a Run. Each call gets a
sequence number. The Run writes the call's result to the journal before handing it back, so after
a crash the same code can start again from the top: calls the journal already holds are answered
from it, in order, and the first call it doesn't hold is made for real. The code between calls must
be deterministic for that to work (it is here: the agent, the planner and the workflow decide only
from what the calls returned), and the Run checks it: a replayed call must ask for exactly what the
journal recorded, or the resume stops.

Only results are recorded. A call that raises stops the whole run (Halted), so nothing after it is
recorded either, and a resume makes the call again, which is what a failure that may be transient
needs. If the code could catch the failure and carry on, the journal would have a gap that a resume
couldn't replay. A tool's ToolError is a result (the model is meant to read it), and so is a bug in
a tool, which Chapter 1's agent shows the model: both are recorded and replayed.
"""
import hashlib
import json
import os
from pathlib import Path


class Crash(BaseException):
    """A simulated kill. BaseException, so no `except Exception` in the code under test can catch it."""


class Halted(BaseException):
    """A call failed (after any retries). The run stops; resuming it makes the call again.

    BaseException, so the agent can't turn it into an observation and carry on past a call the
    journal doesn't hold."""


class Diverged(BaseException):
    """A resumed run asked for something other than what its journal recorded at that position.

    BaseException too: inside the agent it would otherwise become an observation the model reads."""


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def read_jsonl(path, repair=True):
    """The whole lines of a JSON-lines file, as (entries, torn). A crash can cut the last line short:
    it is dropped and, if `repair`, the file cut back to the whole lines, so the next append starts on
    a fresh line. A reader that only inspects (a report) passes repair=False and changes nothing."""
    path = Path(path)
    entries, good = [], 0
    data = path.read_bytes() if path.exists() else b""
    for line in data.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            break                                       # torn last line
        try:
            entries.append(json.loads(line))
        except ValueError:
            break
        good += len(line)
    if repair and good < len(data):
        with open(path, "r+b") as f:
            f.truncate(good)
    return entries, good < len(data)


def append_jsonl(path, entry, crash_mid_write=False):
    """One line, flushed and fsynced before returning. crash_mid_write: for the tests, half a line, then the kill."""
    line = (json.dumps(entry, default=str) + "\n").encode()
    with open(path, "ab") as f:
        if crash_mid_write:
            f.write(line[: len(line) // 2])
            f.flush()
            raise Crash("killed while writing")
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    return json.loads(line)


class Journal:
    """Append-only JSON lines, each flushed and fsynced before the call's result is used."""

    def __init__(self, path):
        self.path = Path(path)
        self.entries, self.torn = read_jsonl(self.path)   # torn: True if a cut line was dropped

    def append(self, entry, crash_mid_write=False):
        self.entries.append(append_jsonl(self.path, entry, crash_mid_write))


class Run:
    """One durable run. `crash` = (sequence number, point) kills it there, for testing recovery.

    Points: "before" (nothing done), "after_effect" (the call ran, the journal doesn't know),
    "mid_write" (the journal line is half written), "after_record" (journalled, not yet returned)."""

    POINTS = ("before", "after_effect", "mid_write", "after_record")

    def __init__(self, journal, run_id, crash=None):
        self.journal, self.run_id, self.crash = journal, run_id, crash
        self.seq = 0
        self.replayed = self.live = 0
        self.live_tokens = 0

    def _maybe_crash(self, n, point):
        if self.crash == (n, point):
            raise Crash(f"killed at call {n}, {point}")

    def step(self, kind, request, do, tokens=None):
        """Answer call number `seq` from the journal, or do it and record it.

        `do(n)` makes the call; it gets the sequence number so an effect can use it in its
        idempotency key. `tokens(result)` says what the call cost, for the live-cost count."""
        n = self.seq
        self.seq += 1
        h = digest([kind, request])
        if n < len(self.journal.entries):
            e = self.journal.entries[n]
            if e["n"] != n or e["kind"] != kind or e["hash"] != h:
                raise Diverged(f"call {n}: the journal has {e['kind']} {e['hash']}, the run asked for {kind} {h}")
            self.replayed += 1
            return e["result"]
        self._maybe_crash(n, "before")
        try:
            result = do(n)
        except Exception as e:                          # not a result: stop, and make the call again on resume
            raise Halted(f"call {n} ({kind}) failed: {type(e).__name__}: {e}") from e
        self._maybe_crash(n, "after_effect")
        entry = {"n": n, "kind": kind, "hash": h, "result": result}
        try:
            self.journal.append(entry, crash_mid_write=self.crash == (n, "mid_write"))
        except Exception as e:                          # a result that can't be recorded: stop, as for a failed call
            raise Halted(f"call {n} ({kind}) could not be recorded: {type(e).__name__}: {e}") from e
        self.live += 1
        if tokens:
            self.live_tokens += tokens(result)
        self._maybe_crash(n, "after_record")
        return self.journal.entries[-1]["result"]     # as read back: live and replay see the same


class DurableClient:
    """A chat client whose calls go through a Run. Drop-in for Chapter 1's clients."""

    def __init__(self, client, run):
        self.client, self.run = client, run

    def chat(self, messages, tools=None):
        def do(n):
            msg, usage = self.client.chat(messages, tools)
            return [msg, usage or {}]
        msg, usage = self.run.step("model", {"messages": messages, "tools": tools}, do,
                                   tokens=lambda r: (r[1] or {}).get("total_tokens") or 0)
        return msg, usage


def durable_tools(tools, run, effects=()):
    """Chapter 1's tools dict with every call going through the Run.

    A tool named in `effects` changes the world. It is called with an extra `key` argument, the run
    id and the call's sequence number, so the system it writes to can drop a second write with the
    same key. The model never sees or chooses the key."""
    from tools import ToolError                         # Chapter 1's, on the path set by the caller
    from faults import transient

    def wrap(name, fn):
        def call(**args):
            def do(n):
                try:
                    out = fn(**args, key=f"{run.run_id}/{n}") if name in effects else fn(**args)
                    return {"ok": out}
                except ToolError as e:                  # a result the model reads: record it
                    return {"tool_error": [e.kind, str(e), e.hint]}
                except Exception as e:
                    if transient(e):                    # not a result: the run halts, and retries on resume
                        raise
                    return {"raised": [type(e).__name__, str(e)]}   # a bug in the tool, shown to the model
            r = run.step("effect" if name in effects else "tool", {"name": name, "args": args}, do)
            if "tool_error" in r:
                raise ToolError(*r["tool_error"])
            if "raised" in r:                           # the same type name and message, live or replayed
                raise type(r["raised"][0], (Exception,), {})(r["raised"][1])
            return r["ok"]
        return call

    return {name: (wrap(name, fn), spec) for name, (fn, spec) in tools.items()}
