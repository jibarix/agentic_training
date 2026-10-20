"""Chapter 1's agent and tasks, with the tools in process or behind MCP servers.

  local   : Chapter 1's registry, in process (the v2 condition of Chapter 1)
  mcp     : the same tools from one MCP server over stdio
  mcp_two : that server plus a second one serving the superseded 2024 handbook; names prefixed

Usage (from this folder):
  python experiment.py --out results/my-smoke --tasks denver --seeds 1 --conds mcp
  python experiment.py --out results/my-run                 # all tasks, 3 seeds, 3 conditions
Each run writes a new folder and refuses to overwrite an old one.
"""
import argparse
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
CH01 = HERE.parent / "ch01"
import bridge                                            # noqa: E402  (puts ../ch01 on the path)
from agent import SYSTEM, Agent                          # noqa: E402
from llm import ChatClient                               # noqa: E402
from mcp_client import StdioClient                       # noqa: E402
from tools import TOOLS                                  # noqa: E402

_spec = importlib.util.spec_from_file_location("ch01_experiment", CH01 / "experiment.py")
ch01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch01)                           # score, FINAL, server_info, sha256

SERVER = [sys.executable, str(HERE / "handbook_server.py")]
ARCHIVE = SERVER + ["--name", "archive", "--dir", str(HERE / "archive"),
                    "--label", "ARCHIVE (2024 edition, superseded)"]
CODE = ["mcp_server.py", "handbook_server.py", "mcp_client.py", "bridge.py", "experiment.py"]
CH01_CODE = ["agent.py", "tools.py", "llm.py", "experiment.py", "tasks.json"]


def timed(registry, log):
    """The same registry, with every call's wall time appended to `log` as [name, ms]."""
    def wrap(name, fn):
        def call(**args):
            t0 = time.perf_counter()
            try:
                return fn(**args)
            finally:
                log.append([name, round(1000 * (time.perf_counter() - t0), 3)])
        return call
    return {name: (wrap(name, fn), spec) for name, (fn, spec) in registry.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--model", default="qwen3.5:4b-q4_K_M")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", default='{"reasoning_effort": "none"}')
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--conds", default="local,mcp,mcp_two")
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
    ap.add_argument("--tool-timeout", type=float, default=10.0)
    a = ap.parse_args()

    out = HERE / a.out
    if out.exists():
        sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
    out.mkdir(parents=True)
    tasks = json.loads((CH01 / "tasks.json").read_text())
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    conds, extra = a.conds.split(","), json.loads(a.extra)
    agent_kw = {"max_steps": 8, "max_tokens": 20_000, "max_obs_chars": 2_000, "hints": True}

    # Servers start once and serve the whole run, as a desktop client would keep them.
    handbook = StdioClient("handbook", SERVER, timeout=a.tool_timeout, trusted=True).start()
    archive = StdioClient("archive", ARCHIVE, timeout=a.tool_timeout, trusted=True).start()
    registries = {"local": TOOLS, "mcp": bridge.registry([handbook]),
                  "mcp_two": bridge.registry([handbook, archive], prefix=True)}

    manifest = {
        "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": {"tag": a.model, **ch01.server_info(a.base_url, a.model)},
        "server": {"base_url": a.base_url},
        "machine": {"python": platform.python_version(), "platform": platform.platform(),
                    "processor": platform.processor()},
        "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)),
                     "extra": extra, "conditions": conds, "tasks": [t["id"] for t in tasks],
                     "tool_timeout": a.tool_timeout, **agent_kw},
        "prompts": {"agent_system": SYSTEM + ch01.FINAL},
        "tools": {c: [s for _, s in registries[c].values()] for c in conds},
        "sha256": {f: ch01.sha256(HERE / f) for f in CODE}
                  | {f"ch01/{f}": ch01.sha256(CH01 / f) for f in CH01_CODE}
                  | {f"ch01/handbook/{p.name}": ch01.sha256(p) for p in sorted((CH01 / "handbook").glob("*"))}
                  | {f"archive/{p.name}": ch01.sha256(p) for p in sorted((HERE / "archive").glob("*"))},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))

    rows = []
    with open(out / "traces.jsonl", "w", encoding="utf-8") as traces:
        for seed in range(1, a.seeds + 1):
            client = ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature,
                                seed=seed, extra=extra)
            for cond in conds:
                for t in tasks:
                    tool_ms = []
                    agent = Agent(client, tools=timed(registries[cond], tool_ms),
                                  system=SYSTEM + ch01.FINAL, **agent_kw)
                    res = agent.run(t["task"])
                    ok = ch01.score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
                    row = {"seed": seed, "cond": cond, "id": t["id"], "status": res.status,
                           "ok": ok, "steps": res.steps, "tokens": res.tokens,
                           "answer": res.answer, "detail": res.detail, "tool_ms": tool_ms}
                    rows.append(row)
                    traces.write(json.dumps({**row, "trace": res.trace}) + "\n")
                    traces.flush()
                    mark = {True: "OK ", False: "BAD", None: "?  "}[ok]
                    print(f"{seed} {cond:8} {t['id']:10} {res.status:11} {mark} "
                          f"steps={res.steps} tok={res.tokens}", flush=True)
    for c in (handbook, archive):
        c.close()
    (out / "runs.json").write_text(json.dumps(rows, indent=1))
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    manifest["servers"] = {c.name: {"restarts": c.restarts, "junk_lines": c.junk,
                                    "dropped": len(c.dropped), "calls": len(c.log)}
                           for c in (handbook, archive)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print("\ncondition  correct  unscored  mean steps  mean tokens")
    for cond in conds:
        r = [x for x in rows if x["cond"] == cond]
        print(f"{cond:9} {sum(x['ok'] is True for x in r):3}/{len(r):<4} "
              f"{sum(x['ok'] is None for x in r):6} {sum(x['steps'] for x in r) / len(r):10.1f} "
              f"{sum(x['tokens'] for x in r) / len(r):11.0f}")
    print(f"\nwrote {out}. Unscored answers have no 'Final answer:' line: read and label them.")


if __name__ == "__main__":
    main()
