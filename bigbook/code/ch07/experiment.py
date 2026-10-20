"""Chapter 7's experiment: a fixed pipeline, a loop with a bare shell, and a loop with an ACI, on the
same 24 bugs.

Each task (tasks.json) starts from a fresh copy of the repository with the bug in it and its
FAIL_TO_PASS tests taken out; each arm gets the issue and works in its own copy; the grader then
runs both test lists on a fresh copy with tests/ put back (tasks.grade). Arms are interleaved
within each repeat, so a slow drift in the server touches all three alike. Five repeats give
pass@1, pass@5 and pass^5 per arm (Chapter 3).

  agentless   agentless.run: 2 calls to localise, SAMPLES calls to repair, then the visible tests
  shell       Chapter 1's agent with harness.shell_tools
  aci         Chapter 1's agent with harness.aci_tools, and harness.Collapsed on its client

Every arm runs code the model wrote: the shell arm its commands, all three the code it edits,
when the tests run. The experiment therefore refuses to start without --run-model-code; read
README.md on where to run it first.

Usage (from this folder):
  python experiment.py --run-model-code --out results/my-smoke --repeats 1 --tasks dates_saturday
  python experiment.py --run-model-code --out results/my-run
  python experiment.py --run-model-code --out results/my-run --resume
"""
import argparse
import importlib.util
import json
import platform
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
CH01, CH03, CH05 = (HERE.parent / f"ch0{i}" for i in (1, 3, 5))
sys.path.insert(0, str(CH01))
sys.path.append(str(CH05))
from agent import Agent                                  # noqa: E402  Chapter 1's
from llm import ChatClient                               # noqa: E402  Chapter 1's
from durable import Halted, read_jsonl                   # noqa: E402  Chapter 5's
from faults import RetryingClient                        # noqa: E402  Chapter 5's
from strategies import Meter                             # noqa: E402  Chapter 5's

_spec = importlib.util.spec_from_file_location("ch05_experiment", CH05 / "experiment.py")
ch05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch05)                           # write_atomic, sha256, Chapter 4's server checks
ch04 = ch05.ch04
sys.path.insert(0, str(HERE))
import agentless                                         # noqa: E402
import harness                                           # noqa: E402
import tasks                                             # noqa: E402

ARMS = ("agentless", "shell", "aci")
LOOP = {"max_steps": 20, "max_tokens": 400_000, "max_obs_chars": 4_000}
RETRY = ch05.RETRY
CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py")},
        **{f"ch05/{f}": CH05 / f for f in ("experiment.py", "durable.py", "faults.py", "strategies.py")},
        **{f"ch07/{f}": HERE / f for f in ("experiment.py", "tasks.py", "tasks.json", "runner.py",
                                           "harness.py", "agentless.py")},
        **{f"ch07/{p.relative_to(HERE).as_posix()}": p for p in sorted((HERE / "repo").rglob("*"))
           if p.is_file() and "__pycache__" not in p.parts}}
DEFAULTS = {"model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1",
            "extra": '{"reasoning_effort": "none"}', "repeats": 5, "temperature": 0.7, "tasks": "all"}


class Halting:
    """A model call that still fails after its retries stops the experiment (durable.Halted is a
    BaseException, so Chapter 1's agent can't record it as a failed run and carry on)."""

    def __init__(self, client):
        self.client = client

    def chat(self, messages, tools=None):
        try:
            return self.client.chat(messages, tools)
        except Exception as e:
            raise Halted(f"model call failed: {type(e).__name__}: {e}") from e


def hashes():
    return {k: ch05.sha256(p) for k, p in CODE.items()}


def plan(task_list, repeats):
    return [(r, t, arm) for r in range(1, repeats + 1) for t in task_list for arm in ARMS]


def name(rep, tid, arm):
    return f"{rep}_{tid}_{arm}"


def loop(arm, task, work, client, events):
    tools = harness.shell_tools(work, events) if arm == "shell" else harness.aci_tools(work, events)
    agent = Agent(client if arm == "shell" else harness.Collapsed(client), tools=tools,
                  system=harness.SYSTEM.format(how=harness.HOW[arm]), **LOOP)
    res = agent.run(harness.task_prompt(task))
    return {"status": res.status, "steps": res.steps, "answer": res.answer, "detail": res.detail,
            "trace": res.trace}


def one(out, rep, task, arm, clients):
    """One run in its own folder under work/; returns the row for traces.jsonl."""
    rid = name(rep, task["id"], arm)
    work = out / "work" / rid
    for p in (work, work.parent / (work.name + ".tmp")):     # left by a run that was killed
        shutil.rmtree(p, ignore_errors=True)
    tasks.start(task, work)
    before = out / "work" / (rid + ".start")
    shutil.rmtree(before, ignore_errors=True)
    tasks.copy_repo(work, before)
    events, meters = [], [Meter(c) for c in clients]
    t0 = time.time()
    if arm == "agentless":
        info = agentless.run(task, work, meters[0], meters[1:], events)
        res = {"status": "chosen" if info["chosen"] is not None else "no_patch", "steps": len(info["calls"]),
               "answer": "", "detail": "", "trace": info}
    else:
        res = loop(arm, task, work, meters[0], events)
    seconds = time.time() - t0
    verdict = tasks.grade(task, work)
    patch = tasks.diff(before, work)
    shutil.rmtree(before, ignore_errors=True)
    return {"rep": rep, "id": task["id"], "module": task["file"], "arm": arm, **verdict,
            "f2p_of": len(task["FAIL_TO_PASS"]), "p2p_of": len(task["PASS_TO_PASS"]),
            "status": res["status"], "steps": res["steps"], "detail": res["detail"], "answer": res["answer"],
            "patch": patch, "suspect": tasks.suspect(patch), "touched": sorted({line[6:].split("\t")[0] for line in patch.splitlines()
                                               if line.startswith("+++ b/")}),
            "events": events, "trace": res["trace"],
            "calls": sum(m.calls for m in meters), "tokens": sum(m.tokens for m in meters),
            "seconds": round(seconds, 2)}


