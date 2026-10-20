"""Is Chapter 1's lookup v2 better than v1? Run both on held-out tasks, with repeats.

  v1       : Chapter 1's agent with lookup as first written
  v2       : the same agent with the revised lookup
  v2_again : v2 once more, on other seeds (101, 102, ...): a comparison of v2 with itself,
             to see how large a difference noise alone makes

The held-out tasks (tasks_heldout.json) were written and frozen before any run. Chapter 1's ten
tasks, on which the revision was found, run under v1 and v2 too, for contrast. The conditions are
interleaved task by task, so a slow spell on the machine falls on all of them alike.

Usage (from this folder):
  python experiment.py --out results/my-smoke --seeds 1 --tasks pd_seattle3,denver
  python experiment.py --out results/my-run              # 50 tasks, 5 seeds; 600 + 100 runs
  python experiment.py --out results/my-run --resume     # continue a run that was interrupted
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
from agent import SYSTEM, Agent                          # noqa: E402
from llm import ChatClient                               # noqa: E402
from tools import TOOLS, TOOLS_V1                        # noqa: E402

from score import score                                  # noqa: E402

CH01 = HERE.parent / "ch01"
_spec = importlib.util.spec_from_file_location("ch01_experiment", CH01 / "experiment.py")
ch01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch01)                           # Chapter 1's prompt suffix and server_info
FINAL = ch01.FINAL
CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py", "experiment.py", "tasks.json")},
        **{f"ch03/{f}": HERE / f for f in ("experiment.py", "score.py", "tasks_heldout.json")}}
AGENT_KW = {"max_steps": 8, "max_tokens": 20_000, "max_obs_chars": 2_000, "hints": True}


def load_tasks():
    held = [{**t, "set": "heldout"} for t in json.loads((HERE / "tasks_heldout.json").read_text())]
    dev = [{**t, "set": "dev", "cluster": "dev"} for t in json.loads((CH01 / "tasks.json").read_text())]
    return held + dev


def plan(tasks, seeds):
    """(seed, task, condition, seed actually sent) in run order."""
    out = []
    for s in range(1, seeds + 1):
        for t in tasks:
            conds = ["v1", "v2"] + (["v2_again"] if t["set"] == "heldout" else [])
            out += [(s, t, c, s + 100 if c == "v2_again" else s) for c in conds]
    return out


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    """The code, the tasks and the handbook, as they are now."""
    return ({k: sha256(p) for k, p in CODE.items()}
            | {f"handbook/{p.name}": sha256(p) for p in sorted((CH01 / "handbook").glob("*"))})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--model", default="qwen3.5:4b-q4_K_M")
    ap.add_argument("--base-url", default="http://localhost:11434/v1")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", default='{"reasoning_effort": "none"}')
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: all)")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out")
    a = ap.parse_args()

    out = HERE / a.out
    tasks = load_tasks()
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    extra = json.loads(a.extra)
    done = set()
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes():
            sys.exit("the code or tasks changed since this run started; start a new run instead")
        for line in open(out / "traces.jsonl", encoding="utf-8"):
            r = json.loads(line)
            done.add((r["seed"], r["id"], r["cond"]))
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        out.mkdir(parents=True)
        manifest = {
            "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": {"tag": a.model, **ch01.server_info(a.base_url, a.model)},
            "server": {"base_url": a.base_url},
            "machine": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.processor()},
            "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)),
                         "v2_again_seeds": list(range(101, 101 + a.seeds)), "extra": extra,
                         "tasks": [t["id"] for t in tasks], **AGENT_KW},
            "prompts": {"agent_system": SYSTEM + FINAL},
            "sha256": hashes(),
        }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))

    clients = {}
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for seed, t, cond, sent in plan(tasks, a.seeds):
            if (seed, t["id"], cond) in done:
                continue
            if sent not in clients:
                clients[sent] = ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature,
                                           seed=sent, extra=extra)
            tools = TOOLS_V1 if cond == "v1" else TOOLS
            t0 = time.time()
            res = Agent(clients[sent], tools=tools, system=SYSTEM + FINAL, **AGENT_KW).run(t["task"])
            ok = score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
            row = {"seed": seed, "sent_seed": sent, "cond": cond, "id": t["id"], "set": t["set"],
                   "cluster": t["cluster"], "status": res.status, "ok": ok, "steps": res.steps,
                   "tokens": res.tokens, "seconds": round(time.time() - t0, 2),
                   "answer": res.answer, "detail": res.detail}
            traces.write(json.dumps({**row, "trace": res.trace}) + "\n")
            traces.flush()
            mark = {True: "OK ", False: "BAD", None: "?  "}[ok]
            print(f"{seed} {cond:8} {t['id']:15} {res.status:11} {mark} steps={res.steps} "
                  f"tok={res.tokens} {row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\nwrote {out}. Unscored answers have no 'Final answer:' line: read and label them.")


if __name__ == "__main__":
    main()
