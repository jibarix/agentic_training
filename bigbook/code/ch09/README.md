# Chapter 9 companion code: spending inference compute

Python 3.10 or later, standard library only. Chapters 1, 3 and 4 (`../ch01`, `../ch03`, `../ch04`)
must sit next to this folder: the agent is Chapter 1's, the statistics and the scorer Chapter 3's,
and the tasks, the handbook, its tools and the agent's settings Chapter 4's. The tests need no model
and run in a few seconds. The experiment needs the model and several hours of GPU time.

| File | What it is |
|---|---|
| `sampling.py` | The ways of choosing. `Recorder` wraps a chat client and logs each call's tokens and the length of any thinking. `amount` reads the number on a run's last `Final answer:` line. `vote` is a majority vote on those amounts (runs without one abstain, ties broken at random), `vote_k` its exact average over every set of k runs, and `agreement` the share of runs that gave the winning amount. `judge` shows the same model the question and each run's tool results and last reply, and reads back one `Choice:` |
| `experiment.py` | Chapter 4's 30 long tasks, its full-context agent unchanged: ten runs with thinking off (seeds 1-10) and three with thinking on (seeds 1-3) per task, then the judge on each group of five thinking-off runs in two orders. 390 runs and 120 judge calls; `--resume` continues with the run's own settings |
| `report.py` | Turns a run folder into the chapter's table and numbers (`../../build/ch09_*`): pass@1 off and on, the vote of 5, the judge of 5, the oracle's pass@5, the generation-verification gap, pass^5, tokens and seconds, and paired differences |
| `test_ch09.py` | Tests with scripted replies: the amount parser, the vote and its estimator, the judge's parsing and evidence, the recorder, the experiment's settings, plan, rows and stop on a failed model call, and the report |
| `book.json` | Which run the chapter uses (`null` until there is one: the chapter then prints "--") |

Thinking on this model is on or off only: Ollama's `/api/show` gives `qwen3.5:4b-q4_K_M` the values
`[false, true]`, and through the OpenAI-compatible endpoint `"reasoning_effort": "none"` turns it
off and `"high"` on. There are no effort levels and no thinking budget to set.

## 1. Tests (no model needed)

From this folder (`bigbook/code/ch09`):

```
python -m unittest -v test_ch09
```

Expected: `Ran 27 tests ... OK`. Every model reply in them is one the tests wrote.

## 2. Smoke run

Serve the model as in Chapter 4's README, with a context window of at least 32,768 tokens
(`OLLAMA_CONTEXT_LENGTH=32768 ollama serve`), and check `ollama ps` shows it. Then one task, one
run of each setting and a judge of one:

```
python experiment.py --out results/my-smoke --off 1 --on 1 --k 1 --tasks meals_emp0103
```

## 3. Pilot

Three tasks, two runs of each setting, groups of two:

```
python experiment.py --out results/my-pilot --off 2 --on 2 --k 2 --tasks meals_emp0103,full_emp0104,billed_emp0101
python report.py results/my-pilot
```

It measures how long a thinking-on run takes and checks that the thinking is received
(`thinking_chars` above 0 for the `on` rows) and saved (`runs/*.thinking.json` not empty).
It also shows whether the server reports token usage: a count it doesn't report is shown as `--`,
not as zero. If a thinking-on run takes more than about 200
seconds, make two thinking-on runs per task in the full run instead of three (`--on 2`); the
chapter's numbers are then written only after `report.py`'s `ON` is changed to match. A pilot is
not the chapter's run.

## 4. The experiment

```
python experiment.py --out results/my-run
```

Every run's trace goes to `runs/<part>_<seed>_<task>_<cond>.json`; the judge reads them. Chapter 1's
trace keeps only the model's replies, so each call's thinking goes beside it, in
`runs/<part>_<seed>_<task>_<cond>.thinking.json`. A model call
that fails stops the experiment with no row for that run:

```
python experiment.py --out results/my-run --resume
```

The resume takes every setting from the manifest and refuses if the code, the tasks, the handbook or
the model's digest has changed, or if the server's window isn't the run's.

## 5. Labelling

The scorer reads the `Final answer:` line. A run with none, or with one the scorer can't read, has
`ok` null or false and may have no amount to vote with; read it and label it in
`results/my-run/adjudication.json`, with the amount the run gave if it gave one:

```
{"labels": [{"cond": "off", "id": "full_emp0104", "seed": 3, "label": true, "amount": "1234.5"}]}
```

Label every run the scorer failed or couldn't score, and check the automatic passes once for each
distinct answer to each task. Accept one unambiguous final value in the right unit or with none;
reject conflicting values, a wrong unit or an unfinished answer. Never take the answer from the
run's thinking or repair its arithmetic. Record the amount the run stated even when it is wrong,
and `"amount": null` when it stated none unambiguously; add a `"why"` for each label and say who
drafted and who checked it (`"drafted": "AI", "checked": "owner"`). Labels apply to the generated
runs only; the judge's choices are scored through them. `report.py` also gives each way's mean
from the scorer and the parser alone (`Raw...`), beside the labelled results.
`report.py` writes the chapter's numbers only from a complete run of the chapter's design;
`python report.py results/my-run` prints any run's summary. Then name the run in `book.json`
(`{"run": "results/my-run"}`) and write the chapter's numbers:

```
python report.py
```

## What the run does not show

Effort levels and thinking budgets (the model has neither), trained outcome or process verifiers,
tree or beam search, revision by a fine-tuned model, allocation by difficulty (30 tasks are too few
to bin), execution as a verifier (Chapter 7 has it), how frontier models behave, or anything past
ten samples. Thirty tasks detect only large differences.
