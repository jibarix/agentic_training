"""Write a run's trace as spans named the way OpenTelemetry's GenAI conventions name them.

Usage: python otel_shape.py [--content] [--limit N] > spans.jsonl
       (Chapter 4's book run, one span per line: each run's invoke_agent span, then its chat and
        execute_tool spans)

The names follow the GenAI semantic conventions at commit SPEC of the semantic-conventions-genai
repository, where every one of them is at "Development" status: they may still change. Nothing
here is OpenTelemetry's SDK, and nothing is sent anywhere; the records are plain JSON in roughly
the shape the SDK would export, so a reader can see what each attribute holds before installing
the real pipeline (an SDK, a collector and a viewer).

Times are rebuilt, not measured: each model call's seconds are its own, and the run's time outside
the model is spread evenly between calls. The messages and tool arguments and results are left out
unless --content is given, as the conventions advise: they can hold anything the user typed or a
tool read. The local server reports no cache counts, so gen_ai.usage.cache_read.input_tokens is
not set; anthropic_usage and openai_usage show what a provider's usage would map to. The traces
don't record why the server stopped each reply, so gen_ai.response.finish_reasons is not set
either: an attribute that isn't known is left out, not guessed. Messages, with --content, are in
the conventions' shape: a role and a list of parts, text and tool calls.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import analysis as A                                     # noqa: E402

SPEC = "547934afa90a34298441caf80c43b27255c3a292"         # semantic-conventions-genai, as read for the chapter
PROVIDER = "ollama"     # not one of the listed well-known values, so a custom one, which the conventions allow
AGENT = "handbook-agent"


def ident(*parts, n=16):
    """A stable hex id from the parts: the same run gives the same trace and span ids."""
    return hashlib.sha256("/".join(map(str, parts)).encode()).hexdigest()[:n]


def anthropic_usage(u):
    """Anthropic's usage block -> GenAI usage attributes. Anthropic's input_tokens leaves out the
    cached tokens, and the conventions' input count includes them, so the three are added."""
    read, write = u.get("cache_read_input_tokens") or 0, u.get("cache_creation_input_tokens") or 0
    return {"gen_ai.usage.input_tokens": u["input_tokens"] + read + write,
            "gen_ai.usage.output_tokens": u["output_tokens"],
            "gen_ai.usage.cache_read.input_tokens": read, "gen_ai.usage.cache_write.input_tokens": write}


def openai_usage(u):
    """OpenAI's usage block -> GenAI usage attributes. Its prompt count already includes the cached part."""
    out = {"gen_ai.usage.input_tokens": u["prompt_tokens"], "gen_ai.usage.output_tokens": u["completion_tokens"]}
    cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens")
    if cached is not None:
        out["gen_ai.usage.cache_read.input_tokens"] = cached
    reasoning = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
    if reasoning is not None:
        out["gen_ai.usage.reasoning.output_tokens"] = reasoning
    return out


def output_messages(text, calls=()):
    """A reply as gen_ai.output.messages: one assistant message whose parts are its text and its tool
    calls, as the pinned examples show. No finish_reason: the traces don't record it."""
    parts = [{"type": "text", "content": text}] if text else []
    for c in calls:
        try:
            args = json.loads(c["arguments"]) if isinstance(c["arguments"], str) else c["arguments"]
        except ValueError:
            args = c["arguments"]                        # kept as the model wrote it
        parts.append({"type": "tool_call", "id": c["id"], "name": c["name"], "arguments": args})
    return [{"role": "assistant", "parts": parts}]


def span(trace, sid, parent, name, kind, t0, t1, attrs, error=None):
    return {"trace_id": trace, "span_id": sid, "parent_span_id": parent, "name": name, "kind": kind,
            "start_time_unix_nano": round(t0 * 1e9), "end_time_unix_nano": round(t1 * 1e9),
            "attributes": attrs | ({"error.type": error} if error else {}),
            "status": {"code": "ERROR" if error else "UNSET"}}


def spans(row, model, start=0.0, content=False):
    """One run of Chapter 4's (a traces.jsonl row) as a list of span records, the agent's first."""
    trace = ident(row["cond"], row["seed"], row["id"], n=32)
    root = ident(trace, "agent")
    steps = row["trace"]
    models = [s for s in steps if s["type"] == "model"]
    log = row["call_log"]
    gap = max(0.0, row["seconds"] - sum(s["seconds"] for s in models)) / max(1, len(models))
    out, t, k = [], start, 0
    for s in steps:
        if s["type"] == "model":
            c = log[k] if k < len(log) else {}
            p = c.get("prompt_tokens")
            attrs = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": PROVIDER,
                     "gen_ai.request.model": model, "gen_ai.conversation.id": trace}
            if p is not None and not s.get("estimated"):
                attrs |= {"gen_ai.usage.input_tokens": p,
                          "gen_ai.usage.output_tokens": s["tokens"] - p - (c.get("summary_tokens") or 0)}
            if content:
                attrs["gen_ai.output.messages"] = output_messages(s["content"], s["calls"])
            out.append(span(trace, ident(trace, "chat", k), root, f"chat {model}", "CLIENT",
                            t, t + s["seconds"], attrs))
            t += s["seconds"] + gap
            k += 1
        elif s["type"] == "tool":
            attrs = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": s["name"],
                     "gen_ai.tool.call.id": s["id"], "gen_ai.tool.type": "function"}
            if content:
                attrs["gen_ai.tool.call.result"] = s["observation"]
            out.append(span(trace, ident(trace, "tool", s["id"]), root, f"execute_tool {s['name']}",
                            "INTERNAL", t - gap, t, attrs))   # the tool's own time isn't recorded
    error = None if row["status"] == "answered" else row["status"]
    agent = {"gen_ai.operation.name": "invoke_agent", "gen_ai.provider.name": PROVIDER,
             "gen_ai.agent.name": AGENT, "gen_ai.request.model": model, "gen_ai.conversation.id": trace}
    if content:
        agent["gen_ai.output.messages"] = output_messages(row["answer"])
    return [span(trace, root, None, f"invoke_agent {AGENT}", "INTERNAL", start, start + row["seconds"],
                 agent, error)] + out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--content", action="store_true", help="also write the replies and tool results")
    ap.add_argument("--limit", type=int, help="only the first N runs")
    a = ap.parse_args(argv)
    rows = A.ch04_rows()[:a.limit]
    model = json.loads((A.CODE / "ch04" / A.CH04_RUN / "manifest.json").read_text())["model"]["tag"]
    t = 1_792_195_200.0                                  # 2026-10-17 00:00 UTC: the run's day, not its clock
    for r in rows:
        for s in spans(r, model, t, a.content):
            print(json.dumps(s))
        t += r["seconds"]


if __name__ == "__main__":
    main()
