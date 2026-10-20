"""The two agent loops' tools: a bare shell, and an agent-computer interface (ACI) after SWE-agent.

Both loops are Chapter 1's agent. What differs is what the model can do and what it sees back.

  shell_tools(work, events)   one tool, shell(command): the command's output, exit status and a
                              time limit, as mini-SWE-agent gives it
  aci_tools(work, events)     view (100 lines at a time, numbered), search (at most 50 results),
                              edit (a range of lines, put back if the file no longer compiles, with
                              the error, the edit and the original shown) and run_tests (dotted
                              test names under tests, or all); no shell
  Collapsed(client)           the ACI's context rule: tool outputs before the last five are cut to
                              one line each before the model sees them

The jail is the same for both: commands and paths are checked against deny-first rules, every
refusal is recorded in `events`, and so is every change to tests/. The rules are a check made by
this code on the text of a command, as Claude Code's permission rules are; they are not a
security boundary, since a program the command starts can do anything its user can. Where that
may run is in README.md.
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.append(str(HERE.parent / "ch01"))
from tools import ToolError                              # noqa: E402  Chapter 1's

import tasks                                             # noqa: E402

SHELL = "cmd.exe" if os.name == "nt" else "/bin/sh"      # what subprocess's shell=True runs
COMMAND_SECONDS = 30
WINDOW, MATCHES, KEEP = 100, 50, 5                      # SWE-agent's viewer, search cap, last-5 rule

# Deny-first: a command matching any rule is refused, whatever else it does.
DENY = [
    ("network", r"\b(curl|wget|ssh|scp|sftp|ftp|telnet|nc|ncat|Invoke-WebRequest|Invoke-RestMethod|iwr|irm"
                r"|bitsadmin|certutil|urllib|requests|http\.client|socket)\b"),
    ("network", r"\bgit\s+(clone|fetch|pull|push|remote|submodule)\b"),
    ("install", r"\b(pip|pip3|conda|npm|npx|winget|choco|apt|apt-get|brew|ensurepip)\b"),
    ("privilege", r"\b(sudo|runas|su|doas)\b"),
    ("system", r"\b(shutdown|reboot|reg|schtasks|crontab|systemctl|sc|netsh|setx)\b"),
    ("outside", r"(^|[\s\"'=(,])~([\\/\s\"')]|$)"),                    # the home folder
    ("outside", r"(^|[\s\"'=(,\\/])\.\.([\\/\s\"')]|$)"),             # a parent, anywhere in a path
    ("outside", r"(^|[\s\"'=(,])([A-Za-z]:[\\/]|\\\\)"),               # a drive or a network path
    ("outside", r"%[A-Za-z_][A-Za-z0-9_]*%|\$\{?[A-Za-z_][A-Za-z0-9_]*"),   # environment variables
]
POSIX_ABSOLUTE = ("outside", r"(^|[\s\"'=(,])/(?!dev/null\b)")     # cmd.exe options start with /
TEST_ID = re.compile(r"tests(\.[A-Za-z_]\w*)*")                    # what run_tests accepts


def denied(command, posix=os.name != "nt"):
    """The name of the first deny rule the command matches, or None. Case is ignored: cmd.exe
    runs CURL as it runs curl."""
    for kind, rx in DENY + ([POSIX_ABSOLUTE] if posix else []):
        if re.search(rx, command, re.IGNORECASE):
            return kind
    return None


class Jail:
    """Paths and commands for one run, all inside `work`."""

    def __init__(self, work, events):
        self.work, self.events = Path(work).resolve(), events
        self.tests = tasks.tree_hash(self.work / "tests")

    def path(self, p, tool):
        """`p` (relative to the work folder) as an absolute path, or ToolError if it leads outside."""
        target = (self.work / str(p).strip().strip("\"'")).resolve()
        if target != self.work and self.work not in target.parents:
            self.events.append({"kind": "refused", "tool": tool, "rule": "outside", "arg": str(p)})
            raise ToolError("not_permitted", f"'{p}' is outside the repository",
                            "Use paths relative to the repository's top folder, e.g. expenses/money.py")
        return target

    def command(self, command):
        rule = denied(command)
        if rule:
            self.events.append({"kind": "refused", "tool": "shell", "rule": rule, "arg": command})
            raise ToolError("not_permitted", f"the command was refused ({rule})",
                            "Work only inside the repository, with no network and no installs.")

    def check_tests(self, tool, arg):
        """Record a change to tests/ (it is allowed; the grader puts tests/ back)."""
        now = tasks.tree_hash(self.work / "tests")
        if now != self.tests:
            self.events.append({"kind": "tests_changed", "tool": tool, "arg": arg})
            self.tests = now


def spec(name, description, props, required):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": {k: {"type": "string", "description": d} for k, d in props.items()},
        "required": required}}}


# -- the bare shell ---------------------------------------------------------------------------------
def shell_tools(work, events):
    jail = Jail(work, events)

    def shell(command):
        jail.command(command)
        code, out = tasks.run(command, jail.work, COMMAND_SECONDS, shell=True)
        jail.check_tests("shell", command)
        events.append({"kind": "command", "arg": command, "exit": code})
        status = f"timed out after {COMMAND_SECONDS} s" if code is None else f"exit status {code}"
        return f"{out}\n[{status}]" if out else f"[{status}]"

    return {"shell": (shell, spec(
        "shell", f"Run one command in {SHELL}, in the repository's top folder, and return its output "
        f"and exit status. Commands are stopped after {COMMAND_SECONDS} seconds.",
        {"command": "the command line"}, ["command"]))}


# -- the agent-computer interface ---------------------------------------------------------------------
def numbered(lines, first):
    return "\n".join(f"{first + i}:{line}" for i, line in enumerate(lines))


def aci_tools(work, events):
    jail = Jail(work, events)

    def view(path, line="1"):
        p = jail.path(path, "view")
        if p.is_dir():
            names = sorted(f"{q.name}/" if q.is_dir() else q.name for q in p.iterdir() if q.name != "__pycache__")
            return "\n".join(names) or "(empty folder)"
        if not p.is_file():
            raise ToolError("not_found", f"no file '{path}'", "view a folder, e.g. view(path='.'), to see its files")
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        try:
            first = max(1, int(str(line).strip()))
        except ValueError:
            raise ToolError("bad_arguments", f"line must be a number, not '{line}'", "e.g. line='1'")
        chunk = lines[first - 1:first - 1 + WINDOW]
        above, below = first - 1, max(0, len(lines) - (first - 1 + WINDOW))
        head = f"[File: {path} ({len(lines)} lines total)]"
        return "\n".join([head] + ([f"({above} more lines above)"] if above else [])
                         + [numbered(chunk, first)] + ([f"({below} more lines below)"] if below else []))

    def search(text, path="."):
        root = jail.path(path, "search")
        files = [root] if root.is_file() else sorted(q for q in root.rglob("*") if q.is_file()
                                                     and q.suffix in (".py", ".md") and "__pycache__" not in q.parts)
        hits = []
        for f in files:
            for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if text in line:
                    hits.append(f"{f.relative_to(jail.work).as_posix()}:{i}:{line.strip()}")
        if not hits:
            return f"No matches found for '{text}' in {path}."
        if len(hits) > MATCHES:
            return f"More than {MATCHES} lines match '{text}'. Search a narrower path or a longer text."
        return f"{len(hits)} matches for '{text}':\n" + "\n".join(hits)

    def edit(path, start, end, text):
        p = jail.path(path, "edit")
        if not p.is_file():
            raise ToolError("not_found", f"no file '{path}'", "Only existing files can be edited.")
        try:
            a, b = int(str(start).strip()), int(str(end).strip())
        except ValueError:
            raise ToolError("bad_arguments", "start and end must be line numbers", "e.g. start='12', end='14'")
        old = p.read_text(encoding="utf-8").splitlines()
        if not (1 <= a <= len(old) + 1 and a - 1 <= b <= len(old)):
            raise ToolError("bad_arguments", f"lines {a}-{b} are not in the file ({len(old)} lines)",
                            "end may be start - 1 to insert before line start")
        added = text.split("\n")
        new = old[:a - 1] + added + old[b:]
        body = "\n".join(new) + "\n"
        if p.suffix == ".py":
            try:
                compile(body, str(p), "exec")
            except SyntaxError as e:
                events.append({"kind": "edit_reverted", "arg": f"{path}:{a}-{b}", "error": e.msg})
                lo = max(1, a - 3)
                return ("Your proposed edit has introduced new syntax error(s). Please read this error message "
                        f"carefully and then retry editing the file.\n\nERRORS:\n- line {e.lineno}: {e.msg}\n\n"
                        "This is how your edit would have looked if applied\n-------------------------------------\n"
                        + numbered(new[lo - 1:a + len(added) + 2], lo)
                        + "\n-------------------------------------\n\nThis is the original code before your edit\n"
                        "-------------------------------------\n" + numbered(old[lo - 1:b + 3], lo)
                        + "\n-------------------------------------\nYour changes have NOT been applied. Please fix "
                        "your edit command and try again.\nDO NOT re-run the same failed edit command. Running it "
                        "again will lead to the same error.")
        p.write_text(body, encoding="utf-8")
        jail.check_tests("edit", f"{path}:{a}-{b}")
        events.append({"kind": "edit", "arg": f"{path}:{a}-{b}"})
        lo = max(1, a - 3)
        return f"[File: {path} ({len(new)} lines total), lines {a}-{b} replaced]\n" + numbered(
            new[lo - 1:a + len(added) + 2], lo)

    def run_tests(tests=""):
        names = tests.split()
        bad = [n for n in names if not TEST_ID.fullmatch(n)]
        if bad:
            events.append({"kind": "refused", "tool": "run_tests", "rule": "test_ids", "arg": tests})
            raise ToolError("bad_arguments", f"not test names: {' '.join(bad)}",
                            "Give dotted test names under tests, e.g. tests.test_money, or nothing for all tests.")
        code, out = tasks.run([sys.executable, "-m", "unittest", *(names or ["discover", "-s", "tests", "-t", "."])],
                              jail.work, tasks.TIMEOUT)
        jail.check_tests("run_tests", tests)
        events.append({"kind": "tests_run", "arg": tests, "exit": code})
        return out if code is not None else out + f"\n[timed out after {tasks.TIMEOUT} s]"

    return {
        "view": (view, spec("view", f"Show {WINDOW} lines of a file, numbered, starting at `line`; or list a "
                            "folder.", {"path": "a file or folder, relative to the repository's top folder",
                                        "line": "the first line to show (default 1)"}, ["path"])),
        "search": (search, spec("search", f"Find the lines that contain `text` in the .py and .md files under "
                                f"`path` (default: the whole repository); at most {MATCHES} results.",
                                {"text": "the text to find (not a regular expression)",
                                 "path": "a file or folder (default '.')"}, ["text"])),
        "edit": (edit, spec("edit", "Replace lines start to end (both included) of a file with `text`. To "
                            "insert without replacing, use end = start - 1. An edit that leaves a .py file "
                            "with a syntax error is not applied.",
                            {"path": "the file", "start": "first line to replace", "end": "last line to replace",
                             "text": "the new lines, with their indentation"}, ["path", "start", "end", "text"])),
        "run_tests": (run_tests, spec("run_tests", "Run the unit tests and show unittest's output.",
                                      {"tests": "test names separated by spaces, e.g. tests.test_money "
                                                "(default: all tests)"}, [])),
    }


class Collapsed:
    """The model client, with each tool output before the last KEEP replaced by one line, as SWE-agent's
    history processor does. The agent's own messages are not changed; only what is sent is."""

    def __init__(self, client, keep=KEEP):
        self.client, self.keep = client, keep

    def chat(self, messages, tools=None):
        tool_at = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
        old = set(tool_at[:-self.keep]) if len(tool_at) > self.keep else set()
        sent = [{**m, "content": f"Old tool output omitted ({len(str(m.get('content', '')).splitlines())} lines)."}
                if i in old else m for i, m in enumerate(messages)]
        return self.client.chat(sent, tools)


SYSTEM = """You fix bugs in a Python repository. Your working folder is the repository's top folder;
{how}
Read AGENTS.md first. Change only the code in expenses/, never tests/. Check your fix by running the
tests. When the issue is fixed, reply with one or two sentences saying what you changed, and no tool call."""
HOW = {"shell": f"you have one tool, shell, which runs a command in {SHELL} there.",
       "aci": "you have four tools: view, search, edit and run_tests. There is no shell."}


def task_prompt(task):
    return f"Fix this issue:\n\n{task['issue']}"
