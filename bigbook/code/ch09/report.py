"""Turn the chapter's run into its table and numbers (bigbook/build/ch09_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)

Five ways to answer each task, all scored on the same thinking-off runs except the second:
  one run, thinking off  : the share of the ten runs that were right (pass@1)
  one run, thinking on   : the same over the three thinking-on runs
  vote of 5              : a majority vote over five runs, averaged exactly over all 252 sets of five
  judge of 5             : the model's pick from each group of five (seeds 1-5, 6-10), in both orders
  any of 5 (the oracle)  : the chance that at least one of five runs is right (pass@5)
The gap between the oracle and a way of choosing is Weaver's generation-verification gap. The
judge is compared with the vote, and its gap measured against the oracle, on the same two groups,
so all three choose among the same runs. A cost that a run's usage doesn't give is shown as "--".
Shares are means over tasks, as in Chapter 3; the clustered intervals group tasks by their kind.
Correctness comes from the run's adjudication.json where a person labelled a run (with the amount
read from its answer, so that it can vote), else the scorer. The five ways' means are also given
from the scorer and the parser alone (Raw...), since a labelled amount makes the vote one with
human help in reading the answers. The chapter's numbers are written only
from a complete run of the chapter's design: 30 tasks, ten runs off and three on, groups of five,
every planned row present once and nothing else.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path
from statistics import fmean, median

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.append(str(HERE.parent / "ch03"))
import sampling as S                                     # noqa: E402
import stats                                             # noqa: E402  Chapter 3's statistics

BUILD = HERE.parent.parent / "build"
TASKS = HERE.parent / "ch04" / "tasks_long.json"
OFF, ON, K = 10, 3, 5
WAYS = {"Off": "one run, thinking off", "On": "one run, thinking on", "Vote": "vote of 5",
        "Judge": "judge of 5", "Oracle": "any of 5 (oracle)"}
PAIRS = {"OnOff": ("On", "Off"), "VoteOff": ("Vote", "Off"), "OnVote": ("On", "Vote"),
         "JudgeSame": ("Judge", "VoteSame"), "JudgeOff": ("Judge", "Off")}
MACROS = ([w + m for w in WAYS for m in ("Mean", "SE", "Tokens", "Seconds")]
          + [p + m for p in PAIRS for m in ("Diff", "Lo", "Hi", "LoCl", "HiCl")]
          + ["VoteSameMean", "VoteOnMean", "OracleSameMean", "GapVote", "GapJudge", "HatK", "Tasks",
             "OffRuns", "OnRuns", "OffRight", "OnRight", "OffUnanswered", "OnUnanswered",
             "OffSteps", "OnSteps", "OffCompletion", "OnCompletion", "OnThinking", "OffThinking",
             "JudgeCalls", "JudgeInvalid", "JudgeSamePick", "JudgeFirst", "JudgeCallTokens",
             "AgreeHighN", "AgreeHighRight", "AgreeLowN", "AgreeLowRight", "NoneRight", "AllRight",
             "LabelledOff", "LabelledOn"]
          + ["Raw" + w + "Mean" for w in WAYS])
PLACEHOLDER = "\\multicolumn{4}{c}{(the run has not been made yet)} \\\\\n"


def tasks():
    return {t["id"]: t for t in json.loads(TASKS.read_text(encoding="utf-8"))}


def groups(off=OFF, k=K):
    return [list(range(i + 1, i + k + 1)) for i in range(0, off - k + 1, k)]


def read_rows(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:                               # a torn last row is ignored
            break
    return rows


def load(run):
    """The run's rows, with a person's label and amount where there is one."""
    rows = read_rows(HERE / run / "traces.jsonl")
    adj = HERE / run / "adjudication.json"
    labels = {}
    if adj.exists():
        labels = {(a["cond"], a["id"], a["seed"]): a for a in json.loads(adj.read_text(encoding="utf-8"))["labels"]}
    for r in rows:
        a = labels.get((r["cond"], r["id"], r["seed"])) if r["part"] == "gen" else None
        if a:
            r["raw"] = {"ok": r["ok"], "amount": r["amount"]}
            r["ok"] = a["label"]
            if "amount" in a:
                r["amount"] = a["amount"]
    return rows


def raw(rows):
    """The rows as the scorer and the parser left them, before any label."""
    return [{**r, **r["raw"]} if "raw" in r else r for r in rows]


def planned(T):
    n = {"off": OFF, "on": ON}
    keys = {("gen", s, t, c) for t in T for c in n for s in range(1, n[c] + 1)}
    keys |= {("judge", g, t, o) for t in T for g in range(1, len(groups()) + 1) for o in ("forward", "reverse")}
    return keys


def not_the_design(run, rows):
    """Why a run is not the chapter's complete design, or None."""
    s = json.loads((HERE / run / "manifest.json").read_text())["settings"]
    T = tasks()
    for k, want in (("off", OFF), ("on", ON), ("k", K), ("tasks", list(T))):
        if s.get(k) != want:
            return f"its {k} is {s.get(k)}, not the chapter's {want}"
    return rows_not_the_design(rows, planned(T))


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


