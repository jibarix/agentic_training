"""The three tools of the handbook agent: lookup, read_file, calculator."""
import ast
import difflib
import math
import operator
import re
from pathlib import Path

HANDBOOK = Path(__file__).parent / "handbook"


class ToolError(Exception):
    """A failure the model can act on. `hint` says how to fix the call."""

    def __init__(self, kind, message, hint=""):
        super().__init__(message)
        self.kind, self.hint = kind, hint


# ---- lookup -----------------------------------------------------------------
def _lines():
    """Every handbook line as (file, line, table header or None)."""
    out = []
    for f in sorted(HANDBOOK.glob("*.md")):
        header = None
        for line in f.read_text(encoding="utf-8").splitlines():
            line = re.sub(r"\s+", " ", line.strip())
            if not line or set(line) <= set("|-# "):
                continue
            if line.startswith("|") and header is None:
                header = line                       # first row of a table
            elif not line.startswith("|"):
                header = None
            out.append((f.name, line, header if line.startswith("|") and line != header else None))
    return out


def lookup_v1(query: str) -> str:
    """First version: counts query words found anywhere in a line (substring match)."""
    words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]
    if not words:
        raise ToolError("bad_arguments", "query has no searchable words",
                        "Use one or two keywords, e.g. 'mileage'.")
    hits = [(sum(w in line.lower() for w in words), name, line) for name, line, _ in _lines()]
    hits = sorted((h for h in hits if h[0]), key=lambda h: -h[0])
    if not hits:
        return "No matches. Files: " + ", ".join(p.name for p in sorted(HANDBOOK.glob("*.md")))
    return "\n".join(f"{name}: {line}" for _, name, line in hits[:5])


def lookup(query: str) -> str:
    """Fixed version: whole words, rare words weigh more (IDF), table rows keep their header."""
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not words:
        raise ToolError("bad_arguments", "query has no searchable words",
                        "Use one or two keywords, e.g. 'mileage'.")
    lines = _lines()
    toks = [set(re.findall(r"[a-z0-9]+", line.lower())) for _, line, _ in lines]
    idf = {w: math.log(len(lines) / (1 + sum(w in t for t in toks))) for w in words}
    hits = [(sum(max(idf[w], 0) for w in words & t), i) for i, t in enumerate(toks)]
    hits = sorted((h for h in hits if h[0] > 0), key=lambda h: -h[0])
    if not hits:
        return "No matches. Files: " + ", ".join(p.name for p in sorted(HANDBOOK.glob("*.md")))
    out = []
    for _, i in hits[:5]:
        name, line, header = lines[i]
        out.append(f"{name}: {header} / {line}" if header else f"{name}: {line}")
    return "\n".join(out)


# ---- read_file --------------------------------------------------------------
def read_file(path: str) -> str:
    target = (HANDBOOK / path).resolve()
    if HANDBOOK.resolve() not in target.parents:
        raise ToolError("permission_denied", f"'{path}' is outside the handbook",
                        "Pass a bare file name.")
    if not target.is_file():
        names = [p.name for p in sorted(HANDBOOK.glob("*.md"))]
        close = difflib.get_close_matches(path, names, n=1, cutoff=0.4)
        hint = f"Did you mean '{close[0]}'? " if close else ""
        hint += "Available files: " + ", ".join(names)
        raise ToolError("not_found", f"no file named '{path}'", hint)
    return target.read_text(encoding="utf-8")


# ---- calculator -------------------------------------------------------------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
_ALLOWED = "Allowed: numbers, + - * / ** and parentheses. Example: (3 * 68) + 2 ** 3"


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitXor):
        raise ToolError("bad_expression", "'^' is not a power operator here",
                        "Use ** for powers. " + _ALLOWED)
    raise ToolError("bad_expression", f"unsupported element {type(node).__name__}", _ALLOWED)


def calculator(expression: str) -> str:
    expr = expression.replace(",", "").replace("$", "").strip()
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise ToolError("bad_expression", f"cannot parse '{expression}'", _ALLOWED)
    try:
        value = _eval(tree.body)
    except ZeroDivisionError:
        raise ToolError("bad_expression", "division by zero", "Check the divisor.")
    return f"{round(value, 6):g}" if isinstance(value, float) else str(value)


# ---- registry: name -> (function, JSON schema) -------------------------------
def spec(name, description, **props):
    params = {k: {"type": "string", "description": d} for k, d in props.items()}
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "required": list(props), "properties": params}}}


TOOLS = {
    "lookup": (lookup, spec(
        "lookup", "Keyword search over the company handbook. Returns 'file: matching line' pairs.",
        query="One or two keywords, e.g. 'per diem Denver'.")),
    "read_file": (read_file, spec(
        "read_file", "Read one handbook file in full.",
        path="File name as returned by lookup, e.g. 'mileage.md'.")),
    "calculator": (calculator, spec(
        "calculator", "Evaluate an arithmetic expression exactly. Use it for every calculation.",
        expression="Arithmetic only, e.g. '4 * 68'.")),
}


# The registry as first written, before the lookup fix (used by experiment.py).
TOOLS_V1 = {**TOOLS, "lookup": (lookup_v1, TOOLS["lookup"][1])}
