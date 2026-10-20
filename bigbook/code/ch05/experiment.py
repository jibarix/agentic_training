"""Chapter 5's experiment, in three parts, on Chapter 4's 30 long tasks.

  compare : agent, plan and workflow (strategies.py), every task, three seeds, interleaved
  crash   : for seed 1, each clean run's journal cut at a random call, as a crash leaves it, then
            resumed: is the answer the clean run's, and what does the resume cost?
  faults  : for seed 1, agent and workflow with a fifth of tool calls failing and no retries, so
            the model sees the failures; compared with the clean runs of compare

Every run is durable (run.py): its journal is in journals/, and a run killed part way through
continues from its last recorded call when the experiment is resumed. Every claim goes to the run's
ledger.jsonl with an idempotency key, so a resume can't file a claim twice.

Usage (from this folder):
  python experiment.py --out results/my-smoke --seeds 1 --tasks meals_emp0103 --parts compare
  python experiment.py --out results/my-run                 # all three parts
  python experiment.py --out results/my-run --resume

A call that still fails after its retries (the server went away, say) stops the experiment with
the run's journal kept and no row written; --resume then continues that run from its journal.

A resume takes every setting from the manifest, refuses if the code, the tasks or the model's
digest has changed, and refuses unless the server's context window is the run's own.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import random
import shutil
import sys
import time
from pathlib import Path

from run import durable_run                              # sets the path to Chapters 1 and 4
from durable import Halted, read_jsonl
from faults import Flaky
from ledger import Ledger
from strategies import AGENT_KW, EXTRACT, LAST, MID, PLAN, REPLAN, STEP, STEP_KW, TRIP

HERE = Path(__file__).parent
CH01, CH03, CH04 = HERE.parent / "ch01", HERE.parent / "ch03", HERE.parent / "ch04"
sys.path.append(str(CH03))
from score import score                                  # noqa: E402  Chapter 3's scorer
from llm import ChatClient                               # noqa: E402

_spec = importlib.util.spec_from_file_location("ch04_experiment", CH04 / "experiment.py")
ch04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch04)                           # server_info (Chapter 1's) and the window check
sys.path.insert(0, str(HERE))       # this folder first again: loading Chapter 4's put Chapter 1's first

CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py")},
        "ch03/score.py": CH03 / "score.py",
        **{f"ch04/{f}": CH04 / f for f in ("handbook_tools.py", "make_handbook.py", "tasks_long.json", "experiment.py")},
        **{f"ch05/{f}": HERE / f for f in ("experiment.py", "run.py", "durable.py", "faults.py", "ledger.py",
                                           "strategies.py")}}
CONDS = ["agent", "plan", "workflow"]
FAULT_CONDS = ["agent", "workflow"]
FAULT_P = 0.2
RETRY = {"attempts": 4, "base": 1.0, "cap": 30.0, "budget": 60.0}
DEFAULTS = {"model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1",
            "extra": '{"reasoning_effort": "none"}', "seeds": 3, "temperature": 0.7, "tasks": "",
            "parts": "compare,crash,faults"}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes():
    return ({k: sha256(p) for k, p in CODE.items()}
            | {f"handbook/{p.name}": sha256(p) for p in sorted((CH04 / "handbook").glob("*"))})


def write_atomic(path, text):
    """Write a whole new file, then swap it in: a kill leaves the old file or the new, never half."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def name(part, seed, tid, cond):
    return f"{part}_{seed}_{tid}_{cond}"


def plan(tasks, seeds, parts):
    out = []
    if "compare" in parts:
        out += [("compare", s, t, c) for s in range(1, seeds + 1) for t in tasks for c in CONDS]
    if "crash" in parts:
        out += [("crash", 1, t, c) for t in tasks for c in CONDS]
    if "faults" in parts:
        out += [("faults", 1, t, c) for t in tasks for c in FAULT_CONDS]
    return out


def cut_at(tid, cond, total):
    """The call a crash lands on: seeded by the task and condition, uniform over calls 1 to total-1."""
    rng = random.Random(f"crash/{tid}/{cond}")
    return rng.randrange(1, total) if total > 1 else 0


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


