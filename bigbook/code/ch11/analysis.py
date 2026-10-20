"""What the book's existing runs cost, how long they took and what their latency is made of.

Usage: python analysis.py            (prints the analysis of Chapter 4's and Chapter 5's book runs)

No model is called. Everything here is read from runs already made: Chapter 4's long-task run
(the run its book.json names, with the person's labels) and Chapter 5's run, which book.json
does not name yet and which may be partial, so only the tasks and seeds that every one of its
conditions reached are compared, with the scorer's verdicts.

  calls      : a run's model calls, each split into new prompt tokens, reused prompt tokens and
               completion tokens (the reuse proxy below), with the tokens a hosted cache could read
  golden     : the four golden signals per condition: latency (p50, p95), errors (runs that ended
               without an answer), traffic (calls per minute of running) and saturation (the
               largest prompt as a share of the server's window)
  per_solved : tokens, seconds and dollars per task solved, at the dated prices in PRICES
  fit        : a least-squares fit of a call's seconds on its new, reused and completion tokens

Two measures of reuse, for two purposes:
  reused : the local latency proxy. The prompt of a call with the whole history starts with the
           prompt and the reply of the call before, which the server has just processed, so its
           first (previous prompt + previous completion) tokens are taken as reused, the rest new.
  cached : the hosted billing model. A hosted cache is written at the end of a request's input, and
           the reply was never sent as input, so a call can read at most the previous call's prompt.
Both are applied to the full-context condition only. Drop and compact keep the system prompt, the
tools and the task, but change the history behind the task at calls the call log doesn't mark one
by one (Chapter 4 counted them), so neither proxy is applied to them, and they are priced with no
cache: a no-cache scenario, not a bound in either direction (cache writes cost more than ordinary
input, and a prefix can miss the cache or fall below the minimum), nor a consequence of their code. The Chapter 4
server, Ollama's OpenAI-compatible endpoint, does not say which tokens it found in its cache.
"""
import importlib.util
import json
import sys
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).parent
CODE = HERE.parent
CH04_RUN, CH05_RUN = "results/2026-10-17-run1", "results/2026-10-18-run1"
WINDOW = 32_768                                          # the window both runs were served with
PRICES_DATE = "2026-10-18"
# USD per million tokens on PRICES_DATE: input, cache write (5-minute), cache read, output, and the
# shortest prompt the provider will cache. Anthropic's from its pricing and prompt-caching pages,
# OpenAI's from its pricing and prompt-caching guides (short-context rates). Prices change.
PRICES = {
    "Claude Sonnet 5.5": ("anthropic", 2.00, 2.50, 0.10, 10.00, 512),
    "Claude Haiku 5.5": ("anthropic", 0.10, 0.125, 0.01, 0.50, 512),
    "Claude Haiku 4.5": ("anthropic", 1.00, 1.25, 0.10, 5.00, 4096),
    "OpenAI gpt-6.1-sol": ("openai", 2.00, 2.50, 0.10, 10.00, 1024),
    "OpenAI gpt-6-luna": ("openai", 0.10, 0.125, 0.01, 0.50, 1024),
}


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ch04_rows(run=CH04_RUN):
    """Chapter 4's rows, with the person's labels where there are some (its report's load)."""
    sys.path.append(str(CODE / "ch03"))
    return _module("ch04_report", CODE / "ch04" / "report.py").load(run)


