"""What weight updates would start from, measured on Chapter 4's run with no model and no GPU.

  degenerate : the share of tasks whose group of runs would all pass or all fail, and so give a
               group-relative method such as GRPO no outcome advantage (observed for groups of 3; for
               larger groups a plug-in projection that takes each observed rate as the true one)
  bill       : the inference time of an RL run's rollouts at the run's measured seconds per run
  sft_rows   : the passing runs of training tasks as chat messages, with the tool schemas the agent
               was given and a weight of 1 on the model's own turns and 0 on everything else. An
               intermediate export: no code here renders the serving template, tokenises it or
               builds the assistant-token mask, which a training job would have to do and check

Usage (from this folder): python offline.py   (writes sft_train.jsonl; trains nothing)
"""
import json
import sys
from pathlib import Path
from statistics import fmean

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import optimise as O                                     # noqa: E402

SFT = HERE / "sft_train.jsonl"
ROLLOUTS = {"A3": 50 * 16 * 8, "A3b": 50 * 8 * 8, "GEPA": 678}   # CMU 11-768 A3 (two parts); GEPA on IFBench


def degenerate(right, n, g):
    """Share of tasks with no group advantage: observed when g == n, else projected at each task's rate c/n."""
    if g == n:
        return fmean(c in (0, n) for c in right.values())
    return fmean((c / n) ** g + (1 - c / n) ** g for c in right.values())


def bill(rollouts, seconds):
    """Hours of inference for the rollouts, before any training step."""
    return rollouts * seconds / 3600


def messages(system, question, trace):
    """A recorded run as chat messages, the model's turns weighted 1 and the rest 0."""
    out = [{"role": "system", "content": system, "weight": 0}, {"role": "user", "content": question, "weight": 0}]
    for t in trace:
        if t["type"] == "model":
            m = {"role": "assistant", "content": t.get("content", ""), "weight": 1}
            if t.get("calls"):
                m["tool_calls"] = [{"id": c["id"], "type": "function",
                                    "function": {"name": c["name"], "arguments": c["arguments"]}}
                                   for c in t["calls"]]
            out.append(m)
        elif t["type"] == "tool":
            out.append({"role": "tool", "tool_call_id": t["id"], "content": t["observation"], "weight": 0})
    return out


def sft_rows(rows, tasks, train, system, tools=()):
    """One example per passing run of a training task, in seed order, with the tool schemas."""
    keep = sorted((r for r in rows if r["ok"] is True and r["id"] in train), key=lambda r: (r["id"], r["seed"]))
    return [{"id": r["id"], "seed": r["seed"], "tools": list(tools),
             "messages": messages(system, tasks[r["id"]]["task"], r["trace"])} for r in keep]


def jsonl(rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


def main():
    sys.path.insert(0, str(HERE.parent / "ch01"))
    from agent import SYSTEM                             # Chapter 1's
    from tools import TOOLS                              # Chapter 1's schemas, which Chapter 4's agent uses
    import importlib.util
    spec = importlib.util.spec_from_file_location("ch01_experiment", HERE.parent / "ch01" / "experiment.py")
    ch01 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ch01)
    tasks = {t["id"]: t for t in json.loads((O.CH04 / "tasks_long.json").read_text(encoding="utf-8"))}
    train = set(json.loads(O.SPLIT.read_text())["train"])
    SFT.write_text(jsonl(sft_rows(O.ch4_rows(), tasks, train, SYSTEM + ch01.FINAL,
                                   [s for _, s in TOOLS.values()])), encoding="utf-8")
    print(f"wrote {SFT.name}")


if __name__ == "__main__":
    main()
