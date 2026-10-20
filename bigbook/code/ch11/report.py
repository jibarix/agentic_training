"""Turn the chapter's analysis and its probe run into its tables and numbers (bigbook/build/ch11_*).

Usage: python report.py                 (writes the build files: the analysis of the existing runs,
                                         and the probe run named in book.json; none yet: "--")
       python report.py results/<run>   (print the probe run's summary only; write nothing)

The analysis is always made, from Chapter 4's book run and Chapter 5's run (analysis.py,
ratelimit.py): no model is called. The probe's numbers are written only from a complete run of
its design: 30 tasks, two seeds, both arms, every planned row present once and nothing else.

Two cache shares, on purpose. The table's is token-weighted: an arm's cached prompt tokens over
all its prompt tokens. The paired difference averages each run's own share, both seeds of a task
averaged, then compares the arms task by task (stamped minus stable, plain and clustered by task
kind). The two need not agree. Prompt seconds are the server's time on the uncached prompt
tokens, per run. A count or duration the server didn't report is unknown, never zero: an arm's
share or prompt seconds is left as "--" if any of its runs lacks it, and so is a difference.
"""
import json
import sys
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
import analysis as A                                     # noqa: E402
import ratelimit as R                                    # noqa: E402
import stats                                             # noqa: E402  Chapter 3's statistics

BUILD = HERE.parent.parent / "build"
CONDS4 = {"full": "Full", "drop": "Drop", "compact": "Compact"}
CONDS5 = {"agent": "Agent", "plan": "Plan", "workflow": "Workflow"}
MODELS = {"Claude Sonnet 5.5": "Sonnet", "Claude Haiku 5.5": "HaikuNew", "Claude Haiku 4.5": "HaikuOld",
          "OpenAI gpt-6.1-sol": "Sol", "OpenAI gpt-6-luna": "Luna"}
SIGNALS = ("Right", "Runs", "PFifty", "PNinetyFive", "Errors", "PerMinute", "TokensSolved", "SecondsSolved")
ARMS = {"stable": "Stable", "stamped": "Stamped"}
DIFFS = {"Hit": "hit", "Prompt": "prompt_seconds", "Seconds": "seconds", "Right": "ok"}
MACROS = ([k + m for k in CONDS4.values() for m in SIGNALS + ("SatMax", "SatMedian")]
          + ["Five" + k + m for k in CONDS5.values() for m in SIGNALS]
          + ["FiveRows", "FiveKept", "FivePairs", "Rows", "Labelled", "FullRightScorer"]
          + ["Fit" + m for m in ("Calls", "Intercept", "New", "Reused", "Completion", "Rsq", "Prompt",
                                 "CompletionTokens", "Seconds")] + ["ReusedShare", "FitRatio"]
          + [k + m for k in MODELS.values() for m in ("Full", "FullCached", "Drop", "Compact", "CacheShare",
                                                      "Saving")]
          + [f"Rl{m}{c}{n}{v}" for m in ("Sonnet", "Fable") for c in ("Plain", "Cached")
             for n in ("Thirty", "Hundred") for v in ("Refused", "Slow", "Minutes", "Stopped", "Honoured")]
          + ["RlStrictSonnetSlow", "RlStrictFableLarge", "RlStrictFableCachedLarge", "RlStrictFableOversized",
             "RlStrictFableCachedOversized", "RlStrictFableOversizedIn", "RlStrictFableOversizedOut",
             "RlStrictFableCachedOversizedIn", "RlStrictFableCachedOversizedOut", "RlHonourOutOfTime", "RlHonourTimeLeft", "RlHonourStops",
             "RlRunsEach", "PricesDate"]
          + [a + m for a in ARMS.values() for m in ("Runs", "Right", "Hit", "Prompt", "Seconds", "Missing",
                                                    "Unknown", "Calls")]
          + ["Probe" + d + m for d in DIFFS for m in ("Diff", "Lo", "Hi", "LoCl", "HiCl")] + ["ProbeTasks"])
