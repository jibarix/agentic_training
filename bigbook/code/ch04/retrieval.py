"""How often does each search put the passage that answers a question in its top results? No model.

Fifty questions about this chapter's handbook: 43 with the file and a phrase that the answering
passage must contain (one of them a false premise, answered by the rule that refutes it), and 7
the handbook can't answer. Six searches: Chapter 1's lookup, both
versions (they return lines); BM25 over exactly the lines lookup indexes, which changes only the
scoring; and BM25 over this chapter's passages at three sizes, which also changes the text indexed
(section names and table headers are attached, headings are not passages).

Usage: python retrieval.py          print the results and any misses
       python retrieval.py --book   also write ../../build/ch04_retrieval.tex and ch04_rnumbers.tex
"""
import json
import re
import sys
from pathlib import Path
from statistics import median

from bm25 import BM25, passages
from handbook_tools import ToolError, ch01_tools, lookup, lookup_v1

HERE = Path(__file__).parent
sys.path.append(str(HERE.parent / "ch03"))
import stats                                             # noqa: E402  Chapter 3's paired comparison
BUILD = HERE.parent.parent / "build"
BOOK = HERE / "handbook"
K = 5                                    # Chapter 1's lookup returns at most five lines


def flat(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def from_lookup(fn):
    def search(q):
        try:
            out = fn(q)
        except ToolError:
            return []
        if out.startswith("No matches."):
            return []
        return [(line.split(": ", 1)[0], line.split(": ", 1)[1], None) for line in out.splitlines()]
    return search


def from_bm25(size):
    units = passages(BOOK, size) if size else [(f, line) for f, line, _ in ch01_tools._lines()]
    index = BM25([text for _, text in units])         # the file name is not indexed, as in lookup

    def search(q):
        return [(units[i][0], units[i][1], s) for i, s in index.top(q, K)]
    return search


SEARCHES = {"lookup v1 (lines)": from_lookup(lookup_v1), "lookup v2 (lines)": from_lookup(lookup),
            "BM25, lookup's lines": from_bm25(None), "BM25, lines": from_bm25(1),
            "BM25, 500 characters": from_bm25(500), "BM25, 1,500 characters": from_bm25(1500)}


def rank(results, q):
    """1-based position of the first result from the right file that contains the phrase."""
    for i, (name, text, _) in enumerate(results, 1):
        if name == q["file"] and flat(q["needle"]) in flat(text):
            return i
    return None


def evaluate(queries):
    out = {}
    for label, search in SEARCHES.items():
        rows = []
        for q in queries:
            res = search(q["q"])
            rows.append({"id": q["id"], "answerable": "needle" in q,
                         "rank": rank(res, q) if "needle" in q else None, "returned": len(res),
                         "chars": sum(len(t) for _, t, _ in res),
                         "top": res[0][2] if res and res[0][2] is not None else None})
        ans = [r for r in rows if r["answerable"]]
        un = [r for r in rows if not r["answerable"]]
        out[label] = {"rows": rows, "n": len(ans), "n_un": len(un),
                      "at1": sum(r["rank"] == 1 for r in ans), "at5": sum(r["rank"] is not None for r in ans),
                      "chars": median(r["chars"] for r in ans),
                      "un_returned": sum(r["returned"] > 0 for r in un),
                      "top_ans": median([r["top"] for r in ans if r["top"] is not None] or [0]),
                      "top_un": median([r["top"] for r in un if r["top"] is not None] or [0]),
                      "misses": [r["id"] for r in ans if r["rank"] is None]}
    return out


def main(book=False):
    queries = json.loads((HERE / "queries.json").read_text(encoding="utf-8"))
    res = evaluate(queries)
    lines, nums = [], {}
    for label, r in res.items():
        print(f"{label:24} top-1 {r['at1']:2}/{r['n']}  top-5 {r['at5']:2}/{r['n']}  median chars {r['chars']:6.0f}  "
              f"unanswerable with results {r['un_returned']}/{r['n_un']}  misses: {', '.join(r['misses'])}")
        if r["top_ans"]:
            print(f"{'':24} median top score: answerable {r['top_ans']:.2f}, unanswerable {r['top_un']:.2f}")
        lines.append(f"{label} & {r['at1']} & {r['at5']} & {r['chars']:,.0f} & {r['un_returned']}/{r['n_un']} \\\\")
    key = {"lookup v1 (lines)": "LOne", "lookup v2 (lines)": "LTwo", "BM25, lookup's lines": "BRaw",
           "BM25, lines": "BLines",
           "BM25, 500 characters": "BFive", "BM25, 1,500 characters": "BFifteen"}
    for label, r in res.items():
        k = key[label]
        nums |= {f"{k}AtOne": r["at1"], f"{k}AtFive": r["at5"], f"{k}Chars": f"{r['chars']:,.0f}",
                 f"{k}Misses": len(r["misses"]), f"{k}Un": r["un_returned"],
                 f"{k}TopAns": f"{r['top_ans']:.1f}", f"{k}TopUn": f"{r['top_un']:.1f}"}
    # Paired comparisons, as in Chapter 3, of being found in the top 5: the whole pipeline (BM25
    # on this chapter's lines minus lookup v2), and the scoring alone (BM25 on lookup's own lines).
    hit = lambda label: {r["id"]: [1 if r["rank"] is not None else 0] for r in res[label]["rows"] if r["answerable"]}
    for name, label in (("", "BM25, lines"), ("Raw", "BM25, lookup's lines")):
        c = stats.compare(hit(label), hit("lookup v2 (lines)"))
        print(f"\n{label} - lookup v2, top 5: {100 * c['diff']:+.1f} points (SE {100 * c['se']:.1f}, "
              f"95% interval {100 * c['ci'][0]:.1f} to {100 * c['ci'][1]:.1f}), {c['n']} questions", end="")
        nums |= {f"{name}Diff": f"{100 * c['diff']:.1f}", f"{name}DiffSE": f"{100 * c['se']:.1f}",
                 f"{name}DiffLo": f"{100 * c['ci'][0]:.1f}", f"{name}DiffHi": f"{100 * c['ci'][1]:.1f}"}
    print()
    # Could a score threshold tell the unanswerable questions apart? Keep only results scoring
    # above the best unanswerable one, and count the answerable questions that still get one.
    rows = res["BM25, lines"]["rows"]
    bar = max(r["top"] for r in rows if not r["answerable"])
    above = sum(r["top"] > bar for r in rows if r["answerable"] and r["rank"] is not None)
    print(f"BM25 lines: above the best unanswerable score ({bar:.2f}), {above} answerable questions keep a hit")
    nums |= {"Bar": f"{bar:.1f}", "AboveBar": above}
    # Why function words outweigh content words here: most line passages are rows of one table.
    units = passages(BOOK, 1)
    idf = BM25([t for _, t in units]).idf
    nums |= {"TripRows": sum(f == "trips_2026q1.md" and "| TR" in t for f, t in units),
             **{f"Idf{w.capitalize()}": f"{idf.get(w, 0):.2f}" for w in ("what", "the", "claim", "mileage", "van")}}
    first = next(iter(res.values()))
    nums |= {"Answerable": first["n"], "Unanswerable": first["n_un"], "Queries": len(queries),
             "Passages": len(passages(BOOK, 1)), "PassagesFive": len(passages(BOOK, 500)),
             "PassagesFifteen": len(passages(BOOK, 1500))}
    files = {"ch04_retrieval.tex": "\n".join(lines) + "\n",
             "ch04_rnumbers.tex": "".join(f"\\newcommand{{\\chfourR{k}}}{{{v}}}\n" for k, v in nums.items())}
    if book:
        BUILD.mkdir(exist_ok=True)
        for name, text in files.items():
            (BUILD / name).write_text(text, encoding="utf-8")
    return files


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main("--book" in sys.argv[1:])
