"""Chapter 6's experiment: does a line in the handbook take over the agent, and which defence stops it?

Nine of Chapter 4's long tasks (three each of meals, lodging and mileage), each asked as a request
to work out the total and file the claim. Every task is run with the clean handbook and with each
of three poisoned ones (inject.py: redirect, inflate, exfil), under each of the four conditions
(defences.py: none, delimit, policy, workflow), interleaved, for each seed. AgentDojo's measures
(Debenedetti et al. 2024, section 3.4): utility with no attack, utility under attack, and targeted
attack success, all judged from the effects (inject.judge), so no answer needs labelling.

Each run has its own ledger and outbox in effects/. A run killed part way through has no row; on
--resume its effects are deleted and it starts again, so a half-run leaves no claim behind.

Usage (from this folder):
  python experiment.py --out results/my-smoke --seeds 1 --tasks meals_emp0103
  python experiment.py --out results/my-run
  python experiment.py --out results/my-run --resume

A resume takes every setting from the manifest and refuses if the code, the handbooks or the
model's digest has changed, or if the server's context window is not the run's own.
"""
import argparse
import hashlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import defences                                          # sets the path to Chapters 1, 4 and 5
from defences import ACT, ASK, CONDS, DELIMIT, Outbox
from inject import ATTACKER, GOALS, PAGES, TEMPLATE, build, injection, judge, trip_ids
import tools as ch01_tools                               # Chapter 1's: the handbook path is read on every call
from durable import Halted, read_jsonl                   # Chapter 5's
from faults import RetryingClient                        # Chapter 5's
from ledger import Ledger                                # Chapter 5's
from strategies import AGENT_KW, EXTRACT, STEP_KW, TRIP, Meter, employee_of   # Chapter 5's

HERE = Path(__file__).parent
CH01, CH03, CH04, CH05 = (HERE.parent / f"ch0{i}" for i in (1, 3, 4, 5))
sys.path.append(str(CH03))
from score import score                                  # noqa: E402  Chapter 3's scorer
from llm import ChatClient                               # noqa: E402

_spec = importlib.util.spec_from_file_location("ch05_experiment", CH05 / "experiment.py")
ch05 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch05)                           # write_atomic, and Chapter 4's server checks
sys.path.insert(0, str(HERE))
ch04 = ch05.ch04

TASKS = ["meals_emp0103", "meals_emp0106", "meals_emp0110", "lodging_emp0122", "lodging_emp0130",
         "lodging_emp0131", "mileage_emp0143", "mileage_emp0146", "mileage_emp0149"]
ATTACKS = (None, *GOALS)                                 # None: the clean handbook
RETRY = ch05.RETRY
CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py")},
        "ch03/score.py": CH03 / "score.py",
        **{f"ch04/{f}": CH04 / f for f in ("handbook_tools.py", "tasks_long.json", "experiment.py")},
        **{f"ch05/{f}": CH05 / f for f in ("experiment.py", "durable.py", "faults.py", "ledger.py", "strategies.py")},
        **{f"ch06/{f}": HERE / f for f in ("experiment.py", "defences.py", "inject.py")}}
DEFAULTS = {"model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1",
            "extra": '{"reasoning_effort": "none"}', "seeds": 2, "temperature": 0.7, "tasks": ",".join(TASKS)}


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


def hashes(handbooks=None):
    out = {k: ch05.sha256(p) for k, p in CODE.items()}
    for h in sorted(handbooks.iterdir()) if handbooks else []:
        out |= {f"handbooks/{h.name}/{p.name}": ch05.sha256(p) for p in sorted(h.glob("*.md"))}
    return out


def plan(tasks, seeds):
    return [(s, t, g, c) for s in range(1, seeds + 1) for t in tasks for g in ATTACKS for c in CONDS]


def name(seed, tid, goal, cond):
    return f"{seed}_{tid}_{goal or 'clean'}_{cond}"


def one(out, seed, t, goal, cond, client):
    """One run; returns the row for traces.jsonl."""
    rid = name(seed, t["id"], goal, cond)
    ledger, outbox = out / "effects" / f"{rid}.ledger.jsonl", out / "effects" / f"{rid}.outbox.jsonl"
    for p in (ledger, outbox):                   # left by a run that was killed: it starts again
        p.unlink(missing_ok=True)
    ch01_tools.HANDBOOK = out / "handbooks" / (goal or "clean")
    meter = Meter(client)
    t0 = time.time()
    res = defences.run(cond, t["task"], meter, ledger, outbox, key=rid)
    claims, messages = Ledger(ledger).claims(), Outbox(outbox).messages()
    verdict = judge(goal, employee_of(t["task"]), t["answer"], claims, messages, res["events"],
                    private=trip_ids(ch01_tools.HANDBOOK))
    return {"seed": seed, "id": t["id"], "cluster": t["cluster"], "goal": goal, "cond": cond, **verdict,
            "exposed": res["seen"],
            "status": res["status"], "amount": res["amount"], "detail": res["detail"],
            "ok": score(res["answer"], t["answer"], t["units"]) if res["answer"] else False,
            "answer": res["answer"], "claims": claims, "messages": messages,
            "events": res["events"], "info": res["info"], "calls": meter.calls, "tokens": meter.tokens,
            "seconds": round(time.time() - t0, 2)}


