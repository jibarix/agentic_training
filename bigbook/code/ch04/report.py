"""Turn the chapter's long-task run into its table and numbers (bigbook/build/ch04_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)
Correctness comes from the run's adjudication.json where a person labelled a run, else the scorer.
"""
import json
import sys
from pathlib import Path
from statistics import fmean, median

HERE = Path(__file__).parent
sys.path.append(str(HERE.parent / "ch03"))
import stats                                             # noqa: E402  Chapter 3's statistics

BUILD = HERE.parent.parent / "build"
CONDS = ("full", "drop", "mask", "compact")
KEYS = {"full": "Full", "drop": "Drop", "mask": "Mask", "compact": "Compact"}
PAIRS = {"CompactDrop": ("compact", "drop"), "CompactFull": ("compact", "full"), "DropFull": ("drop", "full")}
MACROS = ([k + m for k in KEYS.values() for m in ("Right", "Runs", "Mean", "SE", "Tokens", "Triggers",
                                                   "MaxSent", "Steps", "Over")]
          + [p + m for p in PAIRS for m in ("Diff", "SE", "Lo", "Hi", "N", "ClusterLo", "ClusterHi")]
          + ["Budget", "Seeds", "Tasks", "ValuesKept", "LinkedKept", "Summaries", "SummaryShare",
             "SummaryFailures", "SummaryUnknown", "Clusters", "SummaryView", "AgainNext", "AgainOf",
             "DropMoves", "DropLater", "CompactMoves", "CompactLater"])
PLACEHOLDER = "\\multicolumn{6}{c}{(the run has not been made yet)} \\\\\n"


def load(run):
    rows = [json.loads(l) for l in open(HERE / run / "traces.jsonl", encoding="utf-8")]
    adj = HERE / run / "adjudication.json"
    labels = {}
    if adj.exists():
        labels = {(a["cond"], a["id"], a["seed"]): a["label"] for a in json.loads(adj.read_text())["labels"]}
    for r in rows:
        r["ok"] = labels.get((r["cond"], r["id"], r["seed"]), r["ok"])
    return rows


def runs_of(rows, cond):
    out = {}
    for r in rows:
        if r["cond"] == cond:
            out.setdefault(r["id"], []).append(1 if r["ok"] is True else 0)
    return out


def moves(r):
    """Of a run's calls after the first, how many sent a history prefix (after the task) unlike the
    call before: for drop, a new cut; for compact, a new summary accepted at that call."""
    log = r["call_log"]
    if r["cond"] == "compact":
        at = {e["at"] for e in r["events"] if "summary" in e}
        return sum(c["history"] in at for c in log[1:]), max(0, len(log) - 1)
    off = [c["history"] - c["sent"] for c in log]
    return sum(a != b for a, b in zip(off, off[1:])), max(0, len(log) - 1)


def pct(v):
    return f"{100 * v:.1f}"


def render(rows):
    nums, table = {}, []
    for c in CONDS:
        runs = runs_of(rows, c)
        if not runs:
            continue
        rs = [r for r in rows if r["cond"] == c]
        x = list(stats.per_task(runs).values())
        k = KEYS[c]
        nums |= {f"{k}Right": sum(map(sum, runs.values())), f"{k}Runs": len(rs), f"{k}Mean": pct(fmean(x)),
                 f"{k}SE": pct(stats.se(x)), f"{k}Tokens": f"{fmean(r['tokens'] for r in rs):,.0f}",
                 f"{k}Triggers": f"{fmean(r['triggers'] for r in rs):.1f}",
                 f"{k}MaxSent": f"{median(r['max_sent'] for r in rs):,.0f}",
                 f"{k}Steps": f"{fmean(r['steps'] for r in rs):.1f}",
                 f"{k}Over": pct(sum(r["over_calls"] for r in rs) / max(1, sum(r["calls"] for r in rs)))}
        table.append(f"{c} & {nums[k + 'Right']}/{len(rs)} & {nums[k + 'Mean']} ({nums[k + 'SE']}) & "
                     f"{nums[k + 'Tokens']} & {nums[k + 'MaxSent']} & {nums[k + 'Triggers']} \\\\")
    for name, (a, b) in PAIRS.items():
        if runs_of(rows, a) and runs_of(rows, b):
            cmp = stats.compare(runs_of(rows, a), runs_of(rows, b))
            fam = stats.compare(runs_of(rows, a), runs_of(rows, b), {r["id"]: r["cluster"] for r in rows})
            nums |= {f"{name}Diff": pct(cmp["diff"]), f"{name}SE": pct(cmp["se"]), f"{name}Lo": pct(cmp["ci"][0]),
                     f"{name}Hi": pct(cmp["ci"][1]), f"{name}N": cmp["n"],
                     f"{name}ClusterLo": pct(fam["ci"][0]), f"{name}ClusterHi": pct(fam["ci"][1])}
    comp = [r for r in rows if r["cond"] == "compact"]
    cov = [c for r in comp for c in r["coverage"] if c["given"]]
    if comp:
        share = lambda m: pct(sum(c[m] for c in cov) / sum(c["given"] for c in cov)) if cov else "--"
        nums |= {"ValuesKept": share("values"), "LinkedKept": share("linked"),
                 "Summaries": sum(len(r["coverage"]) for r in comp),
                 "SummaryFailures": sum(r["summary_failures"] for r in comp),
                 "SummaryUnknown": sum(r["summary_unknown"] for r in comp),
                 "SummaryShare": pct(sum(r["summary_tokens"] for r in comp) / max(1, sum(r["tokens"] for r in comp)))}
        made = [e for r in comp for e in r["events"] if "summary" in e]          # accepted summaries
        nxt = []                                 # for each with a later call: did that call need one too?
        for r in comp:
            hist = [c["history"] for c in r["call_log"]]
            at = {e["at"] for e in r["events"] if "summary" in e}
            nxt += [b in at for a, b in zip(hist, hist[1:]) if a in at]   # a turn may add several messages
        if made:
            nums |= {"SummaryView": f"{median(e['tokens'] for e in made):,.0f}",
                     "AgainNext": sum(nxt), "AgainOf": len(nxt)}
    for c, k in (("drop", "Drop"), ("compact", "Compact")):
        m = [moves(r) for r in rows if r["cond"] == c]
        if m:
            nums |= {f"{k}Moves": sum(x for x, _ in m), f"{k}Later": sum(n for _, n in m)}
    nums |= {"Budget": f"{rows[0]['budget']:,}", "Seeds": len({r['seed'] for r in rows}),
             "Tasks": len({r['id'] for r in rows}), "Clusters": len({r['cluster'] for r in rows})}
    return table, nums


def files(table, nums):
    """The chapter's two build files as text; check.py compares them with build/."""
    return {"ch04_long.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch04_numbers.tex": "".join(f"\\newcommand{{\\chfour{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


def write(table, nums):
    BUILD.mkdir(exist_ok=True)
    for name, text in files(table, nums).items():
        (BUILD / name).write_text(text, encoding="utf-8")


def main(argv):
    if argv:
        table, nums = render(load(argv[0]))
        print("\n".join(table))
        print(json.dumps(nums, indent=1))
        return
    run = json.loads((HERE / "book.json").read_text()).get("run")
    write(*(render(load(run)) if run else ([], {})))


if __name__ == "__main__":
    main(sys.argv[1:])