def per_task(rows):
    """{task: {"off": {seed: row}, "on": {seed: row}, "judge": {(group, order): row}}}."""
    out = {}
    for r in rows:
        d = out.setdefault(r["id"], {"off": {}, "on": {}, "judge": {}})
        if r["part"] == "gen":
            d[r["cond"]][r["seed"]] = r
        else:
            d["judge"][r["seed"], r["cond"]] = r
    return out


def votes(gen):
    """[(amount, ok)] for runs in seed order, for sampling.vote."""
    return [(None if r["amount"] is None else Decimal(r["amount"]), r["ok"]) for _, r in sorted(gen.items())]


def scores(d, gs, k=K):
    """The task's score lists, one per way of answering (for stats.compare)."""
    off, on = [1 if r["ok"] is True else 0 for _, r in sorted(d["off"].items())], \
              [1 if r["ok"] is True else 0 for _, r in sorted(d["on"].items())]
    v = votes(d["off"])
    seeds = sorted(d["off"])
    by_seed = dict(zip(seeds, v))
    out = {"Off": off, "On": on, "Vote": [S.vote_k(v, k)] if len(v) >= k else [],
           "Oracle": [stats.pass_at_k(len(off), sum(off), k)] if len(off) >= k else [],
           "VoteSame": [S.vote([by_seed[s] for s in g]) for g in gs if all(s in by_seed for s in g)],
           "OracleSame": [1 if any(by_seed[s][1] is True for s in g) else 0
                          for g in gs if all(s in by_seed for s in g)],
           "Judge": [], "VoteOn": [S.vote_k(votes(d["on"]), len(on))] if on else []}
    for (_, _), j in sorted(d["judge"].items()):
        out["Judge"].append(1 if j["pick"] is not None and d["off"][j["pick"]]["ok"] is True else 0)
    return out


