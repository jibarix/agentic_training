# The Big Book of Agentic AI Engineering

A book by J. A. Arroyo on building agentic systems. Each chapter teaches one engineering pattern with a complete working implementation and an experiment designed for a local model; completed experiments include their results. The material is drawn from a survey of university courses on agentic AI taught in 2025 and 2026; the book teaches the content directly and cites its sources so that every claim can be checked.

## Status: draft

**This is a draft, and it is not finished.** `bigbook.pdf` is the October 2026 draft (172 pages).

- The code and tests of every chapter are complete.
- The experiments of Chapters 1 to 4 are complete, and those chapters report their results.
- Experimental work is still under way. The full results of Chapters 5 to 10 and of Chapter 11's cache probe are not yet reported. Chapter 5 has a partial run awaiting completion; the other full runs are pending. Tables for unreported results print "--" in place of each number. The PDF will be updated as each run completes and is checked.
- Chapter 11's analysis uses Chapter 4's run and Chapter 5's partial run. The partial Chapter 5 data is not yet published, so that analysis cannot be reproduced from this repository yet.
- Three course sessions the book cites had not been held when the draft was written. They will be added on a recheck.

Expect the text, the numbers and the code to change before a final version.

## What is here

| Path | What it is |
|---|---|
| `bigbook.pdf` | The draft book |
| `code/` | The companion code: one folder per chapter, each with its own README, tests and (where complete) the reported run |
| `sources/MANIFEST.md` | The source manifest: for each source a chapter uses, its revision, the sections used, its licence, and a hash of the copy checked |

The LaTeX source, the figure sources and the book-level build utilities are not published, so the PDF cannot be rebuilt from this repository. The chapter READMEs' "Rebuild the chapter" steps need those local files; the experiment and report scripts are included. The third-party copies listed in the manifest are kept locally and are not distributed.

## Chapters

| Chapter | Code | Experiment |
|---|---|---|
| Introduction: Do You Need an Agent? | none | none |
| 1. Build a Bounded Tool-Using Agent | `code/ch01` | Complete |
| 2. Move the Tools Behind MCP | `code/ch02` | Complete |
| 3. Tell a Real Improvement from Noise | `code/ch03` | Complete |
| 4. Decide What the Model Sees | `code/ch04` | Complete |
| 5. Plan the Work and Survive a Crash | `code/ch05` | Partial run, awaiting completion |
| 6. Secure the Agent and Keep a Person in the Loop | `code/ch06` | Pending |
| 7. Coding Agents | `code/ch07` | Pending |
| 8. Several Agents, and the Protocol Between Them | `code/ch08` | Pending |
| 9. Spending Inference Compute: Sampling, Thinking and Verifiers | `code/ch09` | Pending |
| 10. Improving the Agent's Policy: Prompts, Fine-Tuning, Distillation and RL | `code/ch10` | Pending |
| 11. Deploy, Operate and Optimise Cost | `code/ch11` | Analysis reported using Chapter 5's partial run; cache probe pending |
| Your Next System | none | none |

## Running the code

The companion code needs Python 3.10 or later and no third-party Python packages. The tests need no model; the experiments need a running model server and the downloaded model weights. From `bigbook/`, for example:

```
cd code/ch01
python -m unittest -v test_agent
```

Most model calls use an OpenAI-style chat endpoint; later experiments also use Ollama-specific checks, and Chapter 11's cache probe uses Ollama's native API. The reported numbers come from `qwen3.5:4b-q4_K_M` served by Ollama on an 8 GB laptop GPU, the only server tested. Chapter 1's README explains how to serve the model; each chapter's README gives its test, smoke-run and full-run commands. Several chapters use earlier chapters' code, so keep the `code/` folders side by side.

## Independence and use of AI

The book is not affiliated with, reviewed by or endorsed by any university, instructor or company it cites. I wrote the draft with the help of an AI assistant (Anthropic's Claude), which helped me draft text and code and run the experiments. I designed each chapter, checked every claim against its source, reviewed the code and its tests, and take responsibility for the content.

## Licence

The companion code is released under the MIT licence (`code/LICENSE`). The book itself is not covered by that licence.
