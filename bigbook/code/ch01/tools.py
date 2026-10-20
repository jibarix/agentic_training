"""The three tools of the handbook agent: lookup, read_file, calculator."""
import ast
import difflib
import math
import operator
import re
from fractions import Fraction
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
# Exact arithmetic on fractions, so 1800 * 1.04 ** 3 is 2024.7552, not a rounded float.
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
_ALLOWED = "Allowed: numbers, + - * / ** and parentheses. Example: (3 * 68) + 2 ** 3"
_MAX_CHARS, _MAX_EXP, _MAX_DIGITS = 200, 100, 40    # bounds: input, exponent, result


def _check(q):
    if max(abs(q.numerator), q.denominator) >= 10 ** _MAX_DIGITS:
        raise ToolError("bad_expression", "a number is too large",
                        f"Results are limited to {_MAX_DIGITS} digits.")
    return q


def _eval(node, src):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        text = ast.get_source_segment(src, node).replace("_", "")
        try:
            return _check(Fraction(text))                   # from the text: 1.04 -> 26/25
        except ValueError:                                  # 0x10 and the like
            return _check(Fraction(node.value))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        base, exp = _eval(node.left, src), _eval(node.right, src)
        if exp.denominator != 1:
            raise ToolError("bad_expression", "powers must be whole numbers", _ALLOWED)
        size = max(len(str(base.numerator)), len(str(base.denominator)))
        if abs(exp) > _MAX_EXP or (size - 1) * abs(exp) > _MAX_DIGITS:
            raise ToolError("bad_expression", "a number is too large",
                            f"Results are limited to {_MAX_DIGITS} digits.")
        if base == 0 and exp < 0:
            raise ToolError("bad_expression", "division by zero", "Check the divisor.")
        return _check(base ** int(exp))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _check(_OPS[type(node.op)](_eval(node.left, src), _eval(node.right, src)))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand, src))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitXor):
        raise ToolError("bad_expression", "'^' is not a power operator here",
                        "Use ** for powers. " + _ALLOWED)
    raise ToolError("bad_expression", f"unsupported element {type(node).__name__}", _ALLOWED)


def _show(q):
    """A fraction as a decimal: exact when it terminates, else 10 significant digits, marked."""
    den, twos, fives = q.denominator, 0, 0
    while den % 2 == 0:
        den, twos = den // 2, twos + 1
    while den % 5 == 0:
        den, fives = den // 5, fives + 1
    exact = den == 1                                        # only 2s and 5s: it terminates
    if exact:
        places = max(twos, fives)
    else:                                                   # leading digit at 10**lead
        lead = len(str(abs(q.numerator))) - len(str(q.denominator))
        while Fraction(10) ** lead > abs(q):
            lead -= 1
        while Fraction(10) ** (lead + 1) <= abs(q):
            lead += 1
        places = max(10, 9 - lead)
    n = round(q * 10 ** places)
    digits = str(abs(n)).rjust(places + 1, "0")
    whole, frac = digits[:len(digits) - places], digits[len(digits) - places:].rstrip("0")
    text = ("-" if n < 0 else "") + whole + ("." + frac if frac else "")
    return text if exact else text + " (rounded)"


def calculator(expression: str) -> str:
    expr = expression.replace(",", "").replace("$", "").strip()
    if len(expr) > _MAX_CHARS:
        raise ToolError("bad_expression", f"expression longer than {_MAX_CHARS} characters",
                        "Split the calculation into steps.")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        raise ToolError("bad_expression", f"cannot parse '{expression}'", _ALLOWED)
    try:
        return _show(_eval(tree.body, expr))
    except ZeroDivisionError:
        raise ToolError("bad_expression", "division by zero", "Check the divisor.")


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
        "calculator", "Evaluate an arithmetic expression with exact decimal arithmetic. A result that does not terminate (1 / 3) is rounded and marked. Use it for every calculation.",
        expression="Arithmetic only, e.g. '4 * 68'.")),
}


# The registry as first written, before the lookup fix (used by experiment.py).
TOOLS_V1 = {**TOOLS, "lookup": (lookup_v1, TOOLS["lookup"][1])}
