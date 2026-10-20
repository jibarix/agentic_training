# Chapter 3 companion code: tell a real improvement from noise

Python 3.10 or later, standard library only. Chapter 1's code (`../ch01`) must sit next to this
folder: the experiment runs its agent, and `measure_scorer.py` reads the hand-labelled runs of
Chapters 1 and 2. The question is whether Chapter 1's revised `lookup` (v2) beats the first one
(v1), on 40 held-out tasks with five runs each, plus a comparison of v2 with itself.

| File | What it is |
|---|---|
| `stats.py` | Standard errors (plain, clustered, paired), confidence intervals, the variance split, minimum detectable effect and tasks needed (Miller 2024), pass@k (Chen et al.) and pass^k (Yao et al.) |
| `score.py` | Chapter 1's scorer with one change: one descriptive word may sit between the number and the unit |
| `measure_scorer.py` | Scores the 180 hand-labelled answers of Chapters 1 and 2 with both scorers and counts the disagreements |
| `tasks_heldout.json` | The 40 held-out tasks, 8 in each of 5 clusters, frozen before the first run |
| `test_ch03.py` | Tests of the statistics (against Miller's worked numbers and brute force), the scorer and the task file |
| `experiment.py` | Runs v1, v2 and v2_again (seeds 101+) on the held-out tasks, and v1 and v2 on Chapter 1's tasks, interleaved task by task; `--resume` continues an interrupted run |
| `report.py` | Turns a run folder into the chapter's tables and numbers (`../../build/ch03_*`) |
| `book.json` | Which run the chapter uses |

## 1. Test (no model needed)

From this folder (`bigbook/code/ch03`):

```
python -m unittest -v test_ch03
python measure_scorer.py
```

Expected: `Ran 12 tests ... OK`, then one line per scorer. The revised scorer passes 84 of the
labelled answers, all of them right, and fails no right answer that has a `Final answer:` line.

## 2. Smoke run

Serve the model as in Chapter 1's README, then:

```
python experiment.py --out results/my-smoke --seeds 1 --tasks pd_seattle3,denver
```

Expected: five lines (v1, v2 and v2_again for the held-out task; v1 and v2 for Chapter 1's).

## 3. Full run

```
python experiment.py --out results/my-run          # 700 runs; about 6 hours on my machine
python experiment.py --out results/my-run --resume # after an interruption
```

A resume refuses to continue if the code, the tasks or the handbook have changed since the run
started (their hashes are in `manifest.json`). A run never overwrites an existing folder.

## 4. Label, then report

Read every answer the scorer leaves unscored (no `Final answer:` line) and every one it fails,
and record your label in the run's `adjudication.json`, in the format of Chapter 2's
(`../ch02/results/2026-10-16-run1/adjudication.json`: a `method`, the label `kinds`, and one entry
per labelled run):

```
{"cond": "v1", "id": "pd_chicago_cap", "seed": 1, "auto": false, "label": true,
 "reason": "States 230 USD per night; the scorer does not read USD/night as a unit.", "kind": "..."}
```

The report uses a label where there is one and the scorer's verdict otherwise:

```
python report.py results/my-run    # print the numbers only
python report.py                   # the run in book.json; writes ../../build/ch03_*
```

## 5. Rebuild the chapter (from `bigbook/`)

```
python snip.py
cd code/ch03 && python report.py && cd ../..
python check.py
pdflatex -disable-installer -interaction=nonstopmode bigbook.tex   # twice
```

## Licence

The code in this folder is released under the MIT licence (see `../LICENSE`).
