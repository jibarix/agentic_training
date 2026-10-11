# EN.601.727 — Machine Programming (Johns Hopkins University, Fall 2026)

- **URL(s):** https://machine-programming.github.io/ (home + schedule), https://machine-programming.github.io/assignments.html, https://machine-programming.github.io/readings.html, https://machine-programming.github.io/project.html, https://machine-programming.github.io/past-versions.html. GitHub org: https://github.com/machine-programming
- **Instructors:** Ziyang Li (instructor, ziyang@cs.jhu.edu); TA Qi Sun; CA Yuming Feng
- **Level/prereqs:** Graduate (600-level, 3 credits). No prerequisites stated on the site.
- **Course format:** In person, Tue/Thu 12:00-1:15pm, Latrobe 107 (Homewood). Lectures, three programming assignments, an oral paper presentation, and a final research project (teams of up to 3). Grading: participation 10%, presentation 10%, A1-A3 15% each, final project 35%. LLM access is through Amazon Bedrock ($200 credits per student); submissions go through GradeScope.
- **Public materials:** Lecture slide PDFs (lectures 1-12 posted as of 2026-10-09; later lectures not yet linked); public starter-code repos for all three assignments; topic-organized reading list. No videos are listed.
- **License:** None stated on the site or the repos.
- **Past offering:** Fall 2025, archived at https://github.com/machine-programming/machine-programming.github.io/tree/2025-fa

**Overview.** The course treats program synthesis from both sides: classic symbolic methods (enumerative bottom-up and top-down search, types, functional specs) and LLM-driven approaches. It is research-oriented and sits where programming languages meet machine learning, with work in Python, C, Rust, Lean, CodeQL and PDDL. The middle module goes straight to coding LLMs and agents: decoding and prompting, iterative refinement, agentic frameworks, and two full lectures on the Model Context Protocol, followed by pre- and post-training of code models. The assignments follow the same path, from a hand-written enumerative synthesizer to evaluating coding LLMs to building a tool-calling coding agent. For an agent builder, the main draw is the practical A3 (an agent loop with file and TODO tools that builds web apps), set against PL foundations.

## Lectures

