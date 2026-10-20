"""Replay the full-context calls of Chapter 4's run as N agents at once against a provider's rate limits.

Usage: python ratelimit.py           (prints the replay for 1, 10, 30 and 100 agents)

No model is called. Each agent replays RUNS_EACH of the run's full-context runs back to back,
call by call, with each call's own tokens and seconds and the run's time outside the model spread
evenly after its calls; the agents start at seeded random times in the first minute. Three token
buckets stand for the provider's limits on requests, input tokens and output tokens per minute.
Anthropic describes its limits as a token bucket but doesn't publish a bucket's size, so the sizes
are assumptions: by default each holds a minute's worth and refills continuously; `per=1` holds one
second's worth instead, a sensitivity scenario suggested by Anthropic's remark that a rate of 60 a
minute "might be enforced as 1 request per second", not a documented capacity. A call goes ahead
only if all three buckets hold enough; else it gets a 429 and
  wait    : waits for the time the buckets need (what a retry-after header gives), then tries again,
            with no limit on its tries or its waiting
  backoff : ignores the header and waits as Chapter 5's retry does (capped exponential with full
            jitter: 4 tries, so three waits drawn from [0, 1], [0, 2] and [0, 4] seconds), and the
            agent stops if the tries run out
  honour  : waits the header's time plus up to 10% jitter, at most 4 tries and 60 seconds of
            waiting per call, and the agent stops if either runs out
The output tokens are charged when the call starts, though the provider counts them as they are
made: a call is refused here sooner than it would be there.

Input tokens are counted two ways: every prompt token, or the cache-aware way Anthropic counts
them for its newer models, where tokens read from the cache don't count (the ideal hosted cache
of analysis.py, which reads at most the previous call's prompt, with the model's minimum). The local server's seconds stand in for a provider's, which
are likely shorter: shorter calls send the same tokens in less time, so the replay understates the
pressure on the limits.
"""
import heapq
import json
import random
import sys
from pathlib import Path
from statistics import median

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch01"))               # Chapter 5's faults raises Chapter 1's ToolError
sys.path.append(str(HERE.parent / "ch05"))
import analysis as A                                     # noqa: E402
from faults import waits                                 # noqa: E402  Chapter 5's backoff

RUNS_EACH = 5
# Anthropic's Start tier on the date of analysis.PRICES: requests, input tokens, output tokens per minute.
LIMITS = {"Claude Sonnet 5.5": (1_000, 2_000_000, 400_000), "Claude Fable 5.1": (1_000, 500_000, 100_000)}
LEAST = {"Claude Sonnet 5.5": 512, "Claude Fable 5.1": 512}   # the shortest prompt each will cache


class Bucket:
    """Holds up to `size`, refilled at `rate` per second; starts full."""

    def __init__(self, size, rate):
        self.size, self.rate, self.level, self.t = size, rate, size, 0.0

    def refill(self, t):
        self.level = min(self.size, self.level + (t - self.t) * self.rate)
        self.t = t

    def wait(self, n):
        """Seconds until the bucket holds n (it has been refilled to now); inf if it never can."""
        return float("inf") if n > self.size else max(0.0, (n - self.level) / self.rate)


def counted(cs, least, cache):
    """The input tokens a limit counts for each call: all of them, or those not read from the cache."""
    out, written = [], False
    for c in cs:
        if cache and c["prompt"] >= least:
            out.append(c["prompt"] - (c["cached"] if written else 0))
            written = True
        else:
            out.append(c["prompt"])
            written = False
    return out


def jobs(rows, least, cache, runs_each=RUNS_EACH, agents=1):
    """For each agent, its calls in order: (input counted, output, seconds, then a gap), and the
    seconds its runs took in the original run."""
    full = sorted((r for r in rows if r["cond"] == "full" and A.calls(r)), key=lambda r: (r["seed"], r["id"]))
    out = []
    for j in range(agents):
        seq, took = [], 0.0
        for k in range(runs_each):
            r = full[(j * runs_each + k) % len(full)]
            cs = A.calls(r)
            gap = max(0.0, r["seconds"] - sum(c["seconds"] for c in cs)) / len(cs)
            seq += [(n, c["completion"], c["seconds"], gap) for n, c in zip(counted(cs, least, cache), cs)]
            took += r["seconds"]
        out.append((seq, took))
    return out


