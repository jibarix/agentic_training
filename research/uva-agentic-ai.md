# CS 6501 — Workshop on Building AI Agents ("Agentic AI") (University of Virginia, Spring 2026)

- **URLs:** home https://www.cs.virginia.edu/~rmw7my/Courses/AgenticAISpring2026/agenticAI.html ; calendar https://www.cs.virginia.edu/~rmw7my/Courses/AgenticAISpring2026/Calendar.html
- **Instructors:** Prof. Henry Kautz; TA Wenqian Ye
- **Level/prereqs:** Graduate-numbered (CS 6501 topics course). No prerequisites are stated. Students are expected to program in Python and to have accounts for an AI coding assistant, Hugging Face, Colab, GitHub, the OpenAI Platform, and Tinker (for fine-tuning).
- **Format:** In-person hands-on workshop, Tue/Thu 2:00-3:15pm. Most programming happens in class with rotating partners, and students keep a GitHub portfolio with one subdirectory per topic. Readings are about one paper per week. Grading: 25% attendance/participation, 20% mid-term and final portfolio review, 55% final project (teams of up to 2; 5-minute video plus Q&A; final report with Motivation/Methods/Evaluation/Conclusions sections).
- **Public materials:** Yes, and plenty of them. Each topic has an HTML page with learning goals, exercises and portfolio requirements, plus PPTX slides, HTML lesson plans/guides, and starter Python scripts/notebooks (relative links on the course site). Some topics also have AI-generated podcasts (MP3/M4A) and one YouTube video. No lecture recordings were seen.
- **License:** None stated.

**Overview.** The course is a practical workshop that teaches agent building by doing. Students start by running small open LLMs locally and on Colab, then move through LangGraph control flow, tool calling (OpenAI format, Ollama, ToolNode/ReAct agents), RAG, vision-language agents, MCP and A2A, and QLoRA-style fine-tuning with Tinker. Each lab is an exercise sheet with measurable experiments (timing, top-K, chunk size, and so on) that students record in their portfolio. After spring break the class switches to lecture-only "state of the art" topics (context management, CoT internals, coding agents, personal agents, distillation, science, math/Lean, video reasoning) while students work on final projects. The course favors small and open models: its first reading is "Small Language Models are the Future of Agentic AI".

## Lectures

