# CSCI 7000-005 — Building AI Agents (University of Colorado Boulder, Spring 2026)

- **URL(s):** https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/index.html ; subpages: syllabus.html, researchProject.html, paperCritiques.html, milestone1.html, finalProject.html (others listed in Notes)
- **Instructor:** Prof. Danny Dig (danny.dig@colorado.edu)
- **Level/prereqs:** Graduate seminar. Assumes undergraduate knowledge of software engineering, programming languages, systems and ML/AI, and that you are already a competent software engineer ("not an introductory SE course").
- **Course format:** Mon/Wed 5:05-6:20pm, mostly on Zoom, with in-person sessions on the first day, mid-semester (Project Bazaar) and the last week (DLC 1B20). Seminar format: two papers per meeting, student-led presentations, one-page critiques due before class, a LangGraph tutorial, an industry guest talk, and a 3-4 person team research project with 4 milestones. Grading: participation 10%, paper critiques 20%, paper presentation 20%, research project 50%. Attendance is mandatory (5 or more unexcused absences fails the course); no laptops in class.
- **Public materials:** Instructor slide PDFs for 4 lectures; the full reading list with paper links; assignment/milestone specifications. No videos or recordings. Paper presentations by students are not posted.
- **License:** None stated.

**Overview.** A seminar on agentic software systems, with a strong tilt toward agentic software engineering (refactoring agents, SWE-agent, AutoCodeRover, OpenHands, configuration of coding agents, code smells). Students learn to read state-of-the-art research critically and to design, implement and evaluate an agentic system. The reading arc runs from agent surveys and a research roadmap through the classic agent patterns (ReAct, Reflexion, Toolformer, Gorilla, PAL), multi-agent frameworks (AutoGen, MetaGPT, debate), to very recent 2025-2026 work on skills, memory, MCP design choices, safety and agent configuration. The project is research-grade, with ACM-format milestone papers. There is little hands-on coding instruction: one LangGraph tutorial plus an optional "tool experience report".

## Lectures

Slide URLs are resolved from the relative `./pdfs/...` links on the schedule page. They were not fetched one by one.

