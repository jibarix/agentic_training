# Chapter 1 companion code: a bounded tool-using agent

Python 3.10 or later, standard library only; nothing to install for the tests. The harness
(`agent.py`) is 146 lines; with the tools (192) and the client (48) the implementation is 386.

| File | What it is |
|---|---|
| `agent.py` | The loop, the dispatcher (tool failures become observations), the budgets and the trace |
| `tools.py` | `lookup` (v2, plus `lookup_v1` as first written), `read_file` (sandboxed), `calculator` (exact, bounded, no `eval`) |
| `llm.py` | `ChatClient` for an OpenAI-style `/chat/completions` endpoint; `ScriptedClient` for tests |
| `handbook/` | The fictional ACME handbook (the environment) |
| `tasks.json` | Ten questions, each with a numeric answer and the units that count |
| `test_agent.py` | Offline tests of the loop, the failure paths, the tools and the scorer |
| `experiment.py` | Runs no-tools, agent with lookup v1 and agent with lookup v2; writes one new run folder |
| `report.py` | Turns a run folder into the chapter's tables and traces (`../../build/`) |
| `book.json` | Which run and which traces the chapter uses |
| `results/2026-10-16-run1/` | The run reported in the chapter, kept as evidence (see below) |

## 1. Test the harness (no model needed)

Run from this folder (`bigbook/code/ch01`):

```
python -m unittest -v test_agent
```

Expected: `Ran 30 tests ... OK` in well under a second.

## 2. Serve a model

The chapter used Ollama 0.40.1 with `qwen3.5:4b-q4_K_M` on an 8 GB laptop GPU:

```
ollama pull qwen3.5:4b-q4_K_M
ollama serve                     # if it is not already running; listens on localhost:11434
```

Another server works if it implements `/chat/completions` with tool calls. Point the experiment
at it with `--base-url` and `--model`, and pass `--api-key` if it needs one. Every request
includes `{"reasoning_effort": "none"}` by default, which switches off thinking on this model under
Ollama. Servers and models handle that option differently; pass `--extra '{}'` to send nothing extra.

## 3. Smoke run: one question, one seed

```
python experiment.py --out results/smoke --tasks denver --seeds 1 --conds v2
```

Expected: one line such as `1 v2       denver     answered    OK  steps=3 tok=2200`, then a
summary. The answer, trace and settings are in `results/smoke/`: `runs.json` (one record per run),
`traces.jsonl` (the same records with every model turn, call id, observation and end event) and
`manifest.json` (model digest, server version, prompts, settings and hashes of the code and
handbook). Read the trace with:

```
python report.py --show results/smoke v2:denver:1
```

`--show` prints the trace and writes nothing, so the chapter's build files are untouched.

## 4. Full run

```
python experiment.py --out results/my-run           # 10 tasks x 3 seeds x 3 conditions
```

About 40 minutes on the laptop GPU above. A run never overwrites an existing folder.

Scoring reads only the answer's last `Final answer: <number> <unit>` line, which the prompts ask
for. The line must hold one number and one of the task's units and nothing else; the number is
compared as a decimal. An answer without that line is left unscored (`ok: null`) for a person to label.

## 5. Rebuild the chapter (from `bigbook/`)

```
python snip.py                                  # listings from the code
cd code/ch01 && python report.py && cd ../..    # tables and traces from the run in book.json
python check.py                                 # read-only: listings, tables, traces, replay, labels
pdflatex -disable-installer -interaction=nonstopmode bigbook.tex   # twice, for the contents
```

## The reported run

`results/2026-10-16-run1/` is the run behind every number in the chapter. It predates the review
that produced the current code, so it differs in four ways, each recorded in the folder:

- Its prompts did not ask for a `Final answer:` line, and its scorer accepted any matching
  number. Every answer was therefore labelled by hand (`adjudication.json`); one automatic pass
  was overturned.
- Its calculator printed six significant figures (`2024.7552` as `2024.76`). `check.py` lists the
  five observations this affects and fails on any other difference.
- Its traces record no call ids on the model side and no end events.
- Its `manifest.json` was written after the run, from the same machine on the same day. Its
  hashes identify the archived files; that they are the code that ran rests on my record, backed
  by the archived tools reproducing all 147 recorded observations.

`code/` in that folder holds the code and handbook as they were when it ran.

## Licence

The code in this folder is released under the MIT licence (see `../LICENSE`).
