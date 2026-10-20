"""Chapter 10's experiment: does a better prompt, found on training tasks, help on held-out ones?

  search : the same model reflects on failed training runs and proposes an instruction, four times
           in turn, each from the best so far (at first Chapter 4's prompt, with Chapter 4's seed-1
           runs as its record); each valid proposal is run once (seed 1) on the 15 training tasks
  held   : three arms on the 15 held-out tasks, ten seeds each, interleaved task by task:
           A  Chapter 4's prompt, unchanged
           B  A plus up to two worked examples, passing runs of training tasks in Chapter 4's run
           C  the new proposal that scored best on the training tasks, frozen before any held-out run;
              Chapter 4's prompt is a parent but never a final choice, so C may score below it
The agent, tools, scorer and settings are Chapter 4's full-context ones, with thinking off.

Usage (from this folder):
  python experiment.py --out results/my-smoke --candidates 1 --seeds 1 --train-tasks meals_emp0110 --tasks meals_emp0112
  python experiment.py --out results/my-pilot --candidates 1 --seeds 2 \\
      --train-tasks meals_emp0110,full_emp0111 --tasks meals_emp0112,full_emp0104
  python experiment.py --out results/my-run                 # 4 reflections, up to 60 + 450 runs
  python experiment.py --out results/my-run --resume

Each run is one row of traces.jsonl and its trace goes to runs/<name>.json, for labelling and for
the next reflection. A model call that raises stops the experiment with no row written; --resume
makes that call again. A resume takes every setting from the manifest and refuses if the code, the
split, Chapter 4's run, the handbook or the model's digest has changed, or if the server's context
window is not the run's own.
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
from statistics import fmean

HERE = Path(__file__).parent
CH01, CH03, CH04, CH09 = (HERE.parent / c for c in ("ch01", "ch03", "ch04", "ch09"))
sys.path.insert(0, str(CH01))
sys.path.insert(1, str(CH04))
from handbook_tools import TOOLS                         # noqa: E402  Chapter 1's tools on Chapter 4's handbook
sys.path.insert(0, str(HERE))
sys.path.append(str(CH03))
import optimise as O                                     # noqa: E402
from agent import SYSTEM, Agent                          # noqa: E402  Chapter 1's
from llm import ChatClient                               # noqa: E402
from score import score                                  # noqa: E402  Chapter 3's scorer


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ch04 = _load("ch04_experiment", CH04 / "experiment.py")  # its agent settings, server_info and the window check
S = _load("ch09_sampling", CH09 / "sampling.py")          # Chapter 9's Recorder and amount reader

CODE = {**{f"ch01/{f}": CH01 / f for f in ("agent.py", "tools.py", "llm.py", "experiment.py")},
        "ch03/score.py": CH03 / "score.py",
        **{f"ch04/{f}": CH04 / f for f in ("handbook_tools.py", "make_handbook.py", "tasks_long.json", "experiment.py")},
        "ch04/run/traces.jsonl": O.CH4_RUN / "traces.jsonl",
        "ch09/sampling.py": CH09 / "sampling.py",
        **{f"ch10/{f}": HERE / f for f in ("experiment.py", "optimise.py", "split.json")}}
AGENT_KW = ch04.AGENT_KW                                 # Chapter 4's full-context agent, unchanged
FINAL = ch04.FINAL
PROMPT = SYSTEM + FINAL                                  # arm A, and Chapter 4's
THINK_OFF = {"reasoning_effort": "none"}                 # as every chapter but 9
SEARCH_SEED = 1
REFLECT_KW = {"temperature": 0.7, "extra": THINK_OFF}   # seeded by the step, so each proposal differs
ARMS = ("A", "B", "C")
DEFAULTS = {"model": "qwen3.5:4b-q4_K_M", "base_url": "http://localhost:11434/v1", "seeds": 10,
            "candidates": 4, "demos": 2, "temperature": 0.7, "tasks": "", "train_tasks": ""}


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


def name(part, seed, tid, cond):
    return f"{part}_{seed}_{tid}_{cond}"


def held_plan(heldout, seeds):
    return [("held", s, t, arm) for s in range(1, seeds + 1) for t in heldout for arm in ARMS]


def generate(t, client, prompt):
    """One agent run; returns (row, trace). Raises Halted if a model call raised."""
    rec = S.Recorder(client)
    t0 = time.time()
    res = Agent(rec, tools=TOOLS, system=prompt, **AGENT_KW).run(t["task"])
    if rec.errors:
        raise Halted(rec.errors[0])
    ok = score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
    a = S.amount(res.answer, t["units"]) if res.status == "answered" else None
    known = lambda f: None if any(c[f] is None for c in rec.calls) else sum(c[f] for c in rec.calls)
    prompts = [c["prompt"] for c in rec.calls]
    row = {"status": res.status, "ok": ok, "amount": None if a is None else str(a), "answer": res.answer,
           "detail": res.detail, "steps": res.steps, "calls": len(rec.calls),
           "tokens": res.tokens if known("total") is not None else None,      # unknown, not zero
           "completion": known("completion"),
           "max_prompt": None if not prompts or None in prompts else max(prompts),
           "seconds": round(time.time() - t0, 2)}
    return row, res.trace


def mean_ok(rows):
    return fmean(r["ok"] is True for r in rows) if rows else 0.0


def best(cands):
    """The candidate with the highest training score; the earliest on a tie. cands: {i: score}."""
    return min(cands, key=lambda i: (-cands[i], i)) if cands else None


def parent_of(step, rows, base):
    """The instruction the step edits and its training record [(task id, row, trace)]: the best
    candidate so far if it beat the base prompt's record, else the base prompt."""
    scored = {i: mean_ok([r for _, r, _ in rec]) for i, (_, rec) in rows.items() if i < step}
    i = best(scored)
    if i is not None and scored[i] > mean_ok([r for _, r, _ in base[1]]):
        return rows[i]
    return base


