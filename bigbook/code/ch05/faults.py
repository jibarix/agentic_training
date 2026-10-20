"""Transient failures, injected on purpose, and retries that tell them apart from everything else.

Three kinds of outcome come back from a call, and each needs a different response:
  a result, even an empty one ("No matches"): use it; retrying gives the same answer;
  a permanent error (bad arguments, an unknown file): retrying gives the same error; report it;
  a transient error (a timeout, a refused connection, HTTP 429 or 5xx): wait, then try again.
Only the third is retried, a bounded number of times, with waits that grow and are jittered so
that many clients retrying at once don't arrive together.
"""
import random
import socket
import time
import urllib.error

from tools import ToolError                             # Chapter 1's


class TransientError(Exception):
    """A failure that may not happen if the same call is made again."""


def transient(e):
    if isinstance(e, (TransientError, TimeoutError, ConnectionError, socket.timeout)):
        return True
    if isinstance(e, urllib.error.HTTPError):
        return e.code == 429 or 500 <= e.code < 600
    if isinstance(e, urllib.error.URLError):           # only if what went wrong underneath is transient
        r = e.reason
        if isinstance(r, socket.gaierror):              # a name that can't be looked up *yet*
            return r.errno == getattr(socket, "EAI_AGAIN", None)
        return isinstance(r, (TimeoutError, ConnectionError, socket.timeout))   # refused, reset, timed out
    return False                                        # a bad URL, a certificate, anything else: permanent


def waits(attempts, base=1.0, cap=30.0, rng=None):
    """The wait before each retry: capped exponential with full jitter, uniform on [0, min(cap, base*2^i)]."""
    rng = rng or random.Random()
    return [rng.uniform(0, min(cap, base * 2 ** i)) for i in range(attempts - 1)]


def retry(fn, attempts=4, base=1.0, cap=30.0, budget=60.0, rng=None, sleep=time.sleep, log=None):
    """fn() until it succeeds, retrying transient errors only. At most `attempts` tries and `budget`
    seconds of waiting in all; then the last transient error is raised, with `tries` set to the tries
    made. Anything else is raised at once. The budget bounds the waiting, not the calls: each call
    needs its own timeout (Chapter 1's client gives up after 300 seconds)."""
    plan, waited = waits(attempts, base, cap, rng), 0.0
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if not transient(e) or i == attempts - 1 or waited + plan[i] > budget:
                e.tries = i + 1
                raise
            if log is not None:
                log.append({"attempt": i + 1, "error": f"{type(e).__name__}: {e}", "wait": round(plan[i], 3)})
            sleep(plan[i])
            waited += plan[i]


class Flaky:
    """Wrap a tool or a client so a seeded share `p` of its calls fail with a TransientError.

    Whether a call fails is drawn from the seed, the call's number and the attempt, not from one
    stream: a resumed run, which replays its first calls instead of making them, meets the same
    failures from then on as the run that was never stopped. `at()` gives the call's number (in
    run.py, the journal's); without it, calls are numbered in the order they are made."""

    def __init__(self, p, seed, at=None):
        self.p, self.seed, self.at, self.failures = p, seed, at, 0
        self.made, self.tries = 0, {}

    def __call__(self):
        n = self.at() if self.at else self.made
        self.made += 1
        k = self.tries[n] = self.tries.get(n, 0) + 1
        if random.Random(f"{self.seed}/{n}/{k}").random() < self.p:
            self.failures += 1
            raise TransientError("service unavailable (injected)")

    def tool(self, fn):
        def call(**args):
            self()
            return fn(**args)
        return call

    def client(self, client):
        flaky = self

        class FlakyClient:
            def chat(self, messages, tools=None):
                flaky()
                return client.chat(messages, tools)
        return FlakyClient()


def retrying_tools(tools, log=None, **kw):
    """A tools dict whose calls retry transient errors; when the retries run out, the model gets
    a ToolError that says so, instead of a stack trace it can't act on."""
    def wrap(fn):
        def call(**args):
            try:
                return retry(lambda: fn(**args), log=log, **kw)
            except Exception as e:
                if transient(e):
                    n = getattr(e, "tries", kw.get("attempts", 4))
                    raise ToolError("unavailable", f"the call failed {n} time{'s' if n > 1 else ''} ({e})",
                                    "It may work later. Don't treat this as an empty result.")
                raise
        return call
    return {name: (wrap(fn), spec) for name, (fn, spec) in tools.items()}


class RetryingClient:
    """A chat client that retries transient errors. A failure after the retries ends the run, as in Chapter 1."""

    def __init__(self, client, log=None, **kw):
        self.client, self.log, self.kw = client, log, kw

    def chat(self, messages, tools=None):
        return retry(lambda: self.client.chat(messages, tools), log=self.log, **self.kw)
