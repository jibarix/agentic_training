"""Chapter 7's tasks: bugs put into a small repository on purpose, and the grader that checks a fix.

The repository (repo/) is the book's own: five modules of an expense package and 52 unit tests,
written for this chapter and not published before it was used. Each task is one
mutation of the code, never of the tests (CMU 11-768 L6, after SWE-smith: "Mutate code, not
tests"), with a short issue written as a user would report it. A mutation is kept only if some
tests fail with it and every test passes without it; the failing ones are its FAIL_TO_PASS tests,
the rest its PASS_TO_PASS, as in SWE-bench.

  start(task, dest)    the repository with the bug in it, and the FAIL_TO_PASS tests taken out:
                       the agent sees the issue, not the test that will judge the fix
  grade(task, work)    a fresh copy of what the agent left, with tests/ put back as it was, and
                       both lists run in a child process with a time limit

  python tasks.py      checks every mutation and writes tasks.json
"""
import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE / "repo"
RUNNER = HERE / "runner.py"
TASKS = HERE / "tasks.json"
TIMEOUT = 60                                     # seconds for one run of the tests

# id, file, [(old, new), ...], issue. Each old text must appear exactly once in the file.
MUTATIONS = [
    ("money_half_up", "expenses/money.py",
     [("from decimal import ROUND_HALF_UP, Decimal", "from decimal import ROUND_HALF_EVEN, Decimal"),
      ("rounding=ROUND_HALF_UP)", "rounding=ROUND_HALF_EVEN)")],
     "Amounts that end in exactly half a cent are sometimes rounded down. round_cents(Decimal('2.665')) "
     "returns 2.66, but company policy (and the docstring) is that half a cent always rounds up, so it "
     "should be 2.67."),
    ("money_dollar", "expenses/money.py",
     [('if s.startswith("$"):', 'if s.endswith("$"):')],
     "parse_amount('$12') raises ValueError: not an amount. The docstring says a leading dollar sign "
     "is allowed, and the bank export writes amounts that way."),
    ("money_blank", "expenses/money.py",
     [("    if not s:\n        return None", "    if s is None:\n        return None")],
     "parse_amount('   ') raises ValueError for a blank cell in the spreadsheet import. Empty or blank "
     "text should give None, as the docstring says."),
    ("money_zero", "expenses/money.py",
     [("value < 0:", "value <= 0:")],
     "parse_amount('0') raises ValueError. Zero is a valid amount (a waived fee, for example); only "
     "negative amounts should be refused."),
    ("money_thousands", "expenses/money.py",
     [('return f"{round_cents(value):,.2f} {currency}"', 'return f"{round_cents(value):.2f} {currency}"')],
     "format_amount(Decimal('25000')) gives '25000.00 USD'. Large amounts should be written with a "
     "thousands separator, '25,000.00 USD', as the docstring shows."),
    ("money_split", "expenses/money.py",
     [("1 if i < extra else 0", "1 if i <= extra else 0")],
     "split(Decimal('20.00'), 3) returns parts that add up to 20.01, and split(Decimal('9.00'), 3) "
     "doesn't give three equal parts. The parts must add up to the total exactly."),
    ("dates_spaces", "expenses/dates.py",
     [("s = str(text).strip()", "s = str(text)")],
     "parse_date(' 2026-05-04') raises ValueError when the date has a space before it, as dates do "
     "in the travel agency's CSV files. Spaces around the date should be ignored."),
    ("dates_same_day", "expenses/dates.py",
     [("    if n < 0:\n", "    if n <= 0:\n")],
     "nights() raises 'check-out is before check-in' when the check-in and check-out are on the same "
     "date (a day room). That is 0 nights, not an error."),
    ("dates_travel_days", "expenses/dates.py",
     [("return (end - start).days + 1", "return (end - start).days")],
     "travel_days(date(2026, 5, 4), date(2026, 5, 6)) returns 2, but the trip covers three days: "
     "the first and the last day both count."),
    ("dates_saturday", "expenses/dates.py",
     [("return day.weekday() >= 5", "return day.weekday() > 5")],
     "is_weekend() returns False for Saturdays, so Saturday travel isn't flagged for approval."),
    ("dates_quarter", "expenses/dates.py",
     [("return (day.month - 1) // 3 + 1", "return day.month // 3 + 1")],
     "quarter(date(2026, 3, 31)) is 2, but March is in the first quarter. The months at the end of "
     "the other quarters are wrong too, and December gives 5."),
    ("rates_city_spaces", "expenses/rates.py",
     [("return city.strip().lower()", "return city.lower()")],
     "rate(' Boston ', 'meals') returns the default rate, 59, instead of Boston's 79, when the city "
     "name has spaces around it."),
    ("rates_default", "expenses/rates.py",
     [("return RATES.get(city_key(city), DEFAULT)[kind]", "return RATES[city_key(city)][kind]")],
     "rate('Albany', 'meals') raises KeyError: 'albany'. A city that isn't in the table should get "
     "the default rates."),
    ("rates_one_day", "expenses/rates.py",
     [("return round_cents(r * PARTIAL)", "return round_cents(r)")],
     "meals_allowance(city, 1) pays the full daily rate for a one-day trip. The policy, and the "
     "docstring, give 75% of it once."),
    ("rates_middle_days", "expenses/rates.py",
     [("r * (days - 2)", "r * (days - 1)")],
     "The meals allowance for a trip of two days or more is one full day's rate too high: "
     "meals_allowance('Chicago', 3) is 276.50 USD, and should be 197.50 USD."),
    ("rates_mileage", "expenses/rates.py",
     [('MILEAGE = Decimal("0.70")', 'MILEAGE = Decimal("0.67")')],
     "mileage(100) gives 67.00 USD. The mileage rate was raised to 0.70 USD per mile this year, so "
     "it should be 70.00 USD."),
    ("claims_receipt", "expenses/claims.py",
     [("line.amount > RECEIPT_OVER", "line.amount >= RECEIPT_OVER")],
     "A line of exactly 75.00 is flagged 'receipt required'. Receipts are needed only for lines above "
     "75.00."),
    ("claims_zero", "expenses/claims.py",
     [("if line.amount <= 0:", "if line.amount < 0:")],
     "problems() accepts a line with an amount of 0.00. It should report 'amount must be positive'."),
    ("claims_cap", "expenses/claims.py",
     [("t > caps[kind]", "t >= caps[kind]")],
     "over_cap() reports a kind whose total is exactly equal to its cap. Only a total above the cap "
     "is over it."),
    ("claims_no_cap", "expenses/claims.py",
     [("if kind in caps and t > caps[kind]", 'if t > caps.get(kind, Decimal("0"))')],
     "over_cap(lines, {}) lists every kind. A kind that has no cap in caps should never be over."),
    ("claims_duplicate_kind", "expenses/claims.py",
     [("(a.kind, a.amount, a.day) == (b.kind, b.amount, b.day)", "(a.amount, a.day) == (b.amount, b.day)")],
     "duplicates() reports a meals line and an 'other' line with the same amount and day as a "
     "duplicate. Lines of different kinds are different expenses."),
    ("claims_kind_order", "expenses/claims.py",
     [("    for kind in KINDS:\n        mine", "    for kind in sorted(KINDS):\n        mine")],
     "by_kind() and the claim summary list lodging before meals. Kinds should come in the order of "
     "KINDS: meals, lodging, mileage, other."),
    ("summary_csv_quote", "expenses/summary.py",
     [('csv.writer(buf, lineterminator="\\n")',
       'csv.writer(buf, lineterminator="\\n", quoting=csv.QUOTE_NONE, escapechar="\\\\")')],
     "to_csv() writes a note that contains a comma as lunch\\, team instead of quoting it, and the "
     "finance system reads that as two columns."),
    ("summary_largest_ties", "expenses/summary.py",
     [("sorted(lines, key=lambda line: (-line.amount, line.day))", "sorted(lines, key=lambda line: line.amount, reverse=True)")],
     "largest() returns lines with equal amounts in the order they were entered. Of two equal "
     "amounts, the line with the earlier day should come first."),
]