PLACEHOLDER = "\\multicolumn{6}{c}{(the run has not been made yet)} \\\\\n"
N_WORD = {30: "Thirty", 100: "Hundred"}


def pct(v):
    return f"{100 * v:.1f}"


def usd(v):
    return f"{v:.3f}" if v >= 0.01 else f"{v:.4f}"


def tasks():
    return {t["id"]: t for t in json.loads((A.CODE / "ch04" / "tasks_long.json").read_text(encoding="utf-8"))}


def signals(g, s):
    return {"Right": g["right"], "Runs": g["runs"], "PFifty": f"{g['p50']:.1f}", "PNinetyFive": f"{g['p95']:.1f}",
            "Errors": pct(g["errors"]), "PerMinute": f"{g['per_minute']:.1f}",
            "TokensSolved": f"{s['tokens']:,.0f}", "SecondsSolved": f"{s['seconds']:.0f}"}


def analysis_numbers():
    """The tables and numbers from the existing runs (no model, no probe)."""
    a = A.analyse()
    nums, sig, price, rl = {"PricesDate": A.PRICES_DATE, "RlRunsEach": R.RUNS_EACH}, [], [], []
    c4, c5 = a["ch04"], a["ch05"]
    nums |= {"Rows": c4["rows"], "Labelled": c4["labelled"], "FullRightScorer": c4["scorer_right"]["full"]}
    for c, k in CONDS4.items():
        g, s = c4["golden"][c], c4["per_solved"][c]
        nums |= {k + m: v for m, v in signals(g, s).items()}
        nums |= {k + "SatMax": pct(g["saturation_max"]), k + "SatMedian": pct(g["saturation_p50"])}
        sig.append(f"4 & {c} & {g['right']}/{g['runs']} & {nums[k + 'PFifty']} & {nums[k + 'PNinetyFive']} & "
                   f"{nums[k + 'Errors']} & {nums[k + 'TokensSolved']} & {nums[k + 'SecondsSolved']} \\\\")
    for c, k in CONDS5.items():
        g, s = c5["golden"][c], c5["per_solved"][c]
        nums |= {"Five" + k + m: v for m, v in signals(g, s).items()}
        sig.append(f"5 & {c} & {g['right']}/{g['runs']} & {nums['Five' + k + 'PFifty']} & "
                   f"{nums['Five' + k + 'PNinetyFive']} & {nums['Five' + k + 'Errors']} & "
                   f"{nums['Five' + k + 'TokensSolved']} & {nums['Five' + k + 'SecondsSolved']} \\\\")
    nums |= {"FiveRows": c5["rows"], "FiveKept": c5["kept"], "FivePairs": c5["pairs"]}
    f = c4["fit"]
    nums |= {"FitCalls": f["calls"], "FitIntercept": f"{f['intercept']:.2f}", "FitNew": f"{f['new_ms']:.3f}",
             "FitReused": f"{f['reused_ms']:.3f}", "FitCompletion": f"{f['completion_ms']:.1f}",
             "FitRsq": f"{f['r2']:.3f}", "FitPrompt": f"{f['prompt']:,}", "FitCompletionTokens": f"{f['completion']:,}",
             "FitSeconds": f"{f['model_seconds']:,.0f}", "ReusedShare": pct(f["reused_share"]),
             "FitRatio": f"{f['new_ms'] / f['reused_ms']:.1f}"}
    for m, k in MODELS.items():
        u = c4["usd"][m]
        nums |= {k + "Full": usd(u["full"]), k + "FullCached": usd(u["full_cached"]), k + "Drop": usd(u["drop"]),
                 k + "Compact": usd(u["compact"]), k + "CacheShare": pct(u["cache_share"]),
                 k + "Saving": pct(1 - u["full_cached"] / u["full"])}
        price.append(f"{m} & {A.PRICES[m][5]:,} & {nums[k + 'Full']} & {nums[k + 'FullCached']} & "
                     f"{nums[k + 'CacheShare']} & {nums[k + 'Drop']} & {nums[k + 'Compact']} \\\\")
    grid = R.table(A.ch04_rows())
    for (model, cache, mode, per, n), v in sorted(grid.items(), key=lambda kv: (kv[0][0] != "Claude Sonnet 5.5",
                                                                               kv[0][1], kv[0][4])):
        if per != 60 or mode != "wait":
            continue
        b, h = grid[model, cache, "backoff", 60, n], grid[model, cache, "honour", 60, n]
        short = "Sonnet" if "Sonnet" in model else "Fable"
        row = {"Refused": f"{v['refused']:,}", "Slow": f"{v['slowdown_p50']:.2f}", "Minutes": f"{v['minutes']:.1f}",
               "Stopped": f"{b['stopped']}", "Honoured": f"{h['stopped']}"}
        if n not in N_WORD:
            continue
        nums |= {f"Rl{short}{'Cached' if cache else 'Plain'}{N_WORD[n]}{m}": x for m, x in row.items()}
        rl.append(f"{model.replace('Claude ', '')} & {'cache-aware' if cache else 'every token'} & {n} & "
                  f"{row['Refused']} & {row['Slow']} & {row['Minutes']} & {b['refused']:,} & {row['Stopped']} & "
                  f"{row['Honoured']} \\\\")
    nums |= {"RlStrictSonnetSlow": f"{grid['Claude Sonnet 5.5', False, 'wait', 1, 100]['slowdown_p50']:.2f}",
             "RlStrictFableLarge": grid["Claude Fable 5.1", False, "wait", 1, 100]["too_large"],
             "RlStrictFableCachedLarge": grid["Claude Fable 5.1", True, "wait", 1, 100]["too_large"],
             "RlStrictFableOversized": f"{grid['Claude Fable 5.1', False, 'wait', 1, 100]['oversized']:,}",
             "RlStrictFableCachedOversized": f"{grid['Claude Fable 5.1', True, 'wait', 1, 100]['oversized']:,}"}
    for cache, name in ((False, "Fable"), (True, "FableCached")):
        g = grid["Claude Fable 5.1", cache, "wait", 1, 100]
        nums[f"RlStrict{name}OversizedIn"] = f"{g['oversized_in']:,}"
        nums[f"RlStrict{name}OversizedOut"] = f"{g['oversized_out']:,}"
    # the honouring policy's stops that ran out of waiting time rather than tries, over the whole grid
    nums["RlHonourOutOfTime"] = sum(g["out_of_time"] for k, g in grid.items() if k[2] == "honour")
    nums["RlHonourTimeLeft"] = sum(g["time_left"] for k, g in grid.items() if k[2] == "honour")
    nums["RlHonourStops"] = sum(g["stopped"] for k, g in grid.items() if k[2] == "honour")
    return {"signals": sig, "prices": price, "ratelimit": rl}, nums