| # | Date | Title | Key topics (short) | Readings/papers | Materials | Tags |
|---|---|---|---|---|---|---|
| 1 | Mon 01/12 | Course introduction (Dig) | Logistics; how to read research papers | Griswold, "How to Read an Engineering Research Paper" http://cseweb.ucsd.edu/~wgg/CSE210/howtoread.html | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/pdfs/CSCI_7000_005_W1L1.pdf | ORG |
| 2 | Wed 01/14 | Survey of agents (Dig) | LLM agent surveys: general and SE | Wang et al., LLM-based autonomous agents survey https://link.springer.com/article/10.1007/s11704-024-40231-1 ; Liu et al., LLM-Based Agents for SE survey https://arxiv.org/pdf/2409.02977 | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/pdfs/W1_L2_SurveyOfAgents.pdf | ARCH, CODE |
| — | Mon 01/19 | MLK Day (no class) | Optional video | https://www.youtube.com/watch?v=vP4iY1TtS3s | — | — |
| 3 | Wed 01/21 | Agentic SE roadmap (Dig) | Foundational pillars and research roadmap for agentic SE | Hassan et al., Agentic Software Engineering https://arxiv.org/pdf/2509.06216 | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/pdfs/W2_L2_Roadmap.pdf | CODE, ARCH |
| 4 | Mon 01/26 | Refactoring agents (students) | Multi-agent rename refactoring; refactoring benchmark | Bellur et al., Multi-Agent Coordinated Rename Refactoring https://arxiv.org/abs/2601.00482 ; Gautam et al., RefactorBench https://openreview.net/pdf?id=NiNIthntx7 | n/a | CODE, MULTI, EVAL |
| 5 | Wed 01/28 | MM-Assist & MANTRA (Dig) | LLM-assisted refactoring (move method); multi-agent refactoring | Bellur et al., Together We Are Better https://danny.cs.colorado.edu/papers/ICSME25_MM-Assist.pdf ; Xu et al., MANTRA https://arxiv.org/abs/2503.14340 | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/pdfs/W3_L2_MM-Mantra.pdf | CODE, MULTI |
| 6 | Mon 02/02 | Project idea pitches | Students pitch projects | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/projectProposal.html | ORG |
| 7 | Wed 02/04 | Project Bazaar (1), in person | Team formation | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/projectTeams.html | ORG |
| 8 | Mon 02/09 | Project Bazaar (2), in person | Team formation | n/a | (same as above) | ORG |
| 9 | Wed 02/11 | ReAct & Web API code gen (students) | Reasoning+acting loop; API integration code benchmark | Yao et al., ReAct https://arxiv.org/abs/2210.03629 ; Maninger et al., Benchmarking Web API Integration Code Generation https://arxiv.org/pdf/2509.20172v4 | n/a | RSN, TOOL, EVAL |
| 10 | Mon 02/16 | Milestone 1 presentations | Research questions, challenges, approach, related work | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/milestone1.html | ORG |
| 11 | Wed 02/18 | Reflexion & Toolformer (students) | Verbal self-reflection; self-taught tool use | Shinn et al., Reflexion https://arxiv.org/abs/2303.11366 ; Schick et al., Toolformer https://arxiv.org/pdf/2302.04761 | n/a | RSN, TOOL, TRAIN |
| 12 | Mon 02/23 | Gorilla & PAL (students) | API-call LLMs; program-aided reasoning | Patil et al., Gorilla https://arxiv.org/pdf/2305.15334 ; Gao et al., PAL https://arxiv.org/pdf/2211.10435 | n/a | TOOL, RSN |
| 13 | Wed 02/25 | SWE-agent & AutoCodeRover (students) | Agent-computer interfaces; repo-level program repair | Yang et al., SWE-agent https://arxiv.org/pdf/2405.15793 ; Zhang et al., AutoCodeRover https://arxiv.org/pdf/2404.05427 | n/a | CODE, ARCH |
| 14 | Mon 03/02 | AutoGen & MetaGPT (students) | Multi-agent conversation frameworks; SOP-driven role agents | Wu et al., AutoGen https://arxiv.org/pdf/2308.08155 ; Hong et al., MetaGPT https://arxiv.org/pdf/2308.00352 | n/a | MULTI, ARCH |
| 15 | Wed 03/04 | Multiagent debate & Agentless (students) | Debate for factuality/reasoning; demystifying SE agents | Du et al., Multiagent Debate https://openreview.net/pdf?id=zj7YuTE4t8 ; Xia et al., Demystifying LLM-Based SE Agents https://dl.acm.org/doi/epdf/10.1145/3715754 | n/a | MULTI, RSN, CODE |
| 16 | Mon 03/09 | LangGraph tutorial & OpenHands | Hands-on LangGraph; open coding-agent platform; tool experience report | Wang et al., OpenHands https://arxiv.org/pdf/2407.16741 | n/a | ARCH, CODE |
| 17 | Wed 03/11 | Milestone 2 presentations | Project progress | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/milestone2.html | ORG |
| — | 03/16, 03/18 | Spring Break (no class) | — | — | — | — |
| 18 | Mon 03/23 | RefAgent & Agentic Skills (students) | Multi-agent refactoring; SoK on agent skills | Oueslati et al., RefAgent https://arxiv.org/pdf/2511.03153 ; Jiang et al., SoK: Agentic Skills https://arxiv.org/pdf/2602.20867 | n/a | CODE, ARCH, TOOL |
| 19 | Wed 03/25 | AppAgent & coding-agent configuration (students) | Smartphone GUI agent; config files of AI coding agents | Zhang et al., AppAgent https://arxiv.org/pdf/2312.13771 ; Santos et al., Decoding the Configuration of AI Coding Agents https://arxiv.org/pdf/2511.09268 | n/a | WEB, CODE |
| 20 | Mon 03/30 | Milestone 3 presentations | Project progress | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/milestone3.html | ORG |
| 21 | Wed 04/01 | MemSkill & More with Less (students) | Memory skills for agents; efficiency | Zhang et al., MemSkill https://arxiv.org/abs/2602.02474 ; Gao & Peng, More with Less https://arxiv.org/pdf/2510.16786 | n/a | MEM, DEPLOY |
| 22 | Mon 04/06 | MetaClaw & code smells (students) | MetaClaw; causal analysis of smells in LLM code | Xia et al., MetaClaw https://arxiv.org/pdf/2603.17187 ; Velasco et al., Causal Perspective on Smells in LLM-Generated Code https://arxiv.org/abs/2511.15817 | n/a | CODE, EVAL |
| 23 | Wed 04/08 | SafePro & ToolDreamer (students) | Agent safety; tool retrieval/selection | Zhou et al., SafePro https://arxiv.org/pdf/2601.06663 ; Sengupta et al., ToolDreamer https://arxiv.org/pdf/2510.19791v2 | n/a | SAFE, TOOL |
| 24 | Mon 04/13 | Swiss Cheese safety & MCP design (students) | Layered AI-safety model; tool orchestration vs code execution in MCP | Shamsujjoha et al., Swiss Cheese Model for AI Safety https://arxiv.org/abs/2408.02205 ; Felendler et al., From Tool Orchestration to Code Execution: MCP Design Choices https://arxiv.org/abs/2602.15945 | n/a | SAFE, TOOL |
| 25 | Wed 04/15 | Guest talk: Ameya Ketkar (Uber), building AI agents in industry | Industry agents; multi-agent SRE incident analysis | Kataria, Intelligent Site Reliability Engineering https://www.researchgate.net/publication/399119176_Intelligent_Site_Reliability_Engineering_A_Multi-agent_LLM_Framework_for_Automated_Incident_Analysis_and_Root_Cause_Determination | n/a | DEPLOY, MULTI, APP |
| 26 | Mon 04/20 | Class summary and insights (Dig), in person | Course wrap-up | n/a | n/a | ORG |
| 27 | Wed 04/22 | Milestone 4 presentations | Empirical evaluation results | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/milestone4.html | ORG |
| 28 | Fri 04/24 | Project Clinic (Dig) | Project help | n/a | n/a | ORG |
| — | Sun 04/26 | No final exam; submit final project | — | n/a | https://danny.cs.colorado.edu/courses/csci7000-005_Sp26/finalProject.html | ORG |