Base for relative material links: `https://www.cs.virginia.edu/~rmw7my/Courses/AgenticAISpring2026/`. Topic-page URLs below were loaded and verified. Slide filenames come from the pages; their resolved URLs were not fetched individually.

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Tue 13 Jan 2026 | Topic 1: Running an LLM | LLM overview, tokenizers, open models, HF benchmark datasets; run Llama 3.2-1B MMLU eval with/without quantization on CPU/GPU/Colab; build a simple chat agent with context management | Belcak et al., Small Language Models are the Future of Agentic AI (https://arxiv.org/pdf/2506.02153); Illustrated GPT-2 (https://jalammar.github.io/illustrated-gpt2/) | Page: .../Topic1Running/Running_an_LLM.html ; slides `Topic1Running/01 Running an LLM.pptx`; code `llama_mmlu_eval.py`, `simple_chat_agent.py`; NoteGPT podcast MP3 | FND, EVAL, DEPLOY |
| 2 | Thu 15 Jan 2026 | (in-class lab, no calendar entry) | n/a | n/a | n/a | ORG |
| 3 | Tue 20 Jan 2026 | Topic 2: Agent Frameworks | LangGraph nodes/edges, conditional routing, parallel models (Llama + Qwen), chat history, multi-agent chat, checkpointing/crash recovery; optional web-search summarizer | LangGraph Graph API overview (https://docs.langchain.com/oss/python/langgraph/graph-api) | Page: .../Topic2Frameworks/Agent%20Control%20Flow%20Frameworks.html ; slides `02 Agent Frameworks.pptx`; code `langgraph_simple_llama_agent.py` | ARCH, MULTI |
| 4 | Thu 22 Jan 2026 | (Topic 2 lab continued, no calendar entry) | n/a | n/a | n/a | ARCH |
| 5 | Tue 27 Jan 2026 | Topic 3: Agent Tool Use (online) | Ollama server, parallel calls, OpenAI API/GPT-4o mini, OpenAI tool-call message format, manual tool handling (calculator), LangGraph multi-tool agent, tool forcing, persistent conversation graph | Schick et al., Toolformer (https://arxiv.org/abs/2302.04761) | Page: .../Topic3Tools/tools.html ; slides `03 Tools.pptx`; code `manual-tool-handling.py`, `langgraph-tool-handling.py`, `gpt4omini_test.py`; guides `ollama_guide.html`, `tool-forcing-strategies.html`; NotebookLM podcast `toolformer.m4a` | TOOL, ARCH |
| 6 | Thu 29 Jan 2026 | Topic 3 lab continued (online) | Breakout rooms continuing Topic 3 | n/a | n/a | TOOL |
| 7 | Tue 03 Feb 2026 | Topic 4: Exploring Tools | ToolNode vs create_react_agent, parallel tool dispatch, tools on remote servers, LangGraph built-in and third-party tool library; "2-Hour Agent Project" with a partner | n/a | Page: .../Topic4Exploring/exploring.html ; slides `exploring.pptx`; code `toolnode_example.py`, `react_agent_example.py`; `agent_tools_reference.html`; MoltReader https://github.com/HenryKautz/MoltReader | TOOL, RSN, ARCH |
| 8 | Thu 05 Feb 2026 | (Topic 4 lab / 2-hour project, no calendar entry) | n/a | n/a | n/a | TOOL |
| 9 | Tue 10 Feb 2026 | Topic 5: Retrieval Augmented Generation | Vector DBs, RAG pipeline, chunk size/overlap, top-K, query phrasing, score thresholds, prompt templates, unanswerable questions, cross-document synthesis (Qwen 2.5 1.5B vs GPT-4o mini) | n/a | Page: .../Topic5RAG/rag.html ; slides `rag.pptx`; notebook `manual_rag_pipeline_universal.ipynb`; `Corpora.zip`; pdf_ocr https://github.com/HenryKautz/pdf_ocr | MEM, EVAL |
| 10 | Thu 12 Feb 2026 | Topic 6: Vision-Language Models | CLIP, contrastive alignment, projection layers, image embeddings, image generation; VLM chat agent in LangGraph; video-surveillance agent (OpenCV keyframes + LLaVA) | Illustrated Stable Diffusion (https://jalammar.github.io/illustrated-stable-diffusion/) | Page: .../Topic6VLM/vlm.html ; slides `vlm_part1.pptx`, `vlm_part2.pdf`, `vlm_part3.pdf`; `vlm_guide.html`, `image_generation_guide.html`; clip_test https://github.com/HenryKautz/clip_test | WEB, APP, FND |
| 11 | Tue 17 Feb 2026 | (no calendar entry) | n/a | n/a | n/a | ORG |
| -- | Tue 24 / Thu 26 Feb 2026 | Catch-up week (no class) | Finish portfolio; sign up for mid-term one-on-one review | n/a | n/a | ORG |
| -- | 03 / 05 Mar 2026 | Spring break | n/a | n/a | n/a | ORG |
| 12 | Tue 10 Mar 2026 | Topic 7: MCP and A2A | Model Context Protocol, tool discovery, remote Asta tools (AI2), Agent-to-Agent protocol, agent cards, registry, ngrok tunneling; quiz-tournament exercise | n/a | Page: .../Topic7MCP/mcp.html ; slides `mcp.pptx`; `mcp_asta_lesson_plan.html`, `a2a_lesson_plan.html`; code `a2a_agent_template.py`, `a2a_test.py`, `a2a_trivia.py`, `A2a_registry.py`, `semantic_similarity.py`, `test_ngrok.sh` | TOOL, MULTI |
| -- | Thu 12 Mar 2026 | Class cancelled | Final project team sign-up | n/a | n/a | ORG |
| 13 | Tue 17 Mar 2026 | Topic 7 cont. (A2A) + Topic 8: LLM Fine-Tuning | Kinds of fine-tuning, fine-tuning vs RAG, QLoRA, Tinker pipeline; text-to-SQL fine-tuning of Llama | QLoRA (https://arxiv.org/abs/2305.14314), listed on the home page | Page: .../Topic8FineTuning/finetuning.html ; slides `finetuning.pptx`; `finetuning_intro_lesson_plan.html`, `sql_finetuning_lesson_plan.html`; data `sql_create_context_v4.json`; `sql_matches.py` | TRAIN, MULTI |
| 14 | Thu 19 Mar 2026 | (no calendar entry) | n/a | n/a | n/a | ORG |
| 15 | Tue 24 Mar 2026 | Topic 9: Context Management | Compression, selection, persistence; how frontier models manage long contexts | AgentFold (https://arxiv.org/abs/2510.24699) and Anthropic "Effective context engineering" are listed on the home page; the topic page itself lists none | Page: .../Topic9Context/context.html ; slides `context.pptx`; `context_management_lesson_plan.html` | MEM |
| 16 | Thu 26 Mar 2026 | Topic 10: Understanding Chain of Thought | CoT prompt varieties, why CoT works, tokenized vs hidden-layer (latent) CoT, hidden thought tokens | CoT (https://arxiv.org/abs/2201.11903) on the home page; topic page lists none | Page: .../Topic10COT/cot.html ; slides `chain_of_thought.pptx`; `chain_of_thought_lesson_plan.html` | RSN |
| 17 | Tue 31 Mar 2026 | Topic 11: Coding Agents | History from statistical LMs, frontier coding agent architecture (Claude Code), skills files, evolutionary programming | AlphaEvolve (https://doi.org/10.48550/arXiv.2506.13131); AVO (https://doi.org/10.48550/arXiv.2603.24517); EvoSkill (https://doi.org/10.48550/arXiv.2603.02766) | Page: .../Topic11Coding/coding.html ; slides `coding_1_history.pptx`, `coding_2_claude.pptx`, `coding_3_evolution.pptx` | CODE, ARCH |
| 18 | Thu 02 Apr 2026 | Topic 12: Personal Agents and Distilling | Clawdbot to OpenClaw/NullClaw/CoPaw/NemoClaw, Claude Cowork; risks of agents controlling accounts; OpenClaw-RL; knowledge distillation | n/a (resource links only) | Page: .../Topic12Personal/personal.html ; slides `personal.pptx`, `Knowledge Distillation Slides.pptx`; `personal_lesson_plan.html`, `distill.html` | WEB, SAFE, TRAIN |
| 19 | Tue 07 Apr 2026 | Topic 13: Agentic AI for Science | Research as an agent loop, scientific agent stack, AI2 tools (Semantic Scholar, OpenScholar, ScholarQA, Asta), JFC HEP case study, Orchestral AI, HEPTAPOD | AutoDiscovery (https://arxiv.org/abs/2507.00310); AI agents perform experimental HEP (https://inspirehep.net/literature/3132489); HEPTAPOD (https://arxiv.org/abs/2512.15867) | Page: .../Topic13Science/science.html ; slides `science.pptx`; HEPTAPOD code https://github.com/tonymenzo/heptapod | APP, MULTI |
| 20 | Thu 09 Apr 2026 | Topic 14: Agentic AI for Mathematics and Verification (guest: Prof. Kevin Sullivan) | Lean as lingua franca; AlphaProof, Lean Copilot, APOLLO, CLEVER; formal methods | Lean4CS1 notes (https://kevinsullivan.github.io/Lean4CS1/) | Page: .../Topic14Math/math.html ; `Kevin Sullivan Agents-Summary.html`, `Kevin Sullivan Agents-Class Note.html` | RSN, APP |
| 21 | Tue 14 Apr 2026 | Topic 15: Visual Reasoning | Video as reasoning substrate, diffusion transformers, Chain-of-Frames vs Chain-of-Steps, emergent working memory and self-correction, MIRAGE critique of VLM evaluation | Demystifying Video Reasoning (https://arxiv.org/abs/2603.16870); Chain-of-Frames (https://arxiv.org/abs/2506.00318); MIRAGE (https://arxiv.org/abs/2603.21687) | Page: .../Topic15Visual/visual.html ; slides `visual.pptx`, `mirage.pptx`; video https://www.youtube.com/watch?v=Gs9TPZmzo-s | RSN, EVAL |
| 22 | Thu 16 Apr 2026 | Final project presentations begin | 5-minute videos due at noon | n/a | n/a | ORG |
| 23 | Tue 21 Apr 2026 | Final project presentations | n/a | n/a | n/a | ORG |
| -- | Thu 23 Apr 2026 | No class | n/a | n/a | n/a | ORG |
| 24 | Tue 28 Apr 2026 | Final project presentations | n/a | n/a | `Spin/index.html` (questioner selector) | ORG |
| -- | Fri 15 May 2026 | Final reports due | n/a | n/a | n/a | ORG |

## Assignments / Projects

All labs below are portfolio exercises, one GitHub subdirectory per topic. Starter files are linked relatively from each topic page.

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| Topic 1 portfolio: Running an LLM | MMLU timing/accuracy study across models, quantization and hardware; chat agent with bounded context and restartability; optional MT-Bench | HF transformers, quantization, benchmarking, context management | `llama_mmlu_eval.py`, `simple_chat_agent.py` via .../Topic1Running/Running_an_LLM.html | FND, EVAL, MEM |
| Topic 2 portfolio: LangGraph agents | Routed, parallel, multi-model LangGraph chat with history and crash recovery; optional web summarizer | LangGraph graphs, routing, checkpointing | `langgraph_simple_llama_agent.py` via .../Topic2Frameworks/Agent%20Control%20Flow%20Frameworks.html | ARCH, MULTI |
| Topic 3 portfolio: Tool use | Ollama parallel timing; manual tool calling with a calculator; LangGraph multi-tool agent with tool_map; persistent graph with Mermaid diagram | OpenAI tool format, tool forcing, checkpointing | `manual-tool-handling.py`, `langgraph-tool-handling.py` via .../Topic3Tools/tools.html | TOOL, ARCH |
| Topic 4: 2-Hour Agent Project | Partner-built mini agent using LangGraph/third-party tools | ToolNode, ReAct agents, tool ecosystem | `toolnode_example.py`, `react_agent_example.py` via .../Topic4Exploring/exploring.html | TOOL, ARCH |
| Topic 5: RAG experiments | 11 controlled RAG experiments (RAG vs no-RAG, top-K, chunking, prompts, unanswerable questions) | Vector retrieval, RAG evaluation | `manual_rag_pipeline_universal.ipynb`, `Corpora.zip` via .../Topic5RAG/rag.html | MEM, EVAL |
| Topic 6: VLM agents | Image-chat LangGraph agent; video-surveillance agent with OpenCV + LLaVA (optional TTS intruder alert) | VLMs, Ollama llava, Gradio | `gradio_quickstart.py` via .../Topic6VLM/vlm.html | WEB, APP |
| Topic 7: MCP + A2A | MCP client for AI2 Asta tools; A2A agents, registry and trivia tournament over ngrok | MCP, A2A, networking | `a2a_agent_template.py` etc. via .../Topic7MCP/mcp.html | TOOL, MULTI |
| Topic 8: Text-to-SQL fine-tuning | Fine-tune Llama on text-to-SQL with Tinker and score semantic SQL matches | LoRA/QLoRA, Tinker, eval | `sql_create_context_v4.json`, `sql_matches.py` via .../Topic8FineTuning/finetuning.html | TRAIN, EVAL |
| Final project (55%) | Team project from a list of 20+ ideas (e.g., distillation, mini coding agent with sub-agents, MemGPT-style memory, debate agents, NL-to-PDDL planner, Lean/SAT assistants, misalignment replication); video, presentation, report | End-to-end agent design and evaluation | n/a | ARCH, EVAL, APP |

## Codebases & tools referenced

- Hugging Face smolagents: https://huggingface.co/docs/smolagents/index
- LangChain / LangGraph: https://www.langchain.com ; LangGraph Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- Model Context Protocol: https://modelcontextprotocol.io/ ; HF MCP course: https://huggingface.co/learn/mcp-course/en/unit0/introduction
- Unsloth: https://unsloth.ai/
- Tinker (Thinking Machines): https://thinkingmachines.ai/tinker/ ; install docs https://tinker-docs.thinkingmachines.ai/install
- Ollama (llava model), Google Colab, OpenAI Platform: https://platform.openai.com/
- Henry Kautz repos: gpt_with_tools https://gitlab.com/HenryKautz/gpt_with_tools ; MoltReader https://github.com/HenryKautz/MoltReader ; pdf_ocr https://github.com/HenryKautz/pdf_ocr ; clip_test https://github.com/HenryKautz/clip_test
- HEPTAPOD: https://github.com/tonymenzo/heptapod ; Orchestral AI: https://orchestral-ai.com
- OpenClaw https://openclaw.ai/ ; NullClaw https://nullclaw.org/ ; NVIDIA NemoClaw https://www.nvidia.com/en-us/ai/nemoclaw/ ; Claude Cowork https://www.anthropic.com/product/claude-cowork
- Brave Search API https://brave.com/search/api/ ; requests ; beautifulsoup4 ; OpenCV ; gradio ; edge-tts
- Background reading on the home page: Anthropic "Effective context engineering for AI agents" https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ; Chip Huyen "Building LLM applications for production" https://huyenchip.com/2023/04/11/llm-engineering.html ; Antonio Gulli "Agent Design Patterns" preview https://docs.google.com/document/d/1rsaK53T3Lg5KoGwvf8ukOUvbELRtH-V0LnOIFDxBryE/preview
- Additional core papers on the home page: ReAct https://arxiv.org/abs/2210.03629 ; Self-Refine https://arxiv.org/abs/2303.17651 ; Tree of Thoughts https://arxiv.org/abs/2305.10601 ; Generative Agents https://arxiv.org/abs/2304.03442 ; Magentic-One https://arxiv.org/html/2411.04468v1 ; ToolOrchestra https://arxiv.org/abs/2511.21689 ; narrow fine-tuning misalignment (Nature 2026) https://doi.org/10.1038/s41586-025-09937-5

## Notes

- The home page and the calendar loaded fully, as did topic pages 1-15. Slide (.pptx/.pdf), lesson-plan and code files are relative links; I did not fetch them one by one, so the filenames are as shown on the pages.
- The URL path is `~rmw7my`, but the page names Henry Kautz as instructor. The home page title is "CS 6501: Workshop on Building AI Agents".
- Thursday sessions with no calendar text (15 Jan, 22 Jan, 5 Feb, 19 Mar) and Tue 17 Feb are probably lab continuations. They are listed as placeholders, not as separate lectures. Counted substantive topic sessions: 15 topics across 14 dated lecture slots, plus 3 presentation days.
- The home page topic list mentions items with no dedicated calendar session (smolagents/HF pipelines, Self-Refine, search-augmented generation, multi-agent systems, AgentFold). These were presumably covered inside the topics above.
- The fetch tool summarized pages, so exercise details were paraphrased, not copied verbatim.
