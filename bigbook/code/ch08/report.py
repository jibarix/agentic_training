"""Turn the chapter's run into its tables and numbers (bigbook/build/ch08_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)

Shares are means over tasks of each task's share of runs, as in Chapter 3; pass^k uses every seed of
a task. Paired comparisons need two tasks or more and print "--" with fewer; the clustered ones group
the tasks by their kind (meals, mileage, full, billed, chain_meals, chain_lodging). Tokens and calls
are also given as multiples of the single agent's. Correctness comes from the run's
adjudication.json where a person labelled a run, else the scorer.

The pipeline's parts are checked against the handbook trip by trip (tasks.json's per_trip): did
the split name the right trips, and did each trip's parts add up to its amount? These are
diagnostics, not causes: a trip's amount can be wrong because the sub-question asked for the wrong
expenses or because the worker erred, and only the traces tell which.
The chapter's numbers are written only from a complete run of the chapter's design: all 36 tasks,
all three arms, five seeds, the A2A part, every planned row present once and nothing else.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path
from statistics import fmean, median

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
import stats                                             # noqa: E402  Chapter 3's statistics

BUILD = HERE.parent.parent / "build"
CONDS = ("single", "orchestrator", "pipeline")
KEYS = {"single": "Single", "orchestrator": "Orch", "pipeline": "Pipe"}
SETS = {"decomposable": "Dec", "sequential": "Seq"}
PAIRS = {"OrchSingle": ("orchestrator", "single"), "PipeSingle": ("pipeline", "single"),
         "PipeOrch": ("pipeline", "orchestrator")}
SEEDS = 5
MAX_WORKERS = 8                                          # strategies.MAX_WORKERS
MACROS = ([k + m for k in KEYS.values() for m in ("Right", "Runs", "Mean", "SE", "HatK", "Tokens", "TokensX",
                                                   "Calls", "CallsX", "Agents", "Seconds", "Unanswered")
                                                   + tuple(s + "Mean" for s in SETS.values())]
          + [p + s + m for p in PAIRS for s in ("",) + tuple(SETS.values()) for m in ("Diff", "Lo", "Hi", "LoCl", "HiCl")]
          + ["Seeds", "Tasks",
             "OrchDelegations", "OrchWorkerFailed", "OrchLimit", "OrchNoDelegation",
             "PipeSplitErrors", "PipePartFailed", "PipeRetried", "PipeParts", "PipePartsRight",
             "PipeRightTrips", "PipeWrong", "PipeWrongSplit", "PipeWrongPart", "PipeWrongOther",
             "WireRuns", "WireRight", "WireCleanRight", "WireRequests", "WirePosts", "WireErrors", "WireBytes",
             "WireTokens", "WireCleanTokens"])
PLACEHOLDER = "\\multicolumn{8}{c}{(the run has not been made yet)} \\\\\n"


def tasks():
    return {t["id"]: t for t in json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))}


def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:                               # a torn last row is ignored
            break
    return rows


def load(run):
    rows = read_rows(HERE / run / "traces.jsonl")
    adj = HERE / run / "adjudication.json"
    labels = {}
    if adj.exists():
        labels = {(a["part"], a["cond"], a["id"], a["seed"]): a["label"]
                  for a in json.loads(adj.read_text(encoding="utf-8"))["labels"]}
    for r in rows:
        r["ok"] = labels.get((r["part"], r["cond"], r["id"], r["seed"]), r["ok"])
    return rows


def planned(T):
    """Every (part, seed, id, cond) the chapter's design runs, as experiment.plan() makes them."""
    keys = {("compare", s, t, c) for s in range(1, SEEDS + 1) for t in T for c in CONDS}
    seen = {}
    for t in T.values():
        seen[t["cluster"]] = seen.get(t["cluster"], 0) + 1
        if seen[t["cluster"]] <= 2:
            keys.add(("a2a", 1, t["id"], "orchestrator"))
    return keys


def not_the_design(run, rows):
    """Why a run is not the chapter's complete design, or None."""
    s = json.loads((HERE / run / "manifest.json").read_text())["settings"]
    T = tasks()
    for k, want in (("seeds", list(range(1, SEEDS + 1))), ("tasks", list(T)), ("conds", list(CONDS)),
                    ("parts", ["compare", "a2a"])):
        if s.get(k) != want:
            return f"its {k} are {s.get(k)}, not the chapter's {want}"
    return rows_not_the_design(rows, planned(T))