## Assignments / Projects

| Name | What you build | Skills | Starter code URL | Tags |
|---|---|---|---|---|
| Paper critiques (20%) | One-page critique per paper (liked / disliked / future directions / open questions / discussion points / summary), due 12pm on the day of class | Critical reading of research | n/a | ORG |
| Tool Experience Report (critique option #2) | Download the tool a paper introduces, run it on your own use case, and write a one-page reflection (experience, strengths, weaknesses, practical impact, recommendations) | Hands-on evaluation of agent tools | n/a | EVAL, CODE |
| Paper presentation (20%) | Lead the discussion of an assigned paper | Presenting research | n/a | ORG |
| Research project (50%, teams of 3-4) | A research-oriented or novel-industrial project on GenAI/agents in SE: proposal (02/02), M1 2-page ACM paper plus 10-min talk (RQs, challenges, approach, 5 or more related works), M2, M3, M4 (empirical evaluation), final conference-style paper (abstract, intro, 10 or more refs, conclusions, lessons learned) | Research design, agent implementation, empirical evaluation, scientific writing | n/a | CODE, EVAL, ORG |

## Codebases & tools referenced

- LangGraph (in-class tutorial on 03/09). The site gives no URL.
- OpenHands (paper): https://arxiv.org/pdf/2407.16741
- SWE-agent (paper): https://arxiv.org/pdf/2405.15793 ; AutoCodeRover (paper): https://arxiv.org/pdf/2404.05427
- AutoGen (paper): https://arxiv.org/pdf/2308.08155 ; MetaGPT (paper): https://arxiv.org/pdf/2308.00352
- ACM proceedings template (milestones/final): https://www.acm.org/publications/proceedings-template
- Piazza: https://piazza.com/colorado/spring2026/csci7000005 ; Canvas (submissions, login required)

## Notes

- All of the index page loaded. Subpages fetched: syllabus, researchProject, paperCritiques, milestone1, finalProject. Not fetched: paperPresentation.html, projectProposal.html, projectTeams.html, milestone2-4.html.
- The course is finished (Spring 2026). Only 4 instructor slide decks are public (lectures 1, 2, 3, 5). Slide URLs were resolved from relative links and not fetched one by one.
- Date inconsistency: the schedule says "Sun 04/26 ... submit final project", while the research-project and final-project pages give 04/27 12pm.
- The location is listed as ECES 114 on the index page but DLC 1B20 for the in-person sessions.
- Lecture titles for student-led sessions are my labels built from the paper names. The site lists only presenter names and papers.
- The syllabus has no AI-use policy and no formal learning objectives.