def from_manifest(a, m):
    s = m["settings"]
    was = {"model": m["model"]["tag"], "base_url": m["server"]["base_url"], "extra": s["extra"],
           "repeats": len(s["repeats"]), "temperature": s["temperature"], "tasks": ",".join(s["tasks"])}
    now = {k: getattr(a, k) for k in was}
    now["extra"] = json.loads(now["extra"]) if now["extra"] is not None else None
    clash = [k for k, v in now.items() if v is not None and v != was[k]]
    if clash:
        sys.exit("these arguments disagree with the run's manifest: " + ", ".join(
            f"--{k.replace('_', '-')} {now[k]!r} (the run used {was[k]!r})" for k in clash))
    for k, v in was.items():
        setattr(a, k, json.dumps(v) if k == "extra" else v)


def clients_for(a, rep, extra):
    """The client that drives an arm, and one more per repair sample, each with its own seed."""
    def make(seed):
        return Halting(RetryingClient(ChatClient(a.model, a.base_url, a.api_key, seed=seed,
                                                 temperature=a.temperature, extra=extra), **RETRY))
    return [make(rep)] + [make(1000 * rep + i) for i in range(1, agentless.SAMPLES + 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--run-model-code", action="store_true",
                    help="confirm that this machine is the place to run code the model writes (README.md)")
    ap.add_argument("--model", help=f"default {DEFAULTS['model']}")
    ap.add_argument("--base-url", help=f"default {DEFAULTS['base_url']}")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", help=f"default {DEFAULTS['extra']}")
    ap.add_argument("--repeats", type=int, help=f"default {DEFAULTS['repeats']}")
    ap.add_argument("--temperature", type=float, help=f"default {DEFAULTS['temperature']}")
    ap.add_argument("--tasks", help="comma-separated task ids (default: all of tasks.json)")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out")
    a = ap.parse_args()
    if not a.run_model_code:
        sys.exit("every arm runs code the model writes; read README.md, then add --run-model-code")

    out = HERE / a.out
    rows = {}
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes():
            sys.exit("the code, the tasks or the repository changed since this run started; start a new run")
        from_manifest(a, manifest)
        digest = ch04.ch01.server_info(a.base_url, a.model).get("digest")
        if digest is None or digest != manifest["model"].get("digest"):
            sys.exit(f"the model's digest is {digest}, not the run's {manifest['model'].get('digest')}")
        ch04.check_window(a.base_url, a.model, manifest["server"].get("window"))
        for r in read_jsonl(out / "traces.jsonl")[0]:    # a row cut off by a kill is dropped; that run starts again
            rows[(r["rep"], r["id"], r["arm"])] = r
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        for k, v in DEFAULTS.items():
            if getattr(a, k) is None:
                setattr(a, k, v)
    every = tasks.load()
    want = [t["id"] for t in every] if a.tasks == "all" else a.tasks.split(",")
    task_list = [t for t in every if t["id"] in want]
    if len(task_list) != len(want):
        sys.exit(f"unknown task ids: {sorted(set(want) - {t['id'] for t in every})}")
    extra = json.loads(a.extra)
    if not a.resume:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        n = ch04.check_window(a.base_url, a.model)
        (out / "work").mkdir(parents=True)
        manifest = {
            "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": {"tag": a.model, **ch04.ch01.server_info(a.base_url, a.model)},
            "server": {"base_url": a.base_url, "window": n},
            "machine": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.processor(), "shell": harness.SHELL},
            "settings": {"temperature": a.temperature, "repeats": list(range(1, a.repeats + 1)), "extra": extra,
                         "tasks": [t["id"] for t in task_list], "arms": list(ARMS), "loop": LOOP,
                         "samples": agentless.SAMPLES, "retry": RETRY, "command_seconds": harness.COMMAND_SECONDS,
                         "test_seconds": tasks.TIMEOUT},
            "prompts": {"system": harness.SYSTEM, "how": harness.HOW, "file": agentless.FILE,
                        "element": agentless.ELEMENT, "repair": agentless.REPAIR},
            "deny": harness.DENY + [harness.POSIX_ABSOLUTE],
            "sha256": hashes(),
        }
    ch05.write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))

    clients = {}
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for rep, t, arm in plan(task_list, a.repeats):
            key = (rep, t["id"], arm)
            if key in rows:
                continue
            if rep not in clients:
                clients[rep] = clients_for(a, rep, extra)
            try:
                row = one(out, rep, t, arm, clients[rep])
            except Halted as e:
                sys.exit(f"{rep} {t['id']} {arm} stopped: {e}\nNo row was written for it. "
                         f"When the server is back: python experiment.py --run-model-code --out {a.out} --resume")
            rows[key] = row
            traces.write(json.dumps(row) + "\n")
            traces.flush()
            kinds = {e["kind"] for e in row["events"]}
            print(f"{rep} {t['id']:22} {arm:9} {row['status']:11} {'FIXED' if row['resolved'] else '-----'} "
                  f"f2p={row['f2p']}/{len(t['FAIL_TO_PASS'])} p2p={row['p2p']}/{len(t['PASS_TO_PASS'])} "
                  f"steps={row['steps']} refused={'refused' in kinds} tests={'tests_changed' in kinds} "
                  f"suspect={len(row['suspect'])} tok={row['tokens']} {row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ch05.write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    print(f"\nwrote {out}.")


if __name__ == "__main__":
    main()
