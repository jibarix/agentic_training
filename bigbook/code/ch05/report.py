"""Turn the chapter's run into its tables and numbers (bigbook/build/ch05_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)
Standard errors and paired comparisons need two tasks or more; with fewer they print "--".
Seconds are the median over runs that were never interrupted (a resumed run's clock covers only
its last part). Correctness comes from the run's adjudication.json where a person labelled a run, else the scorer.
"""
import json
import sys
from pathlib import Path
from statistics import fmean, median

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
sys.path.append(str(HERE.parent / "ch01"))           # the ledger raises Chapter 1's ToolError
import stats                                             # noqa: E402  Chapter 3's statistics
from durable import read_jsonl                           # noqa: E402
from ledger import Ledger                                # noqa: E402

BUILD = HERE.parent.parent / "build"
CONDS = ("agent", "plan", "workflow")
KEYS = {"agent": "Agent", "plan": "Plan", "workflow": "Workflow"}
PAIRS = {"PlanAgent": ("plan", "agent"), "WorkflowAgent": ("workflow", "agent"), "WorkflowPlan": ("workflow", "plan")}
MACROS = ([k + m for k in KEYS.values() for m in ("Right", "Runs", "Mean", "SE", "HatK", "Tokens", "Calls",
                                                   "Seconds", "Unanswered")]
          + [p + m for p in PAIRS for m in ("Diff", "SE", "Lo", "Hi", "SECl", "LoCl", "HiCl")]
          + ["Seeds", "Tasks", "Replans", "RunsReplanned", "ReplannedRight", "GaveUp", "PlanErrors",
             "Routed", "StepFailed", "TripRetries", "Claims", "ClaimsExpected", "RepeatedKeys",
             "CrashRuns", "CrashSame", "CrashRight", "CrashCleanRight", "CrashLiveShare", "CrashReplayed",
             "CrashClaims", "Injected", "FaultCalls"]
          + [f"Fault{KEYS[c]}{m}" for c in ("agent", "workflow") for m in ("Right", "CleanRight", "Diff", "Lo", "Hi")])
PLACEHOLDER = "\\multicolumn{7}{c}{(the run has not been made yet)} \\\\\n"


def load(run):
    rows = read_jsonl(HERE / run / "traces.jsonl", repair=False)[0]   # reads only: a torn last row is ignored
    adj = HERE / run / "adjudication.json"
    labels = {}
    if adj.exists():
        labels = {(a["part"], a["cond"], a["id"], a["seed"]): a["label"]
                  for a in json.loads(adj.read_text(encoding="utf-8"))["labels"]}
    for r in rows:
        r["ok"] = labels.get((r["part"], r["cond"], r["id"], r["seed"]), r["ok"])
    return rows


def runs_of(rows, cond, part="compare", seed=None):
    out = {}
    for r in rows:
        if r["part"] == part and r["cond"] == cond and (seed is None or r["seed"] == seed):
            out.setdefault(r["id"], []).append(1 if r["ok"] is True else 0)
    return out


def seconds(rs):
    s = [r["seconds"] for r in rs if not r.get("interrupted")]
    return f"{median(s):.0f}" if s else "--"


def pct(v):
    return f"{100 * v:.1f}"