def render(rows, k=K, off=OFF):
    """The table and numbers; k and off are the run's own (a pilot's are smaller than the chapter's)."""
    T = tasks()
    gs = groups(off, k)
    by = per_task(rows)
    S_ = {t: scores(d, gs, k) for t, d in by.items()}
    clusters = {t: T[t]["cluster"] for t in T}
    nums, table, fig = {}, [], {}
    gen = {c: [r for r in rows if r["part"] == "gen" and r["cond"] == c] for c in ("off", "on")}
    judges = [r for r in rows if r["part"] == "judge"]
    cost = {"Off": (mean_known(r["tokens"] for r in gen["off"]), fmean(r["seconds"] for r in gen["off"]))
            if gen["off"] else None,
            "On": (mean_known(r["tokens"] for r in gen["on"]), fmean(r["seconds"] for r in gen["on"]))
            if gen["on"] else None}
    if cost["Off"]:
        tok, sec = cost["Off"]
        cost["Vote"] = cost["Oracle"] = (None if tok is None else k * tok, k * sec)
        if judges:
            jt = mean_known(r["tokens"] for r in judges)
            cost["Judge"] = (None if tok is None or jt is None else k * tok + jt,
                             k * sec + fmean(r["seconds"] for r in judges))
    for w, label in WAYS.items():
        x = [fmean(s[w]) for s in S_.values() if s[w]]
        if not x:
            continue
        nums |= {f"{w}Mean": pct(fmean(x)), f"{w}SE": pct(stats.se(x)) if len(x) > 1 else "--"}
        fig[w] = (fmean(x), cost[w][0] if cost.get(w) else None)
        if cost.get(w):
            nums |= {f"{w}Tokens": "--" if cost[w][0] is None else f"{cost[w][0]:,.0f}",
                     f"{w}Seconds": f"{cost[w][1]:.0f}"}
        table.append(f"{label} & {nums[w + 'Mean']} ({nums[w + 'SE']}) & {nums.get(w + 'Tokens', '--')} & "
                     f"{nums.get(w + 'Seconds', '--')} \\\\")
    for w in ("VoteSame", "VoteOn", "OracleSame"):
        x = [fmean(s[w]) for s in S_.values() if s[w]]
        if x:
            nums[f"{w}Mean"] = pct(fmean(x))
            fig[w] = (fmean(x), None)
    nums["_fig"] = fig                                   # for the figure; not a macro
    for name, (a, b) in PAIRS.items():
        p = {t: s[a] for t, s in S_.items() if s[a] and s[b]}
        q = {t: S_[t][b] for t in p}
        if len(p) > 1:
            cmp, cl = stats.compare(p, q), stats.compare(p, q, clusters)
            nums |= {f"{name}Diff": pct(cmp["diff"]), f"{name}Lo": pct(cmp["ci"][0]), f"{name}Hi": pct(cmp["ci"][1]),
                     f"{name}LoCl": pct(cl["ci"][0]), f"{name}HiCl": pct(cl["ci"][1])}
    if all(f"{w}Mean" in nums for w in ("Oracle", "Vote")):
        nums["GapVote"] = pct(fmean(fmean(s["Oracle"]) - fmean(s["Vote"]) for s in S_.values() if s["Oracle"]))
    if "JudgeMean" in nums and "OracleSameMean" in nums:       # the oracle on the judge's own groups
        nums["GapJudge"] = pct(fmean(fmean(s["OracleSame"]) - fmean(s["Judge"]) for s in S_.values()
                                     if s["OracleSame"] and s["Judge"]))
    offs = {t: d["off"] for t, d in by.items() if len(d["off"]) >= k}
    if offs:
        right = {t: sum(r["ok"] is True for r in g.values()) for t, g in offs.items()}
        nums |= {"HatK": pct(fmean(stats.pass_hat_k(len(offs[t]), c, k) for t, c in right.items())),
                 "Tasks": len(offs), "NoneRight": sum(c == 0 for c in right.values()),
                 "AllRight": sum(c == len(offs[t]) for t, c in right.items())}
        high, low = [], []
        for g in offs.values():
            for grp in gs:
                if all(s in g for s in grp):
                    v = votes({s: g[s] for s in grp})
                    (high if S.agreement(v) >= 0.6 else low).append(S.vote(v))
        nums |= {"AgreeHighN": len(high), "AgreeHighRight": pct(fmean(high)) if high else "--",
                 "AgreeLowN": len(low), "AgreeLowRight": pct(fmean(low)) if low else "--"}
    for c, w in (("off", "Off"), ("on", "On")):
        rs = gen[c]
        if rs:
            nums |= {f"{w}Runs": len(rs), f"{w}Right": sum(r["ok"] is True for r in rs),
                     f"{w}Unanswered": sum(r["status"] != "answered" for r in rs),
                     f"{w}Steps": f"{fmean(r['steps'] for r in rs):.1f}",
                     f"{w}Completion": fmt(mean_known(r["completion"] for r in rs)),
                     f"{w}Thinking": f"{fmean(r['thinking_chars'] for r in rs):,.0f}"}
    if judges:
        pairs = {}
        for r in judges:
            pairs.setdefault((r["id"], r["seed"]), {})[r["cond"]] = r["pick"]
        both = [p for p in pairs.values() if len(p) == 2]
        nums |= {"JudgeCalls": len(judges), "JudgeInvalid": sum(r["pick"] is None for r in judges),
                 "JudgeSamePick": f"{sum(p['forward'] is not None and p['forward'] == p['reverse'] for p in both)}"
                                  f"/{len(both)}",
                 "JudgeFirst": pct(fmean(r["pick"] == r["shown"][0] for r in judges)),
                 "JudgeCallTokens": "--" if any(r["tokens"] is None for r in judges)
                                    else f"{median(r['tokens'] for r in judges):,.0f}"}
    return table, nums


def numbers(rows, k=K, off=OFF):
    """render's table and numbers, with the labelled runs counted and the raw means beside them."""
    table, nums = render(rows, k, off)
    rn = render(raw(rows), k, off)[1]
    nums |= {f"Raw{w}Mean": rn[f"{w}Mean"] for w in WAYS if f"{w}Mean" in rn}
    for c, w in (("off", "Off"), ("on", "On")):
        nums[f"Labelled{w}"] = sum(1 for r in rows if r["part"] == "gen" and r["cond"] == c and "raw" in r)
    return table, nums


