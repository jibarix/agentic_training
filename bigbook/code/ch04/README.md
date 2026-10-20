# Chapter 4 companion code: context, memory and retrieval

Python 3.10 or later, standard library only. Chapters 1 and 3 (`../ch01`, `../ch03`) must sit next
to this folder: the agent is Chapter 1's, and the scorer and statistics are Chapter 3's. There are
two parts. The retrieval test needs no model and runs in a second. The long-task experiment needs
the model and a few hours of GPU time.

| File | What it is |
|---|---|
| `handbook/` | A larger fictional handbook: five prose policies (written by hand) and four tables (generated) |
| `make_handbook.py` | Writes the four tables and `tasks_long.json` from a fixed seed; running it again writes identical files |
| `tasks_long.json` | 30 long tasks in 5 clusters, each needing 2 to 5 trips, their rates, and arithmetic; the answers come from the tables |
| `handbook_tools.py` | Chapter 1's tools, pointed at this handbook |
| `context.py` | The four context policies (full, drop, mask, compact), the token estimate, and the client wrapper that sends a policy's view |
| `bm25.py` | BM25 (Robertson and Zaragoza 2009, Eqs. 3.3 and 3.15) and the passage splitter |
| `queries.json` | 50 retrieval questions: 43 with the file and a phrase the answering passage must contain (one is a false premise, answered by the rule that refutes it), 7 the handbook can't answer |
| `retrieval.py` | Runs the 50 questions through both versions of Chapter 1's lookup, through BM25 on exactly the lines lookup indexes, and through BM25 on this chapter's passages at three sizes |
| `test_ch04.py` | Tests of the policies on scripted runs (including failed, empty and oversized summaries and their token costs), the fact coverage, BM25 against the formula, the passages, the task answers, the report and the resume check |
| `experiment.py` | Runs the long tasks under full, drop and compact (mask with `--conds`), interleaved task by task; `--resume` continues with the run's own settings |
| `report.py` | Turns a run folder into the chapter's table and numbers (`../../build/ch04_*`) |
| `book.json` | Which run the chapter uses (`null` until there is one: the chapter then prints "--") |

## 1. Test and retrieval (no model needed)

From this folder (`bigbook/code/ch04`):

```
python -m unittest -v test_ch04
python retrieval.py
```

Expected: `Ran 25 tests ... OK`. Then one line per search with its top-1 and top-5 counts out of 43,
the median characters it returns, how many of the 7 unanswerable questions still got results, and
the questions it missed; last, two paired differences against lookup v2: BM25 on this chapter's
lines (the whole pipeline) and BM25 on lookup's own lines (the scoring alone).
`python retrieval.py --book` also writes the chapter's retrieval table.

## 2. Smoke run: choose the budget

Serve the model as in Chapter 1's README, but with a context window of at least 32,768 tokens.
Ollama's default is 4,096, and it cuts a longer prompt without an error, so the server, not the
policy, would decide what the model sees. Quit the Ollama app, then:

```
OLLAMA_CONTEXT_LENGTH=32768 ollama serve          # PowerShell: $env:OLLAMA_CONTEXT_LENGTH=32768; ollama serve
```

The experiment loads the model, reads the window from `/api/ps`, records it in the manifest, and
refuses to start if it is smaller (or, on resume, different). Then run one task with no budget,
and read the largest prompt the server reports:

```
python experiment.py --out results/my-smoke --seeds 1 --conds full --tasks full_emp0104 --budget 0
```

`max_sent` in the printed line is the largest prompt the agent's history reached. Choose a budget
about half of the typical `max_sent`, so that most runs cross it once or twice, and then smoke-test
the policies with it:

```
python experiment.py --out results/my-smoke2 --seeds 1 --tasks meals_emp0103,full_emp0104 --budget 3000
```

## 3. Full run

```
python experiment.py --out results/my-run --budget 3000            # 30 tasks x 3 seeds x 3 conditions = 270 runs
python experiment.py --out results/my-run --resume                 # after an interruption
```

A resume takes every setting (budget, conditions, tasks, seeds, model, temperature) from the run's
manifest and refuses any argument that disagrees with it. As in Chapter 3, it also refuses if the
code, the tasks or the handbook have changed, and here also if the server can't confirm the model's
digest. A run never overwrites an existing folder.

Each line of `traces.jsonl` holds the run's score; its tokens, including every summary call's, even
rejected ones and ones whose main call then failed; every call's estimated and reported prompt size
and whether it was over the budget (the budget triggers a policy but doesn't bound what it sends);
every policy event, with each summary and the text it was written from; and, for each summary, how
many of the task's facts it was given, how many of their values it kept, and how many it kept on a
line that names their trip, city or vehicle.

## 4. Label, then report

Label the unscored and failed answers in the run's `adjudication.json`, as in Chapter 3. Then name
the run in `book.json` and run `python report.py`. `python report.py results/my-run` prints the
summary without writing anything.