def apply(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise ValueError(f"the text to mutate appears {text.count(old)} times: {old!r}")
        text = text.replace(old, new)
    return text


def copy_repo(src, dest):
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return Path(dest)


def clean_env(work):
    """The environment for code a model wrote: the interpreter first on PATH, home and temp inside
    the work folder, and nothing else of the user's (no tokens or keys that live in variables)."""
    tmp = Path(work).parent / (Path(work).name + ".tmp")
    tmp.mkdir(exist_ok=True)
    env = {"PATH": os.pathsep.join([str(Path(sys.executable).parent), os.environ.get("PATH", "")]),
           "HOME": str(work), "USERPROFILE": str(work), "TEMP": str(tmp), "TMP": str(tmp),
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    for k in ("SYSTEMROOT", "COMSPEC", "PATHEXT", "WINDIR"):    # Windows needs these to start programs
        if k in os.environ:
            env[k] = os.environ[k]
    return env


def run(args, cwd, timeout, shell=False):
    """(exit status or None on timeout, output). A command that runs too long is killed with its
    children: the process gets its own group so that a test it starts dies with it."""
    kw = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
          else {"start_new_session": True})
    p = subprocess.Popen(args, cwd=cwd, env=clean_env(cwd), shell=shell, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kw)
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
        else:
            os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
        return None, out.decode("utf-8", "replace")


def run_tests(repo, ids=(), timeout=TIMEOUT):
    """{test id: outcome} for the given ids, or for every test; on a timeout, every id is "timeout"."""
    code, out = run([sys.executable, "-I", str(RUNNER), str(repo), *ids], repo, timeout)
    if code is None:
        return {i: "timeout" for i in ids} or {"(suite)": "timeout"}
    try:
        if code != 0:                                    # the runner didn't finish normally
            raise ValueError
        res = json.loads(out.strip().splitlines()[-1])
        if not isinstance(res, dict):
            raise ValueError
        return res
    except (ValueError, IndexError):
        return {i: "error" for i in ids} or {"(suite)": "error"}


def hide(text, names):
    """A test module's text without the test methods in `names` ({"Class.method"}); a class left
    with no test is taken out whole."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    cut = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods = [f for f in node.body if isinstance(f, ast.FunctionDef)]
        gone = [f for f in methods if f"{node.name}.{f.name}" in names]
        if gone and len(gone) == len(node.body):
            cut.append(node)
        else:
            cut += gone
    for node in sorted(cut, key=lambda n: n.lineno, reverse=True):
        first = min([node.lineno] + [d.lineno for d in node.decorator_list]) - 1
        last = node.end_lineno
        while first > 0 and not lines[first - 1].strip():   # with the blank lines before it
            first -= 1
        del lines[first:last]
    out = "".join(lines)
    ast.parse(out)
    return out


def start(task, dest):
    """The task's starting repository in `dest`: the bug in, the FAIL_TO_PASS tests out."""
    dest = copy_repo(REPO, dest)
    p = dest / task["file"]
    p.write_text(apply(p.read_text(encoding="utf-8"), task["edits"]), encoding="utf-8")
    hidden = {}
    for tid in task["FAIL_TO_PASS"]:
        mod, cls, meth = tid.rsplit(".", 2)
        hidden.setdefault(mod, set()).add(f"{cls}.{meth}")
    for mod, names in hidden.items():
        f = dest / (mod.replace(".", "/") + ".py")
        f.write_text(hide(f.read_text(encoding="utf-8"), names), encoding="utf-8")
    return dest


def tree_hash(folder):
    """sha256 over every file under `folder` (paths and contents), caches left out."""
    h = hashlib.sha256()
    folder = Path(folder)
    for p in sorted(folder.rglob("*")) if folder.exists() else []:
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.relative_to(folder).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def source_files(folder):
    folder = Path(folder)
    return {p.relative_to(folder).as_posix(): p for p in sorted(folder.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.relative_to(folder).parts[0] != "tests"}


def diff(before, after):
    """A unified diff of everything outside tests/ between two folders."""
    a, b = source_files(before), source_files(after)
    out = []
    for name in sorted(set(a) | set(b)):
        x = a[name].read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if name in a else []
        y = b[name].read_text(encoding="utf-8", errors="replace").splitlines(keepends=True) if name in b else []
        out += difflib.unified_diff(x, y, f"a/{name}", f"b/{name}")
    return "".join(out)


SUSPECT = re.compile(r"\bunittest\b|\bsys\.(modules|exit|stdout|stderr|argv)\b|\b__builtins__\b|\bbuiltins\b"
                     r"|\bos\._exit\b|\batexit\b|\bsetattr\s*\(|\bimportlib\b|\bprint\s*\(|\bexec\s*\(|\beval\s*\(")


def suspect(patch):
    """The added lines of a patch that reach for the test machinery, the process or the output a
    grader reads (none of the repository's own code does). A flag to read, not a verdict."""
    return [line[1:] for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++") and SUSPECT.search(line)]


def grade(task, work, timeout=TIMEOUT):
    """Whether the work fixes the task. The work's files outside tests/ are copied to a fresh
    folder, with tests/ from the original repository, so no edit the agent made to the tests can
    change the verdict (CMU 11-768 A1; NIST's grader restores test files). The code it wrote
    still runs inside the test process, and code written to fool the runner could: see suspect."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "repo"
        fresh.mkdir()
        for name, p in source_files(work).items():
            (fresh / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, fresh / name)
        shutil.copytree(REPO / "tests", fresh / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        res = run_tests(fresh, task["FAIL_TO_PASS"] + task["PASS_TO_PASS"], timeout)
    f2p = sum(res.get(t) == "pass" for t in task["FAIL_TO_PASS"])
    p2p = sum(res.get(t) == "pass" for t in task["PASS_TO_PASS"])
    return {"resolved": f2p == len(task["FAIL_TO_PASS"]) and p2p == len(task["PASS_TO_PASS"]),
            "f2p": f2p, "p2p": p2p, "timeout": "timeout" in res.values(), "outcomes": res}


def make_tasks():
    """Every mutation checked: the clean repository passes all its tests, the mutated one fails some."""
    with tempfile.TemporaryDirectory() as tmp:
        clean = run_tests(REPO)
        bad = sorted(t for t, v in clean.items() if v != "pass")
        if bad:
            raise SystemExit(f"the clean repository fails tests: {bad}")
        out = []
        for i, (tid, file, edits, issue) in enumerate(MUTATIONS):
            work = copy_repo(REPO, Path(tmp) / str(i))
            p = work / file
            p.write_text(apply(p.read_text(encoding="utf-8"), edits), encoding="utf-8")
            res = run_tests(work)
            if set(res) != set(clean):
                raise SystemExit(f"{tid}: the mutated repository has different tests")
            f2p = sorted(t for t, v in res.items() if v != "pass")
            if not f2p:
                raise SystemExit(f"{tid}: no test fails with this mutation")
            out.append({"id": tid, "file": file, "edits": [list(e) for e in edits], "issue": issue,
                        "FAIL_TO_PASS": f2p, "PASS_TO_PASS": sorted(set(clean) - set(f2p))})
    return out


def load():
    return json.loads(TASKS.read_text(encoding="utf-8"))


if __name__ == "__main__":
    tasks = make_tasks()
    TASKS.write_text(json.dumps(tasks, indent=1) + "\n", encoding="utf-8")
    for t in tasks:
        print(f"{t['id']:24} FAIL_TO_PASS {len(t['FAIL_TO_PASS'])}  PASS_TO_PASS {len(t['PASS_TO_PASS'])}")
    print(f"{len(tasks)} tasks -> {TASKS}")
