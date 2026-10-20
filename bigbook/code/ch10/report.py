"""Turn the chapter's run into its table and numbers (bigbook/build/ch10_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)

Two kinds of number:
  offline : measured now on Chapter 4's run, with no model: the share of tasks that would give a
            group-relative RL method no gradient, the inference bill of an RL run's rollouts, the
            fine-tuning file, the split, the arms' prompts and the run's power. Always written.
  the run : arms A, B and C on the 15 held-out tasks, and the search that chose C on the 15
            training tasks. "--" until book.json names a complete run of the chapter's design.
Shares are means over tasks, as in Chapter 3; the clustered intervals group tasks by their kind.
Correctness on held-out runs comes from the run's adjudication.json where a person labelled a run,
else the scorer; the arms' means are also given from the scorer alone (Raw...). The search chose
C by the scorer alone, as it ran, so its rows are never relabelled.
"""
import json
import sys
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
import offline as F                                      # noqa: E402
import optimise as O                                     # noqa: E402
import stats                                             # noqa: E402  Chapter 3's statistics

BUILD = HERE.parent.parent / "build"
TASKS = O.CH04 / "tasks_long.json"
SEEDS, CANDIDATES, DEMOS = 10, 4, 2                      # the chapter's design
DELTA = 0.10                                             # the gain the run is sized against
ARMS = {"A": "A: Chapter 4's prompt", "B": "B: A plus two worked examples", "C": "C: reflected instruction"}
PAIRS = {"BA": ("B", "A"), "CA": ("C", "A")}
OFFLINE = ["ChRuns", "ChRight", "ChTasksAny", "DegenThree", "DegenEight", "DegenSixteen", "SecondsPerRun",
           "HoursAThree", "HoursAThreeB", "HoursGEPA", "RolloutsAThree", "RolloutsAThreeB", "RolloutsGEPA",
           "SFTExamples", "SFTTasks", "SFTTurns", "TrainRight", "HeldRight", "Within", "MDETen", "MDEFive",
           "TasksNeeded", "PromptA", "PromptB", "MaxPromptCh", "PlannedRuns", "PlannedRunsFive", "RunHours",
           "RunHoursFive"]
MACROS = ([a + m for a in ARMS for m in ("Mean", "SE", "Tokens", "Seconds", "Runs", "Right", "Unanswered",
                                         "Steps", "MaxPrompt")]
          + [p + m for p in PAIRS for m in ("Diff", "Lo", "Hi", "LoCl", "HiCl")]
          + ["SearchValid", "SearchBest", "SearchBestTrain", "SearchBaseTrain", "SearchRuns", "LabelledHeld"]
          + ["Raw" + a + "Mean" for a in ARMS] + OFFLINE)
PLACEHOLDER = "\\multicolumn{4}{c}{(the run has not been made yet)} \\\\\n"


def tasks():
    return {t["id"]: t for t in json.loads(TASKS.read_text(encoding="utf-8"))}


def the_split():
    return json.loads(O.SPLIT.read_text())


def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:                               # a torn last row is ignored
            break
    return rows


def load(run):
    """The run's rows, with a person's label on held-out runs where there is one."""
    rows = read_rows(HERE / run / "traces.jsonl")
    adj = HERE / run / "adjudication.json"
    labels = {}
    if adj.exists():
        labels = {(a["cond"], a["id"], a["seed"]): a for a in json.loads(adj.read_text(encoding="utf-8"))["labels"]}
    for r in rows:
        a = labels.get((r["cond"], r["id"], r["seed"])) if r["part"] == "held" else None
        if a:
            r["raw"] = {"ok": r["ok"]}
            r["ok"] = a["label"]
    return rows


def raw(rows):
    """The rows as the scorer left them, before any label."""
    return [{**r, **r["raw"]} if "raw" in r else r for r in rows]


def planned(train, heldout, rows, seeds=SEEDS, candidates=CANDIDATES):
    """Every row the design makes: one per reflection, one per training task for each valid
    proposal (validity is read from the reflection rows), and the three arms' held-out runs."""
    valid = {r["seed"] for r in rows if r["part"] == "reflect" and r.get("instruction")}
    keys = {("reflect", s, "-", "-") for s in range(1, candidates + 1)}
    keys |= {("search", s, t, "C") for s in valid if s <= candidates for t in train}
    keys |= {("held", s, t, a) for s in range(1, seeds + 1) for t in heldout for a in ARMS}
    return keys


