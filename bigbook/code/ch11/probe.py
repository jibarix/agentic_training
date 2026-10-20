"""What does a timestamp at the top of the system prompt do to a whole run: the server's prompt cache,
the prompt seconds, the run's seconds and its answers?

  stable  : Chapter 4's full-context agent as it was: the same system prompt on every call
  stamped : the same, with "Time of this request: <time>" put before the system prompt on every
            call, so two calls share only the stamp's first few tokens, up to where the times differ

This is an end-to-end intervention, not a replay: the stamp changes the model's input, so it can
change the replies, the tool calls and the length of the run, and a difference in right answers
is a possible effect of the stamp, not a sign of a bug. The cache's own effect is read from the
server's per-call counts (cached tokens, prompt seconds), not from the run's seconds alone.

Chapter 4's 30 long tasks, two seeds, both arms: 120 runs, the arms' order alternating from task
to task. The client is native.py's, on Ollama's /api/chat, which reports how many prompt tokens it
read from its cache and how long the others took. The pilot is three tasks, one seed, both arms.

Usage (from this folder):
  python probe.py --out results/my-pilot --pilot
  python probe.py --out results/my-run
  python probe.py --out results/my-run --resume

Every run writes a new folder and refuses to overwrite an old one; a resume refuses if the code or
the model's digest has changed, drops a torn last row (a kill mid-write) and makes that run again.
The manifest is replaced atomically, so a kill can't leave it half-written. The window is sent with every request (num_ctx), so the probe
doesn't need Chapter 4's window check, and one value is used throughout: a new num_ctx reloads
the model.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
CODE = HERE.parent
for d in ("ch01", "ch03", "ch04"):
    sys.path.append(str(CODE / d))
sys.path.insert(0, str(HERE))
from agent import SYSTEM, Agent                          # noqa: E402  Chapter 1's
from context import POLICIES, ContextClient              # noqa: E402  Chapter 4's
from handbook_tools import TOOLS                         # noqa: E402
from native import NativeClient                          # noqa: E402
from score import score                                  # noqa: E402  Chapter 3's scorer

_spec = importlib.util.spec_from_file_location("ch04_experiment", CODE / "ch04" / "experiment.py")
ch04 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch04)                           # its agent settings, prompt suffix and server_info
ARMS = ("stable", "stamped")
PILOT = ["meals_emp0103", "full_emp0104", "billed_emp0101"]
SEEDS, NUM_CTX = 2, 32_768
FILES = {**{f"ch11/{f}": HERE / f for f in ("probe.py", "native.py")}, **ch04.CODE}


class Stamped:
    """Wrap a client so each call's system prompt starts with the time of the call."""

    def __init__(self, client, clock=lambda: datetime.now(timezone.utc).isoformat(timespec="microseconds")):
        self.client, self.clock = client, clock

    def chat(self, messages, tools=None):
        m = [dict(x) for x in messages]
        if m and m[0].get("role") == "system":
            m[0]["content"] = f"Time of this request: {self.clock()}\n\n" + m[0]["content"]
        return self.client.chat(m, tools)


def plan(tasks, seeds, arms=ARMS):
    """(seed, task, arm) in order: the arms swap places from one task to the next."""
    out = []
    for s in range(1, seeds + 1):
        for i, t in enumerate(tasks):
            order = arms if (i + s) % 2 == 0 else arms[::-1]
            out += [(s, t, a) for a in order]
    return out


def total(log, key, digits=None):
    """The sum of one count over a run's calls, or None if any call didn't report it: unknown, not 0."""
    xs = [c[key] for c in log]
    if any(x is None for x in xs):
        return None
    return round(sum(xs), digits) if digits is not None else sum(xs)


def row(seed, t, arm, res, native, seconds):
    log = native.log
    ok = score(res.answer, t["answer"], t["units"]) if res.status == "answered" else False
    return {"seed": seed, "arm": arm, "id": t["id"], "cluster": t["cluster"], "status": res.status, "ok": ok,
            "steps": res.steps, "tokens": res.tokens, "seconds": seconds, "answer": res.answer,
            "detail": res.detail, "calls": len(log),
            "prompt_tokens": total(log, "prompt"),
            "cached_tokens": total(log, "cached"),
            "cached_missing": sum(c["cached"] is None for c in log),
            "prompt_seconds": total(log, "prompt_seconds", 3),
            "eval_seconds": total(log, "eval_seconds", 3),
            "thinking_chars": sum(c["thinking_chars"] for c in log)}


def hashes():
    return {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in FILES.items()}


