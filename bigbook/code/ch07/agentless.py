"""A fixed pipeline after Agentless (Xia et al. 2024): localise, repair, validate. No loop.

  1. file      the model is shown the repository's files and the issue, and names one file
  2. element   it is shown that file's skeleton (signatures, docstrings, module constants) and names
               the functions or constants to change
  3. repair    it is shown their code, with the file's imports, and writes a search/replace edit; SAMPLES samples, each from
               its own client (its own seed)
  4. validate  each edit that applies and compiles is run against the repository's visible tests;
               of the ones that break fewest, the most common (after normalising with ast) is kept

Agentless also writes reproduction tests and samples several localisations; this version leaves
both out, so its step 4 sees only the tests the agent was given.
"""
import ast
import re
import tempfile
from collections import Counter
from pathlib import Path

import tasks

SAMPLES = 4
FILE = """Here is an issue reported in a Python repository, and the repository's files.

ISSUE:
{issue}

FILES:
{files}

Which one file in expenses/ most likely has to change to fix the issue? Reply with its path only."""
ELEMENT = """Here is an issue and the skeleton of {path}: its functions' signatures and docstrings, and
its module-level names.

ISSUE:
{issue}

SKELETON OF {path}:
{skeleton}

Which functions or module-level names have to change to fix the issue? Reply with their names only,
one per line, at most three."""
REPAIR = """Here is an issue and the code that most likely has to change.

ISSUE:
{issue}

CODE FROM {path}:
{code}

Write the fix as one or more search/replace edits in exactly this format:

<<<<<<< SEARCH
lines copied exactly from the code above
=======
the lines to put in their place
>>>>>>> REPLACE

Copy the SEARCH lines exactly, indentation included, and make them long enough to appear only once.
Change nothing else."""
EDIT = re.compile(r"<<<<<<< SEARCH\n(.*?)\n?=======\n(.*?)\n?>>>>>>> REPLACE", re.S)


def ask(client, prompt, calls):
    msg, usage = client.chat([{"role": "user", "content": prompt}])
    text = msg.get("content") if isinstance(msg, dict) and isinstance(msg.get("content"), str) else ""
    calls.append({"prompt": prompt[:200], "reply": text, "tokens": (usage or {}).get("total_tokens")})
    return text


def files(work):
    return sorted(p.relative_to(work).as_posix() for p in Path(work).rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts)


def first_named(text, names, key=lambda n: n):
    """The name in `names` that `text` mentions first, or None."""
    found = [(m.start(), n) for n in names for m in re.finditer(r"(?<![\w/.])" + re.escape(key(n)) + r"(?![\w])", text)]
    return min(found)[1] if found else None


def elements(source):
    """{name: (first line, last line)} for each top-level function, class and assigned name."""
    out = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            out[node.name] = (first, node.end_lineno)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in node.targets if isinstance(node, ast.Assign) else [node.target]:
                if isinstance(t, ast.Name):
                    out[t.id] = (node.lineno, node.end_lineno)
    return out


def skeleton(source):
    lines, out = source.splitlines(), []
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            head = lines[node.lineno - 1]
            doc = ast.get_docstring(node)
            out.append(head + (f'\n    """{doc}"""' if doc else "") + "\n    ...")
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom)):
            out.append("\n".join(lines[node.lineno - 1:node.end_lineno]))
    return "\n".join(out)


def edits(reply):
    return [(s, r) for s, r in EDIT.findall(reply.replace("\r\n", "\n"))]


def patched(source, pairs):
    """The source with the edits made, or None if any SEARCH text is not there exactly once."""
    if not pairs:
        return None
    for search, replace in pairs:
        if not search.strip() or source.count(search) != 1:
            return None
        source = source.replace(search, replace)
    return source


def normal(source):
    """The source's syntax tree as text, for the vote; None if it doesn't compile (ast.parse alone
    accepts a `return` outside a function)."""
    try:
        compile(source, "<repair>", "exec")
        return ast.dump(ast.parse(source))
    except (SyntaxError, ValueError):
        return None


def run(task, work, client, samples, events):
    """Fix `task` in the folder `work`: `client` localises, each client in `samples` writes one repair.
    Returns a summary; the chosen edit, if any, is written into `work`."""
    work, calls = Path(work), []
    info = {"file": None, "names": [], "candidates": [], "chosen": None, "calls": calls}
    sources = [f for f in files(work) if f.startswith("expenses/") and f.endswith(".py")]
    reply = ask(client, FILE.format(issue=task["issue"], files="\n".join(files(work))), calls)
    path = first_named(reply, sources) or first_named(reply, sources, key=lambda n: n.rsplit("/", 1)[-1])
    info["file"] = path
    if path is None:
        return info
    source = (work / path).read_text(encoding="utf-8")
    spans = elements(source)
    reply = ask(client, ELEMENT.format(issue=task["issue"], path=path, skeleton=skeleton(source)), calls)
    at = {n: m.start() for n in spans for m in [re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", reply)] if m}
    names = sorted(at, key=at.get)[:3]
    info["names"] = names
    if not names:
        return info
    lines = source.splitlines()
    imports = [(n.lineno, n.end_lineno) for n in ast.parse(source).body if isinstance(n, (ast.Import, ast.ImportFrom))]
    code = "\n\n".join("\n".join(lines[a - 1:b]) for a, b in sorted(set(imports) | {spans[n] for n in names}))
    prompt = REPAIR.format(issue=task["issue"], path=path, code=code)
    visible = tasks.run_tests(work)
    passing = {t for t, v in visible.items() if v == "pass"}
    with tempfile.TemporaryDirectory() as tmp:
        for i, c in enumerate(samples):
            cand = {"sample": i, "applied": False}
            info["candidates"].append(cand)
            new = patched(source, edits(ask(c, prompt, calls)))
            if new is None or normal(new) is None:
                events.append({"kind": "edit_failed", "arg": f"sample {i}"})
                continue
            trial = tasks.copy_repo(work, Path(tmp) / str(i))
            (trial / path).write_text(new, encoding="utf-8")
            res = tasks.run_tests(trial)
            cand |= {"applied": True, "broken": sorted(t for t in passing if res.get(t) != "pass"),
                     "key": normal(new), "source": new}
    ok = [c for c in info["candidates"] if c["applied"]]
    if ok:
        fewest = min(len(c["broken"]) for c in ok)
        best = [c for c in ok if len(c["broken"]) == fewest]
        votes = Counter(c["key"] for c in best)
        top = max(votes.values())
        chosen = next(c for c in best if votes[c["key"]] == top)     # a tie goes to the earliest sample
        (work / path).write_text(chosen["source"], encoding="utf-8")
        info["chosen"] = chosen["sample"]
    for c in info["candidates"]:
        c.pop("source", None)
        c.pop("key", None)
    return info
