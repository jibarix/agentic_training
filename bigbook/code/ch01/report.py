"""Turn one run folder into the chapter's tables and traces (bigbook/build/).

Usage: python report.py            (the run and traces named in book.json)
       python report.py results/<run> v1:denver:1 v2:denver:1 ...
       python report.py --show results/<run> v2:denver:1     (print traces; write nothing)
Each cond:task:seed becomes build/trace_<n>.txt, in order. Correctness comes from the
run's adjudication.json when there is one (labels a person checked), else from the automatic score.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
BUILD = HERE.parent.parent / "build"
CONDS = ("no_tools", "v1", "v2")
BS = "\\"


def load(run):
    run = HERE / run
    with open(run / "traces.jsonl", encoding="utf-8") as f:
        rows = [json.loads(l) for l in f]
    adj = run / "adjudication.json"
    if adj.exists():
        labels = {(a["cond"], a["id"], a["seed"]): a["label"]
                  for a in json.loads(adj.read_text())["labels"]}
        for r in rows:
            r["ok"] = labels[(r["cond"], r["id"], r["seed"])]
    return rows


def calls_of(t):
    """Model-side calls as (id, name, arguments); the first run recorded no ids."""
    return [(c["id"], c["name"], c["arguments"]) if isinstance(c, dict) else (None, *c)
            for c in t["calls"]]


def short(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n] + " ..."


def fmt_trace(r, width=500, max_obs_lines=6):
    out = [f"task: {r['id']}   condition: {r['cond']}   seed: {r['seed']}   status: {r['status']}   "
           f"correct: {'yes' if r['ok'] else 'no'}"]
    for t in r["trace"]:
        if t["type"] == "model" and "error" in t:
            out.append(f"[{t['step']}] model call failed: {t['error']}")
        elif t["type"] == "model" and t["calls"]:
            text = f"   (text: {short(t['content'], 140)})" if t["content"].strip() else ""
            for cid, name, args in calls_of(t):
                out.append(f"[{t['step']}] model -> {name}({args})" + (f" #{cid}" if cid else "") + text)
                text = ""
        elif t["type"] == "model":
            out.append(f"[{t['step']}] model answers: {short(t['content'], width)}")
        elif t["type"] == "tool":
            lines = [l for l in t["observation"].splitlines() if l.strip()]
            for i, line in enumerate(lines[:max_obs_lines]):
                out.append(("    tool  <- " if i == 0 else "             ") + line)
            if len(lines) > max_obs_lines:
                out.append(f"             ... {len(lines) - max_obs_lines} more lines")
        elif t["type"] == "end":
            out.append(f"    end: {t['status']}" + (f" ({t['detail']})" if t["detail"] else ""))
    return "\n".join(out)


def kinds(r):
    return [m.group(1) for t in r["trace"] if t["type"] == "tool"
            for m in [re.match(r"ERROR (\w+)", t["observation"])] if m]


def render(run, picks):
    """Every build file for this run, as {file name: text}. Writes nothing."""
    rows = load(run)
    seeds = sorted({r["seed"] for r in rows})
    tasks = list(dict.fromkeys(r["id"] for r in rows))
    by = {(r["cond"], r["id"], r["seed"]): r for r in rows}
    label = {"no_tools": "Model alone (no tools)", "v1": "Agent, " + BS + "texttt{lookup} v1",
             "v2": "Agent, " + BS + "texttt{lookup} v2"}
    conds = [c for c in CONDS if any(r["cond"] == c for r in rows)]   # a smoke run may have one
    table = []
    for c in conds:
        rs = [r for r in rows if r["cond"] == c]
        k, n = sum(r["ok"] is True for r in rs), len(rs)
        steps, tok = sum(r["steps"] for r in rs) / n, sum(r["tokens"] for r in rs) / n
        cut = sum(r["status"] in ("step_limit", "token_limit") for r in rs)
        table.append(f"{label[c]} & {k}/{n} & {round(100 * k / n)}{BS}% & {steps:.1f} & {tok:,.0f} & {cut} " + BS * 2)
    files = {"results_table.tex": "\n".join(table) + "\n"}
    files["results_pertask.tex"] = "\n".join(
        BS + "texttt{" + t + "} & " + " & ".join(str(sum(by[(c, t, s)]["ok"] is True for s in seeds))
                                                  for c in conds) + " " + BS * 2 for t in tasks) + "\n"
    for i, key in enumerate(picks, 1):          # cond:task:seed -> trace_<i>.txt
        c, t, s = key.split(":")
        files[f"trace_{i}.txt"] = fmt_trace(by[(c, t, int(s))]) + "\n"
    return rows, files


def summary(rows):
    for c in CONDS:
        rs = [r for r in rows if r["cond"] == c]
        if not rs:
            continue
        print(f"{c:9} {sum(r['ok'] is True for r in rs)}/{len(rs)}  "
              f"{dict(Counter(r['status'] for r in rs))}")
    print("wrong agent runs:", [(r["cond"], r["id"], r["seed"]) for r in rows
                                if r["cond"] != "no_tools" and not r["ok"]])
    print("error kinds:", {c: dict(Counter(k for r in rows if r["cond"] == c for k in kinds(r)))
                           for c in ("v1", "v2")})
    secs = [t["seconds"] for r in rows if r["cond"] != "no_tools"
            for t in r["trace"] if t["type"] == "model"]
    if secs:
        print(f"agent model calls (v1 and v2): {len(secs)}, mean latency {sum(secs) / len(secs):.1f}s")


def main(run=None, *picks):
    if run == "--show":
        by = {(r["cond"], r["id"], r["seed"]): r for r in load(picks[0])}
        for key in picks[1:]:
            c, t, s = key.split(":")
            print(fmt_trace(by[(c, t, int(s))]) + "\n")
        return
    if run is None:
        book = json.loads((HERE / "book.json").read_text())
        run, picks = book["run"], book["traces"]
    rows, files = render(run, picks)
    BUILD.mkdir(exist_ok=True)
    for name, text in files.items():
        (BUILD / name).write_text(text, encoding="utf-8")
    summary(rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:])
