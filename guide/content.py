r"""Hand-written content for the agentic-systems guide.

Mini-markup used inside LaTeX strings (expanded by build_guide.py):
  [[CMU:2]]        -> link to lecture 2 of course CMU in the catalogue (with title)
  [[CMU:2|short]]  -> same, but link text is "CMU 2" only
  [[A:CMU:A1]]     -> link to the CMU assignment whose name starts with "A1"
  [[M:TOOL]]       -> link to the module with that key
  [[C:CMU]]        -> link to the course catalogue entry
"""

RESEARCH = "../research"

# ---------------------------------------------------------------------------
# Courses (order = catalogue order)
# ---------------------------------------------------------------------------
COURSES = [
    dict(code="CMU", short="CMU", file="cmu-11768-verified.md", kind="cmu",
         asg_file="cmu-11768.md",
         title="11-768 AI Agents", inst="Carnegie Mellon University (LTI)", term="Fall 2026",
         people="Graham Neubig, Daniel Fried",
         url="https://www.cmu-agents.com/#/schedule",
         level="Graduate; assumes you have trained neural LMs",
         archetype="Systems + training (build, evaluate, RL-train)",
         slides="L1--14", video="L1--9", codepub="A1--A3 public",
         best="The backbone course: harness engineering, evals, SFT/RL, safety, search.",
         overview=r"""The most complete public agents course in the collection, and the one this guide is built around.
It goes from capabilities (tool use, long-context management, skills and memory, planning) to domains (coding, computer use, deep research), then to training (SFT, RL basics, advanced RL, RL systems), safety and observability, frameworks (OpenHands, LangGraph), interaction and search.
The readings are taken from production systems: harness source code, provider KV-cache pricing pages and the MCP spec.
The three assignments form one pipeline: build a harness (A1), evaluate an agent with an LLM judge (A2), then RL-train an agentic policy (A3).
Slides for lectures 1--14 and recordings for lectures 1--9 are public on the schedule page."""),
    dict(code="STAN26", short="Stanford '26", file="stanford-cs146s-fall2026-verified.md", kind="stan26",
         asg_file="stanford-cs146s.md", asg_section="Fall 2026",
         title="CS146S The Modern Software Developer", inst="Stanford University", term="Fall 2026 (current)",
         people="Mihail Eric", url="https://themodernsoftware.dev/",
         level="Undergrad/grad; CS111/CS161-level programming",
         archetype="Coding-agent practice (practitioner)",
         slides="Weeks 1--3 and week 4 Tue so far", video="none", codepub="Weeks 1--3 assignments",
         best="How production coding agents work and how to set up a repo and a team around them.",
         overview=r"""A practitioner course about building software with coding agents, with an industry guest in most weeks.
The Fall 2026 version focuses on agents. Week~1 builds ``Claude Code in 200 lines'' and dissects production system prompts. Later weeks cover context engineering and MCP, agent skills, CLAUDE.md/AGENTS.md and hooks, agent-ready codebases, agentic code review, security, background agents, and the ``software factory''.
The assignments are short and practical: dissect a real Claude Code trace, build an OAuth MCP server, and author an Agent Skill."""),
    dict(code="STAN25", short="Stanford '25", file="stanford-cs146s.md", kind="std",
         title="CS146S The Modern Software Developer (archive)", inst="Stanford University", term="Fall 2025",
         people="Mihail Eric", url="https://themodernsoftware.dev/fall2025",
         level="Undergrad/grad", archetype="Coding-agent practice (practitioner)",
         slides="Most lectures (Google Slides)", video="none", codepub="8 weekly assignments (branch fall2025)",
         asg_section="Fall 2025",
         best="Slide decks on prompting, building a coding agent, MCP servers, AI testing/security, code review, SRE.",
         overview=r"""The previous offering of CS146S. Its value here is that nearly every lecture has a public slide deck, and the eight assignments (prompting playground, AI-IDE workflow, custom MCP server, Claude Code automations, Warp, Semgrep, Graphite review, multi-stack build) live on the \texttt{fall2025} branch of the assignments repository.
The lecture dates come from an authorized translation and may be off by a day, so treat them as approximate."""),
    dict(code="NEU", short="Northeastern", file="northeastern-agentic-ai.md", kind="std",
         title="Agentic AI", inst="Northeastern University (Khoury)", term="Fall 2026 (in progress)",
         people="Caglar Yildirim", url="https://agenticllms.github.io/",
         level="Gentle on-ramp (Python primer provided)", archetype="Builder (LangChain/LangGraph stack)",
         slides="2 HTML decks", video="none", codepub="Notebooks W02b--W06b, DADA1",
         best="Best guided, notebook-by-notebook path from an LLM API call to a deployed LangGraph agent.",
         overview=r"""Pairs one seminal paper with the matching LangChain/LangGraph documentation in every session.
One running example, the ``Husky Tech'' customer-support agent, grows week by week: a notebook prototype, then a project skeleton, then a Hugging Face Spaces deployment, a LangGraph rewrite, RAG, a self-grading retrieval loop, and then a plan-search-review-replan loop and agentic RAG behind its policy-search tool.
Later sessions cover planning, agentic RAG, three multi-agent sessions, MCP and its security, evaluation, and optimization with DSPy and cost controls.
Sessions after F~11/13 were not posted when this guide was compiled."""),
    dict(code="HARV", short="Harvard", file="harvard-cs2680.md", kind="std",
         title="CS 2680 Modern AI Systems: Agents and System Optimizations", inst="Harvard University (SEAS, MaDSys)",
         term="Fall 2026 (in progress)",
         people="Juncheng Yang", url="https://cs2680.seas.harvard.edu/",
         level="Graduate systems course; CS61 plus a graduate systems course",
         archetype="Agent systems and serving (use, build, optimize, serve)",
         slides="8 decks (Part I)", video="none (not recorded)", codepub="A2--A3 starter repo (no license); A4--A5 unreleased",
         best="Treating an agent as a system to measure: harness design, evaluation, and cost per solved task, then the serving stack underneath.",
         overview=r"""Follows one agentic system from the agent loop down through the serving stack.
Part~I uses a coding agent (Claude Code), then designs one: context management and tool design, multi-agent architecture and communication, memory and reliability, evaluation, and cost and performance. Part~II, from October~19, covers LLM serving: batching and scheduling, speculative decoding, prefix caching, quantization, GPUs and kernels, and routing.
The annotated reading pages and the two reference notes (agent evaluation and benchmarks, cost-effective agents) are worth reading on their own.
The five assignments take one system apart in steps: watch the agent, build the loop, make every token count, serve the model yourself, optimize the full stack.
\textbf{Access:} assignments 2 and 3 call a course model API whose keys go to enrolled students only. Outside the course you can run assignment~2 only against your own OpenAI-compatible endpoint, and assignment~3's leaderboard scoring is not available.
When this guide was last updated (October~16, 2026), annotated reading pages for most Part~II sessions were online but not linked from the home page; no Part~II slides and no specs for assignments 4 and 5 were posted."""),
    dict(code="UB", short="Buffalo", file="buffalo-cse410.md", kind="std",
         title="CSE 410/510 Introduction to Agentic Engineering", inst="University at Buffalo", term="Fall 2026",
         people="Joaquin Carbonara, David Doermann",
         url="https://cse.buffalo.edu/courses/cse410/2026_fall/cse410ae/",
         level="Upper-undergrad / MS", archetype="Engineering discipline (framework-agnostic)",
         slides="none", video="none", codepub="none (lab specs only)",
         best="Five lab specs and a capstone spec that treat an agent as an engineered, evaluated, bounded system.",
         overview=r"""Treats an agent as an engineered system ``not a magic chatbot'': a bounded environment, designed tools, explicit evaluation and safety constraints.
No slides or code are public. What makes it useful is the lab sequence: a minimal tool-using agent, retrieval and memory, workflow graphs, an evaluation harness, and human-in-the-loop safety boundaries. The capstone spec, a useful bounded agent with an architecture document, an eval suite and a risk assessment, is a good template for your own portfolio project."""),
    dict(code="UVA", short="UVA", file="uva-agentic-ai.md", kind="std",
         title="CS 6501 Workshop on Building AI Agents", inst="University of Virginia", term="Spring 2026",
         people="Henry Kautz", url="https://www.cs.virginia.edu/~rmw7my/Courses/AgenticAISpring2026/agenticAI.html",
         level="Graduate workshop; Python", archetype="Hands-on lab workshop (small/open models)",
         slides="PPTX per topic", video="1 + podcasts", codepub="Starter scripts per topic",
         best="The richest set of runnable lab exercises: local LLMs, LangGraph, tools, RAG, VLMs, MCP/A2A, Tinker fine-tuning.",
         overview=r"""A workshop where most of the programming happens in class.
Each topic page has learning goals, an exercise sheet of measurable experiments, PPTX slides and starter scripts.
The first half is labs: running an LLM, LangGraph control flow, tool calling, the tool ecosystem, RAG, vision-language agents, MCP and A2A, and QLoRA-style fine-tuning with Tinker.
The second half is state-of-the-art lectures: context management, chain-of-thought internals, coding agents, personal agents and distillation, and agents for science, mathematics and visual reasoning.
Row numbers in the catalogue are calendar slots. The topic number appears in each title."""),
    dict(code="UW", short="UW-Madison", file="uwmadison-cs839.md", kind="std",
         title="CS 839 AI Agents", inst="University of Wisconsin--Madison", term="Spring 2026",
         people="Aws Albarghouthi", url="https://github.com/barghouthi/ai-agents",
         level="Graduate research seminar", archetype="Research seminar (paper reading)",
         slides="none", video="none", codepub="Demo notebook; MIT license",
         best="A curated, critical reading list from ReAct to self-improving and evolutionary agents, plus a no-frameworks coding-agent assignment.",
         overview=r"""A paper seminar with two main papers and several supplementary papers per session.
It runs from CoT, ReAct, Toolformer and ToT to coding agents, deep research, agents for science, prompt-injection security, agent optimization (DSPy, TextGrad, ADAS, GEPA), self-improving and evolutionary agents, search, multi-agent systems and memory.
The buy-in assignment, a CLI coding agent built on raw API calls with no agent frameworks, is one of the best single exercises in the collection.
The repository is MIT-licensed."""),
    dict(code="JHU", short="JHU", file="jhu-machine-programming.md", kind="std",
         title="EN.601.727 Machine Programming", inst="Johns Hopkins University", term="Fall 2026 (in progress)",
         people="Ziyang Li", url="https://machine-programming.github.io/",
         level="Graduate (PL + ML)", archetype="Program synthesis to coding agents",
         slides="L1--14", video="none", codepub="A1--A3 public",
         best="Ties classic program synthesis to LLM coding agents, with two MCP lectures and a strong web-app agent assignment.",
         overview=r"""Treats code generation from both the symbolic side (enumerative search, types, specifications) and the LLM side (decoding, prompting, iterative refinement, agentic frameworks, MCP, pre- and post-training of code models).
The assignments are the main attraction: an enumerative synthesizer with an LLM step (A1), a rigorous pass@k evaluation of coding LLMs across three languages and four prompting strategies (A2), and a tool-calling web-app agent with secure file tools that builds a chat room, a Tetris variant and a creative app (A3).
The second half covers formal verification, security, HPC, neurosymbolic programming and six student-led paper sessions in which two students defend and attack each paper."""),
    dict(code="CU", short="CU Boulder", file="colorado-csci7000.md", kind="std",
         title="CSCI 7000-005 Building AI Agents", inst="University of Colorado Boulder", term="Spring 2026",
         people="Danny Dig", url="https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/index.html",
         level="Graduate seminar; competent SE assumed", archetype="Research seminar (agentic software engineering)",
         slides="4 instructor decks", video="none", codepub="none",
         best="Research reading on agentic software engineering: refactoring agents, SWE-agent, skills, memory, MCP design choices.",
         overview=r"""A seminar with two papers per meeting, one-page critiques and a team research project with four milestones.
Its reading list leans toward agentic software engineering, from agent surveys and an agentic-SE roadmap through refactoring agents and the classic patterns (ReAct, Reflexion, Toolformer, Gorilla, PAL, AutoGen, MetaGPT, debate) to 2025--2026 work on skills, memory, safety, coding-agent configuration and MCP design.
The ``tool experience report'' (run a paper's tool on your own case and critique it) is a good habit to borrow."""),
    dict(code="MANN", short="Mannheim", file="mannheim-ie685.md", kind="std",
         title="IE 685/686 Large Language Models and Agents", inst="Universit\\\"at Mannheim (DWS)", term="Spring 2026",
         people="Ralph Peeters, Christian Bizer, Aaron Steiner",
         url="https://www.uni-mannheim.de/dws/teaching/course-details/courses-for-master-candidates/ie-685-large-language-models-and-agents/",
         level="Master's; Python + basic ML", archetype="Applied master's course + team project",
         slides="8 PDF decks", video="none", codepub="5 exercise notebooks (zip)",
         best="Compact slide decks from LLM basics to context engineering, plus nine well-specified team-project briefs.",
         overview=r"""A short lecture block (introduction, post-training, prompting, agents and tool use with MCP, RAG, context engineering with deep agents, safety), each with an exercise notebook, followed by a team project.
The nine project briefs (multi-agent gaming, QA agents, job hunting, a shopping assistant, a tutor, a personal assistant, news-reading personas, Wikipedia generation, skill mining) are ready-made portfolio ideas, and each comes with suggested benchmarks."""),
    dict(code="UCHI", short="UChicago", file="uchicago-ai-agents-social-science.md", kind="std",
         title="AI Agents for Social Science and Society", inst="University of Chicago (KnowledgeLab)", term="Winter 2026",
         people="James A. Evans",
         url="https://github.com/KnowledgeLab/AI-Agents-for-Social-Science-and-Society-2026",
         level="Grad / advanced undergrad (computational social science)", archetype="Applied: agents as research instruments",
         slides="none", video="none", codepub="9 weekly notebooks",
         best="Agents as simulated subjects and research assistants; notebooks on multi-agent simulation, LoRA, RL, steering and red-teaming.",
         overview=r"""Treats LLM agents as tools for social science: simulated subjects and ``digital doubles'', research assistants and automated scientists.
Agent-engineering content is concentrated in week~3 (prompted multi-agent simulation with AutoGen and Concordia, RAG) and week~5 (LoRA fine-tuning, benchmarking, tools and MCP). Other weeks cover deep-learning foundations, causal designs, interpretability and steering, RL, multimodal agents, and alignment.
Two notebooks (weeks 6 and 8) were too large to inspect."""),
    dict(code="S329A", short="Stanford 329A", file="stanford-cs329a.md", kind="std",
         title="CS329A Self-Improving AI Agents", inst="Stanford University", term="Autumn 2025",
         people="Aakanksha Chowdhery, Azalia Mirhoseini", url="https://cs329a.stanford.edu/",
         level="Graduate; CS224N or CS229S", archetype="Research course (self-improvement levers) + homeworks",
         slides="none linked", video="9 recordings (Stanford Online)", codepub="HW1--HW3 public repos (HW1 MIT, HW3 Apache-2.0)",
         best="The clearest path through test-time compute, verifiers, RL and open-ended self-improvement, with three public homeworks.",
         overview=r"""Asks how an agent improves through interaction with itself and its environment, and takes the levers in order: repeated sampling and test-time compute, verifiers and process reward models, learning from tool and execution feedback, planning and tree search, and train-time RL (STaR, GRPO, DAPO).
The second half covers open-ended self-improvement (ADAS, AI Scientist, AlphaEvolve), deep-research and software-engineering agents, memory, and long-horizon evaluation, with five guest talks.
The homeworks follow the same arc: test-time scaling on AIME25, code verification with LLM judges and synthetic unit tests, then a self-improving agentic workflow.
No slide decks are posted. The video links were matched to lectures through a third-party index and then checked on YouTube."""),
    dict(code="BRKAG", short="Berkeley '25", file="berkeley-agentic-ai-f25.md", kind="std",
         title="CS194/294-196 Agentic AI", inst="UC Berkeley (RDI)", term="Fall 2025",
         people="Dawn Song (with guest speakers)", url="https://rdi.berkeley.edu/agentic-ai/f25",
         level="Undergraduate and graduate; ML/DL background", archetype="Guest-lecture series + AgentBeats project (also a MOOC)",
         slides="9 of 13 sessions", video="12 of 13 sessions", codepub="AgentBeats tutorial repo (no license stated)",
         best="Industry and lab speakers on post-training, agent evaluation and deployment, and an evaluator-agent project (AgentBeats).",
         overview=r"""A guest-speaker series (OpenAI, NVIDIA, Microsoft, Meta, Sierra, Google DeepMind and others) bracketed by Dawn Song's introduction and closing lecture on agent safety and security.
Recurring themes are post-training for verifiable agentic tasks, agent evaluation and its statistics, multi-agent systems, and lessons from production deployment.
The project is the distinctive part. In phase~1 you build a \emph{green} agent, an evaluator that turns a benchmark into tasks, an environment and scoring. In phase~2 you build the agent under test, called \emph{white} in the course and \emph{purple} in the current AgentBeats competition.
The same lectures ran as a MOOC at agenticai-learning.org/f25."""),
    dict(code="BRKADV", short="Berkeley Adv.", file="berkeley-advanced-llm-agents-sp25.md", kind="std",
         title="CS294/194-280 Advanced Large Language Model Agents", inst="UC Berkeley (RDI)", term="Spring 2025",
         people="Dawn Song, Xinyun Chen, Kaiyu Yang", url="https://rdi.berkeley.edu/adv-llm-agents/sp25",
         level="Upper-division undergraduate and graduate", archetype="Guest-lecture series + Lean labs (also a MOOC)",
         slides="All 12 lectures", video="All 12 lectures", codepub="2 Lean labs in a public Drive folder (no license)",
         best="Research talks on reasoning, post-training, coding and web agents and formal math, plus a compiler-verified agent lab.",
         overview=r"""Picks up where Berkeley's Fall 2024 LLM Agents course left off: inference-time reasoning, iterative preference optimization and open post-training recipes (Tulu~3), language-agent memory and planning, coding agents and vulnerability detection, and multimodal web and computer-use agents.
A four-lecture block on formal mathematics (AlphaProof, autoformalization, theorem proving, abstraction discovery) is followed by a closing lecture on agent safety and security.
Lab~2 is the main draw for agent builders: a verify-and-retry agent loop in which the Lean compiler is the verifier, and grading rejects 	exttt{sorry}. Lab~1, writing two Lean~4 problems with formal specifications, is dataset work rather than an agent task."""),
    dict(code="S329T", short="Stanford 329T", file="stanford-cs329t.md", kind="std",
         title="CS329T Trustworthy ML: Building and Evaluating Agentic Systems", inst="Stanford University", term="Fall 2025",
         people="Anupam Datta, John Mitchell", url="https://web.stanford.edu/class/cs329t/syllabus.html",
         level="Graduate; CS229 + deep learning", archetype="Project course on agent evaluation",
         slides="11 decks (10 sessions)", video="none (not recorded)", codepub="HW1 handout PDF; starter branch 404",
         best="Evaluation-first agent building: Goal-Plan-Action evaluation, LLM judges, MCP tool descriptions, GEPA and red-teaming.",
         overview=r"""A project course on building agentic applications and then evaluating them so they can be improved step by step.
After LLM background, prompting and RAG, it introduces its main evaluation idea, checking whether an agent's goals, plans and actions line up (\emph{Agent GPA}).
Guest talks cover systematic agent evaluation and refining LLM judges, MCP and writing tool descriptions, data curation and RL for agents, GEPA, and agent security.
The one homework traces a LangGraph multi-agent research system in TruLens, has you label its failure modes by hand, and compares your labels with an LLM judge's.
The starter branch linked from the handout no longer exists; an updated version of the notebook is on the TruLens main branch."""),
]

