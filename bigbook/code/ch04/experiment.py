"""Long tasks under a context budget: does compaction keep the facts that dropping old turns loses?

  full    : send the whole history (Chapter 1), with no budget
  drop    : over the budget, drop the oldest turns
  compact : over the budget, send a model-written summary of the oldest turns instead
  mask    : over the budget, blank the oldest tool observations (only with --conds)

The 30 tasks (tasks_long.json, from make_handbook.py) each need three to five trips from the trip
log, each trip's rates, and arithmetic across them, so the history outgrows the budget part way.
The conditions are interleaved task by task, as in Chapter 3. The budget is a setting: pick it from
a smoke run so that most full runs cross it once or twice, and record it in the manifest.

Usage (from this folder):
  python experiment.py --out results/my-smoke --seeds 1 --tasks meals_emp0103 --budget 3000
  python experiment.py --out results/my-run --budget 3000          # 30 tasks, 3 seeds, 3 conditions
  python experiment.py --out results/my-run --resume

A resume takes every setting from the run's manifest, refuses any argument that disagrees with it,
and refuses if the code, the handbook or the model's digest has changed. Every run also refuses
to start unless the server's context window is at least WINDOW tokens, and a resume unless it is
the run's own: Ollama cuts longer prompts silently.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
import urllib.request
from pathlib import Path

from context import POLICIES, ContextClient, coverage
from handbook_tools import TOOLS

HERE = Path(__file__).parent
CH01, CH03 = HERE.parent / "ch01", HERE.parent / "ch03"
sys.path.insert(0, str(CH01))
sys.path.append(str(CH03))
from agent import SYSTEM, Agent                          # noqa: E402
from llm import ChatClient                               # noqa: E402
from score import score                                  # noqa: E402  Chapter 3's scorer

_spec = importlib.util.spec_from_file_location("ch01_experiment", CH01 / "experiment.py")
ch01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch01)                           # Chapter 1's prompt suffix and server_info
FINAL = ch01.FINAL
CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py", "experiment.py")},
        "ch03/score.py": CH03 / "score.py",
        **{f"ch04/{f}": HERE / f for f in ("experiment.py", "context.py", "handbook_tools.py",
                                           "make_handbook.py", "tasks_long.json")}}
AGENT_KW = {"max_steps": 30, "max_tokens": 120_000, "max_obs_chars": 2_000, "hints": True}
WINDOW = 32_768          # the server's context window must be at least this; Ollama's default is 4,096


def plan(tasks, seeds, conds):
    return [(s, t, c) for s in range(1, seeds + 1) for t in tasks for c in conds]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return ({k: sha256(p) for k, p in CODE.items()}
            | {f"handbook/{p.name}": sha256(p) for p in sorted((HERE / "handbook").glob("*"))})


def window(base_url, model):
    """The context window the server loaded the model with (Ollama's native API), or None.

    Ollama cuts a prompt longer than its window without an error, so a history that outgrows the
    window would be cut by the server, not by the policy under test. Loading the model first makes
    /api/ps report it."""
    root = base_url.rsplit("/v1", 1)[0]
    try:
        req = urllib.request.Request(root + "/api/generate", json.dumps({"model": model}).encode(),
                                     {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=300).read()
        with urllib.request.urlopen(root + "/api/ps", timeout=10) as r:
            m = [x for x in json.load(r)["models"] if x["name"] == model]
        return m[0].get("context_length") if m else None
    except Exception:
        return None


def check_window(base_url, model, want=None):
    """Exit unless the window is known and large enough (and, on resume, the run's own)."""
    n = window(base_url, model)
    if n is None or n < WINDOW:
        sys.exit(f"the server's context window is {n}, not at least {WINDOW:,}: restart it with "
                 f"OLLAMA_CONTEXT_LENGTH={WINDOW} (see the README)")
    if want is not None and n != want:
        sys.exit(f"the server's context window is {n:,}, not the run's {want:,}")
    return n


DEFAULTS = {"conds": "full,drop,compact", "model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1",
            "extra": '{"reasoning_effort": "none"}', "seeds": 3, "temperature": 0.7, "tasks": ""}


def from_manifest(a, manifest):
    """On resume: the run's own settings, or exit if an argument given now disagrees with them."""
    s = manifest["settings"]
    was = {"budget": s["budget"], "conds": ",".join(s["conds"]), "model": manifest["model"]["tag"],
           "base_url": manifest["server"]["base_url"], "extra": s["extra"], "seeds": len(s["seeds"]),
           "temperature": s["temperature"], "tasks": ",".join(s["tasks"])}
    now = {k: getattr(a, k) for k in was}
    now["extra"] = json.loads(now["extra"]) if now["extra"] is not None else None
    clash = [k for k, v in now.items() if v is not None and v != was[k] and not (k == "tasks" and v == "")]
    if clash:
        sys.exit("these arguments disagree with the run's manifest: " + ", ".join(
            f"--{k.replace('_', '-')} {now[k]!r} (the run used {was[k]!r})" for k in clash))
    for k, v in was.items():
        setattr(a, k, json.dumps(v) if k == "extra" else v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--budget", type=int, help="estimated prompt tokens per call (required for a new run)")
    ap.add_argument("--conds", help=f"default {DEFAULTS['conds']}")
    ap.add_argument("--model", help=f"default {DEFAULTS['model']}")
    ap.add_argument("--base-url", help=f"default {DEFAULTS['base_url']}")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", help=f"default {DEFAULTS['extra']}")
    ap.add_argument("--seeds", type=int, help=f"default {DEFAULTS['seeds']}")
    ap.add_argument("--temperature", type=float, help=f"default {DEFAULTS['temperature']}")
    ap.add_argument("--tasks", help="comma-separated task ids (default: all)")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out")
    a = ap.parse_args()

    out = HERE / a.out
    done = set()
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes():
            sys.exit("the code or tasks changed since this run started; start a new run instead")
        from_manifest(a, manifest)
        digest = ch01.server_info(a.base_url, a.model).get("digest")
        if digest is None or digest != manifest["model"].get("digest"):   # can't confirm: don't mix
            sys.exit(f"the model's digest is {digest}, not the run's {manifest['model'].get('digest')}")
        check_window(a.base_url, a.model, manifest["server"].get("window"))
        for line in open(out / "traces.jsonl", encoding="utf-8"):
            r = json.loads(line)
            done.add((r["seed"], r["id"], r["cond"]))
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        if a.budget is None:
            sys.exit("--budget is required for a new run")
        for k, v in DEFAULTS.items():
            if getattr(a, k) is None:
                setattr(a, k, v)
    conds = a.conds.split(",")
    tasks = json.loads((HERE / "tasks_long.json").read_text(encoding="utf-8"))
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    extra = json.loads(a.extra)
    if not a.resume:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        n = check_window(a.base_url, a.model)
        out.mkdir(parents=True)
        manifest = {
            "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": {"tag": a.model, **ch01.server_info(a.base_url, a.model)},
            "server": {"base_url": a.base_url, "window": n},
            "machine": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.processor()},
            "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)), "extra": extra,
                         "budget": a.budget, "conds": conds, "tasks": [t["id"] for t in tasks], **AGENT_KW},
            "prompts": {"agent_system": SYSTEM + FINAL, "summary": POLICIES["compact"](1).prompt},
            "sha256": hashes(),
        }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))

    clients = {}
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for seed, t, cond in plan(tasks, a.seeds, conds):
            if (seed, t["id"], cond) in done:
                continue
            if seed not in clients:
                clients[seed] = ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature,
                                           seed=seed, extra=extra)
            policy = POLICIES[cond](None if cond == "full" else a.budget)
            client = ContextClient(clients[seed], policy)
            t0 = time.time()
            res = Agent(client, tools=TOOLS, system=SYSTEM + FINAL, **AGENT_KW).run(t["task"])
            ok = score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
            spent = [e["summary_tokens"] for e in policy.events if "summary_tokens" in e]
            row = {"seed": seed, "cond": cond, "id": t["id"], "cluster": t["cluster"], "status": res.status,
                   "ok": ok, "steps": res.steps, "tokens": res.tokens + client.unbilled,
                   "seconds": round(time.time() - t0, 2),
                   "answer": res.answer, "detail": res.detail, "budget": a.budget,
                   "triggers": len(policy.events), "max_sent": max((c["estimated"] for c in client.calls), default=0),
                   "max_prompt": max((c["prompt_tokens"] or 0 for c in client.calls), default=0),
                   "calls": len(client.calls), "over_calls": sum(c["over"] for c in client.calls),
                   "summary_tokens": sum(s for s in spent if isinstance(s, int)),
                   "summary_unknown": sum(s == "unknown" for s in spent),
                   "summary_failures": sum("error" in e and "input" in e for e in policy.events),
                   "facts": len(t["facts"]),
                   "coverage": [coverage(e["summary"], e["input"], t["facts"])
                                for e in policy.events if "summary" in e]}
            traces.write(json.dumps({**row, "events": policy.events, "call_log": client.calls,
                                     "trace": res.trace}) + "\n")
            traces.flush()
            mark = {True: "OK ", False: "BAD", None: "?  "}[ok]
            print(f"{seed} {cond:7} {t['id']:16} {res.status:11} {mark} steps={res.steps} tok={res.tokens} "
                  f"triggers={row['triggers']} max_sent={row['max_sent']} over={row['over_calls']}/{row['calls']} "
                  f"{row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\nwrote {out}. Unscored answers have no 'Final answer:' line: read and label them.")


if __name__ == "__main__":
    main()
