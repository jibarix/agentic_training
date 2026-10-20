"""Turn the chapter's run into its tables, traces and numbers (bigbook/build/ch02_*).

Usage: python report.py                       (the run and traces named in book.json)
       python report.py --show results/<run> mcp_two:laptop:1 ...   (print traces; write nothing)
Correctness comes from the run's adjudication.json when there is one, else the automatic score.
The wire transcript is generated fresh by sending real messages to the real server code.
"""
import importlib.util
import io
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
BUILD = HERE.parent.parent / "build"
sys.path.insert(0, str(HERE.parent / "ch01"))
_spec = importlib.util.spec_from_file_location("ch01_report", HERE.parent / "ch01" / "report.py")
ch01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch01)                           # Chapter 1's trace format
import bridge                                            # noqa: E402
from handbook_server import handbook_tools               # noqa: E402
from mcp_server import Server                            # noqa: E402

CONDS = ("local", "mcp", "mcp_two")
BS = "\\"
LABEL = {"local": "Tools in process (Chapter 1)", "mcp": "One MCP server",
         "mcp_two": "Two MCP servers, prefixed names"}


def load(run):
    rows = [json.loads(l) for l in open(HERE / run / "traces.jsonl", encoding="utf-8")]
    adj = HERE / run / "adjudication.json"
    if adj.exists():
        labels = {(a["cond"], a["id"], a["seed"]): a["label"] for a in json.loads(adj.read_text())["labels"]}
        for r in rows:
            r["ok"] = labels.get((r["cond"], r["id"], r["seed"]), r["ok"])
    return rows


def tool_calls(r):
    """(name, arguments, observation) for every tool call in a run, in order."""
    out, pending = [], []
    for t in r["trace"]:
        if t["type"] == "model" and "calls" in t:
            pending = ch01.calls_of(t)
        elif t["type"] == "tool":
            _, name, args = pending.pop(0)
            out.append((name, args, t["observation"]))
    return out


def same_observations(rows, a="local", b="mcp"):
    """Distinct (tool, arguments) combinations that appear in both conditions, pooled over tasks and
    seeds, and how many of them got one and the same observation text everywhere."""
    seen = {}
    for r in rows:
        for name, args, obs in tool_calls(r):
            seen.setdefault((name, args), {}).setdefault(r["cond"], set()).add(obs)
    shared = [v for v in seen.values() if a in v and b in v]
    return len(shared), sum(v[a] == v[b] and len(v[a]) == 1 for v in shared)


def archive_runs(rows):
    return [r for r in rows if r["cond"] == "mcp_two"
            and any(n.startswith("archive__") for n, _, _ in tool_calls(r))]


def divergence(by, tasks, seeds, a="local", b="mcp"):
    """Pairs of runs (same task, same seed) in a and b: how many made the same calls and gave the
    same answer, and how many differed already at the first model call, whose request is identical."""
    same = first = 0
    for t in tasks:
        for s in seeds:
            ra, rb = by.get((a, t, s)), by.get((b, t, s))
            if ra is None or rb is None:
                continue
            ca, cb = [c[:2] for c in tool_calls(ra)], [c[:2] for c in tool_calls(rb)]
            same += ca == cb and ra["answer"] == rb["answer"]
            first += ca[:1] != cb[:1]
    return {"SameRuns": same, "FirstCallDiffer": first}


def extra_tokens(rows):
    """The smallest first-call total with two servers minus the smallest with one. Descriptive only:
    the two minima come from different tasks, and a total includes the model's output."""
    first = {c: min(next(t for t in r["trace"] if t["type"] == "model")["tokens"]
                    for r in rows if r["cond"] == c) for c in ("mcp", "mcp_two")
             if any(r["cond"] == c for r in rows)}
    return first["mcp_two"] - first["mcp"] if len(first) == 2 else 0


def spec_chars():
    """Characters of tool specs sent to the model on every call, with one server and with two
    (prefixed, the archive's descriptions labelled): a size that does not depend on the model."""
    class Listed:                                        # just enough of a client for bridge.registry
        def __init__(self, name, label=""):
            self.name, self.server = name, Server(name, "2.0", handbook_tools(label), log=io.StringIO())

        def discover(self):
            pass

        def list_tools(self):
            m = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}}}
            return self.server.handle(m)["result"]["tools"]

    def size(reg):
        return len(json.dumps([spec for _, spec in reg.values()]))
    one = size(bridge.registry([Listed("handbook")]))
    two = size(bridge.registry([Listed("handbook"), Listed("archive", "ARCHIVE (2024 edition, superseded)")],
                               prefix=True))
    return {"SpecCharsOne": f"{one:,}", "SpecCharsTwo": f"{two:,}"}