# ---------------------------------------------------------------------------
# Supplementary (non-course) resources (bookmarks folder + later additions)
# ---------------------------------------------------------------------------
SUPPLEMENTS = [
    dict(key="sup-mcp", name="Model Context Protocol docs (version 2026-07-28)",
         url="https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro", tags=["TOOL", "ARCH"],
         body=r"""MCP is the open standard for connecting an AI application (the \emph{host}) to external context and tools. The host creates one \emph{client} per \emph{server}. Servers expose \emph{tools} (callable functions with JSON-Schema inputs), \emph{resources} (contextual data) and \emph{prompts} (templates), over \emph{stdio} for local servers or \emph{Streamable HTTP} for remote ones, with OAuth recommended.
\textbf{Version caveat:} the 2026-07-28 revision makes the protocol stateless. Every request carries its version and capabilities in \texttt{\_meta}, servers must support a new \texttt{server/discover} method that replaces the old initialize handshake (clients may call it, but can also send requests without it), change notifications move to an opt-in \texttt{subscriptions/listen} stream, and \emph{sampling} and \emph{logging} are deprecated. Course material written before mid-2026 (including several lectures in this guide) teaches the older stateful handshake. The concepts still carry over, but check the current docs before you write code."""),
    dict(key="sup-codeexec", name="Anthropic Engineering: Code execution with MCP",
         url="https://www.anthropic.com/engineering/code-execution-with-mcp", tags=["TOOL", "MEM", "DEPLOY"],
         body=r"""Argues that agents connected to many MCP servers should call tools \emph{through code} instead of through direct tool calls. Each server is exposed as a file tree of small code APIs. The agent reads only the definitions it needs (progressive disclosure) and writes a script that runs in a sandbox, so intermediate data never passes through the context window. In the worked example, context drops from about 150{,}000 to 2{,}000 tokens. The cost is running a secure sandbox. This ties tool use to context engineering and to Skills, and CU Boulder assigns a paper that studies the same design choice ([[CU:24|short]])."""),
    dict(key="sup-openclaw", name="OpenClaw documentation",
         url="https://docs.openclaw.ai/", tags=["ARCH", "DEPLOY", "SAFE"],
         body=r"""An MIT-licensed, self-hosted, always-on personal assistant. A single \emph{gateway} process owns sessions, routing and \emph{channels} (Discord, Signal, Slack, WhatsApp, \ldots). Agents get tools, cron jobs, hooks, webhooks and on-demand skills from the ClawHub registry. It is a useful reference architecture for long-running, multi-channel agents and a cautionary case study: CMU's safety lecture cites an OpenClaw incident report ([[CMU:13|short]]), and UVA discusses the OpenClaw family in its personal-agents lecture ([[UVA:18|short]]). \emph{Catalogued only.} Under your install policy, vet it before installing anything."""),
    dict(key="sup-tinyagent", name="Berkeley BAIR: TinyAgent, Function Calling at the Edge",
         url="https://bair.berkeley.edu/blog/2024/05/29/tiny-agent/", tags=["TOOL", "TRAIN", "DEPLOY"],
         body=r"""A case study in specializing a \emph{small} model for agentic tool use. GPT-4-Turbo generates synthetic function-calling plans, which are validated programmatically. A 1.1B or 7B model is LoRA-fine-tuned to emit LLMCompiler-style DAG plans over 16 macOS tools. A small DeBERTa classifier replaces embedding retrieval for tool selection, roughly halving the prompt. The model is then quantized to 4-bit for llama.cpp. The 1.1B model (80.4\%) beats GPT-4-Turbo (79.1\%) on this fixed toolset while running locally.
Code: \href{https://github.com/SqueezeAILab/TinyAgent}{SqueezeAILab/TinyAgent} (MIT). Read it after [[M:TOOL]] and the SFT lecture in [[M:TRAIN]]."""),
    dict(key="sup-agentsec", name="MIT 6.566 guest lecture: AI Agent Security (Anish Athalye, April 2026)",
         url="https://github.com/anishathalye/ai-agent-security-lecture", tags=["SAFE", "TOOL", "ARCH"],
         body=r"""A single lecture, with a \href{https://www.youtube.com/watch?v=w0oGeKxD5Fc}{recording} and a repository of thirteen small Python scripts, that builds an agent from scratch and then attacks it. The scripts go from raw completion and chat templates, through tools, native tool calling, an agent loop and a CodeAct-style code agent, to a web-summarization prompt-injection demo. They end with two defenses: the dual-LLM pattern and CaMeL, which runs benign and adversarial scenarios with and without CaMeL. The assigned reading is the CaMeL paper, \emph{Defeating Prompt Injections by Design} (Debenedetti et al., 2025). Some scripts need Ollama with a local model and others need an API key. No license is stated. Run it after [[M:TOOL]] and alongside [[M:SAFE]]. Under your install policy, vet \texttt{uv} and the dependencies first."""),
    dict(key="sup-anthauto", name="Anthropic: Building effective agent automations (Martin and Avilla, October 2026)",
         url="https://claude.dev/blog/building-effective-agent-automations/", tags=["DEPLOY", "SAFE", "TOOL"],
         body=r"""A worked example of an unattended, scheduled agent (``daily-brief'', on Claude Managed Agents) that reads sources, tracks what changed and posts a brief to Slack. It is organised as six components: sources, destination, agent, schedule, memory and guardrails. Its rules are the concrete form of the durable-state and idempotency advice in [[M:DEPLOY]]. Read each source from a stored bookmark, not a fixed time window. Report a failed read as unreadable, never as a quiet day. Count a post as sent only when Slack confirms it, and only then update the bookmarks and the ledger. Re-read preferences every run from a store the agent cannot edit. Use read-only credentials wherever the agent only reads, and cap each run's spending at three to five times a normal run at first. Posting requires no human approval. Read-only permissions, a host allowlist and spending limits constrain the automation, but malicious source content can still alter the brief. The post gives design reasoning and failure examples but no measurements. Our suggested companion reading: the \hyperref[sup-openclaw]{OpenClaw} documentation, for comparison with an always-on architecture."""),
    dict(key="sup-notion", name="Notion: How we built a personal data scientist for every Notion employee (David Thomas, October 2026)",
         url="https://www.notion.com/blog/how-we-built-a-personal-data-scientist-for-every-notion-employee", tags=["MEM", "DEPLOY", "EVAL", "APP"],
         body=r"""A production case study of Data Scout, an internal agent that answers plain-language questions from governed Snowflake data through MCP. Each user signs in with their own credentials, so existing access controls apply. A curated, owned library separates data context (metrics, sources, filters), business context and routing guidance. Queries carry structured metadata so traces show which definitions were used. A nightly review agent records missing, stale or conflicting context; a separate triage agent deduplicates findings, applies authorised fixes, and sends ambiguous or higher-risk changes to a person. The post's main lesson is that a query can run cleanly and still answer the wrong question, through wrong meaning, routing, measurement or interpretation. Notion reports that weekly requests to its data team fell by about 80\% within two months and that about half of its employees use the agent. These figures are self-reported, and the post says its evaluation is still maturing: usage and query success do not prove accuracy. Read it with [[M:MEM]] for context engineering and [[M:DEPLOY]] for operations."""),
    dict(key="sup-barkley", name="Jesse Barkley: local agent demos for the CMU executive Agentic AI program (2026)",
         url="https://github.com/jabarkle", tags=["ARCH", "TOOL", "MEM", "RSN", "MULTI"],
         body=r"""Five small repositories written as office-hours support for Carnegie Mellon's executive program \emph{Agentic AI: Building Autonomous Systems for Real-World Applications}. They are teaching demos by one instructor, not a course, and they are the only place in this guide where one system grows in stages. Everything runs on a laptop through Ollama with a 3--4B model, with no API key.
\begin{itemize}
\item \href{https://github.com/jabarkle/EmeritusMCP}{\texttt{EmeritusMCP}}: the smallest useful MCP example. A 32-line server with one read-only tool, and an agent that answers the same question with and without it. Dependencies are pinned.
\item \href{https://github.com/jabarkle/Local-Agent-Demo}{\texttt{Local-Agent-Demo}}: a ``teacher's assistant'' agent. The loop is written out by hand, with a cap of three tool steps. Because the model has no native tool calling, each step is a schema-constrained JSON decision followed by a separate answer call, so you can see that a tool call is text the harness parses. Tools live in a separate MCP server that the agent discovers at start-up. Long-term memory is a JSON file searched by embedding similarity, and two \texttt{SKILL.md} procedures load only when a request needs them. A trace panel shows what the model sees at each step.
\item \href{https://github.com/jabarkle/Agent-with-Subagent}{\texttt{Agent-with-Subagent}}: the same system plus one subagent that starts with an empty context and receives a written briefing. Its README states the delegation test plainly: big input, small output, no need to remember the middle.
\item \href{https://github.com/jabarkle/Agent-with-subagent-and-langgraph}{\texttt{Agent-with-subagent-and-langgraph}}: the same system again as a LangGraph \texttt{StateGraph} with five nodes (recall, decide, act, answer, reflect). Read it beside the hand-written loop to see what the framework adds and hides.
\item \href{https://github.com/jabarkle/EmeritusAgenticAIStarterCode}{\texttt{EmeritusAgenticAIStarterCode}}: Tree of Thoughts as a 75-line beam search in plain Python, then the same search in LangGraph and in CrewAI. The evaluator is the model scoring its own partial paths, so apply the caution in [[M:RSN]]: check that the score carries information before trusting the search.
\end{itemize}
\textbf{Caveats.} The MCP code uses version~2 of the official Python SDK (\texttt{MCPServer}, \texttt{Client}) over stdio. The code was read for this guide but not run. No repository states a licence, there are no tests beyond a set-up check, compiled caches and a filled memory file are committed, and three of the five leave dependency versions open (\texttt{>=}). Under your install policy, pin and vet the packages before installing. Do them in the order listed, after [[M:ARCH]]."""),
    dict(key="sup-cadsmith", name="CADSmith: multi-agent CAD generation with programmatic geometric validation (Barkley, Loghmani and Barati Farimani, 2026)",
         url="https://arxiv.org/abs/2603.26512", tags=["MULTI", "EVAL", "APP"],
         body=r"""A worked example of a fixed multi-agent pipeline whose feedback is a real measurement, not a model's opinion of its own work. A planner writes a design specification, a coder generates CadQuery code with retrieval over the API documentation, an executor runs it in a subprocess and reads exact geometry from the OpenCASCADE kernel, a validator combines those measurements with a vision-language judge that sees three rendered views, and a refiner repairs the code. An inner loop retries execution errors up to three times and an outer loop retries geometric errors up to five. The judge is a stronger model than the coder. The authors report results on their own benchmark of 100 hand-written prompts with hand-written reference scripts, against a single-call baseline and an ablation without vision: mean Chamfer distance falls from 28.37 (single call) to 18.19 (pipeline without vision) to 0.74 (with vision). They also show a part that passed every check with visible gaps. These figures are self-reported and were not reproduced here. Note that it is a workflow in the sense of [[M:ARCH]]: the code fixes the order of the roles. \href{https://github.com/jabarkle/CADSmith}{Code} (no licence stated). Read it with [[M:MULTI]] for roles and with [[M:EVAL]] for the baseline-and-ablation design."""),
    dict(key="sup-colab", name="Google Colab", url="https://colab.research.google.com/", tags=["DEPLOY"],
         body=r"""A hosted Jupyter runtime. Use it to run course notebooks (UChicago, Northeastern, Mannheim, UVA) without a local setup, and to keep experiments with downloaded code off your own machine."""),
]

# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------
TAGS = {
    "FND":   ("Foundations", "4E79A7"),
    "ARCH":  ("Architectures", "59A14F"),
    "TOOL":  ("Tools", "F28E2B"),
    "MEM":   ("Memory/RAG/Context", "B07AA1"),
    "RSN":   ("Reasoning/Planning", "E15759"),
    "MULTI": ("Multi-agent", "76B7B2"),
    "CODE":  ("Coding agents", "EDC948"),
    "WEB":   ("Web/GUI/Multimodal", "FF9DA7"),
    "EVAL":  ("Evaluation", "9C755F"),
    "TRAIN": ("Training", "D37295"),
    "SAFE":  ("Safety/Security", "E03C31"),
    "DEPLOY": ("Deployment", "499894"),
    "APP":   ("Applications", "86BCB6"),
    "ORG":   ("Logistics", "BAB0AC"),
}

# ---------------------------------------------------------------------------
# Modules (learning order). select: tags that pull lectures in; mcp: True/False/None
# split for TOOL lectures mentioning MCP/A2A.
# ---------------------------------------------------------------------------
MODULES = [
dict(key="SETUP", num=0, title="Setup: Your Agent Workbench", tags=[], mcp=None,
objectives=["Have a reproducible Python environment, API access and a sandbox to run course code in.",
            "Know which courses need which accounts and services."],
concepts=r"""Every course here assumes a small workbench, and setting it up once saves friction later.
\begin{itemize}
\item \textbf{Python environment.} CMU and Northeastern use \texttt{uv}; Stanford '25 used Poetry/Conda. Keep one virtual environment per course repository.
\item \textbf{Models.} You need at least one hosted API key (the courses use OpenAI, Anthropic via Bedrock, Gemini and OpenRouter) and, optionally, a local runtime (Ollama is used by Northeastern, UVA and Stanford '25) for cheap, private experiments with small open models.
\item \textbf{Sandboxes.} Agents execute code. CMU runs tools in Modal sandboxes. Colab is the zero-install choice for notebooks. Never let an agent you are developing run commands directly on the machine that holds your credentials.
\item \textbf{Tracing.} Log every model call and tool call from day one (plain JSONL is enough). Every evaluation and debugging lecture assumes you have traces.
\end{itemize}
\textbf{Install policy reminder.} The courses name many packages (LangGraph, FastMCP, Tinker, Modal, \ldots). Treat each install as a deliberate decision: pin versions and check security advisories before installing.""",
sequence=[("[[NEU:3]]", "The setup page walks through uv, \\texttt{.env} keys and a first LLM API call."),
          ("[[UVA:1]]", "Run a small open model locally and on Colab, with and without quantization."),
          ("Supplement: \\hyperref[sup-colab]{Google Colab}", "The runtime for every notebook-based course.")],
readings=[], handson=[]),

dict(key="FND", num=1, title="LLM Foundations and Prompting", tags=["FND"], mcp=None,
objectives=["Explain next-token prediction, pre-training versus post-training, and why instruction-tuned models follow chat templates.",
            "Use prompting techniques (few-shot, CoT, self-consistency, structured output) deliberately.",
            "Run and benchmark a small open model locally."],
concepts=r"""An agent is only as good as the model in its loop, and most agent bugs trace back to how that model was conditioned.
\begin{itemize}
\item \textbf{Pre-training} produces a next-token predictor. \textbf{Post-training} (instruction tuning, RLHF/RL) turns it into an assistant that follows \emph{chat templates}: role-tagged messages, and for agents, tool-call and tool-result segments. CMU's tool-use lecture shows how those templates encode function calls.
\item \textbf{Prompting} is programming in natural language. Few-shot examples, chain-of-thought, self-consistency and explicit output schemas are the basic toolkit. Structured output (JSON or typed objects) is what makes a model's response machine-actionable.
\item \textbf{Cost and latency} scale with tokens, so an agent's prompt is a budget. Context-window limits and KV-cache pricing return in [[M:MEM]] and [[M:DEPLOY]].
\item \textbf{Small versus large models.} UVA's first reading argues that small language models are the future of agentic AI, and the TinyAgent supplement shows a 1.1B model beating a frontier model on a narrow toolset.
\end{itemize}""",
sequence=[("[[NEU:2]]", "Transformers, autoregressive generation, base versus instruction-tuned models (with a local model)."),
          ("[[NEU:3]]", "InstructGPT, CoT, and the LLM API basics notebook."),
          ("[[STAN25:1]] and [[STAN25:2]]", "How an LLM is made, then power prompting (slides)."),
          ("[[MANN:1]]--[[MANN:3|short]]", "Compact decks on LLM basics, post-training and prompt engineering."),
          ("[[UVA:1]]", "Benchmark Llama-3.2-1B on MMLU across hardware and quantization settings.")],
readings=["Vaswani et al., \\href{https://arxiv.org/abs/1706.03762}{\\emph{Attention Is All You Need}} (2017)",
          "Ouyang et al., \\href{https://arxiv.org/abs/2203.02155}{\\emph{InstructGPT}} (2022)",
          "Wei et al., \\href{https://arxiv.org/abs/2201.11903}{\\emph{Chain-of-Thought Prompting}} (2022)",
          "Belcak et al., \\href{https://arxiv.org/abs/2506.02153}{\\emph{Small Language Models are the Future of Agentic AI}} (2025)",
          "Karpathy, \\href{https://www.youtube.com/watch?v=7xTGNNLPyMI}{\\emph{Deep Dive into LLMs}} (video)"],
handson=["[[A:STAN25:Week 1]]", "[[A:UVA:Topic 1]]", "[[A:MANN:Exercise: LLM Intro]]"]),

dict(key="ARCH", num=2, title="The Agent Loop and Agent Architectures", tags=["ARCH"], mcp=None,
objectives=["Define an agent (model + loop + tools + environment + stopping rule) and distinguish workflows from agents.",
            "Implement a ReAct-style loop from scratch, without a framework.",
            "Judge when a graph framework (LangGraph) or an agent SDK earns its complexity."],
concepts=r"""Anthropic's \emph{Building Effective Agents}, assigned by Northeastern, Buffalo and UW, draws the key distinction. A \textbf{workflow} orchestrates LLM calls along predefined code paths (chaining, routing, parallelization, orchestrator--workers, evaluator--optimizer). An \textbf{agent} lets the model choose its own next action in a loop until a stopping condition holds.
\begin{itemize}
\item \textbf{The loop.} Build the prompt (system + history + tool specs), call the model, parse any tool calls, execute them in the environment, append the observations, and repeat until the model answers or a step or token budget runs out. That is a \emph{harness}. CMU A1, JHU A3 and the UW assignment all make you write one.
\item \textbf{State} is the message history plus anything external (files, a scratchpad, a database). Explicit state machines and graphs (Buffalo Lab~3, LangGraph in Northeastern, UVA and CMU) make control flow inspectable, resumable (checkpointing) and testable.
\item \textbf{Frameworks versus raw loops.} Write a loop by hand first. Frameworks such as LangGraph, the OpenAI Agents SDK, OpenHands and smolagents then become shortcuts you understand rather than magic. UW bans frameworks for its assignment for exactly this reason.
\item \textbf{Cognitive architectures} (CoALA) provide a vocabulary for memory, action space and decision procedure that the rest of this guide reuses.
\end{itemize}""",
sequence=[("[[CMU:1]]", "What an agent is, the agent loop and the course map (slides + video)."),
          ("[[STAN26:1]]", "Build a Claude-Code-style agent in about 200 lines, then read the completed code."),
          ("[[UW:2]]", "Instructor walkthrough with a demo notebook. Then do the UW assignment below."),
          ("[[NEU:4]] and [[NEU:6]]", "From a simple tools-and-memory agent to LangGraph state, nodes, edges and cycles."),
          ("[[UVA:3]]", "LangGraph lab: routing, parallel models, checkpointing and crash recovery."),
          ("[[CMU:14]] and [[CMU:15]]", "Two production frameworks compared: OpenHands and LangGraph."),
          ("Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}", "The same small agent as a hand-written loop and as a LangGraph graph, on a local 4B model.")],
readings=["Anthropic, \\href{https://www.anthropic.com/engineering/building-effective-agents}{\\emph{Building Effective Agents}}",
          "Yao et al., \\href{https://arxiv.org/abs/2210.03629}{\\emph{ReAct}} (2022)", "Sumers et al., \\href{https://arxiv.org/abs/2309.02427}{\\emph{CoALA: Cognitive Architectures for Language Agents}} (2023)",
          "Chip Huyen, \\href{https://huyenchip.com/2025/01/07/agents.html}{\\emph{Agents}} (2025)",
          "Wang et al., \\href{https://arxiv.org/abs/2308.11432}{\\emph{A Survey on LLM-based Autonomous Agents}} (2024)"],
handson=["[[A:UW:Build a Coding Agent]]", "[[A:CMU:A1]]", "[[A:UVA:Topic 2]]", "[[A:UB:Lab 3]]", "[[A:UB:Lab 1]]",
         "Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}. Run \\texttt{Local-Agent-Demo}, read \\texttt{agent.py}, then compare it with the LangGraph version."]),

dict(key="TOOL", num=3, title="Tool Use and Function Calling", tags=["TOOL"], mcp=False,
objectives=["Explain how tool calls are encoded in chat templates and parsed by the harness.",
            "Design agent-ergonomic tools (names, schemas, errors, granularity).",
            "Implement manual tool dispatch, then framework tool nodes, and measure tool-selection accuracy."],
concepts=r"""Tools are how an agent acts. Three layers matter:
\begin{itemize}
\item \textbf{Encoding.} The model emits a structured call (name + JSON arguments) inside its chat template, the harness executes it, and the result returns as a tool message. Constrained decoding (e.g.\ XGrammar) can guarantee well-formed calls. Benchmarks such as BFCL measure function-calling accuracy.
\item \textbf{Design.} Tools are an interface for a non-human user. Prefer a few high-level, composable tools with clear names, typed parameters and \emph{informative errors} that tell the model how to recover. ``Code as action'' (CodeAct) replaces many tools with one interpreter. Stanford's readings include Anthropic's \emph{Writing effective tools for agents} and ``APIs don't make good MCP tools''.
\item \textbf{Selection at scale.} With dozens of tools, retrieval over tool descriptions, or a small classifier as in TinyAgent, keeps prompts short and accurate. For hundreds of tools see the code-execution pattern in [[M:MCP]].
\end{itemize}
The research lineage runs from Toolformer (self-taught API calls) to Gorilla (API retrieval), PAL (program-aided reasoning), MRKL and ``What are tools anyway?''.""",
sequence=[("[[CMU:2]]", "Tool use end to end: APIs, chat templates, CodeAct, constrained decoding, BFCL (slides + video)."),
          ("[[UVA:5]]", "Lab: manual tool handling with a calculator, the OpenAI tool format, tool forcing."),
          ("[[UVA:7]]", "ToolNode versus \\texttt{create\\_react\\_agent}, parallel tool dispatch, a 2-hour mini project."),
          ("[[NEU:5]]", "ReAct support agent, tools-versus-model design rules, deploy to HF Spaces."),
          ("[[CU:11]] and [[CU:12]]", "Research reading: Reflexion/Toolformer, then Gorilla/PAL."),
          ("Supplement: \\hyperref[sup-tinyagent]{TinyAgent}", "Tool RAG and small-model function calling at the edge.")],
readings=["Schick et al., \\href{https://arxiv.org/abs/2302.04761}{\\emph{Toolformer}} (2023)", "Patil et al., \\href{https://arxiv.org/abs/2305.15334}{\\emph{Gorilla}} (2023)",
          "Wang et al., \\href{https://arxiv.org/abs/2402.01030}{\\emph{CodeAct: Executable Code Actions}} (2024)", "Gao et al., \\href{https://arxiv.org/abs/2211.10435}{\\emph{PAL}} (2022)",
          "\\href{https://arxiv.org/abs/2403.15452}{\\emph{What Are Tools Anyway?}} (2024)",
          "Anthropic, \\href{https://www.anthropic.com/engineering/writing-tools-for-agents}{\\emph{Writing effective tools for agents}}"],
handson=["[[A:UVA:Topic 3]]", "[[A:UB:Lab 1]]", "[[A:NEU:DADA1]]", "[[A:UVA:Topic 4]]"]),

dict(key="MCP", num=4, title="MCP and Agent Interoperability", tags=["TOOL"], mcp=True,
objectives=["Describe MCP hosts, clients and servers, its primitives and transports, and what changed in the 2026-07-28 revision.",
            "Build and test an MCP server with authentication.",
            "Know when to switch from direct tool calls to code execution against MCP, and what A2A adds."],
concepts=r"""The \textbf{Model Context Protocol} standardizes how tools and context reach an agent: write one server, use it in any host. Read the \hyperref[sup-mcp]{MCP supplement} first, because \textbf{the 2026-07-28 revision made the protocol stateless}, and lectures from before mid-2026 teach the older handshake.
\begin{itemize}
\item \textbf{Primitives:} tools, resources and prompts on the server side, and elicitation on the client side. Transports are stdio (local) and Streamable HTTP (remote, OAuth).
\item \textbf{Server craft:} typed, composable tools; dry-run modes for write tools; \texttt{readOnlyHint}; structured errors; rate-limit handling; protocol-level tests (Stanford '26 week~2).
\item \textbf{Security:} an MCP server is a trust boundary. Northeastern devotes two sessions to MCP security and enterprise auth. See also [[M:SAFE]].
\item \textbf{Scale:} with many servers, loading every tool schema is wasteful. Anthropic's \hyperref[sup-codeexec]{code-execution pattern} and CU Boulder's MCP design-choice paper argue for progressive discovery and code-based orchestration.
\item \textbf{Agent-to-agent:} A2A (agent cards, registries) connects whole agents rather than tools. UVA runs an A2A trivia tournament.
\end{itemize}""",
sequence=[("Supplement: \\hyperref[sup-mcp]{MCP docs}", "Architecture, primitives and the 2026-07-28 changes."),
          ("[[STAN26:4]]", "Full introduction to MCP and tool calling (theory, setup, advanced tool design)."),
          ("[[STAN25:4]]", "Building a custom MCP server (slides + completed exercise)."),
          ("[[JHU:8]] and [[JHU:9]]", "Two MCP lectures in a PL/synthesis context (slides)."),
          ("[[NEU:16]] and [[NEU:17]]", "MCP spec, the security landscape, remote MCP and agent auth."),
          ("[[UVA:12]]", "MCP clients for AI2 Asta tools, then A2A agents, a registry and ngrok."),
          ("Supplement: \\hyperref[sup-codeexec]{Code execution with MCP}", "Then [[CU:24]] for the empirical study."),
          ("Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}", "A 32-line stdio server on version~2 of the Python SDK, and the same question asked with and without it.")],
readings=["MCP specification and \\href{https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices}{security best practices}",
          "Anthropic, \\href{https://www.anthropic.com/engineering/code-execution-with-mcp}{\\emph{Code execution with MCP}} (2025)",
          "Felendler et al., \\href{https://arxiv.org/abs/2602.15945}{\\emph{From Tool Orchestration to Code Execution: MCP Design Choices}} (2026)",
          "\\href{https://arxiv.org/abs/2503.23278}{\\emph{MCP Landscape \\& Security}} (arXiv 2503.23278)"],
handson=["[[A:STAN26:Week 2]]", "[[A:STAN25:Week 3]]", "[[A:UVA:Topic 7]]", "[[A:MANN:Exercise: Agent Programming]]",
         "Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}. Start with \\texttt{EmeritusMCP}: add a second tool to the server and watch the agent discover it."]),

dict(key="MEM", num=5, title="Memory, Retrieval and Context Engineering", tags=["MEM"], mcp=None,
objectives=["Manage a finite context window: selection, compression/compaction, offloading and persistence.",
            "Build and evaluate a RAG pipeline (chunking, embeddings, top-K, reranking, unanswerable questions).",
            "Implement long-term memory and skills with progressive disclosure."],
concepts=r"""Apart from what the model learned in training, everything an agent can use at step $t$ is in its context: the information supplied for that inference. \textbf{Context engineering} decides what goes in.
\begin{itemize}
\item \textbf{Limits.} Models degrade on long inputs (``lost in the middle'', context rot), and every token costs money and latency. KV-cache reuse makes a stable prompt prefix cheap. CMU's long-context lecture uses real provider pricing and harness source code.
\item \textbf{Compaction.} Summarize or fold old turns (model-generated compaction in CMU A1; AgentFold and context-folding in UVA and UW), and offload large observations to files.
\item \textbf{Retrieval (RAG).} Chunk, embed, index, retrieve top-K, optionally rerank, then generate with citations. Treat chunk size, overlap, K, query rewriting and score thresholds as experimental variables (UVA Topic~5 runs 11 controlled experiments). Agentic RAG adds self-grading, correction and routing (Self-RAG, CRAG, Adaptive-RAG).
\item \textbf{Long-term memory and skills.} OS-style memory tiers (MemGPT), reflection-based memories (Generative Agents, Reflexion), workflow and skill induction (AWM, ASI). \emph{Skills} are SKILL.md bundles loaded on demand, the same progressive-disclosure idea Stanford '26 week~3 and CMU A1 teach.
\end{itemize}""",
sequence=[("[[CMU:3]]", "Context management for long-context agents: limits, compaction, KV-cache economics."),
          ("[[CMU:4]]", "Skills and memory: MemGPT, AWM, ASI, ReasoningBank, SkillsBench."),
          ("[[NEU:7]]--[[NEU:9|short]]", "Context engineering, then RAG from scratch to Pinecone, then a self-grading retrieval loop."),
          ("[[UVA:9]]", "The RAG experiment lab (chunking, top-K, unanswerable questions, small versus large model)."),
          ("[[MANN:6]]", "Context-engineering deck and the deep-agent exercise."),
          ("[[STAN26:5]]", "Agent skills, including web skills (then author one in the Week~3 assignment)."),
          ("[[UW:21]] and [[UW:22]]", "Research reading: MemGPT, CoALA, A-Mem, context folding."),
          ("Supplement: \\hyperref[sup-notion]{Notion Data Scout}", "Curated, owned context for a production data agent.")],
readings=["Lewis et al., \\href{https://arxiv.org/abs/2005.11401}{\\emph{Retrieval-Augmented Generation}} (2020)", "Liu et al., \\href{https://arxiv.org/abs/2307.03172}{\\emph{Lost in the Middle}} (2023)",
          "Packer et al., \\href{https://arxiv.org/abs/2310.08560}{\\emph{MemGPT}} (2023)", "Park et al., \\href{https://arxiv.org/abs/2304.03442}{\\emph{Generative Agents}} (2023)",
          "Anthropic, \\href{https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents}{\\emph{Effective context engineering for AI agents}}",
          "Asai et al., \\href{https://arxiv.org/abs/2310.11511}{\\emph{Self-RAG}} (2023); Yan et al., \\href{https://arxiv.org/abs/2401.15884}{\\emph{Corrective RAG}} (2024)"],
handson=["[[A:UVA:Topic 5]]", "[[A:UB:Lab 2]]", "[[A:STAN26:Week 3]]", "[[A:NEU:Husky]]", "[[A:MANN:Exercise: RAG]]",
         "Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}. In \\texttt{Local-Agent-Demo}, change the short-term window and the similarity threshold in \\texttt{config.py} and watch what the model is shown."]),

dict(key="RSN", num=6, title="Reasoning, Planning, Reflection and Search", tags=["RSN"], mcp=None,
objectives=["Choose between ReAct-style interleaving, plan-then-execute and decomposition strategies.",
            "Add reflection/self-critique loops and measure whether they help.",
            "Use search (best-of-N, critics/verifiers, tree search) to trade compute for reliability."],
concepts=r"""\begin{itemize}
\item \textbf{Thinking in tokens.} CoT and self-consistency let the model compute before answering. UVA's CoT lecture looks at why this works and at latent (hidden) reasoning.
\item \textbf{Planning.} Plan-and-execute, least-to-most and decomposed prompting split long tasks. Code-as-policies and DAG plans (LLMCompiler, used in TinyAgent) make plans executable and parallel. CMU's planning lecture asks \emph{when} to plan (``Thinking vs.\ Doing'', ``Calibrate-Then-Act'').
\item \textbf{Reflection.} Reflexion and Self-Refine critique and retry. Northeastern's self-grading RAG loop is a concrete build. Reflection only helps when the feedback signal carries real information (tests, tools, retrieval scores), so measure it.
\item \textbf{Search.} Sample many candidates, then pick with a verifier or critic (CMU Search~1), or explore a tree of states (ToT, LATS, CMU Search~2). AlphaCode, AlphaEvolve and ShinkaEvolve (UW) scale this to evolutionary program search. JHU starts from the classic version: enumerative program synthesis.
\end{itemize}""",
sequence=[("[[CMU:5]]", "Planning, task decomposition and multi-agent coordination (slides + video)."),
          ("[[UW:3]] and [[UW:4]]", "CoT/ReAct, then Toolformer/ToT, with supplementary papers."),
          ("[[NEU:9]] and [[NEU:10]]", "Reflection and self-critique, then planning with skill libraries (Voyager) and ToT."),
          ("[[UVA:16]]", "Understanding chain of thought, including latent CoT."),
          ("[[CMU:20]] and [[CMU:21]]", "Reranking and critic models, then tree search."),
          ("[[UW:17]] and [[UW:18]]", "Searching the solution space: AlphaCode, AlphaGeometry, evolutionary search."),
          ("[[JHU:2]]--[[JHU:4|short]]", "Program synthesis as search (the foundation for A1).")],
readings=["Wang et al., \\href{https://arxiv.org/abs/2203.11171}{\\emph{Self-Consistency}} (2022)", "Yao et al., \\href{https://arxiv.org/abs/2305.10601}{\\emph{Tree of Thoughts}} (2023)",
          "Shinn et al., \\href{https://arxiv.org/abs/2303.11366}{\\emph{Reflexion}} (2023); Madaan et al., \\href{https://arxiv.org/abs/2303.17651}{\\emph{Self-Refine}} (2023)",
          "Zhou et al., \\href{https://arxiv.org/abs/2205.10625}{\\emph{Least-to-Most Prompting}} (2022)", "Zhou et al., \\href{https://arxiv.org/abs/2310.04406}{\\emph{LATS}} (2023)",
          "Kim et al., \\href{https://arxiv.org/abs/2312.04511}{\\emph{LLMCompiler}} (2023)"],
handson=["[[A:JHU:A1]]", "[[A:STAN25:Week 1]]", "[[A:NEU:Husky]]",
         "Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}. Wire a model into \\texttt{tot\\_minimal.py}, then replace the model-scored evaluator with a code check and compare."]),

dict(key="MULTI", num=7, title="Multi-Agent Systems", tags=["MULTI"], mcp=None,
objectives=["Implement handoffs, routers, orchestrator--worker and debate patterns.",
            "Diagnose multi-agent failure modes and decide when one agent is enough."],
concepts=r"""Multiple agents can parallelize work, isolate context (sub-agents with fresh windows) and specialize roles. They also multiply cost and add new failure modes: role confusion, lost information at handoffs, and endless loops.
\begin{itemize}
\item \textbf{Patterns:} router/handoff, orchestrator--workers (Anthropic's multi-agent research system), role-based SOPs (MetaGPT, CAMEL), conversation frameworks (AutoGen), debate, and planner/implementer/reviewer sub-agents in coding tools (Stanford '26 week~4).
\item \textbf{Evidence:} \emph{Why do multi-agent LLM systems fail?} (Northeastern reads it twice) and \emph{Towards a Science of Scaling Agent Systems} (UW) set this against OpenHands' ``don't sleep on single-agent systems''. Start with one agent and add more only when a measurement says so.
\item \textbf{Simulation:} populations of agents as social-science instruments (Generative Agents, Concordia, UChicago week~3).
\end{itemize}""",
sequence=[("[[NEU:12]]--[[NEU:14|short]]", "Three sessions: failure modes and handoffs, role-based MAS, the LangGraph runtime."),
          ("[[CMU:18]]", "Multi-agent interaction (guest lecture)."),
          ("[[UW:19]] and [[UW:20]]", "Generative Agents/CAMEL, then AutoGen and the scaling science of agent systems."),
          ("[[CU:14]] and [[CU:15]]", "AutoGen/MetaGPT, then debate and Agentless."),
          ("[[UCHI:3]]", "Prompted multi-agent social simulation (notebook with AutoGen and Concordia)."),
          ("Supplements: \\hyperref[sup-barkley]{Barkley local agent demos}, \\hyperref[sup-cadsmith]{CADSmith}", "One subagent with its own context and a briefing; then a five-role pipeline checked by a geometry kernel.")],
readings=["Wu et al., \\href{https://arxiv.org/abs/2308.08155}{\\emph{AutoGen}} (2023)", "Hong et al., \\href{https://arxiv.org/abs/2308.00352}{\\emph{MetaGPT}} (2023)", "Li et al., \\href{https://arxiv.org/abs/2303.17760}{\\emph{CAMEL}} (2023)",
          "Du et al., \\href{https://arxiv.org/abs/2305.14325}{\\emph{Multiagent Debate}} (2023)", "Cemri et al., \\href{https://arxiv.org/abs/2503.13657}{\\emph{Why Do Multi-Agent LLM Systems Fail?}} (2025)",
          "Anthropic, \\href{https://www.anthropic.com/engineering/multi-agent-research-system}{\\emph{How we built our multi-agent research system}}"],
handson=["[[A:UVA:Topic 7]]", "[[A:UCHI:Week 3]]", "[[A:MANN:Project topic 1]]", "[[A:STAN25:Week 5]]",
         "Supplement: \\hyperref[sup-barkley]{Barkley local agent demos}. In \\texttt{Agent-with-Subagent}, untick delegation and compare the main agent's context with and without the subagent."]),

dict(key="CODE", num=8, title="Coding Agents", tags=["CODE"], mcp=None,
objectives=["Explain the architecture of production coding agents (system prompt, core tools, sandbox, context management, sub-agents).",
            "Build a coding agent and evaluate it on repository-level tasks.",
            "Make repositories and teams agent-ready (AGENTS.md/CLAUDE.md, hooks, tests, review)."],
concepts=r"""Coding is the domain where agents work best today, because the environment provides dense, verifiable feedback (compilers, tests, linters).
\begin{itemize}
\item \textbf{Anatomy.} A long system prompt, a small core toolset (read, write, edit, bash, search), a sandbox, compaction, TODO/plan tools, and optionally sub-agents. Stanford '26 dissects real system prompts and traces. JHU A3 makes you implement path-validated file tools and TODO tools.
\item \textbf{Interfaces matter.} SWE-agent showed that agent--computer interface design (viewer windows, linting edits) moves benchmark scores. Agentless showed that a fixed pipeline can be competitive, so keep a simple baseline.
\item \textbf{Benchmarks.} SWE-bench (and SWE-Gym, R2E-Gym for training), Terminal-Bench, BaxBench and RedCode (security). See [[M:EVAL]].
\item \textbf{Practice.} Spec-driven development, context files (AGENTS.md/CLAUDE.md), hooks as lint/test gates, agentic code review, background agents, and ``agent readiness'' of a codebase (Stanford '26 weeks~2--8).
\item \textbf{Research frontier.} Refactoring agents (CU Boulder), coding-agent configuration studies, and evolutionary coding agents (AlphaEvolve, Live-SWE-agent).
\end{itemize}""",
sequence=[("[[CMU:6]]", "Agents for coding and software development (slides + video)."),
          ("[[STAN26:1]] and [[STAN26:2]]", "Build a mini Claude Code, then a deep dive into production system prompts."),
          ("[[UW:5]] and [[UW:6]]", "SWE-bench, SWE-agent, OpenHands, BaxBench."),
          ("[[CU:13]]", "SWE-agent and AutoCodeRover (agent--computer interfaces, repository repair)."),
          ("[[JHU:7]] and [[JHU:10]]", "Iterative refinement and agentic frameworks for code (slides)."),
          ("[[HARV:2]] and [[HARV:4]]", "How Claude Code works, then the design space of search, edit and shell tools and of context management (slides)."),
          ("[[STAN26:7]], [[STAN26:9|short]], [[STAN26:11|short]], [[STAN26:15|short]]", "Customizing the agent, agent-ready repos, code review, background agents."),
          ("[[UVA:17]]", "History, Claude Code architecture, skills files and evolutionary programming.")],
readings=["Jimenez et al., \\href{https://arxiv.org/abs/2310.06770}{\\emph{SWE-bench}} (2023)", "Yang et al., \\href{https://arxiv.org/abs/2405.15793}{\\emph{SWE-agent}} (2024)",
          "Wang et al., \\href{https://arxiv.org/abs/2407.16741}{\\emph{OpenHands}} (2024)", "Xia et al., \\href{https://arxiv.org/abs/2407.01489}{\\emph{Agentless}} (2024)",
          "Zhang et al., \\href{https://arxiv.org/abs/2404.05427}{\\emph{AutoCodeRover}} (2024)", "Hassan et al., \\href{https://arxiv.org/abs/2509.06216}{\\emph{Agentic Software Engineering}} roadmap (2025)",
          "Anthropic, \\href{https://www.anthropic.com/engineering/claude-code-best-practices}{\\emph{Claude Code best practices}}"],
handson=["[[A:UW:Build a Coding Agent]]", "[[A:JHU:A3]]", "[[A:CMU:A1]]", "[[A:HARV:A2]]", "[[A:STAN26:Week 1]]",
         "[[A:STAN25:Week 4]]", "[[A:STAN25:Week 7]]"]),

dict(key="WEB", num=9, title="Web, GUI, Computer-Use and Multimodal Agents", tags=["WEB"], mcp=None,
objectives=["Explain observation and action spaces for browser/GUI agents (DOM, accessibility tree, screenshots, coordinates).",
            "Build a vision-language agent and know the main web/OS benchmarks."],
concepts=r"""When there is no API, the agent operates the interface a human would. Observations are HTML/DOM, accessibility trees or screenshots (set-of-marks). Actions are clicks, typing and navigation, or full OS control. These tasks have long horizons, partial observability and irreversible actions, which makes them hard and makes safety and human confirmation central.
Benchmarks progress from MiniWoB and WebShop through Mind2Web and WebArena/VisualWebArena to OSWorld. Training environments include CUA-Gym and OpenCUA. Mobile agents (AppAgent) and embodied agents (SayCan, Voyager) extend the same loop. Personal agents such as the OpenClaw family control real accounts, so read UVA's risk discussion together with [[M:SAFE]].""",
sequence=[("[[CMU:7]]", "Computer-use agents: WebArena, VisualWebArena, OSWorld, OpenCUA (slides + video)."),
          ("[[UVA:10]]", "Vision-language models and a VLM chat agent and video-surveillance agent lab."),
          ("[[CU:19]]", "AppAgent (smartphone GUI) and coding-agent configuration."),
          ("[[UVA:18]]", "Personal agents (OpenClaw family, Claude Cowork) and their risks; distillation."),
          ("[[UCHI:8]]", "Multimodal and embodied agents (notebook).")],
readings=["Zhou et al., \\href{https://arxiv.org/abs/2307.13854}{\\emph{WebArena}} (2023); Koh et al., \\href{https://arxiv.org/abs/2401.13649}{\\emph{VisualWebArena}} (2024)",
          "Xie et al., \\href{https://arxiv.org/abs/2404.07972}{\\emph{OSWorld}} (2024)", "Deng et al., \\href{https://arxiv.org/abs/2306.06070}{\\emph{Mind2Web}} (2023)", "Yao et al., \\href{https://arxiv.org/abs/2207.01206}{\\emph{WebShop}} (2022)",
          "Zhang et al., \\href{https://arxiv.org/abs/2312.13771}{\\emph{AppAgent}} (2023)", "Wang et al., \\href{https://arxiv.org/abs/2305.16291}{\\emph{Voyager}} (2023)"],
handson=["[[A:UVA:Topic 6]]", "[[A:MANN:Project topic 4]]", "[[A:MANN:Project topic 2]]"]),

dict(key="EVAL", num=10, title="Evaluating Agents", tags=["EVAL"], mcp=None,
objectives=["Design task-level evals with success criteria, failure taxonomies and reproducible scripts.",
            "Build and validate an LLM-as-judge against human labels.",
            "Report results honestly (pass@k, variance, cost) and avoid benchmark pitfalls."],
concepts=r"""Evaluation separates agent engineering from demo-building, and every serious course in this collection weights it heavily.
\begin{itemize}
\item \textbf{Levels.} Unit tests for tools, trajectory and intermediate-step checks, end-to-end task success, and human judgments of usefulness.
\item \textbf{Verifiers.} Deterministic tests where possible (SWE-bench, Harbor tasks with reference solutions and \emph{mutants} in CMU A2). LLM-as-judge where not, \emph{validated against human labels} (CMU A2 scores judges by MCC).
\item \textbf{Statistics and cost.} Agents are stochastic: report pass@k over repeated runs (JHU A2), confidence intervals and dollars per task. \emph{AI Agents That Matter} criticizes leaderboards that ignore cost and overfitting.
\item \textbf{Error analysis.} A failure taxonomy (Buffalo Lab~4; CMU A2's four error families) turns logs into engineering decisions.
\item \textbf{Benchmarks:} SWE-bench, $\tau$-bench, AgentBench, WebArena, AgentDojo (security), BrowseComp and DeepResearch Bench (research agents), and METR's time-horizon measurements.
\end{itemize}""",
sequence=[("[[A:CMU:A2]]", "The single best exercise here: author tasks, label runs, build and score a judge."),
          ("[[NEU:18]]", "SWE-bench, $\\tau$-bench, LLM-as-a-judge, LangSmith evaluation."),
          ("[[UB:9]]", "From single-prompt to task-level evals (then Lab~4)."),
          ("[[HARV:8]]", "Benchmark by benchmark: what each one tests and what its grader inspects, plus leakage and saturation (slides and a reference note)."),
          ("[[A:JHU:A2]]", "A rigorous pass@k study across languages, models and prompting strategies."),
          ("[[CMU:20]]", "Critic models: evaluation used at inference time."),
          ("[[UW:22]]", "Includes METR's \\emph{Measuring AI Ability to Complete Long Tasks}.")],
readings=["Zheng et al., \\href{https://arxiv.org/abs/2306.05685}{\\emph{Judging LLM-as-a-Judge}} (2023)", "Yao et al., \\href{https://arxiv.org/abs/2406.12045}{\\emph{$\\tau$-bench}} (2024)",
          "Liu et al., \\href{https://arxiv.org/abs/2308.03688}{\\emph{AgentBench}} (2023)", "Kapoor et al., \\href{https://arxiv.org/abs/2407.01502}{\\emph{AI Agents That Matter}} (2024)",
          "Mohammadi et al., \\href{https://arxiv.org/abs/2507.21504}{\\emph{Evaluation and Benchmarking of LLM Agents}} (KDD 2025)",
          "METR, \\href{https://arxiv.org/abs/2503.14499}{\\emph{Measuring AI Ability to Complete Long Tasks}} (2025)"],
handson=["[[A:CMU:A2]]", "[[A:JHU:A2]]", "[[A:UB:Lab 4]]", "[[A:UVA:Topic 5]]", "[[A:HARV:A2]]"]),

dict(key="TRAIN", num=11, title="Training and Optimizing Agents", tags=["TRAIN"], mcp=None,
objectives=["Fine-tune a model on agent trajectories (SFT, LoRA/QLoRA) and know when fine-tuning beats prompting or RAG.",
            "Implement policy-gradient RL (REINFORCE, GRPO) for multi-turn agents, including async rollouts.",
            "Optimize prompts and programs automatically (DSPy, TextGrad, GEPA)."],
concepts=r"""\begin{itemize}
\item \textbf{SFT and distillation.} Collect or synthesize high-quality trajectories from a strong model, filter them with verifiers, and fine-tune a smaller model (TinyAgent, CMU Training~1, UVA's Tinker text-to-SQL lab). LoRA and QLoRA make this cheap.
\item \textbf{RL from verifiable rewards.} The policy generates trajectories in an environment and receives a reward (tests passed, task solved). Advantages are computed by REINFORCE baselines, PPO with GAE, or GRPO's group-relative normalization (DeepSeekMath, DeepSeek-R1, Dr.~GRPO). Multi-turn agent RL adds credit assignment across tool calls and requires masking tool-output tokens.
\item \textbf{RL systems.} Rollouts dominate cost, so asynchronous producer--consumer training with off-policy corrections (importance weighting) is standard. CMU A3 makes you build both sync and async GRPO on Tinker with a SkyRL server.
\item \textbf{Optimizing without gradients.} DSPy compiles LM programs. TextGrad, GEPA, ADAS and Promptbreeder evolve prompts or whole agent designs (UW weeks on optimizing and self-improving agents).
\end{itemize}""",
sequence=[("[[CMU:8]]", "Supervised fine-tuning for agents (slides + video)."),
          ("[[CMU:9]]", "RL basics: ReST, ReST-EM, DeepSeekMath/GRPO, Dr.~GRPO (slides + video)."),
          ("[[CMU:11]] and [[CMU:12]]", "Advanced RL algorithms, then RL systems (slides)."),
          ("[[UVA:13]]", "Fine-tuning versus RAG, QLoRA, the Tinker pipeline, text-to-SQL."),
          ("[[JHU:11]]--[[JHU:13|short]]", "Pre- and post-training of code LLMs."),
          ("[[UW:13]] and [[UW:14]]", "DSPy/TextGrad, then ADAS/GEPA."),
          ("Supplement: \\hyperref[sup-tinyagent]{TinyAgent}", "An end-to-end distillation case study.")],
readings=["Ouyang et al., \\href{https://arxiv.org/abs/2203.02155}{\\emph{InstructGPT}} (2022)", "Shao et al., \\href{https://arxiv.org/abs/2402.03300}{\\emph{DeepSeekMath (GRPO)}} (2024)",
          "DeepSeek-AI, \\href{https://arxiv.org/abs/2501.12948}{\\emph{DeepSeek-R1}} (2025)", "Singh et al., \\href{https://arxiv.org/abs/2312.06585}{\\emph{ReST-EM}} (2023)",
          "Hu et al., \\href{https://arxiv.org/abs/2106.09685}{\\emph{LoRA}} (2021); Dettmers et al., \\href{https://arxiv.org/abs/2305.14314}{\\emph{QLoRA}} (2023)",
          "Khattab et al., \\href{https://arxiv.org/abs/2310.03714}{\\emph{DSPy}} (2023); Agrawal et al., \\href{https://arxiv.org/abs/2507.19457}{\\emph{GEPA}} (2025)"],
handson=["[[A:CMU:A3]]", "[[A:UVA:Topic 8]]", "[[A:UCHI:Week 5]]", "[[A:UCHI:Week 7]]"]),

dict(key="SAFE", num=12, title="Safety, Security and Oversight", tags=["SAFE"], mcp=None,
objectives=["Threat-model an agent: prompt injection, tool misuse, data exfiltration, supply chain.",
            "Apply defenses: sandboxing, least privilege, capability separation, human approval, monitoring.",
            "Evaluate security with benchmarks such as AgentDojo."],
concepts=r"""An agent with tools is a confused-deputy risk. Simon Willison's \textbf{lethal trifecta} (UW reading) names the dangerous combination: access to private data, exposure to untrusted content, and an exfiltration channel.
\begin{itemize}
\item \textbf{Attacks.} Indirect prompt injection through web pages, documents, tool outputs or MCP servers. Jailbreaks. Malicious or compromised tools and packages. CMU's safety lecture works through real incidents: the OpenClaw incident report, a database-deletion incident, CVE-2025-32711, and the Cline supply-chain compromise.
\item \textbf{Defenses.} Sandboxed execution and credential isolation; least-privilege tools and permission modes; human-in-the-loop approval for irreversible actions (Buffalo Lab~5); capability-based designs that separate control flow from untrusted data (CaMeL); guardrails; layered ``Swiss cheese'' safety.
\item \textbf{Oversight.} Tracing, monitoring and anomaly detection (CMU Safety~2). Static analysis of agent-written code (Semgrep, Stanford weeks on security).
\item \textbf{Alignment.} Sleeper agents, misalignment after narrow fine-tuning, representation engineering (UChicago week~9, UVA project ideas).
\end{itemize}""",
sequence=[("[[CMU:13]]", "Agent safety through real incidents (slides)."),
          ("[[UW:11]] and [[UW:12]]", "Indirect prompt injection and AgentDojo, then CaMeL and browser-agent security."),
          ("[[UB:10]]", "Prompt injection, tool misuse, sandboxing, privacy (then Lab~5)."),
          ("[[STAN25:11]]", "AI QA, SAST/DAST and prompt-injection RCE case studies (slides)."),
          ("[[CMU:16]]", "Observability and monitoring."),
          ("[[NEU:16]] and [[NEU:17]]", "MCP security and enterprise auth."),
          ("[[MANN:9]]", "LLM security and safety (full-stack safety survey).")],
readings=["Greshake et al., \\href{https://arxiv.org/abs/2302.12173}{\\emph{Indirect Prompt Injection}} (2023)", "Debenedetti et al., \\href{https://arxiv.org/abs/2406.13352}{\\emph{AgentDojo}} (2024)",
          "Debenedetti et al., \\href{https://arxiv.org/abs/2503.18813}{\\emph{CaMeL: Defeating Prompt Injections by Design}} (2025)",
          "Willison, \\href{https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/}{\\emph{The lethal trifecta}}",
          "Wang et al., \\href{https://arxiv.org/abs/2504.15585}{\\emph{Full Stack Safety survey}} (2025)", "Hubinger et al., \\href{https://arxiv.org/abs/2401.05566}{\\emph{Sleeper Agents}} (2024)"],
handson=["[[A:UB:Lab 5]]", "[[A:STAN25:Week 6]]", "[[A:UCHI:Week 9]]", "[[A:STAN26:Week 2]]"]),

dict(key="DEPLOY", num=13, title="Deployment, Efficiency and Operations", tags=["DEPLOY"], mcp=None,
objectives=["Deploy an agent as a service and operate it (logging, tracing, cost tracking, fallbacks).",
            "Reduce cost and latency: caching, model routing, small or quantized models, code execution.",
            "Understand long-running and background agent architectures."],
concepts=r"""\begin{itemize}
\item \textbf{Shipping.} Northeastern deploys agents to Hugging Face Spaces and Render. Buffalo adds CI and observability. Stanford '25 covers SRE and incident response with agents.
\item \textbf{Cost and latency.} Prompt and KV caching (keep a stable prefix), model routing and gateways (Stanford '26 week~10), fallbacks and spend policies (Northeastern's optimization session), shorter contexts through tool retrieval or code execution, and small or quantized models on device (TinyAgent, UVA Topic~1). Harvard CS~2680 breaks an agent's cost into turns per task, steps per turn, tokens per step and price per token, and treats completion time as a critical path ([[HARV:10|short]]); its second half goes down into the serving stack (batching, scheduling, speculative decoding, prefix caching, quantization, routing).
\item \textbf{Long-running agents.} Background and asynchronous agents (Stanford '26 week~8) and always-on gateways with channels, cron jobs and hooks (OpenClaw) need durable state, idempotent tools and resumability (checkpointing in [[M:ARCH]]).
\item \textbf{Observability.} Traces of every step are the raw material for evaluation ([[M:EVAL]]), debugging and safety monitoring ([[M:SAFE]]).
\end{itemize}""",
sequence=[("[[NEU:5]] and [[NEU:6]]", "Deploy to Hugging Face Spaces, then Render."),
          ("[[NEU:19]]", "DSPy plus cost tracking, caching, fallbacks and spend policies."),
          ("[[HARV:10]]", "Where an agent's cost and latency come from and how to cut each part (slides and the cost-effective agents note)."),
          ("[[HARV:12|short]]--[[HARV:23|short]]", "LLM serving, from basics to routing and load balancing. Scheduled from October~19, 2026; no materials were posted at the last update."),
          ("[[STAN26:15]] and [[STAN26:19]]", "Background agents, then coding agents in big teams (gateways, routing, cost)."),
          ("[[STAN25:17]]", "Incident response and DevOps with agents (slides)."),
          ("[[CMU:12]]", "RL systems: the systems side of agent training."),
          ("Supplements: \\hyperref[sup-openclaw]{OpenClaw}, \\hyperref[sup-tinyagent]{TinyAgent}", "Always-on gateway architecture; edge deployment."),
          ("Supplements: \\hyperref[sup-anthauto]{Anthropic agent automations}, \\hyperref[sup-notion]{Notion Data Scout}", "Durable state and guardrails for a scheduled agent; operating a production data agent.")],
readings=["Google, \\href{https://sre.google/sre-book/introduction/}{\\emph{SRE book, introduction}}",
          "Anthropic, \\href{https://www.anthropic.com/engineering/code-execution-with-mcp}{\\emph{Code execution with MCP}} (2025)", "Erdogan et al., \\href{https://arxiv.org/abs/2409.00608}{\\emph{TinyAgent}} (2024)",
          "Gao \\& Peng, \\href{https://arxiv.org/abs/2510.16786}{\\emph{More with Less}} (2025)",
          "Anthropic, \\href{https://claude.dev/blog/building-effective-agent-automations/}{\\emph{Building effective agent automations}} (2026)",
          "Notion, \\href{https://www.notion.com/blog/how-we-built-a-personal-data-scientist-for-every-notion-employee}{\\emph{How we built a personal data scientist for every Notion employee}} (2026)"],
handson=["[[A:NEU:DADA1]]", "[[A:UVA:Topic 1]]", "[[A:HARV:A3]]"]),

dict(key="APP", num=14, title="Applications: Deep Research, Science and Society", tags=["APP"], mcp=None,
objectives=["Understand how deep-research and scientific-discovery agents are built and evaluated.",
            "Scope an application agent for a bounded domain with a measurable outcome."],
concepts=r"""\begin{itemize}
\item \textbf{Deep research agents} combine search, browsing, reading and synthesis over many steps (STORM, PaperQA, OpenScholar, Tongyi DeepResearch, DR Tulu). They are evaluated on BrowseComp, DeepResearch Bench and LiveResearchBench.
\item \textbf{Agents for science} range from AI Scientist and autonomous chemistry to the AI co-scientist, sequential falsification, HEPTAPOD for particle physics, and Lean-based mathematics (UVA's guest lecture).
\item \textbf{Society.} Simulated subjects and digital doubles, mixed human--AI experiments, persuasion, the future of work (CMU), and human--agent interaction design (CMU Interaction~2).
\item \textbf{Scoping your own.} Mannheim's nine project briefs and Buffalo's ``useful bounded agent'' spec are good templates: a narrow domain, explicit tools, a benchmark and a risk assessment.
\end{itemize}""",
sequence=[("[[CMU:10]]", "Deep research agents (slides)."),
          ("[[UW:7]]--[[UW:10|short]]", "Deep research, then agents for science (four sessions)."),
          ("[[UVA:19]] and [[UVA:20]]", "Agentic AI for science, then mathematics and verification (Lean)."),
          ("[[CMU:17]] and [[CMU:19]]", "The future of work; human--agent interaction."),
          ("[[C:UCHI]]", "The whole course, for agents as research instruments.")],
readings=["Shao et al., \\href{https://arxiv.org/abs/2402.14207}{\\emph{STORM}} (2024)", "L\\'ala et al., \\href{https://arxiv.org/abs/2312.07559}{\\emph{PaperQA}} (2023)", "Asai et al., \\href{https://arxiv.org/abs/2411.14199}{\\emph{OpenScholar}} (2024)",
          "Lu et al., \\href{https://arxiv.org/abs/2408.06292}{\\emph{The AI Scientist}} (2024)", "Gottweis et al., \\href{https://arxiv.org/abs/2502.18864}{\\emph{Towards an AI Co-Scientist}} (2025)",
          "Park et al., \\href{https://arxiv.org/abs/2304.03442}{\\emph{Generative Agents}} (2023)"],
handson=["[[A:MANN:Project topic 2]]", "[[A:MANN:Project topic 8]]", "[[A:UB:Final Team Project]]", "[[A:UCHI:Final project]]"]),
]