Slide URLs below are resolved from the relative links (`lectures/lecture-N.pdf`) on the home page. Lectures 7, 8 and 10 were confirmed to exist; their files are over 10 MB, so the contents could not be read. The others were not fetched one by one. "Key topics" for lectures whose slides were not read come from the title only.

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Tue Sep 1 | Overview & Introduction to Machine Programming | Course intro; what machine programming is | n/a | https://machine-programming.github.io/lectures/lecture-1.pdf | ORG |
| 2 | Thu Sep 3 | Syntax, Semantics, and Bottom-up Inductive Synthesis | DSL grammars/semantics; bottom-up enumeration from examples | n/a | https://machine-programming.github.io/lectures/lecture-2.pdf | RSN |
| 3 | Tue Sep 8 | Type Systems and Top-down Enumerative Synthesis | Types for pruning; top-down search | n/a | https://machine-programming.github.io/lectures/lecture-3.pdf | RSN |
| 4 | Thu Sep 10 | Functional Specifications and Synthesis | Synthesis from logical/functional specs | n/a | https://machine-programming.github.io/lectures/lecture-4.pdf | RSN |
| 5 | Tue Sep 15 | Language Modeling for Synthesis | LMs as program generators | Code LLM readings (readings page) | https://machine-programming.github.io/lectures/lecture-5.pdf | FND, CODE |
| 6 | Thu Sep 17 | Decoding and Prompting for Synthesis | Decoding strategies; prompting for code | n/a | https://machine-programming.github.io/lectures/lecture-6.pdf | FND, CODE |
| 7 | Tue Sep 22 | Iterative Refinement and Agentic Framework | Feedback/refinement loops; agent framework (A1 due) | n/a | https://machine-programming.github.io/lectures/lecture-7.pdf | ARCH, CODE |
| 8 | Thu Sep 24 | Agentic Frameworks: Model Context Protocol | MCP | n/a | https://machine-programming.github.io/lectures/lecture-8.pdf | TOOL, ARCH |
| 9 | Tue Sep 29 | Agentic Frameworks: Model Context Protocol (2) | MCP, continued | n/a | https://machine-programming.github.io/lectures/lecture-9.pdf | TOOL, ARCH |
| 10 | Thu Oct 1 | Agentic Frameworks: Selected Topics | Agent framework topics (unspecified) | Agents readings: MASAI, AutoCodeRover | https://machine-programming.github.io/lectures/lecture-10.pdf | ARCH, CODE |
| 11 | Tue Oct 6 | Pre-training of Coding Language Models (1) | Code-LLM pre-training (data, tokenization, objectives) | e.g., StarCoder, Code Llama, DeepSeek Coder, The Stack, FIM (readings page) | https://machine-programming.github.io/lectures/lecture-11.pdf | TRAIN, CODE |
| 12 | Thu Oct 8 | Pre-training of Coding Language Models (2) | Pre-training, continued (A2 due Fri Oct 9) | as above | https://machine-programming.github.io/lectures/lecture-12.pdf | TRAIN, CODE |
| 13 | Tue Oct 13 | Post-training of Coding Language Models | Post-training of code LLMs | e.g., CodeDPO, LintSeq (readings page) | n/a (not yet posted) | TRAIN, CODE |
| 14 | Thu Oct 15 | Special Topics in Training Language Models | n/a | n/a | n/a | TRAIN |
| 15 | Tue Oct 20 | PL Kaleidoscope: Formal Verification and Theorem Proving | Verification, theorem proving (e.g., Lean) | n/a | n/a | APP, CODE |
| — | Thu Oct 22 | Fall break (no class) | — | — | — | — |
| 16 | Tue Oct 27 | PL Kaleidoscope: Differentiable Programming and Machine Learning | Differentiable programming | n/a | n/a | APP |
| 17 | Thu Oct 29 | PL Kaleidoscope: Security and Privacy | PL for security/privacy (e.g., CodeQL) | n/a | n/a | SAFE, APP |
| 18 | Tue Nov 3 | PL Kaleidoscope: Hardware and High-Performance Computing | HW/HPC programming | n/a | n/a | APP |
| 19 | Thu Nov 5 | PL Kaleidoscope: Design, Interactive, and Visual Programming | Design, interactive and visual programming | n/a | n/a | APP |
| 20 | Tue Nov 10 | Oral Presentations (1) | Student paper presentations | n/a | n/a | ORG |
| 21 | Thu Nov 12 | Oral Presentations (2) | Student paper presentations | n/a | n/a | ORG |
| 22 | Tue Nov 17 | Oral Presentations (3) | Student paper presentations | n/a | n/a | ORG |
| 23 | Thu Nov 19 | Oral Presentations (4) | Student paper presentations | n/a | n/a | ORG |
| — | Tue Nov 24 / Thu Nov 26 | Fall recess / Thanksgiving (no class) | — | — | — | — |
| 24 | Tue Dec 1 | Oral Presentations (5) | Student paper presentations | n/a | n/a | ORG |
| 25 | Thu Dec 3 | Oral Presentations (6) | Student paper presentations | n/a | n/a | ORG |
| 26 | Tue Dec 8 | Special Topics on Neurosymbolic Programming (1) | Neurosymbolic programming (e.g., Scallop) | n/a | n/a | RSN, APP |
| 27 | Thu Dec 10 | Special Topics on Neurosymbolic Programming (2) | Neurosymbolic programming, continued | n/a | n/a | RSN, APP |
| 28 | TBD (Dec 15-23) | Final Presentation Session | Final project presentations | n/a | n/a | ORG |