def one(out, part, seed, t, cond, client, clean):
    """One run of the plan; returns the row for traces.jsonl."""
    rid = name(part, seed, t["id"], cond)
    journal, ledger = out / "journals" / f"{rid}.jsonl", out / "ledger.jsonl"
    extra = {}
    kw = {"retry_kw": RETRY}
    if part == "crash":
        src = out / "journals" / f"{name('compare', 1, t['id'], cond)}.jsonl"
        lines = src.read_bytes().splitlines(keepends=True)
        n = cut_at(t["id"], cond, len(lines))
        if not journal.exists():                 # the state a crash at call n leaves behind
            journal.write_bytes(b"".join(lines[:n]))
        extra = {"cut_at": n, "clean_calls": len(lines)}
        ledger = out / "ledger_crash.jsonl"
    if part == "faults":
        kw = {"retry_kw": {**RETRY, "attempts": 1},
              "flaky": Flaky(FAULT_P, seed=f"faults/{t['id']}/{cond}")}
        ledger = out / "ledger_faults.jsonl"
    t0 = time.time()
    res, receipt, run, meter = durable_run(cond, t["task"], client, journal, ledger, rid, **kw)
    entries = run.journal.entries
    ok = score(res.answer, t["answer"], t["units"]) if res.answer else False
    row = {"part": part, "seed": seed, "cond": cond, "id": t["id"], "cluster": t["cluster"],
           "status": res.status, "ok": ok, "amount": res.amount, "answer": res.answer, "detail": res.detail,
           "receipt": receipt, "calls": meter.calls, "journal_calls": run.seq,
           "tool_calls": sum(e["kind"] == "tool" for e in entries), "replayed": run.replayed, "live": run.live,
           "tokens": meter.tokens, "live_tokens": run.live_tokens, "seconds": round(time.time() - t0, 2),
           # interrupted: stopped and resumed by something other than the crash part's own cut, so
           # seconds and live_* cover only the last part
           "interrupted": run.replayed > extra.get("cut_at", 0),
           "info": res.info, **extra}
    if part == "faults":                         # from the journal, so a resumed run counts them all
        row["injected"] = sum(e["kind"] == "tool" and (e["result"].get("tool_error") or [None])[0] == "unavailable"
                              for e in entries)
    if part == "crash" and clean is not None:
        row["same_answer"] = res.answer == clean["answer"]
        row["clean_tokens"] = clean["tokens"]
        # what the recovery cost: every model call recorded after the cut, from the journal, so a
        # resume that was itself interrupted and resumed again is counted whole
        row["recovery_tokens"] = sum((e["result"][1] or {}).get("total_tokens") or 0
                                     for e in entries[extra["cut_at"]:] if e["kind"] == "model")
    return row


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
            sys.exit("the code or tasks changed since this run started; start a new run instead")
        from_manifest(a, manifest)
        digest = ch04.ch01.server_info(a.base_url, a.model).get("digest")
        if digest is None or digest != manifest["model"].get("digest"):
            sys.exit(f"the model's digest is {digest}, not the run's {manifest['model'].get('digest')}")
        ch04.check_window(a.base_url, a.model, manifest["server"].get("window"))
        for r in read_jsonl(out / "traces.jsonl")[0]:   # a row cut off by a kill is dropped; that run resumes
            rows[(r["part"], r["seed"], r["id"], r["cond"])] = r
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    else:
        for k, v in DEFAULTS.items():
            if getattr(a, k) is None:
                setattr(a, k, v)
    parts = a.parts.split(",")
    if "crash" in parts and "compare" not in parts:
        sys.exit("the crash part cuts the compare part's journals: run them together")
    tasks = json.loads((CH04 / "tasks_long.json").read_text(encoding="utf-8"))
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
    extra = json.loads(a.extra)
    if not a.resume:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        n = ch04.check_window(a.base_url, a.model)
        (out / "journals").mkdir(parents=True)
        manifest = {
            "run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "model": {"tag": a.model, **ch04.ch01.server_info(a.base_url, a.model)},
            "server": {"base_url": a.base_url, "window": n},
            "machine": {"python": platform.python_version(), "platform": platform.platform(),
                        "processor": platform.processor()},
            "settings": {"temperature": a.temperature, "seeds": list(range(1, a.seeds + 1)), "extra": extra,
                         "tasks": [t["id"] for t in tasks], "parts": parts, "conds": CONDS,
                         "fault_conds": FAULT_CONDS, "fault_p": FAULT_P, "retry": RETRY,
                         "agent": AGENT_KW, "step": STEP_KW},
            "prompts": {"plan": PLAN, "step": STEP, "mid": MID, "last": LAST, "replan": REPLAN,
                        "extract": EXTRACT, "trip": TRIP},
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
                row = one(out, part, seed, t, cond, clients[seed], rows.get(("compare", 1, t["id"], cond)))
            except Halted as e:
                sys.exit(f"{part} {seed} {cond} {t['id']} stopped: {e}\nIts journal is kept and no row was "
                         f"written. When the server is back: python experiment.py --out {a.out} --resume")
            rows[key] = row
            traces.write(json.dumps(row) + "\n")
            traces.flush()
            mark = {True: "OK ", False: "BAD", None: "?  "}[row["ok"]]
            more = (f" cut={row['cut_at']}/{row['clean_calls']} same={row.get('same_answer')}" if part == "crash"
                    else f" injected={row['injected']}" if part == "faults" else "")
            print(f"{part:7} {seed} {cond:8} {t['id']:16} {row['status']:11} {mark} calls={row['calls']} "
                  f"live={row['live']} tok={row['tokens']} {row['seconds']:.0f}s{more}", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    claims = Ledger(out / "ledger.jsonl").claims()
    keys = [c["key"] for c in claims]
    print(f"\nwrote {out}. {len(claims)} claims in the ledger, {len(keys) - len(set(keys))} with a repeated key. "
          "Unscored answers have no 'Final answer:' line: read and label them.")


if __name__ == "__main__":
    main()