# ---------------------------------------------------------------------------
# Learning tracks and the 16-week plan
# ---------------------------------------------------------------------------
TRACKS = [
 dict(name="Track A: Agent Builder (practitioner)",
      who="You want to ship reliable tool-using agents and RAG systems.",
      path=["SETUP", "FND", "ARCH", "TOOL", "MCP", "MEM", "RSN", "EVAL", "SAFE", "DEPLOY"],
      spine=r"Northeastern notebooks for guided builds, UVA labs for experiments, Buffalo lab specs as checkpoints.",
      capstone=r"Buffalo's \emph{useful bounded agent} ([[A:UB:Final Team Project]]), deployed like Northeastern's [[A:NEU:DADA1]]."),
 dict(name="Track B: Coding-Agent Engineer",
      who="You want to build or deeply customize coding agents and agent-ready workflows.",
      path=["SETUP", "ARCH", "TOOL", "MCP", "MEM", "CODE", "EVAL", "SAFE"],
      spine=r"Stanford '26 for practice, CMU for harness internals, UW and CU Boulder for the research context.",
      capstone=r"[[A:UW:Build a Coding Agent]] without frameworks, then extend it to pass the [[A:JHU:A3]] tasks and evaluate it like [[A:JHU:A2]]. An adapted alternative: [[A:HARV:A2]], a harness scored on SWE-bench Pro tasks plus four tasks you write yourself, run against your own model endpoint because the course API is closed to outsiders."),
 dict(name="Track C: Agent Researcher / Trainer",
      who="You want to train agentic models and do research-grade evaluation.",
      path=["FND", "ARCH", "TOOL", "MEM", "RSN", "EVAL", "TRAIN", "MULTI", "SAFE", "APP"],
      spine=r"CMU 11-768 end to end (all three assignments), with UW CS 839 and CU Boulder reading lists; Stanford CS329A for test-time compute and self-improvement, and the two Berkeley series for current research talks.",
      capstone=r"The CMU pipeline: [[A:CMU:A1]] $\rightarrow$ [[A:CMU:A2]] $\rightarrow$ [[A:CMU:A3]], then a research question framed as Northeastern requires (mechanism $\rightarrow$ manipulation $\rightarrow$ measured behavior)."),
]

