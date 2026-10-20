# Chapter 5 companion code: workflows, planning and recovery

Python 3.10 or later, standard library only. Chapters 1, 3 and 4 (`../ch01`, `../ch03`, `../ch04`)
must sit next to this folder: the agent and tools are Chapter 1's, the scorer and statistics
Chapter 3's, and the handbook and the 30 long tasks Chapter 4's. The tests need no model and run in
under a minute. The experiment needs the model and several hours of GPU time.

| File | What it is |
|---|---|
| `durable.py` | The journal (append-only JSON lines, fsynced, a torn last line cut off) and `Run`, which numbers every model call and tool call, records its result, and on resume replays recorded calls and checks that each asks for what was recorded; a call that fails after its retries stops the run (`Halted`) with nothing recorded for it |
| `ledger.py` | The one tool with an effect: `file_claim` writes a claim to a ledger file, and a claim whose idempotency key the ledger already holds writes nothing; a torn last line is dropped; amounts must be above zero. One writer at a time |
| `faults.py` | Which errors are transient, capped exponential backoff with full jitter, a wait budget, and `Flaky`, which fails a seeded share of calls on purpose, drawn by call number so a resumed run meets the same failures |
| `strategies.py` | Three ways to answer a task: `agent` (Chapter 1's agent), `plan` (plan, run each step with a fresh agent, replan a failed step at most twice) and `workflow` (code fixes the steps; the model fills two kinds of slot) |
| `run.py` | One durable run of one strategy on one task, ending with the claim, filed by code through the journal with a key, only for one amount in dollars above zero (`strategies.final_amount`) |
| `test_ch05.py` | Tests with a model that is always right: a crash at every call and every point of four runs, then a resume that must give the clean run's answer and one claim; a call that fails for good, and the resume that finishes the run; the claim filed twice without a key; a torn ledger line; retries; the same faults after a resume; the plan loop's stops and token budget; the amounts that may be claimed; the workflow's reading of the trip log, and its stop when that read fails or finds no table; the experiment and report on two tasks and on one |
| `experiment.py` | Three parts: `compare` (the three strategies, 30 tasks, 3 seeds), `crash` (each seed-1 run's journal cut at a seeded call, then resumed) and `faults` (a fifth of tool calls failing, no retries); `--resume` continues with the run's own settings |
| `report.py` | Turns a run folder into the chapter's table and numbers (`../../build/ch05_*`) |
| `book.json` | Which run the chapter uses (`null` until there is one: the chapter then prints "--") |

## 1. Tests (no model needed)

From this folder (`bigbook/code/ch05`):

```
python -m unittest -v test_ch05
```

Expected: `Ran 39 tests ... OK`. The resume tests kill each run at each of its calls, at four points
of each call (before it, after its effect but before the journal knows, half-way through writing
the journal line, and after it is recorded), so `TestResume` alone makes several hundred runs.

## 2. Smoke run

Serve the model as in Chapter 4's README, with a context window of at least 32,768 tokens
(`OLLAMA_CONTEXT_LENGTH=32768 ollama serve`). Then one task through all three parts:

```
python experiment.py --out results/my-smoke --seeds 1 --tasks meals_emp0103
```

Each line shows the part, seed, strategy, task, status, whether the scorer passed it, the model
calls (`calls`), the journal's calls made live rather than replayed (`live`), the tokens and the
seconds. Standard errors need two tasks or more, so a one-task report prints "--" for them.
A crash line adds where the journal was cut (`cut=7/19`) and whether the resumed answer is the
clean run's (`same=True`); a fault line adds how many failures were injected.

## 3. The experiment

```
python experiment.py --out results/my-run
```

About 420 runs: 270 compared, 90 resumed after a crash and 60 with faults. If it is stopped, `--resume` continues it: the runs already in `traces.jsonl` are
skipped, and a run that was cut off part way continues from its journal. A call that still fails
after its retries (the model server went away) stops the experiment with that run's journal kept and
no row written; `--resume` continues it. The resume refuses if
the code, the tasks or the model's digest has changed, or if the server's window isn't the run's.

Then read the runs the scorer couldn't pass or that gave no answer, and record a label for each in
`results/my-run/adjudication.json`:

```
{"labels": [{"part": "compare", "cond": "plan", "id": "meals_emp0103", "seed": 2,
             "label": false, "why": "..."}]}
```

Name the run in `book.json` and run `python report.py` to write the chapter's table and numbers;
`python report.py results/my-run` prints them without writing anything.

## What is measured

- **compare:** right answers per strategy, with Chapter 3's per-task means, standard errors,
  pass^k and paired differences (plain and clustered by task family); mean tokens and model calls,
  and median seconds over runs never interrupted. Rows also keep `journal_calls` (model, tool and
  claim calls) and `tool_calls`.
- **crash:** for each resumed run, whether its answer is the clean run's, whether it is right, the
  share of the clean run's tokens the resume spent, and the claims in `ledger_crash.jsonl` (one per
  run with an amount above zero, none repeated).
- **faults:** right answers with failures and no retries, against the same tasks' clean seed-1 runs;
  the failures injected, counted from the journals, out of the tool calls.

The ledger keys show whether any claim was filed twice; `report.py` counts repeated keys.