## Assignments / Projects

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| A1: Inductive Synthesis (due Sep 22) | A bottom-up enumerative synthesizer for a geometric-shape DSL (grow / eliminate observational equivalents / search); your own string DSL and synthesizer; then prompts plus output parsing so Claude Sonnet 4.6 (via Bedrock) solves at least 80% of string tasks | Enumerative search, pruning by observational equivalence, DSL design, prompt design, parsing LLM output | https://github.com/machine-programming/assignment-1 | RSN, FND, CODE |
| A2: Evaluating Coding LLMs (due Oct 9) | Execution harnesses for Python/Rust/OCaml; 4 prompting strategies (zero-shot, two-step CoT, iterative refinement with feedback up to 3 rounds, a custom method of about 5 calls or fewer); pass@1/2/3 pipeline over 24 experiments (Claude Haiku vs Sonnet x 3 languages x 4 strategies) on a 16-item xCodeEval/MBPP set; plots | Sandboxed execution with timeouts, error classification, pass@k, experiment scripting, visualization | https://github.com/machine-programming/assignment-2 | EVAL, CODE, RSN |
| A3: Coding LLM Agents (due TBD; repo public) | "WAA" (Web-App Agent): a Python tool-calling loop (tool registry, system prompt, LLM query, parse, execute, terminate or hit the turn limit), file-system tools with path validation and protected files, TODO tools; the agent then builds a personal site, an Express chat room and a creative app; extra credit adds a database plus DB tools | Agent loop design, tool and termination protocols, secure file tools, error recovery, mock-LLM testing, Jest/Supertest/Playwright | https://github.com/machine-programming/assignment-3 | ARCH, TOOL, CODE |
| Final project (35%) | Research project in program synthesis/analysis or related (teams of up to 3): 2-page proposal, implementation, report of at least 4 pages (NeurIPS template), 10-min talk | Research design, implementation, writing | n/a (https://machine-programming.github.io/project.html) | ORG, CODE |
| Oral presentation (10%) | Paper presentation in the Nov-Dec sessions | Paper reading/presenting | n/a | ORG |

## Codebases & tools referenced

- Course site source: https://github.com/machine-programming/machine-programming.github.io
- Assignment repos: https://github.com/machine-programming/assignment-1 , https://github.com/machine-programming/assignment-2 , https://github.com/machine-programming/assignment-3 (all Python, no license listed)
- Amazon Bedrock (Converse API) with Claude Haiku / Claude Sonnet 4.6 (A1, A2); Google Gemini API (`gemini-2.5-pro` in A3's example config)
- A3 stack: Node.js/npm, Express, WebSockets (optional), Jest, Supertest, Playwright
- A2 toolchains: Python `subprocess`/`py_compile`, Rust `cargo`, OCaml `ocaml`/`ocamlc` (dune optional)
- Benchmarks/harnesses on the readings page: LiveCodeBench https://livecodebench.github.io/ , SWE-bench https://arxiv.org/abs/2310.06770 , BigCode Eval Harness https://github.com/bigcode-project/bigcode-evaluation-harness , BigCodeBench https://huggingface.co/blog/leaderboard-bigcodebench , LMArena https://lmarena.ai/?leaderboard
- Agent papers on the readings page: MASAI https://arxiv.org/pdf/2406.11638 , AutoCodeRover https://arxiv.org/abs/2404.05427
- Project-idea tools: Scallop https://scallop.github.io/ , plus Lean, Coq, Z3, CodeQL, Datalog, Prolog, PDDL (Wikipedia links on the project page)
- Report templates: https://www.overleaf.com/latex/templates/neurips-2024/tpsbbrdqcmsh , https://typst.app/universe/package/bloated-neurips/0.8.0/

## Notes

- The course is in progress (Fall 2026). As of 2026-10-09 the schedule links slides only for lectures 1-12. Lectures 13 onward have titles only.
- The assignments page says A3's link "will be posted when released", but https://github.com/machine-programming/assignment-3 is already public with a full README.
- Lecture PDFs 7, 8 and 10 are over 10 MB and could not be read through WebFetch, so their topics are inferred from the titles. Slide URLs for the other lectures come from the relative links and were not fetched one by one.
- The readings page (https://machine-programming.github.io/readings.html) is organized by topic (Code LLMs, Evaluation, Agents, Improving Code Generation, Interpretability), not by lecture. The readings listed in the table are topical matches, not official per-lecture assignments. The "Agents" section is thin (MASAI, AutoCodeRover, one TBD).
- The readings page credits Columbia COMS 6998, MIT 6.S981, UCSD CSE 291 and UW CS294 as inspiration.
- The presentation page (presentation.html) was not fetched.