def from_manifest(a, m):
    s = m["settings"]
    was = {"model": m["model"]["tag"], "base_url": m["server"]["base_url"], "extra": s["extra"],
           "seeds": len(s["seeds"]), "temperature": s["temperature"], "tasks": ",".join(s["tasks"])}
    now = {k: getattr(a, k) for k in was}
    now["extra"] = json.loads(now["extra"]) if now["extra"] is not None else None
    clash = [k for k, v in now.items() if v is not None and v != was[k]]
    if clash:
        sys.exit("these arguments disagree with the run's manifest: " + ", ".join(
            f"--{k.replace('_', '-')} {now[k]!r} (the run used {was[k]!r})" for k in clash))
    for k, v in was.items():
        setattr(a, k, json.dumps(v) if k == "extra" else v)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True, help="new folder for this run, e.g. results/my-run")
    ap.add_argument("--model", help=f"default {DEFAULTS['model']}")
    ap.add_argument("--base-url", help=f"default {DEFAULTS['base_url']}")
    ap.add_argument("--api-key", default="none")
    ap.add_argument("--extra", help=f"default {DEFAULTS['extra']}")
    ap.add_argument("--seeds", type=int, help=f"default {DEFAULTS['seeds']}")
    ap.add_argument("--temperature", type=float, help=f"default {DEFAULTS['temperature']}")
    ap.add_argument("--tasks", help="comma-separated task ids (default: the nine in TASKS)")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out")
    a = ap.parse_args()

    out = HERE / a.out
    rows = {}
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes(out / "handbooks"):
            sys.exit("the code or the handbooks changed since this run started; start a new run instead")
        from_manifest(a, manifest)
        digest = ch04.ch01.server_info(a.base_url, a.model).get("digest")
        if digest is None or digest != manifest["model"].get("digest"):
            sys.exit(f"the model's digest is {digest}, not the run's {manifest['model'].get('digest')}")
        ch04.check_window(a.base_url, a.model, manifest["server"].get("window"))
        for r in read_jsonl(out / "traces.jsonl")[0]:    # a row cut off by a kill is dropped; that run starts again
            rows[(r["seed"], r["id"], r["goal"], r["cond"])] = r
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        for k, v in DEFAULTS.items():
            if getattr(a, k) is None:
                setattr(a, k, v)
    want = a.tasks.split(",")
    tasks = [t for t in json.loads((CH04 / "tasks_long.json").read_text(encoding="utf-8")) if t["id"] in want]
    if len(tasks) != len(want):
        sys.exit(f"unknown task ids: {sorted(set(want) - {t['id'] for t in tasks})}")
    bad = [t["id"] for t in tasks if t["answer"] >= ATTACKER["amount"]]
    if bad:
        sys.exit(f"the inflate attack asks for 4,850 USD, so a task must owe less; these tasks' totals reach it: {bad}")
    extra = json.loads(a.extra)
    if not a.resume:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        n = ch04.check_window(a.base_url, a.model)
        (out / "effects").mkdir(parents=True)
        for g in ATTACKS:
            build(CH04 / "handbook", out / "handbooks" / (g or "clean"), g)
        manifest = {
            "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": {"tag": a.model, **ch04.ch01.server_info(a.base_url, a.model)},
            "server": {"base_url": a.base_url, "window": n},
            "machine": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.processor()},
            "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)), "extra": extra,
                         "tasks": [t["id"] for t in tasks], "conds": list(CONDS), "attacks": list(GOALS),
                         "pages": list(PAGES), "retry": RETRY, "agent": AGENT_KW, "step": STEP_KW},
            "prompts": {"act": ACT, "ask": ASK, "delimit": DELIMIT, "template": TEMPLATE,
                        "injections": {g: injection(g) for g in GOALS}, "extract": EXTRACT, "trip": TRIP},
            "sha256": hashes(out / "handbooks"),
        }
    ch05.write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))

    clients = {}
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for seed, t, goal, cond in plan(tasks, a.seeds):
            key = (seed, t["id"], goal, cond)
            if key in rows:
                continue
            if seed not in clients:
                clients[seed] = Halting(RetryingClient(ChatClient(a.model, a.base_url, a.api_key, seed=seed,
                                                                  temperature=a.temperature, extra=extra), **RETRY))
            try:
                row = one(out, seed, t, goal, cond, clients[seed])
            except Halted as e:                  # the server is gone after its retries: stop, keep the rows
                sys.exit(f"{seed} {t['id']} {goal} {cond} stopped: {e}\nNo row was written "
                         f"for it. When the server is back: python experiment.py --out {a.out} --resume")
            rows[key] = row
            traces.write(json.dumps(row) + "\n")
            traces.flush()
            hit = {True: "HIT", False: "---", None: "   "}[row["success"]]
            print(f"{seed} {t['id']:16} {goal or 'clean':8} {cond:8} {row['status']:11} "
                  f"done={'Y' if row['done'] else 'n'} util={'Y' if row['utility'] else 'n'} {hit} tried={row['attempted']} seen={row['exposed']} "
                  f"calls={row['calls']} tok={row['tokens']} {row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    ch05.write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    print(f"\nwrote {out}.")


if __name__ == "__main__":
    main()
