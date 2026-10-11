# Agentic AI (Northeastern University, Khoury College of Computer Sciences, Fall 2026)

- **URLs:** course site https://agenticllms.github.io/ ; code repo https://github.com/agenticllms/lecture-files ; final-project resources https://agenticllms.github.io/research.html
- **Instructor:** Caglar Yildirim, PhD (Khoury College of Computer Sciences)
- **Level/prereqs:** Not stated. The Week 1 page offers a Python primer for students whose Python is "rusty or new", so it does not assume much programming background. The final project is framed as research.
- **Format:** Two sessions a week (Tuesday/Friday), starting F 9/11. Each session has core and optional papers plus LangChain/LangGraph/LangSmith docs. Hands-on work runs in Jupyter notebooks copied from the lecture-files repo each class day. There is a midterm exam (F 10/30) and a research final project.
- **Public materials:** Per-session reading lists (papers and docs); session pages for Weeks 1-5 (setup steps and notebooks); two HTML slide pages (week3b-slides, week4a-slides); a public code repo of notebooks and project skeletons. No lecture videos (the only videos are external recommended ones, e.g. 3Blue1Brown and Karpathy).
- **License:** Not stated on the site or in the repo README.

**Overview.** The course teaches agent building through the LangChain v1 / LangGraph stack. It moves from LLM foundations to tool calling, memory, context engineering, RAG, reflection, planning, multi-agent orchestration, MCP, evaluation and optimization. Each concept is paired with a seminal paper (ReAct, Toolformer, MemGPT, Reflexion, Voyager, MetaGPT, SWE-bench, DSPy) and the matching framework docs. One running example, the "Husky Tech" customer support agent, is extended week by week: a notebook prototype, then a project skeleton, then a LangGraph rewrite, then RAG, then a self-grading retrieval loop. Students also deploy their agents publicly (Hugging Face Spaces, Render). The final project must be a research contribution, framed as "agentic mechanism -> experimental manipulation -> measured agent behavior". An application alone does not count.

## Lectures

