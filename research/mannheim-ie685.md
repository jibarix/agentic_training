# IE 685 (+ IE 686 project) — Large Language Models and Agents (Universität Mannheim, Data and Web Science Group, Spring 2026 / FSS2026)

- **URL:** https://www.uni-mannheim.de/dws/teaching/course-details/courses-for-master-candidates/ie-685-large-language-models-and-agents/
- **Materials folder (public PDFs/zips linked from the page):** `https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Teaching/Large_Language_Models_and_Agents/FSS2026/` (three PDFs fetched and confirmed to download)
- **Instructors:** Guest Prof. Dr. Ralph Peeters, Prof. Dr. Christian Bizer, Aaron Steiner
- **Level/prereqs:** Master's (Data Science, Social Data Science, Business Informatics); limited to 50 participants. Prereqs: Python programming and basic machine learning.
- **Format:** Weekly lecture (Tue 10:15-11:45) plus exercise (Wed 12:00-13:30) in the first half, then team projects (teams of 5) with weekly coaching. IE685 (3 ECTS) is graded by a written final exam. IE686 (3 ECTS) is the project: 70% report (12 pages) and 30% presentation (12 min + 8 min discussion).
- **Public materials:** Yes. Lecture slide PDFs (7 lectures + project intro), exercise notebooks as zips (LangChain, LangChain+MCP agents, RAG, deep agent), and course evaluation PDFs. No videos. ILIAS is used for team assignment, but the slides and exercises are public on the website.
- **License:** None stated.

**Overview.** This applied master's course runs from LLM foundations (pretraining, post-training and efficient adaptation, prompt engineering) to LLM agents, tool use (LangChain, MCP), RAG, context engineering (deep agents), and safety/security, with evaluation of LLMs and agents listed as a topic. Learning outcomes stress business applications and using agent frameworks on complex tasks. The second half is a team project in which students build (multi-)agent systems or LLM workflows for an assigned domain and compare approaches with some form of evaluation. The literature list consists of surveys (LLMs, LLM-based autonomous agents, agent evaluation, full-stack agent safety).

## Lectures

Slide/exercise URLs = materials folder above + filename. Session dates and filenames come from the course page.

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Tue 10 Feb 2026 | Introduction (to LLMs) | Introduction to LLMs, course organization | Zhao et al., A Survey of LLMs https://arxiv.org/abs/2303.18223 ; Zhou et al., Survey on Pretrained Foundation Models https://link.springer.com/article/10.1007/s13042-024-02443-6 | Slides .../FSS2026/IE685_LA_01_Introduction.pdf | FND, ORG |
| 2 | Tue 17 Feb 2026 | Post-training and Efficient Adaptation | Post-training (instruction tuning / alignment), parameter-efficient adaptation | n/a | Slides .../FSS2026/IE685_LA_02_PosttrainingAndEfficientAdaptation.pdf ; exercise .../FSS2026/IE685_LA_EX_LLM_Introduction.ipynb.zip | TRAIN, FND |
| 3 | Tue 24 Feb 2026 | Prompt Engineering | Prompting techniques | n/a | Slides .../FSS2026/IE685_LA_03_PromptEngineering.pdf ; exercise .../FSS2026/IE686_LA_EX_Langchain_Introduction.ipynb.zip | FND, RSN |
| 4 | Tue 03 Mar 2026 | LLM Agents and Tool Use | LLM-based agents, tool use and environment interaction, MCP | Wang et al., Survey on LLM-based Autonomous Agents https://link.springer.com/article/10.1007/s11704-024-40231-1 | Slides (78 pp.) .../FSS2026/IE685_LA_04_LLMAgentsAndToolUse.pdf ; exercise .../FSS2026/IE685_LA_EX_Agent_Programming_LangChain_MCP.ipynb.zip | ARCH, TOOL |
| 5 | Tue 10 Mar 2026 | Retrieval Augmented Generation | RAG | n/a | Slides .../FSS2026/IE685_LA_05_RetrievalAugmentedGeneration.pdf ; exercise .../FSS2026/IE685_LA_EX_Retrieval_Augmented_Generation.zip | MEM |
| 6 | Tue 17 Mar 2026 | Context Engineering | Context engineering for LLM agents; deep agents | n/a | Slides .../FSS2026/IE685_LA_06_ContextEngineering.pdf ; exercise .../FSS2026/deep_agent.zip | MEM, ARCH |
| 7 | Tue 24 Mar 2026 | Introduction to Student Projects (IE686) | Project goals, procedure, 9 topic areas + own idea, schedule | n/a | Slides .../FSS2026/IE686_LA_07_IntroStudentProjects.pdf | ORG |
| 8 | Tue 14 Apr 2026 | Project feedback and coaching | n/a | n/a | n/a | ORG |
| 9 | Tue 21 Apr 2026 | LLM Security and Safety (+ project coaching) | Safety and security of LLM agents | Wang et al., Full Stack Safety survey https://arxiv.org/abs/2504.15585 | Slides .../FSS2026/IE685_LA_08_SecurityAndSafety.pdf | SAFE |
| 10 | 28 Apr, 05 May, 12 May 2026 | Project work and coaching | n/a (page lists "28.05.2026", likely a typo for 28.04) | n/a | n/a | ORG |
| 11 | 19-20 May 2026 | Presentation of project results | n/a | n/a | n/a | ORG |
| -- | (topic only, no slide deck found) | Evaluation of LLMs and LLM agents | Listed as syllabus topic 8 | Mohammadi et al., Evaluation and benchmarking of LLM agents (KDD 2025) https://dl.acm.org/doi/10.1145/3711896.3736570 | n/a | EVAL |
| -- | May 2026 (date "XX.05.2026") | Final exam (IE685) | n/a | n/a | n/a | ORG |

