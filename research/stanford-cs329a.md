# CS329A — Self-Improving AI Agents (Stanford University, Autumn 2025)

- **URL(s):** https://cs329a.stanford.edu/ (home: overview, staff, schedule, grading, policies), https://cs329a.stanford.edu/pastprojects.html. Bulletin: https://bulletin.stanford.edu/courses/2263721. Recordings playlist (Stanford Online): https://www.youtube.com/playlist?list=PLangBM27OtEA. GitHub org: https://github.com/stanford-cs329a
- **Instructors:** Aakanksha Chowdhery, Azalia Mirhoseini; CAs Chelsea Zou, Shree Reddy, Kaien Yang, Adrian Gamarra Lafuente
- **Level/prereqs:** Graduate, 3 units (bulletin). Bulletin prerequisites: "CS224N or CS229S; Fluency in Python programming and using large language model APIs." The course site lists none.
- **Course format:** In person, Mon/Fri 4:30-5:50pm PT, Skilling Auditorium. Paper-driven lectures with invited speakers, three homeworks, and a team research project (2-4 students, API credits provided). Grading: HW1 15%, HW2 15%, HW3 20%, project proposal 2.5%, midterm presentation + report 10%, final project 35%, poster 2.5%. 4 free late days (max 2 per assignment); audits not allowed; Q&A on EdStem.
- **Public materials:** Schedule with per-lecture paper readings; 9 official lecture recordings on YouTube (Stanford Online, published Aug 2026); public starter-code repos for all three homeworks; Winter 2025 project papers and posters. No standalone slide decks are linked.
- **License:** None stated on the site. HW1 repo: MIT. HW3 repo: Apache-2.0. HW2 repo: no LICENSE file visible.
- **Past offering:** Winter 2025 (projects archived at https://cs329a.stanford.edu/pastprojects.html: 5 papers with posters)

**Overview.** The course asks how an LLM agent can get better through interaction with itself and its environment, and works through the levers in order. It starts with inference-time methods (repeated sampling, test-time compute scaling, verifiers and process reward models), moves to learning from tool and execution feedback (ReAct, RLEF), multi-step planning and tree search, and train-time scaling with RL (STaR, GRPO/DeepSeekMath, DAPO). The second half covers open-ended self-improvement (ADAS, AI Scientist, AlphaEvolve), search and deep-research agents, software-engineering agents, memory, and agentic evaluation on long-horizon tasks, with five guest talks from Google DeepMind, LMCache/UChicago, Reflection AI and Physical Intelligence. The homeworks follow the same arc: test-time scaling on AIME25, code verification with judges and synthetic unit tests on HumanEval, then an API-routing agent with decomposition, fusion, iterative refinement and a deep-research agent. For an agent builder the main draws are the recorded core lectures and HW3, a hands-on tool-routing and research-agent build.

## Lectures

Schedule, dates and readings come from the home page. Video URLs are the official Stanford Online YouTube recordings (titled "Stanford CS329A Self-Improving AI Agents", then "Part N" and the lecture title). Each was opened and its title checked, and parts were matched to lectures by title. Guest lectures, lecture 7, lecture 13 and lecture 14 have no recording. No lecture has slides.

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Mon Sep 22 | Course Overview | Course logistics; framing of self-improving agents | n/a | https://www.youtube.com/watch?v=6YnLB0XbTnI | ORG |
| 2 | Fri Sep 26 | Test-time Compute Scaling | Repeated sampling, inference scaling laws, architecture search over inference techniques | Large Language Monkeys; Archon; Scaling LLM Test-Time Compute Optimally (Snell et al.); How Do Large Language Monkeys Get Their Power (Laws)? | https://www.youtube.com/watch?v=-Ggc37xLj_Y | RSN, EVAL |
| 3 | Mon Sep 29 | Robust Verification | Outcome/process verifiers, weak verifiers, generation-verification gap | Shrinking the Generation-Verification Gap with Weak Verifiers; Training Verifiers to Solve Math Word Problems; Let's Verify Step by Step; Math-Shepherd | https://www.youtube.com/watch?v=p7TdPUcPoik | RSN, EVAL |
| 4 | Fri Oct 3 | Learning from Feedback with Tools/Code | Reason+act loops, RL from execution feedback, AI feedback (HW1 out) | ReAct; RLEF; Constitutional AI | https://www.youtube.com/watch?v=Lxh9RF5S-K0 | TOOL, CODE, TRAIN |
| 5 | Mon Oct 6 | Multi-step Reasoning/Planning | Multi-step RL with synthetic data, tree search, decomposition, parallel planning | SWiRL; Language Agent Tree Search; SPRINT; ADaPT; Wider or Deeper? (adaptive branching tree search) | https://www.youtube.com/watch?v=Ml_fp9XkB8Y | RSN, TRAIN |
| 6 | Fri Oct 10 | Train Time Scaling/Scaling RL | Self-taught reasoning, GRPO, large-scale RL recipes (project proposal due) | STaR; DeepSeekMath; DAPO | https://www.youtube.com/watch?v=yVnmHSAy3ck | TRAIN, RSN |
| 7 | Mon Oct 13 | Open-Ended Evolution of Self-Improving Agents | Automated agent design, automated science, evolutionary coding agents (HW2 out Oct 14) | Automated Design of Agentic Systems; The AI Scientist; AlphaEvolve | n/a | ARCH, CODE, APP |
| 8 | Fri Oct 17 | Self-Improvement with Search & Deep Research Agents | Search-based code generation, agentic search for reasoning models, deep research | AlphaCode; AlphaCode 2 Tech Report; Search-o1 | https://www.youtube.com/watch?v=Uni9dqyuuDM | WEB, RSN, CODE |
| 9 | Mon Oct 20 | Guest: Melvin Johnson (Google DeepMind), Evolution of Post-training from Chatbots to Agents | Post-training for agents (from title only) | n/a | n/a | ORG, TRAIN |
| 10 | Fri Oct 24 | Midterm presentations (1) | 5-10 min project presentations (HW3 out) | n/a | n/a | ORG |
| 11 | Mon Oct 27 | Midterm presentations (2) | Project presentations | n/a | n/a | ORG |
| 12 | Fri Oct 31 | Midterm presentations (3) | Project presentations | n/a | n/a | ORG |
| 13 | Mon Nov 3 | Agentic Frameworks for Software Engineering | Test-time scaling for SWE, GPU-kernel generation, agent-system interfaces | CodeMonkeys; KernelBench; Improving Parallel Program Performance with LLM Optimizers via Agent-System Interfaces | n/a | CODE, ARCH |
| 14 | Fri Nov 7 | Guest: Augmenting Agents with Memory (Junchen Jiang, LMCache/UChicago) | Long-context representations, OS-style memory, KV-cache reuse (HW3 due) | Cartridges; MemGPT; CacheBlend | n/a | MEM, DEPLOY |
| 15 | Mon Nov 10 | Guest: Denny Zhou (Google DeepMind), LLM Reasoning | LLM reasoning (from title only) | n/a | n/a | ORG, RSN |
| 16 | Fri Nov 14 | Guest: Thang Luong (Google DeepMind), Towards AI Superhuman Reasoning | Superhuman reasoning (from title only) | n/a | n/a | ORG, RSN |
| 17 | Mon Nov 17 | Agentic Evaluations & Long-Horizon Tasks | Task-length metrics, economically valuable tasks, research-synthesis benchmarks | Measuring AI Ability to Complete Long Tasks; GDPVal; DeepScholar-Bench | https://www.youtube.com/watch?v=8JAqLnTaZu4 | EVAL |
| 18 | Fri Nov 21 | Guest: Misha Laskin (Reflection AI), Building Agentic Systems for Autonomy | Autonomous agentic systems (from title only) | n/a | n/a | ORG, ARCH |
| — | Mon Nov 24 / Fri Nov 28 | Holidays (no class) | — | — | — | — |
| 19 | Mon Dec 1 | Guest: Danny Driess (Physical Intelligence), Multimodal AI Agents in Robotics | Multimodal robot agents (from title only) | n/a | n/a | ORG, APP |
| 20 | Fri Dec 5 | Future Research Areas | Open problems in self-improving agents (from title only) | n/a | https://www.youtube.com/watch?v=AyO6wyu4DEg | FND |
| — | Wed Dec 10 | Final project due (EoD) | — | — | — | — |
| — | Fri Dec 12 | Final project poster presentation | — | — | — | — |

## Assignments / Projects

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| HW1: Test-time compute scaling (out Oct 3, due Oct 13; 130 pts + 2 bonus) | On AIME25 (30 problems, `math-ai/aime25`) with Qwen3-Next-80B-A3B-Instruct via Together AI: zero-shot baseline; `MajorityVoting` over budgets 1-16; best-of-N with an LLM aggregator (`LLMVoting`, generative reward model); an RLEF-style `SelfImprovementSystem` (generate, critique, regenerate); plots plus a cost-per-API-call analysis | Repeated sampling, majority voting, LLM-as-judge, critique-and-refine loops, accuracy-vs-compute analysis | https://github.com/stanford-cs329a/cs329a-homework1-fall2025-public | RSN, EVAL |
| HW2: Code generation and verification (out Oct 14, due Oct 22 per schedule / Oct 23 per grading; 110 pts) | On HumanEval with Llama-3.2-3B-Instruct-Turbo, code run in a Docker sandbox: `calculate_accuracy` and failure analysis; pass@k for k = 3, 6, 9; an `LLMJudge` that picks among candidates via JSON output; an `LLMUnitTestGenerator` (Qwen2.5-72B) that writes 5 tests from the docstring; checks how often ground truth passes the synthetic tests; pass@3 with synthetic vs ground-truth tests | Sandboxed execution, pass@k, LLM-as-judge, synthetic unit tests as weak verifiers, error analysis | https://github.com/stanford-cs329a/cs329a-homework2-fall2025-public | CODE, EVAL, RSN |
| HW3: Self-improving agentic workflow (out Oct 24, due Nov 7; 120 pts) | An `APIManager` with Google Custom Search, Polygon stock data, Wolfram Alpha and weather (Nominatim + Open-Meteo) tools; LLM-based `route_query` with Pydantic/JSON mode; a `MultiLMAgent` with query decomposition, multi-model fusion, iterative self-refinement and an adaptive `run_pipeline` (full credit at 70% or more QA accuracy); a `DeepResearchAgent` that writes a cited 4-5 paragraph report | Tool routing, structured outputs, decomposition, ensembling/fusion, self-refinement loops, deep-research agents, LLM-judged QA eval | https://github.com/stanford-cs329a/cs329a-homework3-fall2025-public | TOOL, WEB, ARCH, EVAL |
| Project proposal (2.5%, due Oct 10) | Proposal for the team research project | Research design | n/a | ORG |
| Midterm presentation + report (10%) | 5-10 min presentation (Oct 24, 27, 31) plus report | Presenting, writing | n/a | ORG |
| Final project (35%, due Dec 10) + poster (2.5%, Dec 12) | Original research in teams of 2-4 on course topics or benchmarks for agentic workflows (API credits provided) | Research, implementation, writing | n/a (past examples: https://cs329a.stanford.edu/pastprojects.html) | ORG, TRAIN, EVAL |

## Codebases & tools referenced

- Homework repos: https://github.com/stanford-cs329a/cs329a-homework1-fall2025-public (MIT), https://github.com/stanford-cs329a/cs329a-homework2-fall2025-public (no license shown), https://github.com/stanford-cs329a/cs329a-homework3-fall2025-public (Apache-2.0). All Python notebooks plus a course package (`cs329_hw1`, `cs329_hw`, `cs329a_hw3`)
- Together AI API (all homeworks): Qwen3-Next-80B-A3B-Instruct, Llama-3.2-3B-Instruct-Turbo, Qwen2.5-72B-Instruct-Turbo, Meta-Llama-3.1-8B-Instruct-Turbo, Llama-3.3-70B-Instruct-Turbo-Free, gemma-3n-E4B-it, gpt-oss-20B
- Benchmarks/datasets: AIME25 (Hugging Face `math-ai/aime25`), HumanEval (https://arxiv.org/abs/2107.03374); a QA dataset bundled with HW3 (not described)
- HW3 external APIs: Google Custom Search, Polygon, Wolfram Alpha, Geopy Nominatim, Open-Meteo; Pydantic for structured outputs
- Docker (HW2 `humaneval-sandbox` image), conda, python-dotenv, tenacity, ThreadPoolExecutor
- Key papers with code/systems from readings: Archon https://www.arxiv.org/abs/2409.15254, MemGPT https://arxiv.org/abs/2310.08560, CacheBlend http://arxiv.org/abs/2405.16444, KernelBench https://arxiv.org/pdf/2502.10517, CodeMonkeys https://arxiv.org/abs/2501.14723, DAPO https://arxiv.org/abs/2503.14476, AlphaEvolve https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf

## Notes

- I confirmed the consultant's claim of 9 recordings and no slides. The course site links no videos, slides, Canvas or Panopto; its only PDFs are reading papers and past-project files. The recordings are on Stanford Online's YouTube channel (playlist https://www.youtube.com/playlist?list=PLangBM27OtEA, titled "CS329A Self-Improving AI Agents"). The playlist page did not render a video list through WebFetch. The nine video IDs came from a third-party index (https://github.com/flowioo/stanford-cs329a-self-improving-ai-agents), and each watch page was then opened to confirm its official "Part N" title. Third-party sources date the uploads to Aug 3, 2026. I did not check the YouTube license.
- Recording-to-lecture mapping is by title: Parts 1-6 are lectures 1-6, Part 7 ("Self-Improvement and Deep Research Agents") is lecture 8, Part 8 is lecture 17, and Part 9 is lecture 20. Lecture 7 (Open-Ended Evolution), lecture 13 (SWE agents), lecture 14 (memory) and all guest talks have no public recording.
- The schedule is static content on the home page, which WebFetch could read. WebFetch returns converted text, so I could not confirm the HTML markup; the page shows columns #, Date, Description, Paper Readings*, Deadlines. The footnote says readings "may be updated closer to the class date." The site numbers the midterm sessions as one row ("10-12"), split here into lectures 10, 11 and 12.
- The HW2 due date conflicts: the schedule says Oct 22, the grading section says Oct 23. The notebooks give no due dates; the dates in the table come from the course site. HW2 and HW3 point totals are summed from the notebooks' part values.
- I read the homework details from the READMEs and the raw notebooks (`student_homework1.ipynb`, `homework.ipynb`, `homework3.ipynb`). I did not open the package source folders. The HW3 notebook text names `deep_research_agent.py`, but its code imports `cs329a_hw3.DeepResearchAgent`.
- "Key topics" for guest talks and lecture 20 come from titles only. For other lectures they come from titles and listed readings, not from watching the videos.
- Prerequisites come from the Stanford bulletin, not the course site. The Stanford Online course page (https://online.stanford.edu/courses/cs329a-self-improving-ai-agents) returned no content.
- Past-project papers and posters are relative links under `winter2025projects/` on the course site. I did not open them.
