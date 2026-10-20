"""Run every task under three conditions, score the answers, and save a self-describing run.

  no_tools : the model answers with no tools and no handbook (answering without evidence)
  v1       : the agent with the lookup tool as first written (substring match, top 5 lines)
  v2       : the same agent with the revised lookup (whole words, IDF ranking, table header kept)

Usage (from this folder):
  python experiment.py --out results/my-smoke --tasks denver --seeds 1 --conds v2
  python experiment.py --out results/my-run                 # all tasks, 3 seeds, 3 conditions
Each run writes a new folder and refuses to overwrite an old one.
"""
import argparse
import hashlib
import json
import platform
import re
import sys
import time
import urllib.request
from decimal import Decimal
from pathlib import Path

from agent import SYSTEM, Agent, Result
from llm import ChatClient
from tools import TOOLS, TOOLS_V1

HERE = Path(__file__).parent
FINAL = "\nEnd with one last line of the form: Final answer: <number> <unit>"
NO_TOOLS = "You answer questions about the ACME company handbook." + FINAL
CODE = ["agent.py", "tools.py", "llm.py", "experiment.py", "tasks.json"]


_NUM = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?"


def score(answer, expected, units):
    """True or False from the last 'Final answer:' line. None if there is no such line,
    which means a person has to read the answer and decide.

    The line must be exactly: [unit] <number> [unit] [.], with markdown emphasis ignored,
    a unit from `units` (whole token, plural allowed) and no other words."""
    lines = re.findall(r"(?im)^[\s*_#>-]*final answer[\s*_]*:(.*)$", answer)
    if not lines:
        return None
    line = re.sub(r"[*_]", "", lines[-1]).strip().rstrip(".").strip()
    m = re.fullmatch(rf"(\$|[A-Za-z]+)?\s*({_NUM})\s*([A-Za-z]+)?", line)
    if not m:
        return False
    names = {u.lower() for u in units}
    found = [w for w in (m.group(1), m.group(3)) if w]
    if not found or not all(w.lower() in names or w.lower().rstrip("s") in names for w in found):
        return False
    return abs(Decimal(m.group(2).replace(",", "")) - Decimal(str(expected))) <= Decimal("0.01")


def run_no_tools(client, task):
    """One model call, no tools; replies are checked and tokens counted as in Agent.run."""
    messages = [{"role": "system", "content": NO_TOOLS}, {"role": "user", "content": task}]
    t0 = time.time()
    try:
        msg, usage = client.chat(messages)
        if not isinstance(msg, dict):
            raise TypeError("the reply is not a message")
    except Exception as e:
        res = Result("model_error", detail=f"{type(e).__name__}: {e}")
        res.trace.append({"step": 1, "type": "model", "error": res.detail,
                          "seconds": round(time.time() - t0, 2)})
    else:
        text = msg.get("content") if isinstance(msg.get("content"), str) else ""
        used = (usage or {}).get("total_tokens")
        estimated = not isinstance(used, int)
        if estimated:                            # same rough rule as Agent.run
            used = len(json.dumps([messages, msg])) // 4
        res = Result("answered" if text.strip() else "model_error", text, 1, used,
                     "" if text.strip() else "empty reply")
        res.trace.append({"step": 1, "type": "model", "content": text, "calls": [],
                          "tokens": used, "estimated": estimated, "total": used,
                          "seconds": round(time.time() - t0, 2)})
    res.trace.append({"type": "end", "status": res.status, "detail": res.detail,
                      "steps": res.steps, "tokens": res.tokens})
    return res


def server_info(base_url, model):
    """What the server says about itself and the model (Ollama's native API; else empty)."""
    root = base_url.rsplit("/v1", 1)[0]
    info = {}
    try:
        with urllib.request.urlopen(root + "/api/version", timeout=10) as r:
            info["version"] = json.load(r).get("version")
        with urllib.request.urlopen(root + "/api/tags", timeout=10) as r:
            m = [x for x in json.load(r)["models"] if x["name"] == model]
        if m:
            info["digest"], info["details"] = m[0]["digest"], m[0].get("details")
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--model", default="qwen3.5:4b-q4_K_M")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", default='{"reasoning_effort": "none"}',
                    help="JSON merged into every request; use '{}' for servers that reject it")
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--conds", default="no_tools,v1,v2")
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
    a = ap.parse_args()

    out = HERE / a.out
    if out.exists():
        sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
    out.mkdir(parents=True)
    tasks = json.loads((HERE / "tasks.json").read_text())
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    conds, extra = a.conds.split(","), json.loads(a.extra)
    agent_kw = {"max_steps": 8, "max_tokens": 20_000, "max_obs_chars": 2_000, "hints": True}
    manifest = {
        "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": {"tag": a.model, **server_info(a.base_url, a.model)},
        "server": {"base_url": a.base_url},
        "machine": {"python": platform.python_version(), "platform": platform.platform(),
                    "processor": platform.processor()},
        "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)),
                     "extra": extra, "conditions": conds, "tasks": [t["id"] for t in tasks],
                     **agent_kw},
        "prompts": {"agent_system": SYSTEM + FINAL, "no_tools_system": NO_TOOLS},
        "sha256": {f: sha256(HERE / f) for f in CODE}
                  | {f"handbook/{p.name}": sha256(p) for p in sorted((HERE / "handbook").glob("*"))},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))

    rows = []
    with open(out / "traces.jsonl", "w", encoding="utf-8") as traces:
        for seed in range(1, a.seeds + 1):
            client = ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature,
                                seed=seed, extra=extra)
            for cond in conds:
                for t in tasks:
                    if cond == "no_tools":
                        res = run_no_tools(client, t["task"])
                    else:
                        tools = TOOLS_V1 if cond == "v1" else TOOLS
                        res = Agent(client, tools=tools, system=SYSTEM + FINAL, **agent_kw).run(t["task"])
                    ok = score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
                    row = {"seed": seed, "cond": cond, "id": t["id"], "status": res.status,
                           "ok": ok, "steps": res.steps, "tokens": res.tokens,
                           "answer": res.answer, "detail": res.detail}
                    rows.append(row)
                    traces.write(json.dumps({**row, "trace": res.trace}) + "\n")
                    mark = {True: "OK ", False: "BAD", None: "?  "}[ok]
                    print(f"{seed} {cond:8} {t['id']:10} {res.status:11} {mark} "
                          f"steps={res.steps} tok={res.tokens}", flush=True)
    (out / "runs.json").write_text(json.dumps(rows, indent=1))
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
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