def not_the_design(run, rows):
    """Why a run is not the chapter's complete design, or None."""
    s = json.loads((HERE / run / "manifest.json").read_text())["settings"]
    sp = the_split()
    for k, want in (("seeds", SEEDS), ("candidates", CANDIDATES), ("demos", DEMOS),
                    ("train", sp["train"]), ("heldout", sp["heldout"])):
        if s.get(k) != want:
            return f"its {k} is {s.get(k)}, not the chapter's {want}"
    return rows_not_the_design(rows, planned(sp["train"], sp["heldout"], rows))


def rows_not_the_design(rows, want):
    keys = [(r["part"], r["seed"], r["id"], r["cond"]) for r in rows]
    if len(keys) != len(set(keys)):
        return f"it has {len(keys) - len(set(keys))} duplicate rows"
    missing, extra = want - set(keys), set(keys) - want
    if missing or extra:
        return f"it lacks {len(missing)} planned runs and has {len(extra)} unplanned ones"
    return None


def pct(v):
    return f"{100 * v:.1f}"


def mean_known(xs):
    """The mean, or None if any value is unknown: a missing usage is not a cost of zero."""
    xs = list(xs)
    return None if not xs or any(x is None for x in xs) else fmean(xs)


def fmt(v):
    return "--" if v is None else f"{v:,.0f}"


def offline(ch4=None, split=None, task=None):
    """The numbers measured on Chapter 4's run, with no model."""
    ch4 = O.ch4_rows() if ch4 is None else ch4
    sp = the_split() if split is None else split
    T = tasks() if task is None else task
    right = O.successes(ch4)
    n = max(r["seed"] for r in ch4)
    sec = fmean(r["seconds"] for r in ch4)
    runs = {t: [0] * n for t in right}
    for r in ch4:
        runs[r["id"]][r["seed"] - 1] = 1 if r["ok"] is True else 0
    _, within = stats.variance_parts(runs)
    held = len(sp["heldout"])
    sft = F.sft_rows(ch4, T, set(sp["train"]), "")
    nums = {"ChRuns": len(ch4), "ChRight": sum(right.values()), "ChTasksAny": sum(c > 0 for c in right.values()),
            "DegenThree": pct(F.degenerate(right, n, n)), "DegenEight": pct(F.degenerate(right, n, 8)),
            "DegenSixteen": pct(F.degenerate(right, n, 16)), "SecondsPerRun": f"{sec:.1f}",
            "SFTExamples": len(sft), "SFTTasks": len({r["id"] for r in sft}),
            "SFTTurns": sum(m["weight"] for r in sft for m in r["messages"]),
            "TrainRight": sum(right.get(t, 0) for t in sp["train"]),
            "HeldRight": sum(right.get(t, 0) for t in sp["heldout"]),
            "Within": f"{within:.3f}",
            "MDETen": pct(stats.mde(held, 0.0, within, within, 10, 10)),
            "MDEFive": pct(stats.mde(held, 0.0, within, within, 5, 5)),
            "TasksNeeded": f"{stats.tasks_needed(DELTA, 0.0, within, within, 10, 10):.0f}",
            "MaxPromptCh": f"{max(r['max_prompt'] for r in ch4):,}"}
    for k, v in F.ROLLOUTS.items():
        m = {"A3": "AThree", "A3b": "AThreeB", "GEPA": "GEPA"}[k]
        nums |= {f"Rollouts{m}": f"{v:,}", f"Hours{m}": f"{F.bill(v, sec):.1f}"}
    search = CANDIDATES * len(sp["train"])
    for seeds, m in ((10, ""), (5, "Five")):          # fixed, whatever SEEDS is
        total = search + len(ARMS) * held * seeds
        nums |= {f"PlannedRuns{m}": total, f"RunHours{m}": f"{F.bill(total, sec):.1f}"}
    return nums


def prompts(task=None, ch4=None, split=None):
    """The characters in arms A's and B's system prompts."""
    sys.path.insert(0, str(HERE.parent / "ch01"))
    from agent import SYSTEM                             # Chapter 1's
    import importlib.util
    spec = importlib.util.spec_from_file_location("ch01_experiment", HERE.parent / "ch01" / "experiment.py")
    ch01 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ch01)
    T = tasks() if task is None else task
    sp = the_split() if split is None else split
    picked = O.bootstrap(O.ch4_rows() if ch4 is None else ch4, set(sp["train"]), DEMOS)
    a = SYSTEM + ch01.FINAL
    b = O.with_demos(a, [O.render_demo(T[r["id"]]["task"], r["trace"]) for r in picked])
    return {"PromptA": f"{len(a):,}", "PromptB": f"{len(b):,}"}