def figure(fig):
    """Cost against accuracy, and what choosing loses against the oracle, as TikZ. With no run the
    axes are drawn empty and say so; a way with no known cost is listed, not placed at zero."""
    BS = "\\"
    W, H, X2, W2 = 6.0, 4.2, 8.6, 4.6
    out = [f"{BS}begin{{tikzpicture}}[fig,x=1cm,y=1cm,",
           "  pt/.style={circle,fill=ink,inner sep=0,minimum size=4pt},",
           "  orc/.style={circle,draw=ink,fill=white,line width=0.7pt,inner sep=0,minimum size=4.5pt},",
           "  ax/.style={draw=ink!55,line width=0.4pt},",
           "  gap/.style={draw=warm,line width=1.6pt}]"]
    ys = "share right, mean over tasks (\\%)"
    out += [f"  {BS}draw[ax] (0,{H}) -- (0,0) -- ({W},0);",
            f"  {BS}node[fsub,anchor=north] at ({W / 2},-0.45) {{tokens per task, including the judge's}};",
            f"  {BS}node[fsub,rotate=90,anchor=south] at (-0.75,{H / 2}) {{{ys}}};",
            f"  {BS}draw[ax] ({X2},{H}) -- ({X2},0) -- ({X2 + W2},0);",
            f"  {BS}node[fsub,anchor=north] at ({X2 + W2 / 2:.2f},-0.45) {{share right ({BS}%), on the judge's groups}};",
            f"  {BS}node[fglabel,anchor=south west] at (0,{H + 0.1}) {{cost and accuracy}};",
            f"  {BS}node[fglabel,anchor=south west] at ({X2},{H + 0.1}) {{what choosing loses}};"]
    for v in range(0, 101, 25):
        out += [f"  {BS}draw[ax] (0,{v / 100 * H:.3f}) -- ++(-0.08,0) node[fsub,left] {{{v}}};",
                f"  {BS}draw[ax] ({X2 + v / 100 * W2:.3f},0) -- ++(0,-0.08) node[fsub,below] {{{v}}};"]
    ways = ("Off", "On", "Vote", "Judge", "Oracle")
    if not fig or any(w not in fig for w in ways + ("VoteSame", "OracleSame")):
        note = "Not run yet: no points are drawn"
        out += [f"  {BS}node[fnote,text width=4.5cm] at ({W / 2},{H / 2}) {{{note}}};",
                f"  {BS}node[fnote,text width=4.5cm] at ({X2 + W2 / 2:.2f},{H / 2}) {{{note}}};",
                f"{BS}end{{tikzpicture}}"]
        return "\n".join(out) + "\n"
    known = [fig[w][1] for w in ways if fig[w][1] is not None]
    top = max(known) if known else 1
    step = next(s for s in (1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 10 ** 6, 10 ** 7)
                if top / s <= 5)
    xmax = step * -(-top // step)
    for v in range(0, int(xmax) + 1, step):
        out.append(f"  {BS}draw[ax] ({v / xmax * W:.3f},0) -- ++(0,-0.08) node[fsub,below] {{{v:,}}};")
    names = {"Off": "thinking off", "On": "thinking on", "Vote": "vote of 5", "Judge": "judge of 5",
             "Oracle": "oracle: pass@5 of thinking-off runs; needs the answer key"}
    unknown = []
    for w in ways:
        share, tok = fig[w]
        if tok is None:
            unknown.append(names[w])
            continue
        style = "orc" if w == "Oracle" else "pt"
        side = "below" if w == "Vote" else "right"
        wrap = ",text width=2.4cm,align=left" if w == "Oracle" else ""
        out.append(f"  {BS}node[{style},label={{[fsub,font={BS}tiny{wrap}]{side}:{names[w]}}}] "
                   f"at ({tok / xmax * W:.3f},{share * H:.3f}) {{}};")
    if unknown:
        out.append(f"  {BS}node[fsub,font={BS}tiny,anchor=north west,text width={W}cm] at (0,-0.95) "
                   f"{{cost unknown, not drawn: {', '.join(unknown)}}};")
    orc = fig["OracleSame"][0]
    for i, (w, label) in enumerate((("VoteSame", "vote of 5"), ("Judge", "judge of 5"))):
        y = H * (0.7 - 0.4 * i)
        share = fig[w][0]
        out += [f"  {BS}node[fsub,anchor=east] at ({X2 - 0.1},{y:.3f}) {{{label}}};",
                f"  {BS}draw[gap] ({X2 + share * W2:.3f},{y:.3f}) -- ({X2 + orc * W2:.3f},{y:.3f});",
                f"  {BS}node[pt] at ({X2 + share * W2:.3f},{y:.3f}) {{}};",
                f"  {BS}node[orc] at ({X2 + orc * W2:.3f},{y:.3f}) {{}};"]
    out += [f"  {BS}node[fsub,font={BS}tiny,anchor=south] at ({X2 + orc * W2:.3f},{H * 0.7 + 0.15:.3f}) {{oracle}};",
            f"{BS}end{{tikzpicture}}"]
    return "\n".join(out) + "\n"


def files(table, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    return {"ch09_ways.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch09_cost.tex": figure(nums.get("_fig")),
            "ch09_numbers.tex": "".join(f"\\newcommand{{\\cnine{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


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
        s = json.loads((HERE / argv[0] / "manifest.json").read_text())["settings"]
        table, nums = numbers(load(argv[0]), s["k"], s["off"])
        print("\n".join(table))
        print(json.dumps(nums, indent=1))
        why = not_the_design(argv[0], load(argv[0]))
        print("not the chapter's design: " + why if why else "the chapter's complete design")
        return
    run = book_run()
    write(*(numbers(load(run)) if run else ([], {})))


if __name__ == "__main__":
    main(sys.argv[1:])
