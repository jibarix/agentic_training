# Chapter 10 companion code: improving the agent's policy

Python 3.10 or later, standard library only. Chapters 1, 3, 4 and 9 (`../ch01`, `../ch03`, `../ch04`,
`../ch09`) must sit next to this folder: the agent is Chapter 1's, the statistics and the scorer
Chapter 3's, the tasks, handbook, tools, settings and recorded run Chapter 4's, and the call recorder
Chapter 9's. Nothing here trains a model or needs a GPU except the experiment's agent runs, which
need the model and a few hours of GPU time. The tests need no model and run in a second.

| File | What it is |
|---|---|
| `optimise.py` | The split of Chapter 4's 30 long tasks into 15 training and 15 held-out tasks (`split`), arm B's worked examples taken from passing training runs in Chapter 4's run (`bootstrap`, `render_demo`, `with_demos`), and arm C's reflection: the same model reads up to three failed training runs with the expected answer and proposes a new instruction (`REFLECT`, `failure`, `minibatch`, `reflect`), which is refused if it has no `<instructions>` block, is over 2,000 characters or names an employee or trip ID in any case (`parse_instruction`; it catches those IDs only, not other task-specific detail). `--demos 0` gives arm B no examples |
| `split.json` | The split, fixed and recorded: per kind of task, tasks sorted by their right runs in Chapter 4's full-context run, neighbours paired, one of each pair to each side at random (seed 10) |
| `offline.py` | What weight updates would start from, measured on Chapter 4's run with no model: the share of tasks whose group of runs would all pass or all fail (`degenerate`), the inference bill of an RL run's rollouts (`bill`), and the fine-tuning file (`sft_rows`) |
| `sft_train.jsonl` | Written by `python offline.py`: the passing runs of training tasks as chat messages with the agent's tool schemas, a weight of 1 on the model's turns and 0 on the rest. An intermediate export, not trained on: a training job would first render it with the model's serving template, tokenise it, build the assistant-token mask and check it, which needs the tokeniser (an install) |
| `experiment.py` | The search (four reflections in turn, each valid proposal run once on the 15 training tasks, the best frozen) and then arms A, B and C on the 15 held-out tasks, ten seeds each: at most 60 + 450 runs and 4 reflection calls. `--resume` continues with the run's own settings |
| `report.py` | Turns a run folder into the chapter's table and numbers (`../../build/ch10_*`): each arm's success, tokens and seconds, the paired differences B - A and C - A, the search's result, and the offline numbers, which are written whether or not there is a run |
| `test_ch10.py` | Tests with scripted replies: the split, the worked examples, the reflection and its checks, the offline numbers and the exported file, the experiment's settings, plan, rows and stop on a failed model call, and the report |
| `book.json` | Which run the chapter uses (`null` until there is one: the chapter then prints "--" for the run's numbers) |

The defaults are constants and flags that are easy to change: `SPLIT_SEED` in `optimise.py`, the
reflection's `MAX_CHARS` and minibatch size, `--candidates`, `--seeds` and `--demos` in
`experiment.py`, and `SEEDS`, `CANDIDATES`, `DEMOS` in `report.py`, which must match the run the
chapter uses.

## 1. Tests (no model needed)

From this folder (`bigbook/code/ch10`):

```
python -m unittest -v test_ch10
python offline.py
```

Expected: `Ran 30 tests ... OK`, and `wrote sft_train.jsonl`. Every model reply in the tests is one
the tests wrote.

## 2. Smoke run

Serve the model as in Chapter 4's README, with a context window of at least 32,768 tokens
(`OLLAMA_CONTEXT_LENGTH=32768 ollama serve`), and check `ollama ps` shows it. Then one reflection,
one training task and one held-out task, one seed:

```
python experiment.py --out results/my-smoke --candidates 1 --seeds 1 --train-tasks meals_emp0110 --tasks meals_emp0112
```

## 3. Pilot

One reflection on two training tasks, then two held-out tasks with two seeds (2 + 12 runs):

```
python experiment.py --out results/my-pilot --candidates 1 --seeds 2 --train-tasks meals_emp0110,full_emp0111 --tasks meals_emp0112,full_emp0104
python report.py results/my-pilot
```

It checks that the reflection gives a valid `<instructions>` block (the `reflect` row's `why` is
empty), that arm B's prompt fits (`max_prompt` well under the window), and how long a run of each arm
takes. A pilot is not the chapter's run.

## 4. The experiment

```
python experiment.py --out results/my-run
```

Every run's trace goes to `runs/<part>_<seed>_<task>_<cond>.json`; the reflections read the training
ones. A model call that fails stops the experiment with no row for that run:

```
python experiment.py --out results/my-run --resume
```

The resume takes every setting from the manifest and refuses if the code, the split, Chapter 4's run,
the handbook or the model's digest has changed, or if the server's window isn't the run's. Arm C's
prompt, the best new proposal on the training tasks (Chapter 4's prompt is a parent but never the final
choice), is frozen in the manifest (`frozen`) before the first held-out run. `--seeds 5` halves the
held-out runs (285 in all); the chapter's numbers are then written only after `report.py`'s `SEEDS`
is changed to match.

## 5. Labelling

The scorer reads the `Final answer:` line. A held-out run with none, or with one the scorer can't
read, has `ok` null or false; read it and label it in `results/my-run/adjudication.json`:

```
{"labels": [{"cond": "B", "id": "full_emp0104", "seed": 3, "label": true}]}
```

Label every held-out run the scorer failed or couldn't score, and check the automatic passes once
for each distinct answer to each task. Accept one unambiguous final value in the right unit or with
none; reject conflicting values, a wrong unit or an unfinished answer. Never repair the run's
arithmetic. Add a `"why"` for each label and say who drafted and who checked it
(`"drafted": "AI", "checked": "owner"`). Label without looking at which arm a run came from where you
can: the `cond` is in the row, so draft the labels from the answers alone. Labels apply to held-out
runs only; the search chose arm C by the scorer alone, as it ran, and its rows are left as they are.
`report.py` also gives each arm's mean from the scorer alone (`Raw...`), beside the labelled results.
`report.py` writes the run's numbers only from a complete run of the chapter's design;
`python report.py results/my-run` prints any run's summary. Then name the run in `book.json`
(`{"run": "results/my-run"}`) and write the chapter's numbers:

```
python report.py
```

## What the run does not show

Any change to the model's weights: no fine-tuning, distillation or RL is run, and the packages they
would need (`torch`, `transformers`, `peft`, `trl`, `bitsandbytes`, `accelerate`, `datasets`,
`unsloth`, `huggingface_hub` with the `Qwen/Qwen3.5-4B` weights, and `llama.cpp` if the GGUF route back to Ollama
is taken; direct Safetensors import is the other, equally untested route) are not installed. Nor does it show full GEPA (one module, no Pareto pool, four
proposals), MIPROv2's joint search of instructions and examples, how the prompts behave on another
model or on tasks unlike the handbook's, or small gains: on illustrative planning estimates (Chapter 4's within-task variance, independent arms,
no variation in the effect between tasks), fifteen held-out tasks detect about 12 points at ten seeds.
The held-out tasks are held out of Chapter 10's optimisation, not unseen: Chapter 4's results shaped the split.
