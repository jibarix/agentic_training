# CS 839 — AI Agents (University of Wisconsin-Madison, Spring 2026)

- **URLs:** repo https://github.com/barghouthi/ai-agents ; schedule https://github.com/barghouthi/ai-agents/blob/main/README.md ; course info https://github.com/barghouthi/ai-agents/blob/main/course-info.md ; assignment https://github.com/barghouthi/ai-agents/blob/main/assignment.md
- **Instructor:** Aws Albarghouthi. The repo pages do not name him. The attribution comes from the repo owner (`barghouthi`) and the LICENSE copyright line.
- **Level/prereqs:** Graduate seminar (CS 839 is UW's advanced-topics number). No prerequisites are stated.
- **Format:** Seminar. The instructor gives an overview in week 0. After that, each class has two 25-minute student paper presentations plus about 10 minutes of discussion, and everyone reads the papers. Grading: 15% buy-in assignment (build a coding agent), 15% participation, 10% presentation, 10% paper reviews, 50% final research project (one-page proposal due Feb 24; write-up and presentation). Compute credits come from Google and Thinking Machines.
- **Public materials:** A reading list with paper links (main and supplementary papers per session), one demo notebook (`demos/agents.ipynb`), the assignment spec, and presentation advice. No slides or videos.
- **License:** MIT (Copyright 2025 Aws Albarghouthi).

**Overview.** This is a research-paper seminar on LLM agents. It starts from the classic reasoning-and-acting papers (CoT, ReAct, Toolformer, ToT) and moves to current frontiers: coding/SWE agents, deep-research and AI-scientist agents, agent security and prompt injection, automatic optimization of agent programs (DSPy, TextGrad, GEPA, ADAS), self-improving and evolutionary agents (Voyager, AlphaEvolve, ShinkaEvolve), search over solution spaces, multi-agent systems, and memory/context folding. The tone is critical. Presenters must place each paper in the literature and assess its limitations. The one hands-on assignment asks students to build a coding agent from scratch without frameworks.

## Lectures

Main papers are listed first, and supplementary papers are marked "supp.".

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Tue 20 Jan 2026 | Class overview | Course logistics, overview of the agents space | n/a | n/a | ORG |
| 2 | Thu 22 Jan 2026 | Building agents | Instructor intro to building LLM agents | Building Effective Agents (Anthropic) https://www.anthropic.com/engineering/building-effective-agents (listed as "see also" in week 1) | Demo notebook https://github.com/barghouthi/ai-agents/blob/main/demos/agents.ipynb (session association assumed) | ARCH, TOOL |
| 3 | Tue 27 Jan 2026 | Reasoning and acting I | Chain-of-thought, ReAct | CoT https://arxiv.org/abs/2201.11903 ; ReAct https://arxiv.org/abs/2210.03629 ; supp.: Self-Consistency https://arxiv.org/abs/2203.11171 , Kimi K2 https://arxiv.org/abs/2507.20534 , Llama 3 Herd https://arxiv.org/abs/2407.21783 , Constitutional AI https://arxiv.org/abs/2212.08073 | n/a | RSN, FND |
| 4 | Thu 29 Jan 2026 | Reasoning and acting II | Tool learning, Tree/Graph of Thoughts | Toolformer https://arxiv.org/abs/2302.04761 ; Tree of Thoughts https://arxiv.org/abs/2305.10601 ; supp.: LLMs as Tool Makers https://arxiv.org/abs/2305.17126 , ART https://arxiv.org/abs/2303.09014 , Graph of Thoughts https://ojs.aaai.org/index.php/AAAI/article/view/29720 | n/a | TOOL, RSN |
| 5 | Tue 03 Feb 2026 | Coding agents I | SWE benchmarks, SWE-agent ACI | SWE-bench https://arxiv.org/abs/2310.06770 ; SWE-agent https://arxiv.org/abs/2405.15793 ; supp.: Terminal-Bench https://openreview.net/forum?id=a7Qa4CcHak , Agentless https://arxiv.org/abs/2407.01489 | n/a | CODE, EVAL |
| 6 | Thu 05 Feb 2026 | Coding agents II | Open agent platforms, secure code generation benchmarks | OpenHands https://arxiv.org/abs/2407.16741 ; BaxBench https://arxiv.org/pdf/2502.11844 ; supp.: RepairAgent https://arxiv.org/abs/2403.17134 , RedCode https://arxiv.org/abs/2411.07781 , WebArena https://arxiv.org/abs/2307.13854 | n/a | CODE, SAFE, EVAL |
| 7 | Tue 10 Feb 2026 | Deep research agents I | Article writing, autonomous research labs | STORM https://arxiv.org/abs/2402.14207 ; Agent Laboratory https://arxiv.org/abs/2501.04227 ; supp.: ResearchAgent https://arxiv.org/abs/2404.07738 , Deep research agents roadmap https://arxiv.org/pdf/2506.18096 , Anthropic multi-agent research system https://www.anthropic.com/engineering/multi-agent-research-system | n/a | APP, MULTI |
| 8 | Thu 12 Feb 2026 | Deep research agents II | Literature QA agents, research benchmarks | PaperQA https://arxiv.org/abs/2312.07559 ; LiveResearchBench https://arxiv.org/abs/2510.14240 ; supp.: Can LLMs Generate Novel Research Ideas? https://arxiv.org/abs/2409.04109 , DR Tulu https://arxiv.org/pdf/2511.19399 | n/a | APP, MEM, EVAL |
| 9 | Tue 17 Feb 2026 | Agents for science I | AI Scientist, autonomous chemistry | The AI Scientist https://arxiv.org/abs/2408.06292 ; Autonomous chemical research with LLMs https://www.nature.com/articles/s41586-023-06792-0 ; supp.: ChemCrow https://arxiv.org/abs/2304.05376 | n/a | APP |
| 10 | Thu 19 Feb 2026 | Agents for science II | AI co-scientist, hypothesis falsification | Towards an AI Co-Scientist https://arxiv.org/abs/2502.18864 ; Agentic Sequential Falsifications https://arxiv.org/abs/2502.09858 ; supp.: SciAgents https://arxiv.org/abs/2409.05556 | n/a | APP, MULTI |
| 11 | Tue 24 Feb 2026 | Security & prompt injection I | Indirect prompt injection, AgentDojo benchmark | Indirect Prompt Injection https://arxiv.org/abs/2302.12173 ; AgentDojo https://arxiv.org/abs/2406.13352 ; supp.: Jailbroken https://arxiv.org/abs/2307.02483 | n/a | SAFE, EVAL |
| 12 | Thu 26 Feb 2026 | Security & prompt injection II | Capability-based defenses, browser agent security | CaMeL https://arxiv.org/abs/2503.18813 ; ceLLMate https://arxiv.org/abs/2512.12594 ; supp.: Lethal trifecta https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/ , Meta practical agent security https://ai.meta.com/blog/practical-ai-agent-security/ | n/a | SAFE |
| 13 | Tue 03 Mar 2026 | Optimizing agents I | Declarative LM programs, textual gradients | DSPy https://arxiv.org/abs/2310.03714 ; TextGrad https://arxiv.org/abs/2406.07496 ; supp.: LLMs as Optimizers https://arxiv.org/abs/2309.03409 | n/a | ARCH, TRAIN |
| 14 | Thu 05 Mar 2026 | Optimizing agents II | Automated agent design, reflective prompt evolution | ADAS https://arxiv.org/abs/2408.08435 ; GEPA https://arxiv.org/abs/2507.19457 ; supp.: EvoPrompt https://arxiv.org/abs/2309.08532 , Trace https://arxiv.org/abs/2406.16218 | n/a | ARCH, TRAIN |
| 15 | Tue 10 Mar 2026 | Self-improving agents I | Lifelong skill libraries, self-referential agents | Voyager https://arxiv.org/abs/2305.16291 ; Gödel Agent https://arxiv.org/abs/2410.04444 | n/a | ARCH, WEB |
| 16 | Thu 12 Mar 2026 | Self-improving agents II | Evolutionary coding agents, live self-evolving SWE agent | AlphaEvolve https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/ ; Live-SWE-agent https://arxiv.org/abs/2511.13646 ; supp.: LATS https://arxiv.org/abs/2310.04406 | n/a | CODE, RSN |
| 17 | Tue 17 Mar 2026 | Searching the solution space I | Large-scale sampling and search for code and math | AlphaCode https://arxiv.org/abs/2203.07814 ; AlphaGeometry https://www.nature.com/articles/s41586-023-06747-5 ; supp.: AlphaProof https://www.nature.com/articles/s41586-025-09833-y , AlphaZero https://arxiv.org/abs/1712.01815 | n/a | RSN, CODE |
| 18 | Thu 19 Mar 2026 | Searching the solution space II | LLM-driven evolutionary search | ShinkaEvolve https://arxiv.org/abs/2509.19349 ; Evolution through Large Models https://arxiv.org/abs/2206.08896 ; supp.: Digital Red Queen https://arxiv.org/abs/2601.03335 , Promptbreeder https://arxiv.org/abs/2309.16797 | n/a | RSN |
| 19 | Tue 24 Mar 2026 | Multi-agent systems I | Generative agents, role-playing agents | Generative Agents https://arxiv.org/abs/2304.03442 ; CAMEL https://arxiv.org/abs/2303.17760 ; supp.: Multiagent Debate https://arxiv.org/abs/2305.14325 | n/a | MULTI |
| 20 | Thu 26 Mar 2026 | Multi-agent systems II | Multi-agent frameworks, scaling laws for agent systems, single vs multi-agent | AutoGen https://arxiv.org/abs/2308.08155 ; Science of Scaling Agent Systems https://arxiv.org/abs/2512.08296 ; supp.: Single agent systems https://openhands.dev/blog/dont-sleep-on-single-agent-systems , Prompt Infection https://arxiv.org/abs/2410.07283 , MetaGPT https://arxiv.org/abs/2308.00352 , AgentVerse https://arxiv.org/abs/2308.10848 | n/a | MULTI, ARCH |
| -- | 28 Mar - 5 Apr 2026 | Spring break | n/a | n/a | n/a | ORG |
| 21 | Tue 07 Apr 2026 | Memory I | OS-style memory hierarchy, cognitive architectures | MemGPT https://arxiv.org/abs/2310.08560 ; CoALA https://arxiv.org/abs/2309.02427 ; supp.: Think-in-Memory https://arxiv.org/abs/2311.08719 , A-Mem https://arxiv.org/pdf/2502.12110 , Recursive language models https://arxiv.org/abs/2512.24601 | n/a | MEM, ARCH |
| 22 | Thu 09 Apr 2026 | Memory & other topics II | Mixture-of-agents, context folding, long-horizon task measurement | Mixture-of-Agents https://arxiv.org/abs/2406.04692 ; Context-Folding https://arxiv.org/pdf/2510.11967 ; supp.: More Agents Is All You Need https://arxiv.org/pdf/2402.05120 , Measuring AI Ability to Complete Long Tasks https://arxiv.org/pdf/2503.14499 | n/a | MEM, MULTI, EVAL |
| 23 | Week of 14 Apr 2026 | Project work | n/a | n/a | n/a | ORG |
| 24 | Week of 21 Apr 2026 | Project presentations | n/a | n/a | n/a | ORG |
| 25 | Week of 28 Apr 2026 | Project presentations | n/a | n/a | n/a | ORG |

## Assignments / Projects

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| Build a Coding Agent (buy-in, individual, 15%) | A CLI coding agent like Claude Code / Cursor CLI / Gemini CLI, using raw LLM API calls with no agent frameworks (LangChain, Strands, CrewAI banned; thin wrappers like litellm allowed). It must parse and execute tool calls, have a polished UI, a README, and one non-trivial program the agent built | Agent loop, function calling, tool execution, CLI UX | None. Spec: https://github.com/barghouthi/ai-agents/blob/main/assignment.md | CODE, TOOL, ARCH |
| Paper presentation (10%) | 25-minute presentation of assigned paper(s) with literature context and critique | Critical reading | n/a | ORG |
| Paper reviews (10%) | Written reviews submitted on Canvas | Critical reading | n/a | ORG |
| Final research project (50%) | Research project on AI agents (pairs encouraged); one-page proposal due Feb 24; write-up and presentation | Research design, agent implementation, evaluation | n/a | ARCH, EVAL |

## Codebases & tools referenced

- Course demo notebook: https://github.com/barghouthi/ai-agents/blob/main/demos/agents.ipynb
- DSPy (codebase mentioned alongside the DSPy paper): https://arxiv.org/abs/2310.03714
- litellm (allowed thin wrapper in the assignment); LangChain, Strands, CrewAI (named as disallowed)
- Example coding-agent CLIs: Claude Code, Cursor CLI, Gemini CLI
- Benchmarks/environments in the readings: SWE-bench, Terminal-Bench, AgentDojo, WebArena, BaxBench, RedCode, LiveResearchBench
- Presentation advice: https://www.youtube.com/watch?v=aFT79TmffPk ; https://pages.graphics.cs.wisc.edu/777-S11/2011/04/08/advice-on-presentations/

## Notes

- README.md, assignment.md, course-info.md, LICENSE, and the repo contents (via the GitHub API) all loaded. The repo holds only those files plus `demos/agents.ipynb`.
- The README gives the schedule by week with Tue/Thu splits. Session dates were derived from the week start dates (Jan 20 = Tue). Week 3 is listed as "Feb 10" and Week 9 as "Mar 24".
- The instructor's name is not on any course page. It was inferred from the GitHub owner and LICENSE (Aws Albarghouthi). A web search found no separate UW course page.
- The demo notebook's contents were not inspected, and its link to session 2 is an assumption.