def replay(work, limits, mode="wait", per=60, seed=1):
    """Run the agents' calls against the limits. "stopped" counts agents a call that could not get
    through stopped (its tries or its waiting budget ran out, or it is larger than a bucket);
    "too_large" counts the agents stopped at a call larger than a bucket, and "oversized" every
    call in the work that is larger than any bucket, reached or not, with "oversized_in" and
    "oversized_out" those larger than the input or the output bucket. "out_of_tries" and
    "out_of_time" split the stops of the bounded policies: the tries ran out, or the next wait
    would have taken the honouring policy past its 60 seconds; "time_left" counts the honouring
    policy's stops out of tries whose next wait would still have fitted in the 60 seconds."""
    rpm, itpm, otpm = limits
    buckets = [Bucket(x * per / 60, x / 60) for x in (rpm, itpm, otpm)]
    rng = random.Random(seed)
    queue = [(rng.uniform(0, 60), j, 0, 0, 0.0) for j in range(len(work))]   # (time, agent, call, try, waited)
    heapq.heapify(queue)
    start = {j: t for t, j, *_ in queue}
    plans = {}
    every = [c for seq, _ in work for c in seq]
    out = {"agents": len(work), "calls": 0, "refused": 0, "stopped": 0, "too_large": 0, "waited": 0.0,
           "oversized": sum(any(n > b.size for b, n in zip(buckets, (1, c[0], c[1]))) for c in every),
           "oversized_in": sum(c[0] > buckets[1].size for c in every),
           "oversized_out": sum(c[1] > buckets[2].size for c in every),
           "out_of_tries": 0, "out_of_time": 0, "time_left": 0}
    ended = {}
    while queue:
        t, j, i, tries, waited = heapq.heappop(queue)
        seq, _ = work[j]
        if i == len(seq):
            ended[j] = t
            continue
        n_in, n_out, secs, gap = seq[i]
        need = (1, n_in, n_out)
        for b in buckets:
            b.refill(t)
        w = max(b.wait(n) for b, n in zip(buckets, need))
        if w <= 1e-9:
            for b, n in zip(buckets, need):
                b.level -= n
            out["calls"] += 1
            heapq.heappush(queue, (t + secs + gap, j, i + 1, 0, 0.0))
            continue
        out["refused"] += 1
        if w == float("inf"):
            out["too_large"] += 1
            out["stopped"] += 1
            continue
        if mode == "backoff":                            # the header is ignored
            plan = plans.setdefault((j, i), waits(4, 1.0, 30.0, rng))
            if tries == len(plan):
                out["stopped"] += 1
                out["out_of_tries"] += 1
                continue
            w = plan[tries]
        elif mode == "honour":                           # the header is a minimum, plus jitter
            w *= 1 + rng.uniform(0, 0.1)
            if tries == 3 or waited + w > 60.0:
                out["stopped"] += 1
                out["out_of_tries" if tries == 3 else "out_of_time"] += 1
                out["time_left"] += tries == 3 and waited + w <= 60.0   # the next wait would have fitted
                continue
        out["waited"] += w
        heapq.heappush(queue, (t + w, j, i, tries + 1, waited + w))
    slow = [(ended[j] - start[j]) / work[j][1] for j in ended]
    out["slowdown_p50"] = median(slow) if slow else None
    out["slowdown_max"] = max(slow) if slow else None
    out["minutes"] = (max(ended.values()) - min(start.values())) / 60 if ended else None
    return out


def table(rows, ns=(1, 10, 30, 100), seed=1):
    """{(model, cache, mode, per, n): replay result} for the chapter's grid."""
    out = {}
    for model, lim in LIMITS.items():
        for cache in (False, True):
            for n in ns:
                work = jobs(rows, LEAST[model], cache, agents=n)
                for mode, per in (("wait", 60), ("backoff", 60), ("honour", 60), ("wait", 1)):
                    out[model, cache, mode, per, n] = replay(work, lim, mode, per, seed)
    return out


def main():
    rows = A.ch04_rows()
    for k, v in table(rows).items():
        print(json.dumps({"model": k[0], "cache": k[1], "mode": k[2], "per": k[3], "agents": k[4]}
                         | {a: round(b, 2) if isinstance(b, float) else b for a, b in v.items()}))


if __name__ == "__main__":
    main()