def ch04_labels(run=CH04_RUN):
    """How many runs a person labelled, and the scorer's own count of right runs per condition."""
    adj = json.loads((CODE / "ch04" / run / "adjudication.json").read_text(encoding="utf-8"))["labels"]
    right = {}
    for line in (CODE / "ch04" / run / "traces.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        right[r["cond"]] = right.get(r["cond"], 0) + (r["ok"] is True)
    return len(adj), right


def ch05_rows(run=CH05_RUN):
    """Chapter 5's rows, every part of its run; a torn last row is ignored."""
    rows = []
    for line in (CODE / "ch05" / run / "traces.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:                               # a torn last row is ignored
            break
    return rows


def percentile(xs, q):
    """The q-quantile with linear interpolation between ranks (numpy's default)."""
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def calls(row):
    """[{prompt, new, reused, cached, completion, summary, seconds}] for a run's model calls, or [] if its
    trace and call log don't line up or a count was estimated. A compacting run's step tokens
    include the summary's tokens (Chapter 4's ContextClient adds them), so they are taken out of
    the completion here and kept apart as `summary`."""
    steps = [s for s in row.get("trace", []) if s.get("type") == "model"]
    log = row.get("call_log", [])
    if len(steps) != len(log):
        return []
    out, prev = [], None
    for s, c in zip(steps, log):
        p, tot = c.get("prompt_tokens"), s.get("tokens")
        if p is None or tot is None or s.get("estimated"):
            return []
        summ = c.get("summary_tokens") or 0
        comp = tot - p - summ
        if comp < 0:
            return []
        full = prev is not None and row["cond"] == "full"
        new = max(p - prev[0] - prev[1], 0) if full else p
        out.append({"prompt": p, "new": new, "reused": p - new, "cached": min(prev[0], p) if full else 0,
                    "completion": comp, "summary": summ, "seconds": s["seconds"]})
        prev = (p, comp)
    return out


def golden(rows):
    """{cond: {...}}: the four golden signals and the run counts, one condition at a time."""
    out = {}
    for c in sorted({r["cond"] for r in rows}):
        rs = [r for r in rows if r["cond"] == c]
        secs = [r["seconds"] for r in rs]
        out[c] = {"runs": len(rs), "right": sum(r["ok"] is True for r in rs),
                  "p50": percentile(secs, 0.5), "p95": percentile(secs, 0.95),
                  "errors": sum(r["status"] != "answered" for r in rs) / len(rs),
                  "statuses": {s: sum(r["status"] == s for r in rs) for s in sorted({r["status"] for r in rs})},
                  "per_minute": 60 * sum(r["calls"] for r in rs) / sum(secs),
                  "saturation_max": max(r.get("max_prompt", 0) for r in rs) / WINDOW if "max_prompt" in rs[0]
                  else None,
                  "saturation_p50": percentile([r["max_prompt"] for r in rs], 0.5) / WINDOW
                  if "max_prompt" in rs[0] else None}
    return out


def price(cs, model, cache):
    """Dollars for a list of calls. Without a cache every prompt token is input. With the ideal
    cache, a call's prompt is cached only if it is at least the provider's minimum: the tokens a
    hosted cache could read (the previous prompt) are read if the call before was long enough to be
    written, and the rest are written. Summary tokens, whose split into prompt and completion isn't
    recorded, are priced as input, which understates them by whatever part was output."""
    _, inp, write, read, out, least = PRICES[model]
    usd, written = 0.0, False
    for c in cs:
        if not cache or c["prompt"] < least:
            usd += c["prompt"] * inp
            written = False
        else:
            hit = c["cached"] if written else 0
            usd += hit * read + (c["prompt"] - hit) * write
            written = True
        usd += c["completion"] * out + c["summary"] * inp
    return usd / 1e6


def per_solved(rows, cond, model=None, cache=False):
    """Tokens, seconds and (with a model) dollars per task solved, over all of a condition's runs:
    what the failed runs cost is charged to the ones that succeeded."""
    rs = [r for r in rows if r["cond"] == cond]
    right = sum(r["ok"] is True for r in rs)
    if not right:
        return None
    out = {"tokens": sum(r["tokens"] for r in rs) / right, "seconds": sum(r["seconds"] for r in rs) / right}
    if model:
        out["usd"] = sum(price(calls(r), model, cache) for r in rs) / right
    return out


def cache_share(rows, model):
    """The share of the full-context prompt tokens the ideal cache would read, with the model's minimum."""
    least, read, total = PRICES[model][5], 0, 0
    for r in rows:
        if r["cond"] != "full":
            continue
        written = False
        for c in calls(r):
            total += c["prompt"]
            if c["prompt"] >= least:
                read += c["cached"] if written else 0
                written = True
            else:
                written = False
    return read / total


def solve(A, b):
    """Gauss-Jordan elimination with partial pivoting: x with A x = b."""
    n = len(b)
    A, b = [row[:] for row in A], b[:]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p], b[i], b[p] = A[p], A[i], b[p], b[i]
        for r in range(n):
            if r != i:
                f = A[r][i] / A[i][i]
                A[r] = [a - f * x for a, x in zip(A[r], A[i])]
                b[r] -= f * b[i]
    return [b[i] / A[i][i] for i in range(n)]


def ols(X, y):
    """Least squares by the normal equations, and R squared."""
    k = len(X[0])
    beta = solve([[sum(x[i] * x[j] for x in X) for j in range(k)] for i in range(k)],
                 [sum(x[i] * v for x, v in zip(X, y)) for i in range(k)])
    m = fmean(y)
    res = sum((v - sum(a * b for a, b in zip(x, beta))) ** 2 for x, v in zip(X, y))
    return beta, 1 - res / sum((v - m) ** 2 for v in y)


def fit(rows):
    """A full-context call's seconds ~ a + b*new + c*reused + d*completion, over every call."""
    cs = [c for r in rows if r["cond"] == "full" for c in calls(r)]
    beta, r2 = ols([(1.0, c["new"], c["reused"], c["completion"]) for c in cs], [c["seconds"] for c in cs])
    prompt = sum(c["prompt"] for c in cs)
    return {"calls": len(cs), "intercept": beta[0], "new_ms": 1e3 * beta[1], "reused_ms": 1e3 * beta[2],
            "completion_ms": 1e3 * beta[3], "r2": r2, "reused_share": sum(c["reused"] for c in cs) / prompt,
            "prompt": prompt, "completion": sum(c["completion"] for c in cs),
            "model_seconds": sum(c["seconds"] for c in cs)}


CONDS5 = {"agent", "plan", "workflow"}


def common(rows):
    """Chapter 5's comparison rows for the (task, seed) pairs that all three conditions reached.
    The run's other parts (crash and fault runs) share tasks and seeds, so only part "compare" is
    read; a comparison key seen twice, or a condition outside the design, is refused."""
    rows = [r for r in rows if r.get("part") == "compare"]
    keys = [(r["id"], r["seed"], r["cond"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{len(keys) - len(set(keys))} duplicate comparison rows")
    if {r["cond"] for r in rows} - CONDS5:
        raise ValueError(f"conditions outside the design: {sorted({r['cond'] for r in rows} - CONDS5)}")
    have = {}
    for r in rows:
        have.setdefault((r["id"], r["seed"]), set()).add(r["cond"])
    keep = {k for k, v in have.items() if v == CONDS5}
    return [r for r in rows if (r["id"], r["seed"]) in keep], len(keep)


def analyse():
    """Everything the chapter reports from the existing runs, as one dict."""
    r4 = ch04_rows()
    r5, pairs = common(ch05_rows())
    labelled, scorer = ch04_labels()
    out = {"ch04": {"rows": len(r4), "golden": golden(r4), "fit": fit(r4), "labelled": labelled,
                    "scorer_right": scorer,
                    "calls_ok": sum(bool(calls(r)) for r in r4),
                    "per_solved": {c: per_solved(r4, c) for c in ("full", "drop", "compact")},
                    "usd": {m: {"full": per_solved(r4, "full", m)["usd"],
                                "full_cached": per_solved(r4, "full", m, cache=True)["usd"],
                                "drop": per_solved(r4, "drop", m)["usd"],
                                "compact": per_solved(r4, "compact", m)["usd"],
                                "cache_share": cache_share(r4, m)} for m in PRICES}},
           "ch05": {"rows": sum(r.get("part") == "compare" for r in ch05_rows()), "kept": len(r5), "pairs": pairs, "golden": golden(r5),
                    "per_solved": {c: per_solved(r5, c) for c in ("agent", "plan", "workflow")}}}
    return out


def main():
    print(json.dumps(analyse(), indent=1))


if __name__ == "__main__":
    main()