def rows_not_the_design(rows, want):
    keys = [(r["part"], r["seed"], r["id"], r["cond"]) for r in rows]
    if len(keys) != len(set(keys)):
        return f"it has {len(keys) - len(set(keys))} duplicate rows"
    missing, extra = want - set(keys), set(keys) - want
    if missing or extra:
        return f"it lacks {len(missing)} planned runs and has {len(extra)} unplanned ones"
    return None


def runs_of(rows, cond, part="compare", only=None):
    out = {}
    for r in rows:
        if r["part"] == part and r["cond"] == cond and (only is None or only(r)):
            out.setdefault(r["id"], []).append(1 if r["ok"] is True else 0)
    return out


def pct(v):
    return f"{100 * v:.1f}"


def parts_check(r, t):
    """For a pipeline row on a decomposable task: (did the parts name exactly the task's trips?,
    {trip: did its parts' amounts add up to the handbook's amount for it?}). Parts are grouped by the
    trip they name, so a split into one part per trip and one per expense and trip are both checked;
    a part that names no trip is checked as the trip "". Every trip the split named is counted: one
    with a part that failed or was never run is not right. A wrong amount can come from the
    sub-question as well as from the worker: telling which needs the traces."""
    trips = {p["trip"] for p in r["info"].get("parts") or []}
    results = r["info"].get("results", [])
    asked = {}
    for p in r["info"].get("parts") or []:
        asked[p["trip"]] = asked.get(p["trip"], 0) + 1
    sums, done = {x: Decimal(0) for x in trips}, {x: 0 for x in trips}
    for p in results:
        if p["amount"] is not None:
            sums[p["trip"]] = sums.get(p["trip"], Decimal(0)) + Decimal(p["amount"])
            done[p["trip"]] = done.get(p["trip"], 0) + 1
    ok = {x: x in t["per_trip"] and done[x] >= asked.get(x, 0) and v == Decimal(t["per_trip"][x])
          for x, v in sums.items()}
    return trips == set(t["trips"]), ok


