# Stanford CS146S — Fall 2026 schedule, VERIFIED (rendered in Chrome, 2026-10-16)

Source: https://themodernsoftware.dev/ (Syllabus tab). Supersedes nothing for Fall 2025 (see stanford-cs146s.md); this is the current offering.
Slides posted for weeks 1-3, W4 Tue 10/13 and W5 Tue 10/20 so far (none for the guest sessions W4 Thu, Boris Cherny, or W5 Thu, Eno Reyes); W1 also has completed code, prompts, transcript (Thu); W2 Tue and Thu have transcripts; W2 Thu has a Skills link. Reading lists posted for weeks 1-5. Assignment specs for weeks 1-5 are on the repo's `master` branch.

| Wk | Date | Session | Tags |
|---|---|---|---|
| 1 The Internals of Coding Agents | Tue 9/22 | Course intro + build Claude Code in 200 lines (readings: Building a Coding Agent; Lessons from Building Claude Code; Dive into Claude Code) | CODE, ARCH |
| 1 | Thu 9/24 | How SOTA coding agents are designed: deep dive into system prompts | CODE, FND |
| 2 Advanced Context Engineering | Tue 9/29 | Advanced prompting + agentic dev frameworks (RePPIT, spec-driven development) (readings: The Context Tax: When to Compact; OpenSpec; Superpowers; Enterprise MCP (Cloudflare)) | FND, MEM |
| 2 | Thu 10/1 | Full introduction to MCP and tool-calling (theory, setup, advanced tool design) | TOOL |
| 3 Agent Skills and CLI | Tue 10/6 | All about agent skills (incl. web skills) (readings: pstack; Matt Pocock's Skills; browse.sh) | MEM, TOOL |
| 3 | Thu 10/8 | Guest: Lee Robinson | APP |
| 4 Customizing Your Agent and Repository | Tue 10/13 | CLAUDE.md, AGENTS.md, hooks; subagent patterns (planner/implementer/reviewer) (readings: I Still Prefer MCP Over Skills; AGENTS.md (Factory Docs); Steering Claude Code: Skills, Hooks, Rules, Subagents, and More; Writing a Good CLAUDE.md) | CODE, MULTI |
| 4 | Thu 10/15 | Guest: Boris Cherny (Claude Code, Anthropic) | CODE |
| 5 Agent-Ready Codebases | Tue 10/20 | Agent readiness in your repos: structure, docs, tests, checks; scoring and auditing readiness (readings: Making Codebases Agent Ready; Making Ergonomic Repositories) | CODE, EVAL |
| 5 | Thu 10/22 | Guest: Eno Reyes (Factory) | CODE |
| 6 Agentic Code Review | Tue 10/27 | Agentic code review: best practices and architectures | CODE, EVAL |
| 6 | Thu 10/29 | Guest: Silas Alberti (Cognition) | CODE |
| 7 Security | Tue 11/3 | Security in AI codebases | SAFE |
| 7 | Thu 11/5 | Guest: Isaac Evans (Semgrep) | SAFE |
| 8 Background Agents | Tue 11/10 | Background agents: launching tasks asynchronously | DEPLOY, ARCH |
| 8 | Thu 11/12 | Guest: Rajesh Bhatia (Cloudflare) | DEPLOY |
| 9 Building an AI-Native Team | Tue 11/17 | Guest: Elad Gil | APP |
| 9 | Thu 11/19 | Guest: Amjad Masad (Replit) | APP |
| 10 Software Factory + Future | Tue 12/1 | Coding agents in big teams (MCP portals, LLM gateways, cost optimization, model routing) | DEPLOY |
| 10 | Thu 12/3 | The Software Factory: self-running, self-improving software systems | ARCH, DEPLOY |

## Notes

- Last checked 2026-10-26 by fetching the site with curl and reading the schedule data in its Next.js bundle (now chunk 0wms-bb2f7br5.js, deployment dpl_EoEpUynztqbX3iVcaKwgvHvUqaiA), not by rendering in Chrome; also read the assignments repo through the GitHub API and raw files. New since 2026-10-18: (1) W4 reading list, four items: "I Still Prefer MCP Over Skills" https://david.coffee/i-still-prefer-mcp-over-skills ; "AGENTS.md (Factory Docs)" https://docs.factory.com/harness/agents-md ; "Steering Claude Code: Skills, Hooks, Rules, Subagents, and More" https://claude.com/resources/articles/steering-claude-code-skills-hooks-rules-subagents-and-more ; "Writing a Good CLAUDE.md" https://hlyr.dev/blog/writing-a-good-claude-md . (2) W5 Tue 10/20 slides https://docs.google.com/presentation/d/1yCxocmUrGIN7IrC42WB6NW08PtYYFLe1ombDj3Ay6_8/edit?usp=drive_link ; session title now "Agent readiness in your repos (structure, docs, and checks that make repos agent-friendly)". (3) W5 reading list: "Making Codebases Agent Ready" https://www.youtube.com/watch?v=ShuJ_CN6zr4 ; "Making Ergonomic Repositories" https://x.com/trybasis/status/2056881705269580023 . W5 topics: what makes a repo agent-ready; scoring and auditing readiness; common gaps that block agents in real repos. (4) Week 4 assignment (commit 2026-10-19), "Make a Messy Repo Agent-Ready": explore an unfamiliar OSS repo (htmx, dayjs, slidev, pixijs, yt-dlp, etc.) and write its AGENTS.md or CLAUDE.md (project, architecture, exact commands, conventions, guardrails; about a page), then run two tasks with it and report one change; https://github.com/mihail911/modern-software-dev-assignments/blob/master/week4/assignment.md (CODE, MEM). (5) Week 5 assignment (commit 2026-10-26), "Agent-Readiness Report": run Factory's Droid `/readiness-report` on three OSS repos (eight pillars, five maturity levels), compare where they fall short, and critique the framework; https://github.com/mihail911/modern-software-dev-assignments/blob/master/week5/assignment.md (CODE, EVAL). These two belong in the Fall 2026 assignment table in stanford-cs146s.md, which this check did not edit. Not new: W4 Thu 10/15 (Boris Cherny) and W5 Thu 10/22 (Eno Reyes) have no materials; no new transcripts (only 9/24, 9/29 and 10/1 are linked; guessed /materials/ paths for later dates return 404). Week 6 (Tue 10/27, tomorrow) has no materials or readings yet. Weeks 6-10 titles, sessions, dates and guests are unchanged; the bundle lists three topic bullets per week for weeks 6-10, which I could not compare with the 2026-10-18 bundle because that copy was not kept. The Fall 2026 slide links are flagged `gated` in the bundle, so they may need a login; I did not open them. Suggested next recheck: 2026-11-02, after week 6.
- Checked 2026-10-18 by reading the schedule data in the site's Next.js bundle (chunk 06~g0g2oopgbg.js, deployment dpl_FMCmZJyLnhUS5sKMavFNFoDLrh2o), not by rendering in Chrome; the previous check (2026-10-16) rendered the Syllabus tab in Chrome. Nothing new: W4 Thu 10/15 (Boris Cherny) still has no materials, W4 Tue still has slides only, and W1-W3 links and reading lists are as recorded. Weeks 5-10 titles and topics are unchanged. Suggested next recheck: 2026-10-23, after week 5.
- New since 2026-10-09: W4 Tue 10/13 slides; transcripts for W2 Tue 9/29 and Thu 10/1; W2 reading list (four items, not recorded on 2026-10-09, so it may have been missed then rather than newly added).
- W4 Tue session title on the site is now "Customizing your agentic setup (CLAUDE.md, AGENTS.md, hooks)"; subagent patterns appear as a W4 topic. W4 has no reading list. W4 Thu (Boris Cherny, listed as "Creator of Claude Code @ Anthropic") has no materials yet.
- Guest affiliations shown on the site: Lee Robinson (Model Behavior @ SpaceX), Eno Reyes (CTO @ Factory), Silas Alberti (SVP Research @ Cognition), Isaac Evans (CEO @ Semgrep), Rajesh Bhatia (Senior Director @ Cloudflare), Elad Gil (Investor @ Gil Capital), Amjad Masad (CEO @ Replit). No guest or date changes.
