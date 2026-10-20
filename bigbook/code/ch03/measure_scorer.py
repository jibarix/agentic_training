"""Score every hand-labelled answer from Chapters 1 and 2 with Chapter 1's scorer and with this
chapter's, and count how each agrees with the hand labels.

Usage: python measure_scorer.py
"""
import importlib.util
import json
from pathlib import Path

from score import score

CODE = Path(__file__).parent.parent
RUNS = [CODE / "ch01/results/2026-10-16-run1", CODE / "ch02/results/2026-10-16-run1"]


def _ch01_score():
    spec = importlib.util.spec_from_file_location("ch01_experiment", CODE / "ch01/experiment.py")
    import sys
    sys.path.insert(0, str(CODE / "ch01"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.score


def labelled():
    """(chapter, record, hand label, task) for every hand-labelled answer."""
    tasks = {t["id"]: t for t in json.loads((CODE / "ch01/tasks.json").read_text())}
    out = []
    for run in RUNS:
        labels = {(a["cond"], a["id"], a["seed"]): a["label"]
                  for a in json.loads((run / "adjudication.json").read_text())["labels"]}
        for line in open(run / "traces.jsonl", encoding="utf-8"):
            r = json.loads(line)
            out.append((run.parent.parent.name, r, labels[(r["cond"], r["id"], r["seed"])], tasks[r["id"]]))
    return out


def confusion(scorer, rows):
    """Counts of (scorer says, hand label): pass/fail/none against right/wrong."""
    c = {}
    for _, r, label, t in rows:
        s = scorer(r["answer"], t["answer"], t["units"]) if r["status"] == "answered" else False
        c[(s, label)] = c.get((s, label), 0) + 1
    return c


def main():
    rows = labelled()
    for name, f in (("chapter 1", _ch01_score()), ("chapter 3", score)):
        c = confusion(f, rows)
        print(f"{name}: {len(rows)} answers; " + ", ".join(
            f"{ {True: 'pass', False: 'fail', None: 'none'}[s]}/{'right' if l else 'wrong'} {n}"
            for (s, l), n in sorted(c.items(), key=str)))
        for ch, r, label, t in rows:
            s = f(r["answer"], t["answer"], t["units"]) if r["status"] == "answered" else False
            if s is not None and s != label:
                print("   disagrees:", ch, r["cond"], r["id"], r["seed"], "label", label,
                      "|", r["answer"].strip().splitlines()[-1][:90])


if __name__ == "__main__":
    main()
