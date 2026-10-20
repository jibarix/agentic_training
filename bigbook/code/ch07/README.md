# Chapter 7 companion code: coding agents

Python 3.10 or later, standard library only. Chapters 1, 3 and 5 (`../ch01`, `../ch03`, `../ch05`)
must sit next to this folder: the agent is Chapter 1's, the statistics Chapter 3's, and the retries,
journal helpers and meters Chapter 5's. The tests need no model and run in about fifteen seconds.
The experiment needs the model and several hours of GPU time, and it runs code the model writes.

| File | What it is |
|---|---|
| `repo/` | The repository the agent works on: a small expense-claims package (`expenses/`, five modules, 234 lines), 52 `unittest` tests and an `AGENTS.md` with the test command and three rules. Written for this book and never published |
| `runner.py` | Runs the given test ids (or all) in a repository and prints their outcomes as JSON on the last line; the grader and the pipeline call it in a child process |
| `tasks.py` | The 24 bugs, each a few exact edits to one module with an issue written for it; `make_tasks` keeps a bug only if the clean repository passes every test and the mutated one fails one or more, which gives its FAIL_TO_PASS and PASS_TO_PASS lists (`tasks.json`). `start` makes a task's starting folder with the FAIL_TO_PASS tests taken out; `grade` copies the work's files outside `tests/` to a fresh folder with the original `tests/` and runs both lists, with a time limit |
| `harness.py` | The two loops' tools: a bare `shell` (output, exit status, 30-second limit), and an ACI after SWE-agent (`view` 100 numbered lines, `search` with at most 50 results, `edit` by line range, put back with the error if the file no longer compiles, and `run_tests`, which takes only dotted test names under `tests`; no shell). The same deny-first command and path rules for both, with every refusal and every change to `tests/` recorded. `Collapsed` cuts the tool outputs before the last five to one line before the model sees them |
| `agentless.py` | The fixed pipeline after Agentless: the model names a file, then the functions to change from the file's skeleton, then writes four search/replace repairs, each from its own seed; each repair that applies and compiles is run against the visible tests, and among those that break fewest the most common (after normalising with `ast`) is kept |
| `test_ch07.py` | Tests with scripted replies: the tasks and every issue's stated values, the hidden tests, the grader (a fix, a regression, emptied tests, a hang, a forged result, class fixtures and a failing teardown, and the asserts rebound: it is fooled, and the patch is flagged), the deny rules, the ACI's edit guard, the context rule, the pipeline's vote, one run of each arm, and the report |
| `experiment.py` | 24 tasks × three arms × five repeats, arms interleaved; `--resume` continues with the run's own settings |
| `report.py` | Turns a run folder into the chapter's tables and numbers (`../../build/ch07_*`) |
| `book.json` | Which run the chapter uses (`null` until there is one: the chapter then prints "--") |

## 1. Tests (no model needed)

From this folder (`bigbook/code/ch07`):

```
python -m unittest -v test_ch07
```

Expected: `Ran 38 tests ... OK`. Every command and edit the tests make is one the tests wrote.
`python tasks.py` rebuilds `tasks.json` from the mutations; a test checks that it is unchanged.

## 2. Where to run the experiment

Every arm runs code the model writes. The shell arm runs its commands; all three arms run the
tests on code it edited. The deny rules in `harness.py` check the text of a command, as a coding
agent's permission rules do, and they are not a security boundary: `python -c` with a few lines
of `os` calls can go anywhere its user can. On native Windows nothing stronger is available
without installing something (Claude Code's own sandbox doesn't run there). The rules, the
cleaned environment (no variables of yours beyond those Windows needs to start a program) and the
time limits make a mistake less likely, not impossible.

So run the experiment where a stray command can do no harm: a virtual machine, a container, a
WSL distribution or a spare user account with nothing of value, with the network off if you can.
`experiment.py` refuses to start without `--run-model-code`, which says you have done that.

The task files (`tasks.json`, `tasks.py`) hold the answers and sit in this folder, above every
run's folder (`results/<run>/work/<run id>`). A command that reaches them is solution
contamination in NIST's sense; the path rules refuse `..`, but code the model writes can still get
there. Look for `tasks.json` in the commands in `traces.jsonl` before trusting a shell-arm result.

The grader puts the original tests back, so editing them gains nothing. But the code under test
runs in the same process as the tests, and code written to fool the runner (rebinding
`unittest`'s asserts, printing a result line of its own) could. Each row's `suspect` lists the
added lines of its patch that touch `unittest`, `sys`, `builtins`, `print` and the like, which the
repository's own code never does; read every flagged patch before trusting a result.

## 3. Smoke run

Serve the model as in Chapter 4's README, with a context window of at least 32,768 tokens
(`OLLAMA_CONTEXT_LENGTH=32768 ollama serve`). Then one task, every arm:

```
python experiment.py --run-model-code --out results/my-smoke --repeats 1 --tasks dates_saturday
```

Each line shows the repeat, task, arm, status, whether the bug was fixed (`FIXED`), the
FAIL_TO_PASS and PASS_TO_PASS tests that pass out of how many, the steps, whether a command was
refused, whether `tests/` was changed, the tokens and the seconds.

## 4. The experiment

```
python experiment.py --run-model-code --out results/my-run
```

360 runs. Each run works in its own folder under `work/`, which is kept, so its final state can
be inspected; a folder left by a run that was killed is deleted and the run starts again. A model
call that still fails after its retries stops the experiment with no row for that run. The resume
refuses if the code, the tasks, the repository or the model's digest has changed, or if the
server's window isn't the run's.

Nothing needs labelling: the grader decides every run. `report.py` writes the chapter's numbers
only from a complete run (every repeat, task and arm its manifest names); `python report.py
results/my-run` prints a partial one with its `k`. Then name the run in `book.json`
(`{"run": "results/my-run"}`) and write the chapter's numbers:

```
python report.py
```

## What the run does not show

The repository is small and every bug is in one module, most of them one line; real issues
touch more code and come with less help. The tests the grader runs are the specification, and a
fix that passes them can still be wrong (SWE-bench Verified's audit). Agentless here leaves out
its reproduction tests and its several localisations, so the pipeline is weaker than the
paper's. And one 4B model can't say which design is best for a stronger one: the sources expect
the best point to move as models improve.
