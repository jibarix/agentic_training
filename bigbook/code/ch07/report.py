"""Turn the chapter's run into its tables and numbers (bigbook/build/ch07_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)

The grader decides every run (tasks.grade), so there is nothing to label. Shares are means over
tasks of each task's share of runs, as in Chapter 3; pass@k and pass^k use every repeat of a task
(k = the number of repeats). Paired comparisons need two tasks or more, and print "--" with fewer;
the clustered ones group the tasks by the module their bug is in. The chapter's numbers are
written only from a complete run of the chapter's design: all 24 tasks, all three arms, five
repeats, every row present.
"""
import json
import sys
from pathlib import Path
from statistics import fmean, median

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
sys.path.append(str(HERE.parent / "ch05"))
import stats                                             # noqa: E402  Chapter 3's statistics
from durable import read_jsonl                           # noqa: E402  Chapter 5's

BUILD = HERE.parent.parent / "build"
ARMS = ("agentless", "shell", "aci")
KEYS = {"agentless": "Agentless", "shell": "Shell", "aci": "Aci"}
PAIRS = {"AciShell": ("aci", "shell"), "AciAgentless": ("aci", "agentless"), "ShellAgentless": ("shell", "agentless")}
MODULES = ("money", "dates", "rates", "claims", "summary")
REPEATS = 5                                              # the chapter's design: every task, every arm, five times
MACROS = ([k + m for k in KEYS.values() for m in ("Resolved", "ResolvedSE", "PassK", "PassHatK", "Runs", "Partial",
                                                   "Broke", "NoPatch", "Refused", "TestsChanged", "Calls", "Tokens",
                                                   "Seconds", "Steps", "Answered", "Suspect")]
          + [k + m.capitalize() for k in KEYS.values() for m in MODULES]
          + [p + m for p in PAIRS for m in ("Diff", "Lo", "Hi", "LoCl", "HiCl")]
          + ["Repeats", "Tasks", "AciReverted", "AgentlessFileRight", "AgentlessNoCandidate", "ShellRefusals",
             "ShellCommands"])
PLACEHOLDER = "\\multicolumn{8}{c}{(the run has not been made yet)} \\\\\n"
MODULE_PLACEHOLDER = "\\multicolumn{6}{c}{(the run has not been made yet)} \\\\\n"


def missing(run, rows):
    """The (repeat, task, arm) runs the run's manifest asks for and traces.jsonl lacks."""
    s = json.loads((HERE / run / "manifest.json").read_text())["settings"]
    have = {(r["rep"], r["id"], r["arm"]) for r in rows}
    return [(rep, t, arm) for rep in s["repeats"] for t in s["tasks"] for arm in s["arms"] if (rep, t, arm) not in have]


def not_the_design(settings):
    """Why a run's settings are not the chapter's design (the tables say pass@5), or None."""
    every = [t["id"] for t in json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))]
    for k, want in (("repeats", list(range(1, REPEATS + 1))), ("tasks", every), ("arms", list(ARMS))):
        if settings.get(k) != want:
            return f"its {k} are {settings.get(k)}, not the chapter's {want}"
    return None


def load(run):
    return read_jsonl(HERE / run / "traces.jsonl", repair=False)[0]   # reads only: a torn last row is ignored


def pct(v):
    return f"{100 * v:.1f}"


def by_task(rows, test):
    out = {}
    for r in rows:
        out.setdefault(r["id"], []).append(1 if test(r) else 0)
    return out


def share(rows, test):
    """(mean over tasks, its standard error or None)."""
    x = list(stats.per_task(by_task(rows, test)).values())
    return fmean(x), (stats.se(x) if len(x) > 1 else None)


def kinds(r):
    return [e["kind"] for e in r["events"]]


def module(r):
    return r["module"].rsplit("/", 1)[-1].removesuffix(".py")


