"""Chapter 9's experiment: more runs or longer thinking on Chapter 4's 30 long tasks, then pick one.

  gen   : Chapter 4's full-context agent on each task, ten runs with thinking off (seeds 1-10) and
          three with thinking on (seeds 1-3), interleaved task by task as in Chapter 3
  judge : for each task and each group of five thinking-off runs (seeds 1-5, 6-10), the same
          model, thinking off, picks one run; once with the runs in seed order and once reversed

The vote and the oracle need no model: report.py computes them from the gen runs, so every way of
choosing is scored on the same samples.

Usage (from this folder):
  python experiment.py --out results/my-smoke --off 1 --on 1 --k 1 --tasks meals_emp0103
  python experiment.py --out results/my-pilot --off 2 --on 2 --k 2 --tasks meals_emp0103,full_emp0104,billed_emp0101
  python experiment.py --out results/my-run                     # 390 runs and 120 judge calls
  python experiment.py --out results/my-run --resume

Each run is one row of traces.jsonl, and its trace goes to runs/<name>.json for labelling and for
the judge. A model call that raises stops the experiment with no row written; --resume makes that
run again. A resume takes every setting from the manifest and refuses if the code, the tasks, the
handbook or the model's digest has changed, or if the server's context window is not the run's own.
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
import sampling as S                                     # noqa: E402
from agent import SYSTEM, Agent                          # noqa: E402  Chapter 1's
from llm import ChatClient                               # noqa: E402
from score import score                                  # noqa: E402  Chapter 3's scorer

_spec = importlib.util.spec_from_file_location("ch04_experiment", CH04 / "experiment.py")
ch04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch04)                           # its agent settings, server_info and the window check

CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py", "experiment.py")},
        "ch03/score.py": CH03 / "score.py",
        **{f"ch04/{f}": CH04 / f for f in ("handbook_tools.py", "make_handbook.py", "tasks_long.json", "experiment.py")},
        **{f"ch09/{f}": HERE / f for f in ("experiment.py", "sampling.py")}}
AGENT_KW = ch04.AGENT_KW                                 # Chapter 4's full-context agent, unchanged
PROMPT = SYSTEM + ch04.FINAL
THINK = {"off": {"reasoning_effort": "none"}, "on": {"reasoning_effort": "high"}}   # Ollama: false, true
JUDGE_KW = {"temperature": 0.0, "seed": 1, "extra": THINK["off"]}
DEFAULTS = {"model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1", "off": 10, "on": 3,
            "k": 5, "temperature": 0.7, "tasks": ""}


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


def groups(off, k):
    """The thinking-off seeds in disjoint groups of k: [[1..k], [k+1..2k], ...]; a short tail is dropped."""
    return [list(range(i + 1, i + k + 1)) for i in range(0, off - k + 1, k)]


def plan(tasks, off, on, k):
    n = {"off": off, "on": on}
    out = [("gen", s, t, c) for s in range(1, max(off, on) + 1) for t in tasks for c in ("off", "on") if s <= n[c]]
    out += [("judge", g, t, order) for t in tasks for g in range(1, len(groups(off, k)) + 1)
            for order in ("forward", "reverse")]
    return out


def name(part, seed, tid, cond):
    return f"{part}_{seed}_{tid}_{cond}"


def generate(t, client):
    """One agent run; returns (row, trace, the thinking of each call). Raises Halted if a call raised."""
    rec = S.Recorder(client)
    t0 = time.time()
    res = Agent(rec, tools=TOOLS, system=PROMPT, **AGENT_KW).run(t["task"])
    if rec.errors:
        raise Halted(rec.errors[0])
    ok = score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
    a = S.amount(res.answer, t["units"]) if res.status == "answered" else None
    known = lambda f: None if any(c[f] is None for c in rec.calls) else sum(c[f] for c in rec.calls)
    row = {"status": res.status, "ok": ok, "amount": None if a is None else str(a), "answer": res.answer,
           "detail": res.detail, "steps": res.steps, "calls": len(rec.calls),
           "tokens": res.tokens if known("total") is not None else None,      # unknown, not zero
           "completion": known("completion"),
           "thinking_chars": sum(c["thinking_chars"] for c in rec.calls), "seconds": round(time.time() - t0, 2)}
    return row, res.trace, rec.thoughts


def pick(t, seeds, order, traces, client):
    """One judge call on the runs of `seeds`; returns the row. Raises Halted if the call raised."""
    shown = seeds if order == "forward" else seeds[::-1]
    t0 = time.time()
    try:
        i, reply, usage = S.judge(client, t["task"], [S.evidence(traces[s]) for s in shown])
    except Exception as e:
        raise Halted(f"{type(e).__name__}: {e}")
    return {"shown": shown, "pick": None if i is None else shown[i], "reply": reply,
            "tokens": usage.get("total_tokens"), "seconds": round(time.time() - t0, 2)}


def from_manifest(a, m):
    s = m["settings"]
    was = {"model": m["model"]["tag"], "base_url": m["server"]["base_url"], "off": s["off"], "on": s["on"],
           "k": s["k"], "temperature": s["temperature"], "tasks": ",".join(s["tasks"])}
    clash = [k for k in was if getattr(a, k) is not None and getattr(a, k) != was[k]
             and not (k == "tasks" and getattr(a, k) == "")]
    if clash:
        sys.exit("these arguments disagree with the run's manifest: " + ", ".join(
            f"--{k.replace('_', '-')} {getattr(a, k)!r} (the run used {was[k]!r})" for k in clash))
    for k, v in was.items():
        setattr(a, k, v)


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
    ap.add_argument("--off", type=int, help=f"thinking-off runs per task, default {DEFAULTS['off']}")
    ap.add_argument("--on", type=int, help=f"thinking-on runs per task, default {DEFAULTS['on']}")
    ap.add_argument("--k", type=int, help=f"runs the judge chooses among, default {DEFAULTS['k']}")
    ap.add_argument("--temperature", type=float, help=f"default {DEFAULTS['temperature']}")
    ap.add_argument("--tasks", help="comma-separated task ids (default: all)")
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
        if not (1 <= a.k <= a.off) or a.on < 0:
            sys.exit("need 1 <= --k <= --off and --on >= 0")
    tasks = json.loads((CH04 / "tasks_long.json").read_text(encoding="utf-8"))
    if a.tasks:
        tasks = [t for t in tasks if t["id"] in a.tasks.split(",")]
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
            "settings": {"temperature": a.temperature, "off": a.off, "on": a.on, "k": a.k,
                         "groups": groups(a.off, a.k), "think": THINK, "judge": JUDGE_KW,
                         "tasks": [t["id"] for t in tasks], "agent": AGENT_KW},
            "prompts": {"agent_system": PROMPT, "judge": S.JUDGE},
            "sha256": hashes(),
        }
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))

    clients = {}
    judge_client = ChatClient(a.model, a.base_url, a.api_key, temperature=JUDGE_KW["temperature"],
                              seed=JUDGE_KW["seed"], extra=JUDGE_KW["extra"])
    gs = groups(a.off, a.k)
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for part, seed, t, cond in plan(tasks, a.off, a.on, a.k):
            key = (part, seed, t["id"], cond)
            if key in rows:
                continue
            try:
                if part == "gen":
                    if (seed, cond) not in clients:
                        clients[seed, cond] = ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature,
                                                         seed=seed, extra=THINK[cond])
                    row, trace, thoughts = generate(t, clients[seed, cond])
                    write_atomic(out / "runs" / f"{name(*key)}.json", json.dumps(trace))
                    write_atomic(out / "runs" / f"{name(*key)}.thinking.json", json.dumps(thoughts))
                else:
                    runs = {s: json.loads((out / "runs" / f"{name('gen', s, t['id'], 'off')}.json").read_text())
                            for s in gs[seed - 1]}
                    row = pick(t, gs[seed - 1], cond, runs, judge_client)
            except Halted as e:
                sys.exit(f"{part} {seed} {cond} {t['id']} stopped: {e}\nNo row was written. When the server "
                         f"is back: python experiment.py --out {a.out} --resume")
            row = {"part": part, "seed": seed, "cond": cond, "id": t["id"], "cluster": t["cluster"], **row}
            rows[key] = row
            traces.write(json.dumps(row) + "\n")
            traces.flush()
            if part == "gen":
                mark = {True: "OK ", False: "BAD", None: "?  "}[row["ok"]]
                print(f"gen   {seed:2} {cond:3} {t['id']:16} {row['status']:11} {mark} steps={row['steps']} "
                      f"tok={row['tokens']} think={row['thinking_chars']} {row['seconds']:.0f}s", flush=True)
            else:
                print(f"judge {seed:2} {cond:7} {t['id']:16} shown={row['shown']} pick={row['pick']} "
                      f"{row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    print(f"\nwrote {out}. Unscored answers have no 'Final answer:' line: read and label them "
          f"(adjudication.json; give the amount you read, so the vote can count it).")


if __name__ == "__main__":
    main()