Repo base: https://github.com/agenticllms/lecture-files/tree/main/ . The site numbers session pages "Week Na/Nb" (a = Tuesday, b = Friday). I mapped them to the schedule on that basis (see Notes).

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | F 9/11 | Introduction to Agentic AI | Workflows vs agents; course setup (VS Code, Python primer) | Building Effective Agents (Anthropic) [core]; Rise and Potential of LLM Agents (arXiv 2309.07864); LangGraph "Workflows and agents"; LangChain "Philosophy" | https://agenticllms.github.io/week1.html ; Python primer https://colab.research.google.com/drive/1s60I7NQiTpOWg2tK-KmFyiC8ZAY24lo7?usp=sharing | ORG, ARCH |
| 2 | T 9/15 | LLM Foundations (I) | Transformers, autoregressive generation; run a local open-weight model (Ollama, Qwen 3.5); base vs instruction-tuned comparison | Attention Is All You Need [core]; GPT-1 "Improving Language Understanding"; videos: 3Blue1Brown LLMs visualized, Karpathy "Let's build GPT" | https://agenticllms.github.io/week2a.html ; https://www.youtube.com/watch?v=wjZofJX0v4M ; https://www.youtube.com/watch?v=kCc8FmEb1nY | FND, DEPLOY |
| 3 | F 9/18 | LLM Foundations (II) | Instruction tuning/RLHF, CoT; LLM API basics; environment setup (uv, .env keys) | InstructGPT [core]; Chain-of-Thought (2201.11903); LangChain Models, Messages docs | https://agenticllms.github.io/week2b-setup.html ; code W02b (W02b.1_LLM_API_Basics.ipynb, W02b.2_AgentBasics.ipynb) https://github.com/agenticllms/lecture-files/tree/main/W02b | FND, TRAIN |
| 4 | T 9/22 | Simple Agent Architecture | Tools and agent loop; short-term memory, structured output; agentui.py chat UI | Toolformer [core]; MRKL (2205.00445); LangChain Tools, Agents docs | https://agenticllms.github.io/week3a.html ; code W03a (W03a.1_ShortTerm_Memory.ipynb, W03a.2_Structured_Output.ipynb, agentui.py) https://github.com/agenticllms/lecture-files/tree/main/W03a | ARCH, TOOL, MEM |
| 5 | F 9/25 | Tool-Calling | ReAct; Husky Tech customer support agent; notebook to project skeleton; deploy to HF Spaces (Gradio); tools-vs-model design rules | ReAct [core]; What Are Tools Anyway? (2403.15452); LangChain short-term memory, structured output docs | https://agenticllms.github.io/week3b.html ; slides https://agenticllms.github.io/week3b-slides.html ; code W03b https://github.com/agenticllms/lecture-files/tree/main/W03b | TOOL, RSN, DEPLOY |
| 6 | T 9/29 | Short-term & Long-term Memory | Memory in agents; LangGraph basics (state, nodes, edges, reducers, cycles); deploy to Render | Generative Agents [core]; MemGPT (2310.08560); Thinking in LangGraph, Graph API, Persistence docs | https://agenticllms.github.io/week4a.html ; slides "Why LangGraph?" https://agenticllms.github.io/week4a-slides.html ; code W04a https://github.com/agenticllms/lecture-files/tree/main/W04a | MEM, ARCH, DEPLOY |
| 7 | F 10/2 | Context Management | Lost-in-the-middle, context engineering, middleware; LangGraph messages/tools/state; support agent in LangGraph | Lost in the Middle [core]; Effective Context Engineering (Anthropic); LangChain context engineering, middleware docs | https://agenticllms.github.io/week4b.html ; code W04b https://github.com/agenticllms/lecture-files/tree/main/W04b | MEM, ARCH |
| 8 | T 10/6 | Retrieval-Augmented Generation | Chunking, embeddings, cosine similarity, vector store (dict, then Pinecone) | RAG (2005.11401) [core]; RAG Survey sec. 2-3 (2312.10997); LangChain Retrieval, Semantic search docs | https://agenticllms.github.io/week5a.html ; code W05a https://github.com/agenticllms/lecture-files/tree/main/W05a | MEM |
| 9 | F 10/9 | Reflection & Self-critique | Self-grading retrieval loop, query rewriting; RAG inside the support agent; rate limits/cost | Reflexion [core]; Self-RAG; Self-Refine; LangGraph Graph API loops, unit testing docs | https://agenticllms.github.io/week5b.html ; code W05b https://github.com/agenticllms/lecture-files/tree/main/W05b | RSN, MEM |
| 10 | T 10/13 | Planning & Task Decomposition | Skill libraries, ToT, task decomposition; subgraphs, skills | Voyager [core]; Tree of Thoughts; HuggingGPT (skim); LangGraph Subgraphs, Skills docs | n/a | RSN, ARCH |
| 11 | F 10/16 | Agentic RAG | Corrective/adaptive RAG, multi-source routing | Corrective RAG (2401.15884) [core]; Adaptive-RAG (2403.14403); Custom RAG agent, router knowledge base docs | n/a | MEM, RSN |
| 12 | T 10/20 | Multi-Agent Orchestration I | MAS failure modes; handoffs, routers | Why Do Multi-Agent LLM Systems Fail? (2503.13657) [core]; AutoGen; Anthropic multi-agent research system; handoffs/router docs | n/a | MULTI |
| 13 | F 10/23 | Multi-Agent Orchestration II | Role-based MAS; subagents, custom workflows | MetaGPT [core]; CAMEL (skim); Subagents, Custom workflow docs | n/a | MULTI |
| 14 | T 10/27 | Multi-Agent Orchestration III | MAS failures revisited; LangGraph runtime (Pregel), Studio | Why MAS Fail sec. 4-5 (re-read) [core]; Agents Are Not Enough (2412.16241, optional); LangGraph runtime, Studio docs | n/a | MULTI, ARCH |
| 15 | F 10/30 | Midterm Exam | Exam | n/a | n/a | ORG |
| 16 | T 11/3 | Model Context Protocol | MCP spec, MCP security landscape | MCP intro/spec [core]; MCP Landscape & Security (2503.23278); LangChain MCP, Agent Server MCP docs | n/a | TOOL, SAFE |
| 17 | F 11/6 | MCP in Agentic Systems | Remote MCP, agent auth, enterprise MCP security | Enterprise MCP Security (2504.08623, skim) [core]; LangSmith Remote MCP, Agent Auth docs | n/a | TOOL, SAFE, DEPLOY |
| 18 | T 11/10 | Agentic AI Evaluation | Benchmarks, trajectory/intermediate-step eval, LLM-as-judge | SWE-bench [core]; tau-bench (2406.12045); LLM-as-a-Judge (2306.05685); AgentBench (skim); LangSmith evaluation docs | n/a | EVAL |
| 19 | F 11/13 | Agentic AI Optimization | Prompt/program optimization (DSPy); cost tracking, caching, fallbacks, spend policies | DSPy (2310.03714) [core]; LangSmith cost tracking, caching, fallbacks, spend policies, insights docs | n/a | DEPLOY, FND |

