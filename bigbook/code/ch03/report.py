"""Turn the chapter's run into its tables and numbers (bigbook/build/ch03_*).

Usage: python report.py                 (the run named in book.json)
       python report.py results/<run>   (print the summary only; write nothing)
Correctness comes from the run's adjudication.json where a person labelled a run, else the scorer.
"""
import json
import re
import sys
from pathlib import Path
from statistics import fmean, median

import stats
from measure_scorer import _ch01_score as ch01_score, confusion, labelled
from score import score

HERE = Path(__file__).parent
BUILD = HERE.parent.parent / "build"
BS = "\\"
CONDS = ("v1", "v2", "v2_again")
KEYS = {"v1": "VOne", "v2": "VTwo", "v2_again": "VTwoAgain"}     # macro names take letters only
MACROS = ([k + m for k in KEYS.values() for m in ("Right", "AutoRight", "Runs", "Mean", "SE", "SERuns", "SECl", "HatK",
                                                    "PassK", "Tokens", "Seconds")]
          + [k + m for k in ("VTwoVOne", "AA", "Dev") for m in ("Diff", "SE", "Lo", "Hi", "SEUnpaired", "Corr",
                                                                 "N", "SECl", "LoCl", "HiCl", "TasksDiffer")]
          + ("K Tasks Between Within OmegaTwo SeedCov WithinDiff WithinSum MDE MDEOne MDEHundred TasksForFive "
             "MDEIndep TasksForFiveIndep").split())


def load(run):
    rows = [json.loads(l) for l in open(HERE / run / "traces.jsonl", encoding="utf-8")]
    adj = HERE / run / "adjudication.json"
    labels = {}
    if adj.exists():
        labels = {(a["cond"], a["id"], a["seed"]): a["label"] for a in json.loads(adj.read_text())["labels"]}
    for r in rows:
        r["auto"] = r["ok"]
        r["ok"] = labels.get((r["cond"], r["id"], r["seed"]), r["ok"])
    return rows


def runs_of(rows, cond, which="heldout"):
    """{task: [1 or 0 per run]} for one condition and task set; unlabelled unscored runs count as 0."""
    out = {}
    for r in rows:
        if r["cond"] == cond and r["set"] == which:
            out.setdefault(r["id"], []).append(1 if r["ok"] is True else 0)
    return out


def seed_cov(rows, cond_a, cond_b, which="heldout"):
    """Mean over tasks of the covariance between two conditions' runs with the same seed."""
    by = {}
    for r in rows:
        if r["set"] == which and r["cond"] in (cond_a, cond_b):
            by.setdefault(r["id"], {}).setdefault(r["seed"], {})[r["cond"]] = 1 if r["ok"] is True else 0
    covs = []
    for seeds in by.values():
        pairs = [(v[cond_a], v[cond_b]) for v in seeds.values() if len(v) == 2]
        if len(pairs) > 1:
            ma, mb = fmean(p for p, _ in pairs), fmean(q for _, q in pairs)
            covs.append(sum((p - ma) * (q - mb) for p, q in pairs) / (len(pairs) - 1))
    return fmean(covs) if covs else 0.0


def summary(rows, cond, which="heldout"):
    runs = runs_of(rows, cond, which)
    flat = [v for s in runs.values() for v in s]
    x = list(stats.per_task(runs).values())
    clusters = {r["id"]: r["cluster"] for r in rows}
    k = min(len(s) for s in runs.values())
    rs = [r for r in rows if r["cond"] == cond and r["set"] == which]
    return {"right": sum(flat), "runs": len(flat), "tasks": len(runs), "mean": fmean(x),
            "se_runs": stats.se(flat),                                   # wrong: runs as independent
            "se": stats.se(x), "se_cl": stats.se_clustered(x, [clusters[t] for t in runs]),
            "pass1": fmean(stats.pass_at_k(len(s), sum(s), 1) for s in runs.values()),
            "passk": fmean(stats.pass_at_k(len(s), sum(s), k) for s in runs.values()),
            "hatk": fmean(stats.pass_hat_k(len(s), sum(s), k) for s in runs.values()),
            "k": k, "tokens": fmean(r["tokens"] for r in rs), "seconds": median(r["seconds"] for r in rs),
            "steps": fmean(r["steps"] for r in rs)}