def render(rows):
    """The table and the run's numbers."""
    T = tasks()
    clusters = {t: T[t]["cluster"] for t in T}
    held = [r for r in rows if r["part"] == "held"]
    nums, table = {}, []
    by = {a: {} for a in ARMS}
    for r in held:
        by[r["cond"]].setdefault(r["id"], []).append(1 if r["ok"] is True else 0)
    for a, label in ARMS.items():
        rs = [r for r in held if r["cond"] == a]
        if not rs:
            continue
        x = [fmean(s) for s in by[a].values()]
        nums |= {f"{a}Mean": pct(fmean(x)), f"{a}SE": pct(stats.se(x)) if len(x) > 1 else "--",
                 f"{a}Tokens": fmt(mean_known(r["tokens"] for r in rs)),
                 f"{a}Seconds": f"{fmean(r['seconds'] for r in rs):.0f}",
                 f"{a}Runs": len(rs), f"{a}Right": sum(r["ok"] is True for r in rs),
                 f"{a}Unanswered": sum(r["status"] != "answered" for r in rs),
                 f"{a}Steps": f"{fmean(r['steps'] for r in rs):.1f}",
                 f"{a}MaxPrompt": fmt(None if any(r["max_prompt"] is None for r in rs)
                                      else max(r["max_prompt"] for r in rs))}
        table.append(f"{label} & {nums[a + 'Mean']} ({nums[a + 'SE']}) & {nums[a + 'Tokens']} & "
                     f"{nums[a + 'Seconds']} \\\\")
    for name, (a, b) in PAIRS.items():
        p = {t: s for t, s in by[a].items() if t in by[b]}
        q = {t: by[b][t] for t in p}
        if len(p) > 1:
            cmp, cl = stats.compare(p, q), stats.compare(p, q, clusters)
            nums |= {f"{name}Diff": pct(cmp["diff"]), f"{name}Lo": pct(cmp["ci"][0]), f"{name}Hi": pct(cmp["ci"][1]),
                     f"{name}LoCl": pct(cl["ci"][0]), f"{name}HiCl": pct(cl["ci"][1])}
    refl = [r for r in rows if r["part"] == "reflect"]
    search = [r for r in rows if r["part"] == "search"]
    if refl:
        scores = {}
        for r in search:
            scores.setdefault(r["seed"], []).append(r["ok"] is True)
        scores = {s: fmean(v) for s, v in scores.items()}
        nums |= {"SearchValid": f"{sum(bool(r.get('instruction')) for r in refl)}/{len(refl)}",
                 "SearchRuns": len(search)}
        if scores:
            best = min(scores, key=lambda s: (-scores[s], s))
            nums |= {"SearchBest": best, "SearchBestTrain": pct(scores[best])}
    return table, nums


def numbers(rows):
    """render's table and numbers, with the labelled runs counted, the raw means beside them, and
    the offline numbers, which need no run."""
    table, nums = render(rows)
    rn = render(raw(rows))[1]
    nums |= {f"Raw{a}Mean": rn[f"{a}Mean"] for a in ARMS if f"{a}Mean" in rn}
    if rows:
        nums["LabelledHeld"] = sum(1 for r in rows if r["part"] == "held" and "raw" in r)
    sp = the_split()
    base = [r for r in O.ch4_rows() if r["seed"] == 1 and r["id"] in sp["train"]]
    if any(r["part"] == "reflect" for r in rows):
        nums["SearchBaseTrain"] = pct(fmean(r["ok"] is True for r in base))
    return table, nums | offline() | prompts()


def files(table, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    return {"ch10_arms.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch10_numbers.tex": "".join(f"\\newcommand{{\\cten{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


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
        table, nums = numbers(load(argv[0]))
        print("\n".join(table))
        print(json.dumps(nums, indent=1))
        why = not_the_design(argv[0], load(argv[0]))
        print("not the chapter's design: " + why if why else "the chapter's complete design")
        return
    run = book_run()
    write(*numbers(load(run) if run else []))


if __name__ == "__main__":
    main(sys.argv[1:])
