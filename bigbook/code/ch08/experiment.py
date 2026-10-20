"""Chapter 8's experiment: one agent, an orchestrator with workers, and a fixed pipeline, on 36 tasks.

  compare : single, orchestrator and pipeline (strategies.py) on every task of tasks.json, five
            seeds, interleaved task by task as in Chapter 3
  a2a     : for seed 1, the orchestrator on 12 tasks (two of each kind) with its workers behind the
            localhost A2A server (a2a.py), to check the protocol carries the same work

Usage (from this folder):
  python experiment.py --out results/my-smoke --seeds 1 --tasks meals_emp0140,chain_meals_tr0067
  python experiment.py --out results/my-pilot --seeds 2 --tasks <five ids> --parts compare
  python experiment.py --out results/my-run                 # 540 + 12 runs
  python experiment.py --out results/my-run --resume

Each finished run is one row of traces.jsonl, and every agent's trace (lead, workers, splitter,
parts) goes to runs/<run>.json for labelling. A run whose model call raised (the server went away or
timed out) stops the experiment with no row written; --resume then makes that run again from the
start. A resume takes every setting from the manifest, refuses if the code, the tasks, the handbook
or the model's digest has changed, and refuses unless the server's context window is the run's own.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
CH01, CH03, CH04 = HERE.parent / "ch01", HERE.parent / "ch03", HERE.parent / "ch04"
sys.path.insert(0, str(CH01))
sys.path.insert(1, str(CH04))
from handbook_tools import TOOLS                         # noqa: E402  Chapter 1's tools on Chapter 4's handbook
sys.path.insert(0, str(HERE))
sys.path.append(str(CH03))
import a2a                                               # noqa: E402
import strategies as S                                   # noqa: E402
from llm import ChatClient                               # noqa: E402  Chapter 1's
from score import score                                  # noqa: E402  Chapter 3's scorer

_spec = importlib.util.spec_from_file_location("ch04_experiment", CH04 / "experiment.py")
ch04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch04)                           # server_info (Chapter 1's) and the window check
sys.path.insert(0, str(HERE))

CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py")},
        "ch03/score.py": CH03 / "score.py",
        **{f"ch04/{f}": CH04 / f for f in ("handbook_tools.py", "make_handbook.py", "tasks_long.json", "experiment.py")},
        **{f"ch08/{f}": HERE / f for f in ("experiment.py", "strategies.py", "a2a.py", "make_tasks.py", "tasks.json")}}
CONDS = ["single", "orchestrator", "pipeline"]
DEFAULTS = {"model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1",
            "extra": '{"reasoning_effort": "none"}', "seeds": 5, "temperature": 0.7, "tasks": "",
            "parts": "compare,a2a"}


class Halted(Exception):
    pass


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return ({k: sha256(p) for k, p in CODE.items()}
            | {f"handbook/{p.name}": sha256(p) for p in sorted((CH04 / "handbook").glob("*"))})


def write_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def a2a_tasks(tasks):
    """Two tasks of each kind, the first two in the file."""
    out, seen = [], {}
    for t in tasks:
        seen[t["cluster"]] = seen.get(t["cluster"], 0) + 1
        if seen[t["cluster"]] <= 2:
            out.append(t)
    return out


def plan(tasks, seeds, parts):
    out = []
    if "compare" in parts:
        out += [("compare", s, t, c) for s in range(1, seeds + 1) for t in tasks for c in CONDS]
    if "a2a" in parts:
        out += [("a2a", 1, t, "orchestrator") for t in a2a_tasks(tasks)]
    return out


def name(part, seed, tid, cond):
    return f"{part}_{seed}_{tid}_{cond}"


def one(part, seed, t, cond, client):
    """One run; returns (row, traces). Raises Halted if any model call raised."""
    meter = S.Meter(client)
    t0 = time.time()
    if part == "a2a":
        server = a2a.Server(lambda text: S.work(text, meter, TOOLS)).start()
        try:
            out = S.orchestrator(t["task"], meter, TOOLS, send=a2a.Client(server.url).sender(server.traces))
        finally:
            server.stop()
        wire = server.log
    else:
        out = S.STRATEGIES[cond](t["task"], meter, TOOLS)
        wire = None
    if meter.errors:
        raise Halted(meter.errors[0])
    ok = score(out.answer, t["answer"], t["units"]) if out.answer else False
    row = {"part": part, "seed": seed, "cond": cond, "id": t["id"], "set": t["set"], "cluster": t["cluster"],
           "status": out.status, "ok": ok, "answer": out.answer, "detail": out.detail,
           "calls": meter.calls, "tokens": meter.tokens, "seconds": round(time.time() - t0, 2),
           "agents": len(out.traces), "info": {k: v for k, v in out.info.items() if k != "errors"}}
    if wire is not None:
        row["wire"] = {"requests": len(wire), "posts": sum(w["method"] != "GET agent card" for w in wire),
                       "errors": sum(w["error"] is not None for w in wire),
                       "json_bytes": sum(w["bytes_in"] + w["bytes_out"] for w in wire)}   # bodies, not headers
    return row, out.traces


def from_manifest(a, m):
    s = m["settings"]
    was = {"model": m["model"]["tag"], "base_url": m["server"]["base_url"], "extra": s["extra"],
           "seeds": len(s["seeds"]), "temperature": s["temperature"], "tasks": ",".join(s["tasks"]),
           "parts": ",".join(s["parts"])}
    now = {k: getattr(a, k) for k in was}
    now["extra"] = json.loads(now["extra"]) if now["extra"] is not None else None
    clash = [k for k, v in now.items() if v is not None and v != was[k] and not (k == "tasks" and v == "")]
    if clash:
        sys.exit("these arguments disagree with the run's manifest: " + ", ".join(
            f"--{k.replace('_', '-')} {now[k]!r} (the run used {was[k]!r})" for k in clash))
    for k, v in was.items():
        setattr(a, k, json.dumps(v) if k == "extra" else v)


def read_rows(path):
    """Rows of traces.jsonl; a torn last line (a kill mid-write) is dropped, and that run is made again."""
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                break
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--model", help=f"default {DEFAULTS['model']}")
    ap.add_argument("--base-url", help=f"default {DEFAULTS['base_url']}")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", help=f"default {DEFAULTS['extra']}")
    ap.add_argument("--seeds", type=int, help=f"default {DEFAULTS['seeds']}")
    ap.add_argument("--temperature", type=float, help=f"default {DEFAULTS['temperature']}")
    ap.add_argument("--tasks", help="comma-separated task ids (default: all)")
    ap.add_argument("--parts", help=f"default {DEFAULTS['parts']}")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out")
    a = ap.parse_args()

    out = HERE / a.out
    rows = {}
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes():
            sys.exit("the code, tasks or handbook changed since this run started; start a new run instead")
        from_manifest(a, manifest)
        digest = ch04.ch01.server_info(a.base_url, a.model).get("digest")
        if digest is None or digest != manifest["model"].get("digest"):
            sys.exit(f"the model's digest is {digest}, not the run's {manifest['model'].get('digest')}")
        ch04.check_window(a.base_url, a.model, manifest["server"].get("window"))
        good = read_rows(out / "traces.jsonl")
        write_atomic(out / "traces.jsonl", "".join(json.dumps(r) + "\n" for r in good))
        for r in good:
            rows[(r["part"], r["seed"], r["id"], r["cond"])] = r
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        for k, v in DEFAULTS.items():
            if getattr(a, k) is None:
                setattr(a, k, v)
    parts = a.parts.split(",")
    tasks = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    extra = json.loads(a.extra)
    if not a.resume:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        n = ch04.check_window(a.base_url, a.model)
        (out / "runs").mkdir(parents=True)
        manifest = {
            "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": {"tag": a.model, **ch04.ch01.server_info(a.base_url, a.model)},
            "server": {"base_url": a.base_url, "window": n},
            "machine": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.processor()},
            "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)), "extra": extra,
                         "tasks": [t["id"] for t in tasks], "parts": parts, "conds": CONDS,
                         "agent": S.AGENT_KW, "lead": S.LEAD_KW, "worker": S.WORKER_KW, "split": S.SPLIT_KW,
                         "max_workers": S.MAX_WORKERS, "max_tokens": S.MAX_TOKENS},
            "prompts": {"lead": S.LEAD, "contract": S.CONTRACT, "worker": S.WORKER, "split": S.SPLIT,
                        "part": S.PART, "part_worker": S.PART_WORKER, "final": S.FINAL},
            "sha256": hashes(),
        }
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))

    clients = {}
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for part, seed, t, cond in plan(tasks, a.seeds, parts):
            key = (part, seed, t["id"], cond)
            if key in rows:
                continue
            if seed not in clients:
                clients[seed] = ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature,
                                           seed=seed, extra=extra)
            try:
                row, agent_traces = one(part, seed, t, cond, clients[seed])
            except Halted as e:
                sys.exit(f"{part} {seed} {cond} {t['id']} stopped: {e}\nNo row was written. When the server "
                         f"is back: python experiment.py --out {a.out} --resume")
            write_atomic(out / "runs" / f"{name(*key)}.json", json.dumps(agent_traces))
            rows[key] = row
            traces.write(json.dumps(row) + "\n")
            traces.flush()
            mark = {True: "OK ", False: "BAD", None: "?  "}[row["ok"]]
            print(f"{part:7} {seed} {cond:12} {t['id']:22} {row['status']:12} {mark} agents={row['agents']} "
                  f"calls={row['calls']} tok={row['tokens']} {row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    print(f"\nwrote {out}. Unscored answers have no 'Final answer:' line: read and label them.")


if __name__ == "__main__":
    main()
