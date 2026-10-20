# Chapter 2 companion code: the tools behind MCP

Python 3.10 or later, standard library only; no MCP SDK. Chapter 1's code (`../ch01`) must sit
next to this folder: the server serves its tools and the experiment runs its agent. The server
(`mcp_server.py`) is 170 lines, the client 174 and the bridge 75. The protocol is MCP revision
2026-07-28 (stateless: no `initialize`; every request carries its version in `_meta`), tools only,
over stdio.

| File | What it is |
|---|---|
| `mcp_server.py` | `Server.handle` (one message in, one response out, no I/O), `server/discover`, `tools/list` with paging, `tools/call`, and the stdio loop |
| `handbook_server.py` | Chapter 1's three tools behind the server; fault switches `--crash-on-call N`, `--slow NAME=S`, `--noise` |
| `mcp_client.py` | `StdioClient`: starts and supervises the server process; timeouts, cancellation, restart, shutdown, retry only for trusted read-only tools |
| `bridge.py` | Turns one or more servers' tools into a Chapter 1 registry, with optional `server__tool` prefixes, and every failure into a Chapter 1 `ToolError` |
| `archive/` | A fictional, superseded 2024 edition of the handbook, served by a second server |
| `test_mcp.py` | Tests of the server, the subprocess and its failures, and the bridge (same specs and observations as Chapter 1) |
| `experiment.py` | Runs Chapter 1's agent and tasks with the tools in process, behind one server, and behind two |
| `report.py` | Turns a run folder into the chapter's tables, traces, numbers and wire transcript (`../../build/`) |
| `book.json` | Which run and which traces the chapter uses |

## 1. Test (no model needed)

From this folder (`bigbook/code/ch02`):

```
python -m unittest -v test_mcp
```

Expected: `Ran 32 tests ... OK` in a few seconds (one test waits for a slow tool to time out).

## 2. Talk to the server by hand

The server reads one JSON message per line on stdin and writes one per line on stdout; its log
goes to stderr. Every request needs `_meta` with the protocol version and client capabilities:

```
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientCapabilities":{}}}}' | python handbook_server.py
```

## 3. Smoke run

Serve the model as in Chapter 1's README, then:

```
python experiment.py --out results/my-smoke --tasks denver --seeds 1
```

Expected: three lines (`local`, `mcp`, `mcp_two`), each `answered OK`. Read a trace with:

```
python report.py --show results/my-smoke mcp_two:denver:1
```

## 4. Full run

```
python experiment.py --out results/my-run           # 10 tasks x 3 seeds x 3 conditions
```

The servers start once and serve the whole run. At the end, `manifest.json` records for each
server how many times it was restarted, any non-JSON lines it printed, any replies that arrived
too late, and how many calls it served. A run never overwrites an existing folder. Answers without
a `Final answer:` line are left unscored for a person to label in `adjudication.json`.

## 5. Rebuild the chapter (from `bigbook/`)

```
python snip.py
cd code/ch02 && python report.py && cd ../..
python check.py
pdflatex -disable-installer -interaction=nonstopmode bigbook.tex   # twice
```

## Licence

The code in this folder is released under the MIT licence (see `../LICENSE`).