# -- the probe -------------------------------------------------------------------------------------

def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:                               # a torn last row is ignored
            break
    return rows


def load(run):
    return read_rows(HERE / run / "traces.jsonl")


def planned(T, seeds=2):
    return {(s, t, a) for t in T for s in range(1, seeds + 1) for a in ARMS}


def not_the_design(run, rows):
    """Why a probe run is not the chapter's complete design, or None."""
    s = json.loads((HERE / run / "manifest.json").read_text())["settings"]
    T = tasks()
    if s.get("pilot") or s.get("seeds") != [1, 2] or s.get("tasks") != list(T):
        return "it is a pilot, or its seeds or tasks are not the chapter's"
    keys = [(r["seed"], r["id"], r["arm"]) for r in rows]
    if len(keys) != len(set(keys)):
        return f"it has {len(keys) - len(set(keys))} duplicate rows"
    missing, extra = planned(T) - set(keys), set(keys) - planned(T)
    if missing or extra:
        return f"it lacks {len(missing)} planned runs and has {len(extra)} unplanned ones"
    return None


def value(r, what):
    """One run's outcome; None if the server didn't report what it needs."""
    if what == "hit":
        if r["cached_tokens"] is None or r["prompt_tokens"] is None:
            return None
        return r["cached_tokens"] / r["prompt_tokens"] if r["prompt_tokens"] else 0.0
    if what == "ok":
        return 1.0 if r["ok"] is True else 0.0
    return r[what]