def pct(v, d=1):
    return f"{100 * v:.{d}f}"


def tex(text):
    """Minus signs and missing correlations, as LaTeX should print them."""
    return re.sub(r"(?<![\w.])-(?=\d)", "$-$", text.replace("nan", "--"))


def forest(comps):
    """The comparisons as a TikZ point-and-interval plot; a missing interval is said to be missing.
    The file is written as is: tex() would turn a coordinate's minus sign into a printed one."""
    if not comps:
        return (f"{BS}begin{{center}}{BS}small{BS}itshape No comparison yet: the run has fewer than two tasks "
                f"under both conditions.{BS}end{{center}}\n")
    bounds = [v for c in comps for v in (c["lo"], c["hi"], c["diff"] - 1.96 * c["se_u"], c["diff"] + 1.96 * c["se_u"])]
    lim = 5 * int(-(-max(abs(v) for v in bounds) // 5))
    width, h = 7.0, 1.25
    x = lambda v: f"{(v + lim) / (2 * lim) * width:.3f}"
    top = h * len(comps)
    out = [f"{BS}begin{{tikzpicture}}[fig,x=1cm,y=1cm,",
           "  unp/.style={draw=ink!35,line width=0.7pt,fdash},",
           "  pai/.style={draw=ink!60,line width=1.1pt},",
           "  clu/.style={draw=ink,line width=1.9pt},",
           "  hot/.style={draw=warm,line width=1.9pt},",
           "  dot/.style={circle,fill=ink,inner sep=0,minimum size=3.2pt}]",
           f"  {BS}draw[ink!25,line width=0.4pt] ({x(0)},0.15) -- ({x(0)},{top + 0.1:.3f});"]
    for v in range(-lim, lim + 1, 5):
        sign = "$-$" if v < 0 else ""
        out.append(f"  {BS}draw[ink!55,line width=0.4pt] ({x(v)},0.15) -- ++(0,-0.08) node[fsub,below] {{{sign}{abs(v)}}};")
    out.append(f"  {BS}draw[ink!55,line width=0.4pt] (0,0.15) -- ({width:.3f},0.15);")
    out.append(f"  {BS}node[fsub,anchor=north] at ({width / 2:.3f},-0.35) {{difference in success rate, "
               f"percentage points (v2 higher to the right)}};")
    for i, c in enumerate(comps):
        y = top - h * i - h / 2 + 0.15
        out.append(f"  {BS}node[fsub,anchor=east,align=right,text=ink] at (-0.25,{y:.3f}) {{{c['label']}}};")
        out.append(f"  {BS}node[fsub,anchor=west,align=left] at ({width + 0.25:.3f},{y:.3f}) "
                   f"{{{c['n']} tasks{BS}{BS}[-1pt]corr.{BS} {c['corr']:.2f}}};".replace("nan", "--"))
        lines = [("unp", c["diff"] - 1.96 * c["se_u"], c["diff"] + 1.96 * c["se_u"], y + 0.32),
                 ("pai", c["lo"], c["hi"], y)]
        if c["clo"] is not None:
            lines.append(("hot" if c["planned"] else "clu", c["clo"], c["chi"], y - 0.32))
        else:
            out.append(f"  {BS}node[fsub,font={BS}tiny,anchor=west] at ({x(c['lo'])},{y - 0.32:.3f}) "
                       f"{{clustered: reported for the held-out tasks only}};")
        for style, lo, hi, yy in lines:
            out.append(f"  {BS}draw[{style}] ({x(lo)},{yy:.3f}) -- ({x(hi)},{yy:.3f});")
            out.append(f"  {BS}node[dot{',fill=warm' if style == 'hot' else ''}] at ({x(c['diff'])},{yy:.3f}) {{}};")
    for j, (style, text) in enumerate((("unp", "unpaired $\\pm$1.96 SE, for contrast"), ("pai", "paired"),
                                       ("clu", "paired, clustered by topic"),
                                       ("hot", "paired, clustered: the planned comparison"))):
        lx, ly = -1.2 + 4.8 * (j % 2), -1.1 - 0.42 * (j // 2)
        out.append(f"  {BS}draw[{style}] ({lx:.3f},{ly:.3f}) -- ++(0.45,0) node[fsub,anchor=west] {{{text}}};")
    out.append(f"{BS}end{{tikzpicture}}")
    return "\n".join(out) + "\n"


def render(rows):
    files, nums = {}, {}
    table = []
    for c in CONDS:
        if not runs_of(rows, c):                    # a partial run (python report.py results/<run>)
            continue
        s = summary(rows, c)
        lo, hi = stats.ci(s["mean"], s["se"])
        table.append(f"{BS}texttt{{{c.replace('_', BS + '_')}}} & {s['right']}/{s['runs']} & {pct(s['mean'])} & "
                     f"({pct(s['se'])}) & {pct(lo)} to {pct(hi)} & {pct(s['hatk'])} & {pct(s['passk'])} & "
                     f"{s['tokens']:,.0f} {BS * 2}")
        key = KEYS[c]
        nums.update({f"{key}Right": s["right"], f"{key}Runs": s["runs"], f"{key}Mean": pct(s["mean"]),
                     f"{key}SE": pct(s["se"]), f"{key}SERuns": pct(s["se_runs"]), f"{key}SECl": pct(s["se_cl"]),
                     f"{key}HatK": pct(s["hatk"]), f"{key}PassK": pct(s["passk"]),
                     f"{key}AutoRight": sum(r["auto"] is True for r in rows if r["cond"] == c and r["set"] == "heldout"),
                     f"{key}Tokens": f"{s['tokens']:,.0f}", f"{key}Seconds": f"{s['seconds']:.1f}"})
    nums["K"], nums["Tasks"] = s["k"], s["tasks"]
    files["ch03_results.tex"] = "\n".join(table) + "\n"

    clusters = {r["id"]: r["cluster"] for r in rows}
    comps = [("v2 $-$ v1, held-out", "VTwoVOne", runs_of(rows, "v2"), runs_of(rows, "v1")),
             ("v2 $-$ v2 again, held-out", "AA", runs_of(rows, "v2"), runs_of(rows, "v2_again")),
             ("v2 $-$ v1, Chapter 1's tasks", "Dev", runs_of(rows, "v2", "dev"), runs_of(rows, "v1", "dev"))]
    plot = []
    for label, key, a, b in comps:
        common = set(a) & set(b)                    # in a partial run, only the tasks both have
        if len(common) < 2:
            continue
        a, b = {t: a[t] for t in common}, {t: b[t] for t in common}
        c = stats.compare(a, b)
        cl = stats.compare(a, b, clusters) if key != "Dev" else None
        plot.append({"label": label, "n": c["n"], "corr": c["corr"], "diff": 100 * c["diff"],
                     "lo": 100 * c["ci"][0], "hi": 100 * c["ci"][1], "se_u": 100 * c["se_unpaired"],
                     "clo": 100 * cl["ci"][0] if cl else None, "chi": 100 * cl["ci"][1] if cl else None,
                     "planned": key == "VTwoVOne"})       # the comparison chosen before the run
        nums.update({f"{key}Diff": pct(c["diff"]), f"{key}SE": pct(c["se"]), f"{key}Lo": pct(c["ci"][0]),
                     f"{key}Hi": pct(c["ci"][1]), f"{key}SEUnpaired": pct(c["se_unpaired"]),
                     f"{key}Corr": f"{c['corr']:.2f}", f"{key}N": c["n"]})
        if cl:
            nums.update({f"{key}SECl": pct(cl["se"]), f"{key}LoCl": pct(cl["ci"][0]), f"{key}HiCl": pct(cl["ci"][1])})
        nums[f"{key}TasksDiffer"] = sum(fmean(a[t]) != fmean(b[t]) for t in a)
    files["ch03_forest.tex"] = forest(plot)

    # Power: what this eval can detect, from its own variance estimates
    a, b = runs_of(rows, "v2"), runs_of(rows, "v1")
    common = set(a) & set(b)
    a, b = {t: a[t] for t in common}, {t: b[t] for t in common}
    if len(a) > 1 and min(map(len, (a | b).values())) > 1:   # variance within a task needs two runs
        between_a, within_a = stats.variance_parts(a)
        between_b, within_b = stats.variance_parts(b)
        d = [fmean(a[t]) - fmean(b[t]) for t in a]
        n, k = nums["Tasks"], nums["K"]
        # v1 and v2 ran with the same seeds, so a task's runs under the two are correlated: the
        # within-task variance of a difference is var_a + var_b - 2 cov, not the sum. "Indep" plans a
        # future run with fresh seeds per version: same omega2, no covariance in the noise term
        cov = seed_cov(rows, "v2", "v1")
        within_d = within_a + within_b - 2 * cov
        var_d = sum((v - fmean(d)) ** 2 for v in d) / (len(d) - 1)
        omega2 = max(0.0, var_d - within_d / k)
        nums.update({"Between": f"{between_a:.3f}", "Within": f"{within_a:.3f}", "OmegaTwo": f"{omega2:.3f}",
                     "SeedCov": f"{cov:.3f}", "WithinDiff": f"{within_d:.3f}",
                     "WithinSum": f"{within_a + within_b:.3f}",
                     "MDE": pct(stats.mde(n, omega2, within_d, 0, k, k)),
                     "MDEOne": pct(stats.mde(n, omega2, within_d)),
                     "MDEHundred": pct(stats.mde(n, omega2, within_d, 0, 100, 100)),
                     "TasksForFive": f"{stats.tasks_needed(0.05, omega2, within_d, 0, k, k):,.0f}",
                     "MDEIndep": pct(stats.mde(n, omega2, within_a, within_b, k, k)),
                     "TasksForFiveIndep": f"{stats.tasks_needed(0.05, omega2, within_a, within_b, k, k):,.0f}"})

    # The scorer against the hand labels
    old = labelled()
    for prefix, scorer in (("Scorer", score), ("OldScorer", ch01_score())):
        c3 = confusion(scorer, old)
        nums.update({f"{prefix}Pass": c3.get((True, True), 0), f"{prefix}FalsePass": c3.get((True, False), 0),
                     f"{prefix}FalseFail": c3.get((False, True), 0), f"{prefix}Fail": c3.get((False, False), 0),
                     f"{prefix}None": sum(v for (s, _), v in c3.items() if s is None)})
    nums["ScorerAnswers"] = len(old)
    held = [r for r in rows if r["set"] == "heldout"]
    nums.update({"Unscored": sum(r["auto"] is None for r in rows),
                 "AutoDisagree": sum(r["auto"] is not None and r["auto"] != r["ok"] for r in rows),
                 "AutoFalseFail": sum(r["auto"] is False and r["ok"] is True for r in rows),
                 "AutoFalsePass": sum(r["auto"] is True and r["ok"] is not True for r in rows),
                 "UnscoredRight": sum(r["auto"] is None and r["ok"] is True for r in rows),
                 "AllRuns": len(rows), "HeldRuns": len(held),
                 "ModelCalls": sum(t["type"] == "model" for r in rows for t in r["trace"])})
    for k in MACROS:
        nums.setdefault(k, "--")                    # not computable yet in a partial run
    files["ch03_numbers.tex"] = "".join(f"{BS}newcommand{{{BS}chthree{k}}}{{{v}}}\n" for k, v in nums.items())
    return files, nums


def written(name, text):
    """The text of a build file as main() writes it."""
    return text if name.endswith("_forest.tex") else tex(text)


def main(run=None):
    show = run is not None
    run = run or json.loads((HERE / "book.json").read_text())["run"]
    files, nums = render(load(run))
    for k, v in nums.items():
        print(f"{k:20} {v}")
    if not show:
        BUILD.mkdir(exist_ok=True)
        for name, text in files.items():
            (BUILD / name).write_text(written(name, text), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:])
