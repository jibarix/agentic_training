# Chapter 8 companion code: several agents, and A2A

Python 3.10 or later, standard library only. Chapters 1, 3 and 4 (`../ch01`, `../ch03`, `../ch04`)
must sit next to this folder: the agent is Chapter 1's, the statistics and the scorer Chapter 3's,
and the handbook, its tools and the model checks Chapter 4's. The tests need no model and run in a
few seconds. The experiment needs the model and several hours of GPU time.

| File | What it is |
|---|---|
| `strategies.py` | The three arms. `single`: Chapter 1's agent with every tool. `orchestrator`: a lead with two tools, the calculator and `delegate`, whose four arguments (objective, inputs, return, done when) fill the sub-task contract; each worker is a fresh agent with the handbook tools that ends with a JSON `Result:` line. At most eight sub-tasks and 250,000 tokens per run; workers can't delegate. `pipeline`: a splitter lists sub-questions whose amounts add up to the answer, a fresh worker answers each, each asked once more if it gives no amount, and code adds them |
| `a2a.py` | A minimal A2A v1.0.1 server and client: the Agent Card with ETag and cache headers, the JSON-RPC binding with `SendMessage` (blocking) and `GetTask`, the `A2A-Version` header, and the error codes for what it leaves out (streaming, push, cancel, list, multi-turn, authentication, signed cards). It binds to 127.0.0.1 only |
| `make_tasks.py` | Builds `tasks.json` from Chapter 4's handbook: 24 decomposable tasks (meals, mileage, full, billed; six each) and 12 sequential ones (chain_meals, chain_lodging; six each), with each decomposable task's trips and per-trip amounts. No employee from Chapter 4's tasks is used; the meals and mileage tasks share three employees |
| `test_ch08.py` | Tests with scripted replies: the parsers, the worker, the orchestrator's contract, limits and budget, the pipeline's retries, the A2A server and client on a free local port, the tasks against the handbook, the experiment's plan and its stop on a failed model call, and the report |
| `experiment.py` | 36 tasks × three arms × five seeds, arms interleaved (540 runs), then the orchestrator through A2A on 12 tasks at seed 1; `--resume` continues with the run's own settings |
| `report.py` | Turns a run folder into the chapter's tables and numbers (`../../build/ch08_*`) |
| `book.json` | Which run the chapter uses (`null` until there is one: the chapter then prints "--") |

## 1. Tests (no model needed)

From this folder (`bigbook/code/ch08`):

```
python -m unittest -v test_ch08
```

Expected: `Ran 40 tests ... OK`. Every model reply in them is one the tests wrote. The A2A tests
start a server on a free port of 127.0.0.1 and stop it. `python make_tasks.py` rebuilds
`tasks.json` from the handbook; a test checks that it is unchanged.

## 2. Smoke run

Serve the model as in Chapter 4's README, with a context window of at least 32,768 tokens
(`OLLAMA_CONTEXT_LENGTH=32768 ollama serve`), and check `ollama ps` shows it. Then two tasks, every
arm, one seed, and the A2A part on them:

```
python experiment.py --out results/my-smoke --seeds 1 --tasks meals_emp0140,chain_meals_tr0067
```

Each line shows the part, seed, arm, task, status, whether the answer was right (`OK`, `BAD`, or
`?` for no `Final answer:` line), the agents, model calls, tokens and seconds.

## 3. Pilot

Before the full run, five tasks (one of each kind but mileage), three arms, two seeds, no A2A:

```
python experiment.py --out results/my-pilot --seeds 2 --parts compare --tasks meals_emp0140,full_emp0119,billed_emp0123,chain_meals_tr0067,chain_lodging_tr0179
python report.py results/my-pilot
```

It checks that every arm finishes and measures how hard the tasks are for the single agent. Kim and
colleagues found coordination helping least above about 45%; whether that carries over to a 4B
model on this handbook is a hypothesis the full run tests. A pilot is not the chapter's run.

## 4. The experiment

```
python experiment.py --out results/my-run
```

552 runs: 540 compared, then 12 through A2A. Every agent's trace (lead, workers, splitter, parts)
goes to `runs/<part>_<seed>_<task>_<arm>.json`. A model call that fails stops the experiment with no
row for that run:

```
python experiment.py --out results/my-run --resume
```

The resume takes every setting from the manifest and refuses if the code, the tasks, the handbook or
the model's digest has changed, or if the server's window isn't the run's.

## 5. Labelling

The scorer reads the `Final answer:` line. A run with none, or with one the scorer can't read, has
`ok` null or false; read it and label it in `results/my-run/adjudication.json`:

```
{"labels": [{"part": "compare", "cond": "orchestrator", "id": "full_emp0119", "seed": 3, "label": true}]}
```

For the chapter's discussion, read a sample of failed orchestrator and pipeline runs in `runs/` and
note the failure modes by MAST's names (Cemri et al.). Their paper is CC BY-NC-ND: use the names,
and don't copy its definitions into the run folder.

`report.py` writes the chapter's numbers only from a complete run of the chapter's design; `python
report.py results/my-run` prints any run's summary. Then name the run in `book.json`
(`{"run": "results/my-run"}`) and write the chapter's numbers:

```
python report.py
```

## What the run does not show

One GPU answers one call at a time, so the workers run one after another: the run measures
accuracy, tokens and calls, not the time parallel agents save. All agents are the same 4B model,
so nothing here tests specialisation by model. The A2A part runs on one machine with no
authentication; it shows the protocol's shape, not how to run it between parties who don't trust
each other. Thirty-six tasks detect only large differences, and each set alone only very large ones.