def render(rows):
    nums, table, mods = {}, [], []
    tasks = {r["id"]: r for r in rows}
    clusters = {t: module(r) for t, r in tasks.items()}
    runs = {}
    for r in rows:
        runs[(r["id"], r["arm"])] = runs.get((r["id"], r["arm"]), 0) + 1
    k = min(runs.values(), default=0)                    # the repeats every task has in every arm
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        key = KEYS[arm]
        m, s = share(rs, lambda r: r["resolved"])
        solved = by_task(rs, lambda r: r["resolved"])
        nums |= {f"{key}Resolved": pct(m), f"{key}ResolvedSE": pct(s) if s is not None else "--",
                 f"{key}Runs": len(rs),
                 f"{key}Partial": pct(share(rs, lambda r: not r["resolved"] and r["f2p"] > 0)[0]),
                 f"{key}Broke": pct(share(rs, lambda r: r["p2p"] < r["p2p_of"])[0]),
                 f"{key}NoPatch": pct(share(rs, lambda r: not r["patch"])[0]),
                 f"{key}Refused": pct(share(rs, lambda r: "refused" in kinds(r))[0]),
                 f"{key}TestsChanged": pct(share(rs, lambda r: "tests_changed" in kinds(r))[0]),
                 f"{key}Suspect": pct(share(rs, lambda r: bool(r.get("suspect")))[0]),
                 f"{key}Answered": pct(share(rs, lambda r: r["status"] in ("answered", "chosen"))[0]),
                 f"{key}Calls": f"{fmean(r['calls'] for r in rs):.1f}",
                 f"{key}Steps": f"{fmean(r['steps'] for r in rs):.1f}",
                 f"{key}Tokens": f"{fmean(r['tokens'] for r in rs):,.0f}",
                 f"{key}Seconds": f"{median(r['seconds'] for r in rs):.0f}"}
        if k:
            nums |= {f"{key}PassK": pct(fmean(stats.pass_at_k(len(v), sum(v), k) for v in solved.values())),
                     f"{key}PassHatK": pct(fmean(stats.pass_hat_k(len(v), sum(v), k) for v in solved.values()))}
        for mod in MODULES:
            ms = [r for r in rs if module(r) == mod]
            if ms:
                nums[f"{key}{mod.capitalize()}"] = pct(share(ms, lambda r: r["resolved"])[0])
        table.append(f"{arm} & {nums[key + 'Resolved']} ({nums[key + 'ResolvedSE']}) & {nums.get(key + 'PassK', '--')} & "
                     f"{nums.get(key + 'PassHatK', '--')} & {nums[key + 'Broke']} & {nums[key + 'Refused']} & "
                     f"{nums[key + 'Calls']} & {nums[key + 'Tokens']} \\\\")
        mods.append(f"{arm} & " + " & ".join(nums.get(f"{key}{mod.capitalize()}", "--") for mod in MODULES) + " \\\\")
    for p, (x, y) in PAIRS.items():
        a = by_task([r for r in rows if r["arm"] == x], lambda r: r["resolved"])
        b = by_task([r for r in rows if r["arm"] == y], lambda r: r["resolved"])
        if len(a) > 1 and set(a) == set(b):
            cmp, cl = stats.compare(a, b), stats.compare(a, b, clusters)
            nums |= {f"{p}Diff": pct(cmp["diff"]), f"{p}Lo": pct(cmp["ci"][0]), f"{p}Hi": pct(cmp["ci"][1]),
                     f"{p}LoCl": pct(cl["ci"][0]), f"{p}HiCl": pct(cl["ci"][1])}
    if rows:
        nums |= {"Repeats": k, "Tasks": len(tasks)}
    aci = [r for r in rows if r["arm"] == "aci"]
    if aci:
        nums["AciReverted"] = f"{fmean(kinds(r).count('edit_reverted') for r in aci):.2f}"
    al = [r for r in rows if r["arm"] == "agentless"]
    if al:
        nums["AgentlessFileRight"] = pct(fmean(r["trace"].get("file") == r["module"] for r in al))
        nums["AgentlessNoCandidate"] = pct(fmean(r["trace"].get("chosen") is None for r in al))
    sh = [r for r in rows if r["arm"] == "shell"]
    if sh:
        refused = sum(kinds(r).count("refused") for r in sh)
        nums |= {"ShellRefusals": refused,                # commands tried = those run + those refused
                 "ShellCommands": refused + sum(kinds(r).count("command") for r in sh)}
    return table, mods, nums


def files(table, mods, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    return {"ch07_arms.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch07_modules.tex": "\n".join(mods) + "\n" if mods else MODULE_PLACEHOLDER,
            "ch07_numbers.tex": "".join(f"\\newcommand{{\\chseven{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


def write(table, mods, nums):
    BUILD.mkdir(exist_ok=True)
    for name, text in files(table, mods, nums).items():
        (BUILD / name).write_text(text, encoding="utf-8")


def main(argv):
    if argv:
        rows = load(argv[0])
        table, mods, nums = render(rows)
        print(f"k = {nums.get('Repeats', 0)}; runs missing: {len(missing(argv[0], rows))}")
        print("\n".join(table + mods))
        print(json.dumps(nums, indent=1))
        return
    run = json.loads((HERE / "book.json").read_text()).get("run")
    rows = load(run) if run else []
    if run:
        why = not_the_design(json.loads((HERE / run / "manifest.json").read_text())["settings"])
        if why:
            sys.exit(f"{run} can't make the chapter's numbers: {why}")
        gone = missing(run, rows)
        if gone:                                         # pass@5 and the pairs need every run
            sys.exit(f"{run} lacks {len(gone)} runs (first {gone[0]}); finish it with --resume first")
    write(*render(rows))


if __name__ == "__main__":
    main(sys.argv[1:])