The schedule on the site ended at F 11/13 when fetched (2026-10-09). Later sessions are probably not posted yet.

## Assignments / Projects

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| DADA1: The Trip Planner Agent | A conversational day-trip planner with tools: get_weather (Open-Meteo), find_attractions/restaurants/transit (Tavily), find_events (Ticketmaster). It has memory-based plan revision, a structured Itinerary/DayPlan output, 8 test prompts, and a Gradio app deployed on Render. Graded on tool routing, honesty at data limits, sources and memory. Optional extra credit: a find_performer_events chained tool | Tool design, prompting, memory, structured output, deployment | https://github.com/agenticllms/lecture-files/tree/main/DADA1 | TOOL, MEM, DEPLOY |
| Husky Tech Customer Support Agent (running in-class build, W03b-W05b) | A support agent with 4 tools and ticket filing. It is built as a notebook, then a project skeleton, then deployed to HF Spaces, then rewritten in LangGraph, then given RAG over husky_policy.md, then a reflection/self-grading loop | Tool calling, LangGraph, RAG, reflection, deployment | https://github.com/agenticllms/lecture-files/tree/main/W03b (also W04b, W05a, W05b) | TOOL, ARCH, MEM |
| Final Project (research) | A research contribution: agentic mechanism -> experimental manipulation -> measured behavior (e.g., memory policy -> stale-action rate). Suggested scope: controlled experiments on benchmarks, LoRA fine-tuning of 4-9B open models, trajectory analysis, fixed-token-budget architecture comparisons. Anchor papers cover eval, fine-tuning, safety, tool use/MCP and memory | Research design, experimentation, evaluation | n/a (resources: https://agenticllms.github.io/research.html) | EVAL, TRAIN, ORG |
| Midterm Exam (F 10/30) | Exam | n/a | n/a | ORG |

## Codebases & tools referenced

- Course repo: https://github.com/agenticllms/lecture-files (folders DADA1, W02b, W03a, W03b, W04a, W04b, W05a, W05b; requirements.txt; example.env)
- requirements.txt: langchain, langchain-openai, langchain-anthropic, langchain-google-genai, langchain-tavily, langchain-ollama, langgraph, python-dotenv, ipykernel, requests, gradio, langchain-openrouter (W05a adds langchain-pinecone, numpy, optional langchain-nvidia-ai-endpoints)
- LangChain / LangGraph docs: https://docs.langchain.com/oss/python/langgraph/workflows-agents ; LangSmith eval/cost docs: https://docs.langchain.com/langsmith/evaluation-concepts
- Ollama: https://ollama.com/download ; Qwen 3.5 models: https://ollama.com/library/qwen3.5
- uv: https://astral.sh/uv/install.sh
- Pinecone: https://www.pinecone.io
- Hugging Face Spaces: https://huggingface.co/new-space
- Render: https://render.com ; GitHub CLI: https://cli.github.com
- Model Context Protocol: https://modelcontextprotocol.io/docs/getting-started/intro
- APIs used: Gemini (default model, GOOGLE_API_KEY), Tavily, Ticketmaster Discovery, Open-Meteo, OpenRouter, NVIDIA embeddings

## Notes

- Session-page-to-lecture mapping is my inference. The Week 3a page ("Memory & Structured Output") sits on T 9/22, whose lecture title is "Simple Agent Architecture". Its notebooks follow the memory/structured-output docs listed under F 9/25. Tuesday notebooks may run one session ahead of or behind the lecture topic.
- Only week3b-slides.html and week4a-slides.html were found. week5a-slides.html returned 404. No slides are linked for the other sessions.
- "DADA" and "ICA" are not expanded anywhere I saw. Week 1 says "no ICA this week", so ICA probably means in-class activity.
- The DADA1 due date and the course grading breakdown were not found on any page I saw.
- All pages loaded successfully.