def wire():
    """A transcript of real requests and the server's real replies, one JSON message per line."""
    s = Server("handbook", "2.0", handbook_tools(), page_size=1, log=io.StringIO())
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientCapabilities": {}}
    msgs = [("server/discover", {}), ("tools/list", {"cursor": "2"}),
            ("tools/call", {"name": "calculator", "arguments": {"expression": "4 * 68"}}),
            ("tools/call", {"name": "read_file", "arguments": {"path": "travel.md"}}),
            ("tools/call", {"name": "search", "arguments": {"query": "Denver"}})]
    out = []
    for i, (method, params) in enumerate(msgs, 1):
        m = {"jsonrpc": "2.0", "id": i, "method": method, "params": {**params, "_meta": meta}}
        out += ["-> " + json.dumps(m), "<- " + json.dumps(s.handle(m)), ""]
    old = {"jsonrpc": "2.0", "id": 6, "method": "tools/list",
           "params": {"_meta": {**meta, "io.modelcontextprotocol/protocolVersion": "2025-11-25"}}}
    out += ["-> " + json.dumps(old), "<- " + json.dumps(s.handle(old))]
    # After the first exchange, the repeated _meta objects are shown as {...}.
    info = '"_meta": ' + json.dumps({"io.modelcontextprotocol/serverInfo": s.info})
    out = out[:3] + [l.replace(json.dumps(meta), "{...}").replace(info, '"_meta": {...}') for l in out[3:]]
    return "\n".join(out) + "\n"


def render(run, picks):
    rows = load(run)
    conds = [c for c in CONDS if any(r["cond"] == c for r in rows)]
    tasks = list(dict.fromkeys(r["id"] for r in rows))
    seeds = sorted({r["seed"] for r in rows})
    by = {(r["cond"], r["id"], r["seed"]): r for r in rows}
    table = []
    for c in conds:
        rs = [r for r in rows if r["cond"] == c]
        k, n = sum(r["ok"] is True for r in rs), len(rs)
        ms = [m for r in rs for _, m in r["tool_ms"]]
        table.append(f"{LABEL[c]} & {k}/{n} & {sum(r['steps'] for r in rs) / n:.1f} & "
                     f"{sum(r['tokens'] for r in rs) / n:,.0f} & {len(ms)} & {statistics.median(ms):.2f} "
                     + BS * 2)
    files = {"ch02_results.tex": "\n".join(table) + "\n",
             "ch02_pertask.tex": "\n".join(
                 BS + "texttt{" + t + "} & " + " & ".join(str(sum(by[(c, t, s)]["ok"] is True for s in seeds))
                                                           for c in conds) + " " + BS * 2 for t in tasks) + "\n",
             "ch02_wire.txt": wire()}
    shared, same = same_observations(rows)
    arch = archive_runs(rows)
    model_s = [t["seconds"] for r in rows for t in r["trace"] if t["type"] == "model" and "seconds" in t]
    nums = {"SharedCalls": shared, "SameObs": same, "ArchiveRuns": len(arch),
            "ArchiveWrong": sum(r["ok"] is not True for r in arch),
            "ModelSeconds": f"{statistics.mean(model_s):.1f}", "ModelCalls": len(model_s), "Runs": len(rows),
            **divergence(by, tasks, seeds), "ExtraTokens": extra_tokens(rows), **spec_chars()}
    mean = {c: statistics.mean(r["tokens"] for r in rows if r["cond"] == c) for c in conds}
    if "mcp" in mean and "mcp_two" in mean:
        nums["TwoMoreTokens"] = f"{100 * (mean['mcp_two'] / mean['mcp'] - 1):.0f}"
    files["ch02_numbers.tex"] = "".join(f"{BS}newcommand{{{BS}chtwo{k}}}{{{v}}}\n" for k, v in nums.items())
    for i, key in enumerate(picks, 1):
        c, t, s = key.split(":")
        files[f"ch02_trace_{i}.txt"] = ch01.fmt_trace(by[(c, t, int(s))]) + "\n"
    return rows, files


def summary(rows):
    for c in CONDS:
        rs = [r for r in rows if r["cond"] == c]
        if rs:
            ms = [m for r in rs for _, m in r["tool_ms"]]
            print(f"{c:8} {sum(r['ok'] is True for r in rs)}/{len(rs)}  statuses "
                  f"{sorted({r['status'] for r in rs})}  tool calls {len(ms)}, median {statistics.median(ms):.2f} ms, "
                  f"max {max(ms):.1f} ms")
    print("wrong:", [(r["cond"], r["id"], r["seed"]) for r in rows if r["ok"] is not True])
    print("shared (tool, args) local/mcp, same observation:", same_observations(rows))
    print("mcp_two runs that used the archive:", [(r["id"], r["seed"], r["ok"]) for r in archive_runs(rows)])


def main(run=None, *picks):
    if run == "--show":
        by = {(r["cond"], r["id"], r["seed"]): r for r in load(picks[0])}
        for key in picks[1:]:
            c, t, s = key.split(":")
            print(ch01.fmt_trace(by[(c, t, int(s))]) + "\n")
        return
    if run is None:
        book = json.loads((HERE / "book.json").read_text())
        run, picks = book["run"], book["traces"]
    rows, files = render(run, picks)
    BUILD.mkdir(exist_ok=True)
    for name, text in files.items():
        (BUILD / name).write_text(text, encoding="utf-8")
    summary(rows)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:])
