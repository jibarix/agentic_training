# CSE 410/510 — Introduction to Agentic Engineering (University at Buffalo, Fall 2026)

- **URL:** https://cse.buffalo.edu/courses/cse410/2026_fall/cse410ae/ (a single page holds the syllabus and schedule; no separate subpages were found)
- **Instructors:** Dr. Joaquin Carbonara and Dr. David Doermann
- **Level/prereqs:** Upper-division undergrad (CSE 410) and graduate (CSE 510; approved as an MS capstone option for Fall 2026). Prereq: CSE 250 Data Structures or equivalent, or instructor approval. Students need Python, Git/GitHub, technical documentation and debugging. Recommended: CSE 331, 368, 442, 435, 474. Enrollment is by force registration.
- **Format:** In person, 3 credits. One weekly block (Wed 5:00-7:40 PM, Clemens 120) combining lecture, lab and project studio. Aug 24 - Dec 7, 2026. Grading: notes/math/quizzes/participation 25%, labs 35%, team project 30%, final oral exam 10%.
- **Public materials:** Syllabus with week-level schedule, lab descriptions and reference lists only. No slides, videos or code are published.
- **License:** Not stated.

**Overview.** The course is project-based and treats an agent as an engineered system, "not a magic chatbot". Each agent has a bounded environment, designed interfaces and tools, and explicit evaluation and safety constraints. Math (linear algebra, probability, graph theory, optimization, RL, statistics) is taught in context as an engineering tool, e.g. a cosine-similarity studio. The course is framework-agnostic: OpenAI Agents SDK, LangGraph, LlamaIndex or custom code are all allowed, and local models via Ollama are supported. Evaluation harnesses, error taxonomies, human-in-the-loop design and risk analysis get as much weight as building. The course ends with a team "useful bounded agent" that ships with an architecture document, an eval suite and a risk assessment.

## Lectures

The schedule is weekly and marked tentative. Each week is one Wednesday session. Exact session dates are not given beyond week ranges, except the final demos on Wed Dec 2.

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Aug 24-28 | What is agentic engineering? | Agents, environments, tools, goals, constraints | Reading Note 1 (specific reading not listed) | n/a | ORG, ARCH |
| 2 | Aug 31-Sep 4 | Foundation models as components | Prompting, context, structured outputs | Reading Note 2 | n/a | FND |
| 3 | Sep 8-11 | Tool/function calling and ReAct | Tool calling, ReAct; studio on linear algebra and cosine similarity | Reading Note 3 | n/a | TOOL, RSN |
| 4 | Sep 14-18 | Retrieval-augmented generation and context construction | RAG, context building | Reading Note 4 | n/a | MEM |
| 5 | Sep 21-25 | Embeddings, vector search, reranking | Embeddings, vector DBs, reranking | n/a | n/a | MEM |
| 6 | Sep 28-Oct 2 | Agent workflows | Graphs, state machines, LangGraph or custom orchestration | n/a | n/a | ARCH |
| 7 | Oct 5-9 | Planning and decomposition | When should an agent plan? | n/a | n/a | RSN |
| 8 | Oct 14-16 | Human-agent interaction and memory | Human-in-the-loop, memory architectures | n/a | n/a | MEM, SAFE |
| 9 | Oct 19-23 | Evaluation of agents | From single-prompt to task-level evals | n/a | n/a | EVAL |
| 10 | Oct 26-30 | Security and privacy | Prompt injection, tool misuse, sandboxing, privacy | n/a | n/a | SAFE |
| 11 | Nov 2-6 | Multi-agent systems and coordination | MAS coordination | n/a | n/a | MULTI |
| 12 | Nov 9-13 | Coding agents, testing, CI, observability | Coding agents, testing, CI, observability | n/a | n/a | CODE, DEPLOY |
| 13 | Nov 16-20 | Applied agents and responsible deployment | Data science, discovery and education agents; responsible deployment | n/a | n/a | APP, DEPLOY |
| 14 | Nov 23-28 | No class (Thanksgiving) | Independent work on report and demo | n/a | n/a | ORG |
| 15 | Nov 30-Dec 7 (Wed Dec 2) | Final demos, critique, synthesis | Team demos | n/a | n/a | ORG |
| Final | Dec 9-16 | Final project submission | Final report and repository at exam time | n/a | n/a | ORG |

## Assignments / Projects

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| Lab 1: A Minimal Tool-Using Agent (Wk 2-4) | Python agent choosing among a calculator, a file reader and a search/lookup tool. Submit a design note and successful/failed runs | Tool calling, agent loop, failure analysis | n/a | TOOL, ARCH |
| Lab 2: Retrieval and Memory (Wk 4-6) | Small RAG pipeline over a course-selected corpus. Compare keyword/dense/hybrid retrieval, compute cosine similarity, do error analysis | RAG, embeddings, retrieval eval | n/a | MEM, EVAL |
| Lab 3: Workflow Graphs and State Machines (Wk 6-9) | Agentic workflow as a graph/state machine with explicit states, transitions, failure handling and logging | Orchestration, state design, logging | n/a | ARCH |
| Lab 4: Evaluation Harness (Wk 9-11) | Eval suite for a bounded task: test cases, success criteria, metrics, failure taxonomy, reproducible script | Agent evaluation | n/a | EVAL |
| Lab 5: Human-in-the-Loop and Safety Boundaries (Wk 11-13) | Add human approval, structured outputs, guardrails or permission boundaries. Analyze where autonomy should be restricted | HITL, guardrails, permissions | n/a | SAFE |
| Math mini-assignment 1 (Wk 3-5) | Linear algebra for ML: vectors, cosine similarity | Math for retrieval | n/a | FND, MEM |
| Math mini-assignment 2 (Wk 5-8) | Content not specified | n/a | n/a | FND |
| Reading/design notes 1-4 (Wk 1-4) | Weekly notes on readings (content not specified) | Reading, design writing | n/a | ORG |
| Project proposal (Wk 7), Midterm architecture review (Wk 8-10), Project checkpoint (Wk 12), Draft report (before Wk 15) | Team project milestones | Design documentation | n/a | ORG, ARCH |
| Final Team Project: Useful Bounded Agent | Working agent for a bounded task. Deliverables: problem statement, environment/tool inventory, architecture diagram, repo, eval dataset/script, results and error analysis, security/privacy/ethics risk assessment, demo, final report | End-to-end agent engineering | n/a | ARCH, EVAL, SAFE |
| Final oral exam (10%) | Oral exam | n/a | n/a | ORG |

## Codebases & tools referenced

- Chip Huyen, "Agents": https://huyenchip.com/2025/01/07/agents.html
- Anthropic, "Building Effective Agents": https://www.anthropic.com/engineering/building-effective-agents
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- LlamaIndex: https://docs.llamaindex.ai/
- Also mentioned without URLs: OpenAI function/tool calling docs, Ollama, OpenAI-compatible APIs, vector databases/local vector stores, Jupyter, Git/GitHub
- Books (no URLs): Russell & Norvig, *AI: A Modern Approach*; Caldwell, *The Agentic AI Bible*; Huyen, *AI Engineering* (O'Reilly 2025); Sutton & Barto, *Reinforcement Learning* 2nd ed.
- Research references (no URLs given): ReAct, Toolformer, RAG (Lewis et al.), Generative Agents, SWE-bench, WebArena

## Notes

- The page loaded fully. It is the only page: there are no separate schedule, syllabus, lab or slide subpages.
- Readings are not mapped to weeks. Reading Notes 1-4 have no specified readings.
- No public slides, videos or starter code. The tags come from the week topics only.
- The page shows no 410 vs 510 differences in workload.