PLAN = [  # week, modules, watch/read, build
 ("1", "SETUP, FND", "[[NEU:2|short]], [[NEU:3|short]], [[STAN25:2|short]]", "[[A:UVA:Topic 1]]; [[A:STAN25:Week 1]]"),
 ("2", "ARCH", "[[CMU:1|short]], [[STAN26:1|short]], [[UW:2|short]]", "Raw ReAct loop from scratch (start [[A:UW:Build a Coding Agent]])"),
 ("3", "TOOL", "[[CMU:2|short]], [[UVA:5|short]], [[UVA:7|short]]", "[[A:UVA:Topic 3]]; [[A:UB:Lab 1]]"),
 ("4", "MCP", "MCP docs, [[STAN26:4|short]], [[JHU:8|short]]--[[JHU:9|short]]", "[[A:STAN26:Week 2]]"),
 ("5", "MEM (context)", "[[CMU:3|short]], [[CMU:4|short]], [[NEU:7|short]]", "Add compaction and skills to your agent ([[A:STAN26:Week 3]])"),
 ("6", "MEM (RAG)", "[[NEU:8|short]], [[NEU:9|short]], [[UVA:9|short]]", "[[A:UVA:Topic 5]]; [[A:UB:Lab 2]]"),
 ("7", "ARCH (graphs)", "[[NEU:6|short]], [[UVA:3|short]], [[CMU:15|short]]", "[[A:UB:Lab 3]]; [[A:NEU:DADA1]]"),
 ("8", "RSN", "[[CMU:5|short]], [[NEU:10|short]], [[S329A:2|short]]; before A1: [[JHU:2|short]]--[[JHU:4|short]]", "[[A:JHU:A1]]"),
 ("9", "CODE", "[[CMU:6|short]], [[STAN26:2|short]], [[UW:5|short]]--[[UW:6|short]]", "[[A:CMU:A1]] or [[A:JHU:A3]]"),
 ("10", "EVAL", "[[NEU:18|short]], [[UB:9|short]], [[S329T:7|short]], [[BRKAG:5|short]]", "[[A:CMU:A2]] or [[A:JHU:A2]] (pick one; each fills the week. Do the other later as a multi-week project)"),
 ("11", "MULTI", "[[NEU:12|short]]--[[NEU:14|short]], [[UW:20|short]]", "[[A:UVA:Topic 7]] (A2A)"),
 ("12", "WEB", "[[CMU:7|short]], [[UVA:10|short]]", "[[A:UVA:Topic 6]]"),
 ("13", "TRAIN (SFT)", "[[CMU:8|short]], [[UVA:13|short]], TinyAgent", "[[A:UVA:Topic 8]]"),
 ("14", "TRAIN (RL)", "[[CMU:9|short]], [[CMU:11|short]], [[CMU:12|short]], [[S329A:6|short]]", "[[A:CMU:A3]]"),
 ("15", "SAFE", "[[CMU:13|short]], [[UW:11|short]]--[[UW:12|short]], [[UB:10|short]], [[BRKAG:13|short]]", "[[A:UB:Lab 5]]"),
 ("16", "DEPLOY, APP", "[[NEU:19|short]], [[STAN26:15|short]], [[CMU:10|short]]", "Capstone ([[A:UB:Final Team Project]])"),
]
