"""Run every task under three conditions and score the answers.

  no_tools : the model answers from memory (the baseline the agent must beat)
  v1       : the agent with the lookup tool as first written (substring match, top 5 lines)
  v2       : the same agent after one fix to lookup (whole words, IDF ranking, table header kept)

Usage: python experiment.py [model] [seeds]     e.g. python experiment.py qwen3.5:4b-q4_K_M 3
"""
import json
import re
import sys
from pathlib import Path

from agent import Agent, Result
from tools import TOOLS, TOOLS_V1
from llm import ChatClient

HERE = Path(__file__).parent
NO_TOOLS = "You answer questions about the ACME company handbook. Reply with the final number and its unit."


def correct(answer, expected):
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", answer.replace(",", ""))]
    return any(abs(n - expected) < 0.011 for n in nums)


def run_no_tools(client, task):
    msg, usage = client.chat([{"role": "system", "content": NO_TOOLS}, {"role": "user", "content": task}])
    return Result("answered", msg.get("content") or "", 1, usage.get("total_tokens", 0))


def main(model="qwen3.5:4b-q4_K_M", seeds=3):
    tasks = json.loads((HERE / "tasks.json").read_text())
    out_dir = HERE / "results"
    out_dir.mkdir(exist_ok=True)
    rows = []
    with open(out_dir / "traces.jsonl", "w", encoding="utf-8") as traces:
        for seed in range(1, seeds + 1):
            client = ChatClient(model, temperature=0.7, seed=seed, extra={"reasoning_effort": "none"})
            for cond in ("no_tools", "v1", "v2"):
                for t in tasks:
                    res = run_no_tools(client, t["task"]) if cond == "no_tools" else \
                          Agent(client, tools=TOOLS_V1 if cond == "v1" else TOOLS).run(t["task"])
                    row = {"seed": seed, "cond": cond, "id": t["id"], "status": res.status,
                           "ok": res.status == "answered" and correct(res.answer, t["answer"]),
                           "steps": res.steps, "tokens": res.tokens, "answer": res.answer}
                    rows.append(row)
                    traces.write(json.dumps({**row, "trace": res.trace}) + "\n")
                    print(f"{seed} {cond:8} {t['id']:10} {res.status:11} {'OK ' if row['ok'] else 'BAD'} "
                          f"steps={res.steps} tok={res.tokens}", flush=True)
    (out_dir / "runs.json").write_text(json.dumps(rows, indent=1))
    print("\ncondition  accuracy  mean steps  mean tokens")
    for cond in ("no_tools", "v1", "v2"):
        r = [x for x in rows if x["cond"] == cond]
        print(f"{cond:9} {sum(x['ok'] for x in r):3}/{len(r):<4} {sum(x['steps'] for x in r)/len(r):9.1f} "
              f"{sum(x['tokens'] for x in r)/len(r):11.0f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "qwen3.5:4b-q4_K_M", int(sys.argv[2]) if len(sys.argv) > 2 else 3)