def render(rows, run=None):
    nums, table = {}, []
    clusters = {r["id"]: r["cluster"] for r in rows}
    compare = [r for r in rows if r["part"] == "compare"]
    for c in CONDS:
        runs = runs_of(rows, c)
        if not runs:
            continue
        rs = [r for r in compare if r["cond"] == c]
        x = list(stats.per_task(runs).values())
        k = KEYS[c]
        n_seeds = min(len(v) for v in runs.values())
        hat = fmean(stats.pass_hat_k(len(v), sum(v), n_seeds) for v in runs.values())
        nums |= {f"{k}Right": sum(map(sum, runs.values())), f"{k}Runs": len(rs), f"{k}Mean": pct(fmean(x)),
                 f"{k}SE": pct(stats.se(x)) if len(x) > 1 else "--", f"{k}HatK": pct(hat),
                 f"{k}Tokens": f"{fmean(r['tokens'] for r in rs):,.0f}",
                 f"{k}Calls": f"{fmean(r['calls'] for r in rs):.1f}",
                 f"{k}Seconds": seconds(rs),
                 f"{k}Unanswered": sum(r["amount"] is None for r in rs)}
        table.append(f"{c} & {nums[k + 'Right']}/{len(rs)} & {nums[k + 'Mean']} ({nums[k + 'SE']}) & "
                     f"{nums[k + 'HatK']} & {nums[k + 'Tokens']} & {nums[k + 'Calls']} & {nums[k + 'Seconds']} \\\\")
    for name, (a, b) in PAIRS.items():
        if len(runs_of(rows, a)) > 1 and len(runs_of(rows, b)) > 1:
            p, q = runs_of(rows, a), runs_of(rows, b)
            cmp, cl = stats.compare(p, q), stats.compare(p, q, clusters)
            nums |= {f"{name}Diff": pct(cmp["diff"]), f"{name}SE": pct(cmp["se"]), f"{name}Lo": pct(cmp["ci"][0]),
                     f"{name}Hi": pct(cmp["ci"][1]), f"{name}SECl": pct(cl["se"]), f"{name}LoCl": pct(cl["ci"][0]),
                     f"{name}HiCl": pct(cl["ci"][1])}
    plans = [r for r in compare if r["cond"] == "plan"]
    if plans:
        re_ = [r for r in plans if r["info"].get("replans")]
        nums |= {"Replans": sum(r["info"].get("replans", 0) for r in plans), "RunsReplanned": len(re_),
                 "ReplannedRight": sum(r["ok"] is True for r in re_),
                 "GaveUp": sum(r["status"] == "gave_up" for r in plans),
                 "PlanErrors": sum(r["status"] == "plan_error" for r in plans)}
    flows = [r for r in compare if r["cond"] == "workflow"]
    if flows:
        nums |= {"Routed": sum("routed" in r["info"] for r in flows),
                 "StepFailed": sum(r["status"] == "step_failed" for r in flows),
                 "TripRetries": sum(len(r["info"].get("retried", [])) for r in flows)}
    if compare:
        nums |= {"Seeds": len({r["seed"] for r in compare}), "Tasks": len({r["id"] for r in compare}),
                 "ClaimsExpected": sum(r["amount"] is not None and float(r["amount"]) > 0 for r in compare)}
    if run:
        keys = [c["key"] for c in Ledger(HERE / run / "ledger.jsonl").claims(repair=False)]
        nums |= {"Claims": len(keys), "RepeatedKeys": len(keys) - len(set(keys)),
                 "CrashClaims": len(Ledger(HERE / run / "ledger_crash.jsonl").claims(repair=False))}
    crash = [r for r in rows if r["part"] == "crash"]
    if crash:
        clean = {(r["id"], r["cond"]): r for r in compare if r["seed"] == 1}
        nums |= {"CrashRuns": len(crash), "CrashSame": sum(bool(r.get("same_answer")) for r in crash),
                 "CrashRight": sum(r["ok"] is True for r in crash),
                 "CrashCleanRight": sum(clean[(r["id"], r["cond"])]["ok"] is True for r in crash),
                 "CrashLiveShare": pct(sum(r["recovery_tokens"] for r in crash) / max(1, sum(r["clean_tokens"] for r in crash))),
                 "CrashReplayed": f"{fmean(r['cut_at'] for r in crash):.1f}"}
    faults = [r for r in rows if r["part"] == "faults"]
    if faults:
        nums |= {"Injected": sum(r["injected"] for r in faults), "FaultCalls": sum(r["tool_calls"] for r in faults)}
        for c in ("agent", "workflow"):
            f, base = runs_of(rows, c, "faults"), runs_of(rows, c, "compare", seed=1)
            if f and base:
                base = {t: base[t] for t in f}
                k = "Fault" + KEYS[c]
                nums |= {f"{k}Right": sum(map(sum, f.values())), f"{k}CleanRight": sum(map(sum, base.values()))}
                if len(f) > 1:
                    cmp = stats.compare(f, base)
                    nums |= {f"{k}Diff": pct(cmp["diff"]), f"{k}Lo": pct(cmp["ci"][0]), f"{k}Hi": pct(cmp["ci"][1])}
    return table, nums


def files(table, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    return {"ch05_compare.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch05_numbers.tex": "".join(f"\\newcommand{{\\chfive{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


def write(table, nums):
    BUILD.mkdir(exist_ok=True)
    for name, text in files(table, nums).items():
        (BUILD / name).write_text(text, encoding="utf-8")


def main(argv):
    if argv:
        table, nums = render(load(argv[0]), argv[0])
        print("\n".join(table))
        print(json.dumps(nums, indent=1))
        return
    run = json.loads((HERE / "book.json").read_text()).get("run")
    write(*(render(load(run), run) if run else ([], {})))


if __name__ == "__main__":
    main(sys.argv[1:])
