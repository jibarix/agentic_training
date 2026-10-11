# Reference docs: MCP, Code execution with MCP, OpenClaw, Google Colab

## 1. Model Context Protocol (MCP), docs version 2026-07-28

- **URLs:** Intro https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro ; Architecture https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture ; Spec https://modelcontextprotocol.io/specification/latest ; Docs index https://modelcontextprotocol.io/llms.txt ; Inspector https://github.com/modelcontextprotocol/inspector ; Reference servers https://github.com/modelcontextprotocol/servers
- **What it is:** An open-source standard for connecting AI applications to external systems: data sources (files, databases), tools (search, calculators) and workflows (specialized prompts). The docs call it "a USB-C port for AI applications". It is supported by Claude, ChatGPT, VS Code, Cursor, MCPJam and others. MCP defines only context exchange. It does not dictate how the app uses the LLM or manages context.
- **Key concepts:**
  - **Participants:** An *MCP host* (the AI app, e.g., Claude Code, Claude Desktop, VS Code) creates one *MCP client* per *MCP server*. Each client keeps a dedicated connection to its server. A server is any program that provides context, local or remote.
  - **Two layers:** a *data layer* (JSON-RPC 2.0 messages, discovery, primitives, notifications) and a *transport layer* (connection setup, framing, auth).
  - **Transports:** *stdio* (local subprocess, usually one client) and *Streamable HTTP* (HTTP POST plus optional Server-Sent Events, for remote servers serving many clients; bearer tokens, API keys or headers, with OAuth recommended).
  - **Server primitives:** *Tools* (executable functions, `tools/list`, `tools/call`, JSON-Schema `inputSchema`), *Resources* (contextual data such as file contents or DB schemas), *Prompts* (reusable templates or few-shot examples). Discovery uses `*/list`, retrieval `*/get`/`resources/read`.
  - **Client primitives:** *Elicitation* (`elicitation/create`, where the server asks the user for input or confirmation via Multi Round-Trip Requests). *Sampling* (`sampling/createMessage`) and *Logging* are **deprecated as of 2026-07-28**; the docs say to call LLM provider APIs directly and to log via stderr or OpenTelemetry instead.
  - **2026-07-28 protocol changes:** MCP is now **stateless**. Every request carries protocol version, client capabilities and client info in `_meta`. A mandatory `server/discover` replaces stateful init and returns versions, capabilities and cacheable `ttlMs`/`cacheScope`. Change notifications are opt-in via a long-lived `subscriptions/listen` stream (e.g., `notifications/tools/list_changed`) and are best-effort. Optional *extensions* include a Tasks extension (durable handles for long-running requests) and MCP Apps (interactive UIs inside clients). Client best practices recommend *progressive tool discovery* when federating many servers.
- **Why it matters to an agent builder:** MCP is the de facto interface for giving agents tools and context. One server works across many hosts, and an agent's tool registry can be assembled from many servers. The 2026-07-28 stateless redesign (discover, `_meta`, subscriptions) and the deprecation of sampling and logging change how current servers and clients should be written, so tutorials older than mid-2026 may be out of date. Security best practices: https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices
- **Tags:** TOOL, ARCH

## 2. Anthropic Engineering: "Code execution with MCP: Building more efficient agents"

- **URL:** https://www.anthropic.com/engineering/code-execution-with-mcp (Adam Jones and Conor Kelly, Nov 4, 2025)
- **What it is:** An engineering post arguing that agents should call MCP servers *through code* rather than through direct tool calls.
- **Key concepts / the token-efficiency argument:**
  - **Problem 1:** Most clients load every tool definition into context up front. With thousands of tools, that means hundreds of thousands of tokens before the agent reads the request.
  - **Problem 2:** Intermediate results pass through the model, often twice (read, then write back into another tool call). A 2-hour meeting transcript adds about 50,000 tokens.
  - **Approach:** Expose each MCP server as a filesystem of code APIs (one TypeScript file per tool). The agent explores the tree and reads only the definitions it needs (*progressive disclosure*), optionally via a `search_tools` tool with adjustable detail levels. It then writes code that calls the tools inside a sandboxed execution environment.
  - **Result:** The example drops from about 150,000 to about 2,000 tokens, a 98.7% saving.
  - **Other benefits:** Data can be filtered or aggregated in the sandbox before it reaches the model. Loops, conditionals and retries run as code instead of chained tool calls. Privacy improves because intermediate data stays out of context and PII can be tokenized by the client. State can persist in files. Working code can be saved as reusable functions or *Skills* (SKILL.md).
  - **Caveats:** It needs a secure sandbox, resource limits and monitoring, which adds operational and security cost that direct tool calls avoid.