## Assignments / Projects

The weekly exercises are Jupyter notebooks distributed as zips. The IE686 project topics come from slides 7-16 of the project-intro PDF.

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| Exercise: LLM Introduction | Intro notebook for working with LLMs | LLM APIs/basics | https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Teaching/Large_Language_Models_and_Agents/FSS2026/IE685_LA_EX_LLM_Introduction.ipynb.zip | FND |
| Exercise: LangChain Introduction | LangChain basics notebook | LangChain | .../FSS2026/IE686_LA_EX_Langchain_Introduction.ipynb.zip | FND, ARCH |
| Exercise: Agent Programming with LangChain + MCP | Tool-using agents with LangChain and MCP | Agents, tool calling, MCP | .../FSS2026/IE685_LA_EX_Agent_Programming_LangChain_MCP.ipynb.zip | TOOL, ARCH |
| Exercise: RAG | RAG pipeline notebook | Retrieval, RAG | .../FSS2026/IE685_LA_EX_Retrieval_Augmented_Generation.zip | MEM |
| Exercise: Deep Agent | Deep-agent / context-engineering exercise | Context engineering, planning agents | .../FSS2026/deep_agent.zip | MEM, ARCH |
| Project topic 1: Multi-Agent Gaming | Agent teams that cooperate in, or compete at, games (Codenames worked well before) | Multi-agent coordination, eval by win rate/ELO | AgentBench https://github.com/THUDM/AgentBench ; SmartPlay https://github.com/microsoft/SmartPlay | MULTI, EVAL |
| Project topic 2: QA Agents | RAG (multi-)agent QA over web search that explains its evidence | RAG, web search, benchmark eval | BrowseComp https://openai.com/index/browsecomp/ ; Meta CRAG KDD Cup 2024 https://www.aicrowd.com/challenges/meta-comprehensive-rag-benchmark-kdd-cup-2024 | MEM, WEB, EVAL |
| Project topic 3: Job Hunting Agents | From a query plus CV, search job APIs, extract facts, present structured results | Tool/API use, extraction | https://apislist.com/category/28/jobs | TOOL, APP |
| Project topic 4: Online Shopping Assistant | Product search/recommendation agent with structured feature comparison | Web agents, benchmarks | AgentBench ; WebArena https://webarena.dev/ ; WebShop https://webshop-pnlp.github.io/ | WEB, APP, EVAL |
| Project topic 5: Personal Tutor | Agent that explains concepts, finds knowledge gaps, tracks progress | Memory, personalization | n/a | APP, MEM |
| Project topic 6: Personal Assistant | Agent that manages calendar/mail/chat | Tool use, personal-data integration | n/a | TOOL, APP |
| Project topic 7: Personas Reading the News | Persona agents browsing political news; study effects on memory/beliefs | Agent simulation, memory | Personas provided by instructors (not public) | MULTI, MEM, APP |
| Project topic 8: Wikipedia Article Generation | RAG/agent system to generate Wikipedia articles, evaluated against real articles with rubrics | RAG, LLM-as-judge | WikiGenBench, WikiAutoGen (named, no URLs) | MEM, EVAL, APP |
| Project topic 9: Skill-Mining from Public Data | RAG system that summarizes developer skills/roles from GitHub profiles | RAG, extraction | GitHub profiles | MEM, APP |
| Project topic X: Own idea | Student-proposed topic, subject to approval | n/a | n/a | APP |

## Codebases & tools referenced

- LangChain: https://www.langchain.com/langchain
- Tavily (search API): https://www.tavily.com/
- MCP (named in the exercise filename)
- AgentBench: https://github.com/THUDM/AgentBench
- SmartPlay: https://github.com/microsoft/SmartPlay
- WebArena: https://webarena.dev/ ; WebShop: https://webshop-pnlp.github.io/
- BrowseComp: https://openai.com/index/browsecomp/ ; Meta CRAG (KDD Cup 2024): https://www.aicrowd.com/challenges/meta-comprehensive-rag-benchmark-kdd-cup-2024
- Course evaluation PDFs: .../FSS2026/IE_685_Large_Language_Models_and_Agents_Lecture_Evaluation_FSS2026.pdf ; .../FSS2026/IE_686_Large_Language_Models_and_Agents_Project_Evaluation_FSS2026.pdf

## Notes

- The course page loaded fully. Slide and exercise links on the page are relative and resolve under `https://www.uni-mannheim.de/media/...`; three PDFs (lectures 04, 06, 07) were fetched and downloaded successfully. Only the project-intro deck (07) was actually read. Key topics for lectures 2-6 and 8 are inferred from their titles and the syllabus list, not from the slide contents.
- The WebFetch tool could not extract text from the slide PDFs (binary). Lecture 4 is a 78-page deck tagged German-language (`/Lang(de)`), but the visible slides of deck 07 are in English.
- Syllabus topic 8, "Evaluation of LLMs and LLM agents", has no dedicated slide deck or dated session on the page. It may be folded into other lectures or the projects.
- Exercise zips were not downloaded or opened (per instructions; no code was run).
- The page lists one session date as "28.05.2026", which is out of order and probably means 28.04.2026. The IE686 project deck's own schedule uses Wednesday coaching dates (15.04-13.05) and presentations on 19.05 and 20.05.
- No separate public GitHub repo or videos were found for this course.