def render(rows):
    T = tasks()
    nums, table = {}, []
    clusters = {t: T[t]["cluster"] for t in T}
    compare = [r for r in rows if r["part"] == "compare"]
    base = {}
    for c in CONDS:
        runs = runs_of(rows, c)
        if not runs:
            continue
        rs = [r for r in compare if r["cond"] == c]
        x = list(stats.per_task(runs).values())
        k = KEYS[c]
        n_seeds = min(len(v) for v in runs.values())
        tok, calls = fmean(r["tokens"] for r in rs), fmean(r["calls"] for r in rs)
        if c == "single":
            base = {"tokens": tok, "calls": calls}
        nums |= {f"{k}Right": sum(map(sum, runs.values())), f"{k}Runs": len(rs), f"{k}Mean": pct(fmean(x)),
                 f"{k}SE": pct(stats.se(x)) if len(x) > 1 else "--",
                 f"{k}HatK": pct(fmean(stats.pass_hat_k(len(v), sum(v), n_seeds) for v in runs.values())),
                 f"{k}Tokens": f"{tok:,.0f}", f"{k}Calls": f"{calls:.1f}",
                 f"{k}Agents": f"{fmean(r['agents'] for r in rs):.1f}",
                 f"{k}Seconds": f"{median(r['seconds'] for r in rs):.0f}",
                 f"{k}Unanswered": sum(r["status"] != "answered" for r in rs)}
        if base:
            nums |= {f"{k}TokensX": f"{tok / base['tokens']:.1f}", f"{k}CallsX": f"{calls / base['calls']:.1f}"}
        for s, sk in SETS.items():
            sub = runs_of(rows, c, only=lambda r, s=s: r["set"] == s)
            if sub:
                nums[f"{k}{sk}Mean"] = pct(fmean(stats.per_task(sub).values()))
        table.append(f"{c} & {nums[k + 'Right']}/{len(rs)} & {nums[k + 'Mean']} ({nums[k + 'SE']}) & "
                     f"{nums.get(k + 'DecMean', '--')} & {nums.get(k + 'SeqMean', '--')} & {nums[k + 'HatK']} & "
                     f"{nums[k + 'Tokens']} ({nums.get(k + 'TokensX', '--')}$\\times$) & "
                     f"{nums[k + 'Calls']} ({nums.get(k + 'CallsX', '--')}$\\times$) \\\\")
    for name, (a, b) in PAIRS.items():
        for s, sk in (("", None),) + tuple((v, k) for k, v in SETS.items()):
            only = None if sk is None else (lambda r, sk=sk: r["set"] == sk)
            p, q = runs_of(rows, a, only=only), runs_of(rows, b, only=only)
            if len(p) > 1 and len(q) > 1:
                cmp, cl = stats.compare(p, q), stats.compare(p, q, clusters)
                nums |= {f"{name}{s}Diff": pct(cmp["diff"]), f"{name}{s}Lo": pct(cmp["ci"][0]),
                         f"{name}{s}Hi": pct(cmp["ci"][1]), f"{name}{s}LoCl": pct(cl["ci"][0]),
                         f"{name}{s}HiCl": pct(cl["ci"][1])}
    orch = [r for r in compare if r["cond"] == "orchestrator"]
    if orch:
        d = [r["info"].get("delegations", []) for r in orch]
        nums |= {"OrchDelegations": f"{fmean(map(len, d)):.1f}",
                 "OrchWorkerFailed": sum(x["state"] != "completed" for ds in d for x in ds),
                 "OrchLimit": sum(len(ds) >= MAX_WORKERS for ds in d),
                 "OrchNoDelegation": sum(not ds for ds in d)}
    pipe = [r for r in compare if r["cond"] == "pipeline"]
    if pipe:
        nums |= {"PipeSplitErrors": sum(r["status"] == "split_error" for r in pipe),
                 "PipePartFailed": sum(r["status"] == "part_failed" for r in pipe),
                 "PipeRetried": sum(len(r["info"].get("retried", [])) for r in pipe)}
        dec = [r for r in pipe if r["set"] == "decomposable" and r["info"].get("parts")]
        checks = [(r, *parts_check(r, T[r["id"]])) for r in dec]
        wrong = [(r, rt, ok) for r, rt, ok in checks if r["ok"] is not True and r["status"] == "answered"]
        nums |= {"PipeParts": sum(len(ok) for _, _, ok in checks),
                 "PipePartsRight": sum(sum(ok.values()) for _, _, ok in checks),
                 "PipeRightTrips": sum(rt for _, rt, _ in checks),
                 "PipeWrong": len(wrong),
                 "PipeWrongSplit": sum(not rt for _, rt, _ in wrong),
                 "PipeWrongPart": sum(rt and not all(ok.values()) for _, rt, ok in wrong),
                 "PipeWrongOther": sum(rt and all(ok.values()) for _, rt, ok in wrong)}
    if compare:
        nums |= {"Seeds": len({r["seed"] for r in compare}), "Tasks": len({r["id"] for r in compare})}
    wire = [r for r in rows if r["part"] == "a2a"]
    if wire:
        clean = {r["id"]: r for r in orch if r["seed"] == 1}
        same = [clean[r["id"]] for r in wire if r["id"] in clean]
        nums |= {"WireRuns": len(wire), "WireRight": sum(r["ok"] is True for r in wire),
                 "WireCleanRight": sum(r["ok"] is True for r in same) if len(same) == len(wire) else "--",
                 "WireRequests": sum(r["wire"]["requests"] for r in wire),
                 "WireErrors": sum(r["wire"]["errors"] for r in wire),
                 "WirePosts": sum(r["wire"]["posts"] for r in wire),
                 "WireBytes": f"{fmean(r['wire']['json_bytes'] for r in wire):,.0f}",
                 "WireTokens": f"{fmean(r['tokens'] for r in wire):,.0f}",
                 "WireCleanTokens": f"{fmean(r['tokens'] for r in same):,.0f}" if same else "--"}
    return table, nums


def files(table, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    return {"ch08_compare.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch08_numbers.tex": "".join(f"\\newcommand{{\\cheight{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


def write(table, nums):
    BUILD.mkdir(exist_ok=True)
    for name, text in files(table, nums).items():
        (BUILD / name).write_text(text, encoding="utf-8")


def book_run():
    """The run book.json names, if it is the complete design; else None (placeholders)."""
    run = json.loads((HERE / "book.json").read_text()).get("run")
    if run:
        why = not_the_design(run, load(run))
        if why:
            sys.exit(f"book.json names {run}, but {why}")
    return run


def main(argv):
    if argv:
        table, nums = render(load(argv[0]))
        print("\n".join(table))
        print(json.dumps(nums, indent=1))
        why = not_the_design(argv[0], load(argv[0]))
        print("not the chapter's design: " + why if why else "the chapter's complete design")
        return
    run = book_run()
    write(*(render(load(run)) if run else ([], {})))


if __name__ == "__main__":
    main(sys.argv[1:])
