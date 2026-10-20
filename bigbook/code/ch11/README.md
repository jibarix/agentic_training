# Chapter 11 companion code: deploy, operate and optimise cost

Python 3.10 or later, standard library only. Chapters 1, 3, 4 and 5 (`../ch01`, `../ch03`, `../ch04`,
`../ch05`) must sit next to this folder: the agent and its client are Chapter 1's, the statistics and
the scorer Chapter 3's, the tasks, tools, context policies and the long-task run Chapter 4's, and the
backoff and the workflow run Chapter 5's. The analysis reads runs that already exist and calls no
model; it takes under a minute of CPU. The cache-break probe needs the model and about an hour of GPU.

| File | What it is |
|---|---|
| `analysis.py` | Reads Chapter 4's book run (with its labels) and Chapter 5's run. `calls` splits each model call into new, reused and completion tokens (`reused`, the previous prompt and reply, is the local server's reuse, used for the latency fit only) and gives `cached`, what a hosted cache could read: the previous prompt, never its reply; `golden` gives the four golden signals per condition; `price` and `per_solved` price the calls from the dated table `PRICES`, with no cache and with an ideal prefix cache that respects each provider's minimum; `fit` is the least-squares latency fit; `common` keeps Chapter 5's comparison rows whose task and seed reached all three conditions and refuses duplicates or other conditions |
| `ratelimit.py` | Replays Chapter 4's full-context calls as 1 to 100 agents at once against Anthropic's Start-tier limits (`LIMITS`), with token buckets whose sizes are assumed (a minute's allowance; a second's as a sensitivity scenario). A refused call waits as a `retry-after` header says, with no limit (`wait`); ignores the header and backs off as Chapter 5's retry does (`backoff`); or honours the header plus up to 10% jitter within four tries and 60 seconds (`honour`). `oversized` counts every call larger than any bucket (`oversized_in`, `oversized_out` by bucket), `too_large` the agents stopped at one; `out_of_tries`, `out_of_time` and `time_left` say why the bounded policies stopped |
| `otel_shape.py` | Writes a run's trace as span records named after the OpenTelemetry GenAI conventions (`invoke_agent`, `chat`, `execute_tool`; commit `SPEC`), as JSON lines. No SDK, no export. `anthropic_usage` and `openai_usage` map each provider's usage block to the conventions' counts. No stopping reason is written, since the traces don't record it; `--content` writes replies as messages of parts |
| `native.py` | A chat client for Ollama's native `/api/chat`, which reports how many prompt tokens came from the server's cache (`prompt_eval_cached_count`); it takes and returns messages in Chapter 1's shape |
| `probe.py` | The cache-break probe: Chapter 4's 30 long tasks, full context, two seeds, with a stable system prompt or one that starts with the time of each request. 120 runs; `--pilot` is three tasks and one seed. An end-to-end intervention: the stamp can change the runs themselves. On resume a torn last row is dropped, a bad row before the last stops the resume with the file untouched, and the manifest is replaced whole |
| `report.py` | Writes the chapter's tables and numbers (`../../build/ch11_*`): the analysis always, the probe from the run `book.json` names |
| `test_ch11.py` | Tests with made-up rows and replies: the token split, the signals, the pricing and the cache minimum, the fit, the buckets and the replay, the span records and the usage mappings, the native client's messages and counts, the probe's plan, stamp and rows, and the report |
| `book.json` | Which probe run the chapter uses (`null` until there is one: the probe's table then prints "--") |

The trace records use the GenAI attribute names, all at "Development" status in the conventions:
the names may still change.

## 1. Tests (no model needed)

From this folder (`bigbook/code/ch11`):

```
python -m unittest -v test_ch11
```

Expected: `Ran 38 tests ... OK`. Every model reply in them is one the tests wrote.

## 2. The analysis (no model needed)

```
python analysis.py          # signals, tokens, seconds and dollars per solved task, the latency fit
python ratelimit.py         # the rate-limit replay
python otel_shape.py --limit 20
python report.py            # writes the chapter's numbers
```

Chapter 5's run may be partial: its traces hold 190 rows of the comparison only. The analysis keeps
the comparison rows whose task and seed reached every condition (189 rows, 63 pairs) and uses the
scorer's verdicts, since that run has no labels. The compacting condition's step tokens include its
summariser's, which is right for its total cost; the trace doesn't split them into prompt and reply,
so its dollar price counts them all as input, which understates it. Drop and compact are priced with
no cache, as a scenario.

## 3. Probe pilot

Serve the model as in Chapter 4's README and check `ollama ps` shows it. The probe sends the window
(`num_ctx`, 32,768) with every request, so the server's default doesn't matter, but use the same
value throughout: a new window reloads the model. Then:

```
python probe.py --out results/my-pilot --pilot
```

Six runs. Check three things before the full run: the rows have `cached_missing` 0 and their
durations (the server reports `prompt_eval_cached_count`; a missing count or duration is recorded
as unknown, not as 0, and `report.py` won't publish an arm's figure, or a difference, that an
unknown would enter); the tool results reach the model (the runs answer as Chapter 4's did); and
the runtime fits a night. The arms' cached shares are not a check: they are the probe's result,
read from the full run only. A pilot is not the chapter's run.

The order is decided: the pilot runs first; the 120-run probe waits behind the other chapters'
pending experiments, and it goes ahead only if the pilot shows valid instrumentation and a
workable runtime, never because of what the pilot's numbers say. The chapter's main analysis
uses no GPU.

## 4. The probe

```
python probe.py --out results/my-run
python probe.py --out results/my-run --resume      # after an interruption
```

The resume takes every setting from the manifest and refuses if the code, the tasks or the model's
digest has changed. `report.py` writes the probe's numbers only from a complete run of the design;
name it in `book.json` (`{"run": "results/my-run"}`) and run `python report.py`.

## 5. A real OpenTelemetry pipeline (not used by the book)

To see the same spans in a trace viewer you would need an OpenTelemetry SDK and exporter for Python,
a collector, and a viewer. None is installed here, and each is a package to vet before installing:
check its current version, that it supports your Python, and its known vulnerabilities. The book's
JSON records show what each attribute holds without them.

## What the code does not show

Hosted-API latency, cache hit rates or time to first token (every vendor figure is priced from a
table dated 2026-10-18, never measured); concurrency on the local server (one request at a time);
batch jobs; a cascade or router (deferred: see the chapter); or an OTLP export.
