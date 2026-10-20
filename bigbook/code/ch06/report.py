"""Turn the chapter's run into its tables and numbers (bigbook/build/ch06_*).

Usage: python report.py                 (the run named in book.json; none yet: placeholders, "--")
       python report.py results/<run>   (print the summary only; write nothing)

Every measure comes from the effects (inject.judge), so there is nothing to label. Shares are
means over tasks of each task's share of runs, as in Chapter 3; standard errors and paired
comparisons need two tasks or more, and print "--" with fewer.

Approvals are counted from the same runs, with no model: under "none", every action the model
takes is one a person would be asked to approve; under "policy", only the ones the code refused.
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
from inject import attack_call                          # noqa: E402

BUILD = HERE.parent.parent / "build"
CONDS = ("none", "delimit", "policy", "workflow")
KEYS = {"none": "None", "delimit": "Delimit", "policy": "Policy", "workflow": "Workflow"}
GKEYS = {"redirect": "Redirect", "inflate": "Inflate", "exfil": "Exfil"}
PAIRS = {k: c for c, k in KEYS.items() if c != "none"}
MACROS = ([k + m for k in KEYS.values() for m in ("Benign", "BenignSE", "Attacked", "ASR", "ASRSE", "Runs",
                                                   "Seen", "Tried", "Tokens", "Seconds")]
          + [k + g for k in KEYS.values() for g in GKEYS.values()]
          + [k + g + "Tried" for k in KEYS.values() for g in GKEYS.values()]
          + [p + m for p in PAIRS for m in ("ASRDiff", "ASRLo", "ASRHi", "ASRLoCl", "ASRHiCl",
                                             "BenignDiff", "BenignLo", "BenignHi")]
          + ["Seeds", "Tasks", "NoneSeenASR", "AskBenign", "AskAttack", "AskPrecision", "Asks",
             "PolicyAskBenign", "PolicyAskAttack", "PolicyAsks", "PolicyPrecision", "PolicyCaught",
             "PolicyAttackCalls"])
PLACEHOLDER = "\\multicolumn{8}{c}{(the run has not been made yet)} \\\\\n"


def load(run):
    return read_jsonl(HERE / run / "traces.jsonl", repair=False)[0]   # reads only: a torn last row is ignored


def pct(v):
    return f"{100 * v:.1f}"


def by_task(rows, field):
    out = {}
    for r in rows:
        out.setdefault(r["id"], []).append(1 if r[field] else 0)
    return out


def share(rows, field):
    """(mean over tasks, its standard error or None)."""
    x = list(stats.per_task(by_task(rows, field)).values())
    return fmean(x), (stats.se(x) if len(x) > 1 else None)


def asks(r, refused_only):
    """The model's actions in a run that a person would be asked to approve."""
    return [e for e in r["events"] if e["kind"] == "effect" and e.get("by") != "code"
            and (not refused_only or e.get("result", "").startswith("not_permitted"))]


def render(rows):
    nums, table = {}, []
    clusters = {r["id"]: r["cluster"] for r in rows}
    for c in CONDS:
        rs = [r for r in rows if r["cond"] == c]
        if not rs:
            continue
        k = KEYS[c]
        clean, hit = [r for r in rs if r["goal"] is None], [r for r in rs if r["goal"] is not None]
        if clean:
            m, s = share(clean, "utility")
            nums |= {f"{k}Benign": pct(m), f"{k}BenignSE": pct(s) if s is not None else "--"}
        if hit:
            m, s = share(hit, "success")
            nums |= {f"{k}Attacked": pct(share(hit, "utility")[0]), f"{k}ASR": pct(m),
                     f"{k}ASRSE": pct(s) if s is not None else "--",
                     f"{k}Seen": pct(fmean(r["exposed"] for r in hit)),
                     f"{k}Tried": pct(fmean(bool(r["attempted"]) for r in hit))}
            for g, gk in GKEYS.items():
                gs = [r for r in hit if r["goal"] == g]
                if gs:
                    nums |= {f"{k}{gk}": f"{sum(r['success'] for r in gs)}/{len(gs)}",
                             f"{k}{gk}Tried": f"{sum(bool(r['attempted']) for r in gs)}/{len(gs)}"}
        nums |= {f"{k}Runs": len(rs), f"{k}Tokens": f"{fmean(r['tokens'] for r in rs):,.0f}",
                 f"{k}Seconds": f"{median(r['seconds'] for r in rs):.0f}"}
        table.append(f"{c} & {nums.get(k + 'Benign', '--')} & {nums.get(k + 'Attacked', '--')} & "
                     + " & ".join(nums.get(k + gk, "--") for gk in GKEYS.values())
                     + f" & {nums.get(k + 'ASR', '--')} ({nums.get(k + 'ASRSE', '--')}) & {nums[k + 'Tokens']} \\\\")
    base = [r for r in rows if r["cond"] == "none"]
    for p, c in PAIRS.items():
        rs = [r for r in rows if r["cond"] == c]
        for field, tag, sel in (("success", "ASR", lambda r: r["goal"] is not None),
                                ("utility", "Benign", lambda r: r["goal"] is None)):
            a, b = by_task([r for r in rs if sel(r)], field), by_task([r for r in base if sel(r)], field)
            if len(a) > 1 and len(b) > 1 and set(a) == set(b):
                cmp = stats.compare(a, b)
                nums |= {f"{p}{tag}Diff": pct(cmp["diff"]), f"{p}{tag}Lo": pct(cmp["ci"][0]),
                         f"{p}{tag}Hi": pct(cmp["ci"][1])}
                if tag == "ASR":
                    cl = stats.compare(a, b, clusters)
                    nums |= {f"{p}ASRLoCl": pct(cl["ci"][0]), f"{p}ASRHiCl": pct(cl["ci"][1])}
    if rows:
        nums |= {"Seeds": len({r["seed"] for r in rows}), "Tasks": len({r["id"] for r in rows})}
    seen = [r for r in base if r["goal"] is not None and r["exposed"]]
    if seen:
        nums["NoneSeenASR"] = pct(fmean(r["success"] for r in seen))
    for c, pre, refused in (("none", "Ask", False), ("policy", "PolicyAsk", True)):
        rs = [r for r in rows if r["cond"] == c]
        clean, hit = [r for r in rs if r["goal"] is None], [r for r in rs if r["goal"] is not None]
        every = [e for r in rs for e in asks(r, refused)]
        if clean:
            nums[f"{pre}Benign"] = f"{fmean(len(asks(r, refused)) for r in clean):.2f}"
        if hit:
            nums[f"{pre}Attack"] = f"{fmean(len(asks(r, refused)) for r in hit):.2f}"
        if rs:                                   # a count of zero is a count; a share of none is "--"
            nums[f"{pre}s"] = len(every)
        if every:
            nums["AskPrecision" if pre == "Ask" else "PolicyPrecision"] = pct(
                fmean(attack_call(e) is not None for e in every))
    pol = [e for r in rows if r["cond"] == "policy" for e in asks(r, False) if attack_call(e) is not None]
    if any(r["cond"] == "policy" for r in rows):
        nums |= {"PolicyAttackCalls": len(pol),
                 "PolicyCaught": sum(e.get("result", "").startswith("not_permitted") for e in pol)}
    return table, nums


def files(table, nums):
    """The chapter's build files as text; check.py compares them with build/."""
    return {"ch06_attacks.tex": "\n".join(table) + "\n" if table else PLACEHOLDER,
            "ch06_numbers.tex": "".join(f"\\newcommand{{\\chsix{m}}}{{{nums.get(m, '--')}}}\n" for m in MACROS)}


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