- **Related:** Cloudflare "Code Mode" https://blog.cloudflare.com/code-mode/ ; Agent Skills https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview ; Claude Code sandboxing https://www.anthropic.com/engineering/claude-code-sandboxing . CU Boulder CSCI 7000 assigns a related paper: Felendler et al., "From Tool Orchestration to Code Execution: A Study of MCP Design Choices" https://arxiv.org/abs/2602.15945
- **Why it matters to an agent builder:** It is a concrete pattern for scaling to many tools without blowing up the context window and cost. It ties together context engineering, code-as-action and skills, and it frames the security trade-off of running model-written code.
- **Tags:** TOOL, MEM, DEPLOY

## 3. OpenClaw

- **URL:** https://docs.openclaw.ai/ (installer at https://openclaw.ai/install.sh). The docs home page does not give a GitHub URL.
- **What it is:** An open-source (MIT), self-hosted personal AI assistant developed by the OpenClaw Foundation (a 501(c)(3)). It runs on your own machine or server and connects chat apps (Discord, Signal, Telegram, WhatsApp, Slack, etc.) to AI coding agents.
- **Key concepts:**
  - **Gateway:** a single process that is the source of truth for sessions, routing and channel connections. Control UI at `http://127.0.0.1:18789/` (`openclaw gateway install`, `openclaw dashboard`).
  - **Channels:** chat-app plugins. One gateway serves all of them.
  - **Agents:** sessions with multi-agent routing, isolated per agent, workspace or sender.
  - **Tools/automation:** agent tool use plus cron jobs, hooks and webhooks.
  - **Skills:** repeatable procedures loaded on demand. Plugins come from **ClawHub**.
  - **Memory:** listed under agent architecture (sessions/context). Not detailed on the home page.
  - **Security:** tokens, allowlists (e.g., `channels.whatsapp.allowFrom`) and safety controls.
  - **Install:** Node 24.16+/26 plus a model-provider API key, via the install script, npm/pnpm/bun, Docker, Nix or source. (Catalogued only; per the user's install policy, nothing should be installed without vetting and approval.)
  - **Doc sections (relative paths on docs.openclaw.ai):** /start/getting-started, /install, /channels, /concepts/architecture, /tools, /clawhub, /providers, /platforms, /gateway, /cli, /releases, /help
- **Why it matters to an agent builder:** A working open-source reference for a long-running, always-on, multi-channel agent: gateway/session architecture, multi-agent routing, skills, scheduled automation and an attack surface exposed to messaging apps (allowlists matter). It is a useful case study for deployment and safety. CU Boulder CSCI 7000 also assigns "MetaClaw" (https://arxiv.org/pdf/2603.17187); whether it relates to OpenClaw was not checked.
- **Tags:** ARCH, DEPLOY, SAFE

## 4. Google Colab

- **URL:** https://colab.research.google.com/ (not fetched; noted as the runtime environment)
- **What it is:** A hosted Jupyter notebook environment, to be used as the runtime for running self-study exercises without local setup.
- **Why it matters:** It gives a zero-install sandbox for notebook-based agent experiments (API calls, small MCP clients), and it keeps runtime work off the local machine.
- **Tags:** DEPLOY

## Notes

- All MCP intro, MCP architecture, Anthropic post and OpenClaw home pages loaded fully. OpenClaw subpages were not fetched.
- The MCP "2026-07-28" protocol details (stateless `_meta`, `server/discover`, `subscriptions/listen`, deprecation of sampling/logging) come from the architecture page and differ from the older 2025 spec (initialize handshake, sessions).