def demos(rows, tasks, train, n):
    """Arm B's worked examples and the runs they came from."""
    picked = O.bootstrap(rows, set(train), n)
    return [O.render_demo(tasks[r["id"]]["task"], r["trace"]) for r in picked], \
           [{"id": r["id"], "seed": r["seed"], "steps": r["steps"]} for r in picked]


def from_manifest(a, m):
    s = m["settings"]
    was = {"model": m["model"]["tag"], "base_url": m["server"]["base_url"], "seeds": s["seeds"],
           "candidates": s["candidates"], "demos": s["demos"], "temperature": s["temperature"],
           "tasks": ",".join(s["heldout"]), "train_tasks": ",".join(s["train"])}
    clash = [k for k in was if getattr(a, k) is not None and getattr(a, k) != was[k]
             and not (k in ("tasks", "train_tasks") and getattr(a, k) == "")]
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
    ap.add_argument("--seeds", type=int, help=f"runs per held-out task and arm, default {DEFAULTS['seeds']}")
    ap.add_argument("--candidates", type=int, help=f"reflected instructions to try, default {DEFAULTS['candidates']}")
    ap.add_argument("--demos", type=int, help=f"worked examples in arm B, default {DEFAULTS['demos']}")
    ap.add_argument("--temperature", type=float, help=f"default {DEFAULTS['temperature']}")
    ap.add_argument("--tasks", help="comma-separated held-out task ids (default: all 15)")
    ap.add_argument("--train-tasks", help="comma-separated training task ids (default: all 15)")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in --out")
    a = ap.parse_args()

    out = HERE / a.out
    rows = {}
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes():
            sys.exit("the code, split, Chapter 4's run or the handbook changed since this run started; "
                     "start a new run instead")
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
        if a.seeds < 1 or a.candidates < 1 or a.demos < 0:
            sys.exit("need --seeds >= 1, --candidates >= 1 and --demos >= 0")
    tasks = {t["id"]: t for t in json.loads((CH04 / "tasks_long.json").read_text(encoding="utf-8"))}
    sp = json.loads(O.SPLIT.read_text())
    train = [i for i in sp["train"] if not a.train_tasks or i in a.train_tasks.split(",")]
    heldout = [i for i in sp["heldout"] if not a.tasks or i in a.tasks.split(",")]
    if set(train) & set(heldout) or not train or not heldout:
        sys.exit("the training and held-out tasks must be non-empty and come from their own sides of split.json")
    ch4 = O.ch4_rows()
    demo_text, demo_src = demos(ch4, tasks, sp["train"], a.demos)
    prompts = {"A": PROMPT, "B": O.with_demos(PROMPT, demo_text)}
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
            "settings": {"temperature": a.temperature, "seeds": a.seeds, "candidates": a.candidates,
                         "demos": a.demos, "search_seed": SEARCH_SEED, "reflect": REFLECT_KW, "think": THINK_OFF,
                         "train": train, "heldout": heldout, "split_seed": O.SPLIT_SEED, "agent": AGENT_KW,
                         "demo_runs": demo_src},
            "prompts": {"A": prompts["A"], "B": prompts["B"], "reflect": O.REFLECT, "final": FINAL},
            "sha256": hashes(),
        }
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))

    def agent_client(seed):
        return ChatClient(a.model, a.base_url, a.api_key, temperature=a.temperature, seed=seed, extra=THINK_OFF)

    def stop(what, e):
        sys.exit(f"{what} stopped: {e}\nNo row was written. When the server is back: "
                 f"python experiment.py --out {a.out} --resume")

    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        def keep(key, row):
            row = {"part": key[0], "seed": key[1], "id": key[2], "cond": key[3],
                   "cluster": tasks[key[2]]["cluster"] if key[2] in tasks else "-", **row}
            rows[key] = row
            traces.write(json.dumps(row) + "\n")
            traces.flush()
            return row

        # -- search: reflect, then score the proposal on the training tasks --------------------
        base_rec = [(r["id"], r, r["trace"]) for r in sorted(ch4, key=lambda r: r["id"])
                    if r["seed"] == SEARCH_SEED and r["id"] in train]
        base = (SYSTEM, base_rec)
        cands = {}                                       # step -> (instruction, [(task, row, trace)])
        search_client = agent_client(SEARCH_SEED)
        for step in range(1, a.candidates + 1):
            key = ("reflect", step, "-", "-")
            if key not in rows:
                instr, rec = parent_of(step, cands, base)
                failed = {tid: (r, tr) for tid, r, tr in rec if r["ok"] is not True}
                batch = O.minibatch(list(failed), step)
                fb = [O.failure(tasks[tid], failed[tid][1], failed[tid][0]["answer"]) for tid in batch]
                if not fb:
                    keep(key, {"instruction": None, "why": "the parent failed no training task",
                               "parent": instr, "batch": [], "reply": "", "tokens": None, "seconds": 0})
                else:
                    t0 = time.time()
                    client = ChatClient(a.model, a.base_url, a.api_key, temperature=REFLECT_KW["temperature"],
                                        seed=step, extra=REFLECT_KW["extra"])
                    try:
                        new, why, reply, usage = O.reflect(client, instr, fb)
                    except Exception as e:
                        stop(f"reflect {step}", f"{type(e).__name__}: {e}")
                    keep(key, {"instruction": new, "why": why, "parent": instr, "batch": batch, "reply": reply,
                               "tokens": usage.get("total_tokens"), "seconds": round(time.time() - t0, 2)})
                print(f"reflect {step}: {'valid' if rows[key]['instruction'] else 'invalid: ' + rows[key]['why']}",
                      flush=True)
            instr = rows[key]["instruction"]
            if instr is None:
                continue
            rec = []
            for tid in train:
                k = ("search", step, tid, "C")
                if k not in rows:
                    try:
                        row, trace = generate(tasks[tid], search_client, instr + FINAL)
                    except Halted as e:
                        stop(f"search {step} {tid}", e)
                    write_atomic(out / "runs" / f"{name(*k)}.json", json.dumps(trace))
                    keep(k, row)
                    print(f"search {step} {tid:16} {row['status']:11} {'OK ' if row['ok'] else 'BAD'} "
                          f"steps={row['steps']} {row['seconds']:.0f}s", flush=True)
                trace = json.loads((out / "runs" / f"{name(*k)}.json").read_text())
                rec.append((tid, rows[k], trace))
            cands[step] = (instr, rec)
        scores = {i: mean_ok([r for _, r, _ in rec]) for i, (_, rec) in cands.items()}
        chosen = best(scores)
        if chosen is None:
            sys.exit("no reflection gave a valid instruction, so arm C has none; see the reflect rows")
        prompts["C"] = cands[chosen][0] + FINAL
        manifest["frozen"] = {"candidate": chosen, "train_scores": scores, "prompt": prompts["C"]}
        write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))

        # -- held-out: the three arms, interleaved ------------------------------------------
        clients = {}
        for key in held_plan(heldout, a.seeds):
            if key in rows:
                continue
            _, seed, tid, arm = key
            clients.setdefault(seed, agent_client(seed))
            try:
                row, trace = generate(tasks[tid], clients[seed], prompts[arm])
            except Halted as e:
                stop(f"held {seed} {arm} {tid}", e)
            write_atomic(out / "runs" / f"{name(*key)}.json", json.dumps(trace))
            row = keep(key, row)
            mark = {True: "OK ", False: "BAD", None: "?  "}[row["ok"]]
            print(f"held {seed:2} {arm} {tid:16} {row['status']:11} {mark} steps={row['steps']} "
                  f"tok={row['tokens']} prompt={row['max_prompt']} {row['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    print(f"\nwrote {out}. Unscored answers have no 'Final answer:' line: read and label them (adjudication.json).")


if __name__ == "__main__":
    main()