def write_atomic(path, text):
    """Write a temporary file, flush it to disk, then replace: the old file or the new, never half."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def recover(path):
    """The rows of traces.jsonl. Only a torn last line (a kill mid-write) is repaired: it is dropped,
    the file is rewritten without it and that run is made again. A whole last row that lost only its
    newline is kept, and the newline is restored so that the next append starts a line of its own.
    A bad line before the last means the file is damaged some other way: ValueError, and the file
    is left as it is."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    rows = []
    for k, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except ValueError:
            if k < len(lines) - 1:
                raise ValueError(f"{path}: line {k + 1} of {len(lines)} is not a whole row; not repaired")
            write_atomic(path, "".join(json.dumps(r) + "\n" for r in rows))
            return rows
    if text and not text.endswith("\n"):
        write_atomic(path, "".join(json.dumps(r) + "\n" for r in rows))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pilot", action="store_true", help="three tasks, one seed")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--model", default="qwen3.5:4b-q4_K_M")
    ap.add_argument("--root", default="http://localhost:11434")
    ap.add_argument("--temperature", type=float, default=0.7)
    a = ap.parse_args(argv)
    out = HERE / a.out
    tasks = json.loads((CODE / "ch04" / "tasks_long.json").read_text(encoding="utf-8"))
    done = set()
    if a.resume:
        manifest = json.loads((out / "manifest.json").read_text())
        if manifest["sha256"] != hashes():
            sys.exit("the code or tasks changed since this run started; start a new run instead")
        s = manifest["settings"]
        a.model, a.root, a.temperature, a.pilot = manifest["model"]["tag"], manifest["server"]["root"], \
            s["temperature"], s["pilot"]
        digest = ch04.ch01.server_info(a.root + "/v1", a.model).get("digest")
        if digest is None or digest != manifest["model"].get("digest"):
            sys.exit(f"the model's digest is {digest}, not the run's {manifest['model'].get('digest')}")
        done = {(r["seed"], r["id"], r["arm"]) for r in recover(out / "traces.jsonl")}
        manifest.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    if a.pilot:
        tasks = [t for t in tasks if t["id"] in PILOT]
    seeds = 1 if a.pilot else SEEDS
    if not a.resume:
        if out.exists():
            sys.exit(f"{out} already exists; choose a new --out so old evidence is kept")
        out.mkdir(parents=True)
        manifest = {"run": out.name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "model": {"tag": a.model, **ch04.ch01.server_info(a.root + "/v1", a.model)},
                    "server": {"root": a.root, "api": "/api/chat", "num_ctx": NUM_CTX},
                    "machine": {"python": platform.python_version(), "platform": platform.platform(),
                                "processor": platform.processor()},
                    "settings": {"temperature": a.temperature, "seeds": list(range(1, seeds + 1)), "think": False,
                                 "pilot": a.pilot, "arms": list(ARMS), "tasks": [t["id"] for t in tasks],
                                 **ch04.AGENT_KW},
                    "prompts": {"agent_system": SYSTEM + ch04.FINAL, "stamp": "Time of this request: <time>\\n\\n"},
                    "sha256": hashes()}
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))
    with open(out / "traces.jsonl", "a", encoding="utf-8") as traces:
        for seed, t, arm in plan(tasks, seeds):
            if (seed, t["id"], arm) in done:
                continue
            native = NativeClient(a.model, a.root, a.temperature, seed, NUM_CTX)
            inner = Stamped(native) if arm == "stamped" else native
            client = ContextClient(inner, POLICIES["full"](None))
            t0 = time.time()
            res = Agent(client, tools=TOOLS, system=SYSTEM + ch04.FINAL, **ch04.AGENT_KW).run(t["task"])
            r = row(seed, t, arm, res, native, round(time.time() - t0, 2))
            traces.write(json.dumps({**r, "native_log": native.log, "call_log": client.calls,
                                     "trace": res.trace}) + "\n")
            traces.flush()
            known = r["cached_tokens"] is not None and r["prompt_tokens"]
            hit = f"{r['cached_tokens'] / r['prompt_tokens']:.0%}" if known else "unknown"
            ps = "unknown" if r["prompt_seconds"] is None else f"{r['prompt_seconds']:.1f}"
            print(f"{seed} {arm:7} {t['id']:16} {res.status:11} ok={r['ok']} calls={r['calls']} "
                  f"cached={hit} prompt_s={ps} {r['seconds']:.0f}s", flush=True)
    manifest["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    write_atomic(out / "manifest.json", json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