def probe_numbers(rows):
    """The probe's table rows and numbers; nothing if there are no rows."""
    if not rows:
        return [], {}
    T = tasks()
    nums, table = {"ProbeTasks": len({r["id"] for r in rows})}, []
    for arm, k in ARMS.items():
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        known = all(value(r, "hit") is not None for r in rs)
        hit = pct(sum(r["cached_tokens"] for r in rs) / max(1, sum(r["prompt_tokens"] for r in rs))) \
            if known else "--"
        prompt = f"{fmean(r['prompt_seconds'] for r in rs):.1f}" \
            if all(r["prompt_seconds"] is not None for r in rs) else "--"
        nums |= {k + "Runs": len(rs), k + "Right": sum(r["ok"] is True for r in rs), k + "Hit": hit,
                 k + "Prompt": prompt, k + "Seconds": f"{fmean(r['seconds'] for r in rs):.1f}",
                 k + "Missing": sum(r["cached_missing"] for r in rs),
                 k + "Unknown": sum(value(r, "hit") is None or r["prompt_seconds"] is None for r in rs),
                 k + "Calls": f"{fmean(r['calls'] for r in rs):.1f}"}
        table.append(f"{arm} & {nums[k + 'Right']}/{len(rs)} & {nums[k + 'Hit']} & {nums[k + 'Prompt']} & "
                     f"{nums[k + 'Seconds']} & {nums[k + 'Calls']} \\\\")
    clusters = {t: T[t]["cluster"] for t in T}
    for d, what in DIFFS.items():
        if any(value(r, what) is None for r in rows):
            continue                                     # unknown in some run: no difference is published
        a, b = {}, {}
        for r in rows:
            (a if r["arm"] == "stamped" else b).setdefault(r["id"], []).append(value(r, what))
        both = sorted(set(a) & set(b))
        if len(both) < 2:
            continue
        a, b = {t: a[t] for t in both}, {t: b[t] for t in both}
        cmp, cl = stats.compare(a, b), stats.compare(a, b, clusters)
        f = pct if what in ("hit", "ok") else (lambda v: f"{v:.1f}")
        nums |= {f"Probe{d}Diff": f(cmp["diff"]), f"Probe{d}Lo": f(cmp["ci"][0]), f"Probe{d}Hi": f(cmp["ci"][1]),
                 f"Probe{d}LoCl": f(cl["ci"][0]), f"Probe{d}HiCl": f(cl["ci"][1])}
    return table, nums


def numbers(rows):
    """The analysis's tables and numbers, and the probe's from its rows ([] before the run)."""
    tables, nums = analysis_numbers()
    ptable, pnums = probe_numbers(rows)
    return tables | {"probe": ptable}, nums | pnums


def files(tables, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    out = {f"ch11_{k}.tex": "\n".join(v) + "\n" if v else PLACEHOLDER for k, v in tables.items()}
    out["ch11_numbers.tex"] = "".join(f"\\newcommand{{\\celeven{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)
    return out


def write(tables, nums):
    BUILD.mkdir(exist_ok=True)
    for name, text in files(tables, nums).items():
        (BUILD / name).write_text(text, encoding="utf-8")


def book_run():
    """The probe run book.json names, if it is the complete design; else None (placeholders)."""
    run = json.loads((HERE / "book.json").read_text()).get("run")
    if run:
        why = not_the_design(run, load(run))
        if why:
            sys.exit(f"book.json names {run}, but {why}")
    return run


def main(argv):
    if argv:
        table, nums = probe_numbers(load(argv[0]))
        print("\n".join(table))
        print(json.dumps(nums, indent=1))
        why = not_the_design(argv[0], load(argv[0]))
        print("not the chapter's design: " + why if why else "the chapter's complete design")
        return
    run = book_run()
    write(*numbers(load(run) if run else []))


if __name__ == "__main__":
    main(sys.argv[1:])
