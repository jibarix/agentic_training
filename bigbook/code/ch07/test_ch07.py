"""Offline tests for Chapter 7: the tasks and their issues, the grader, the jail, the ACI's tools,
the context rule, the Agentless pipeline and one run of each arm. No model: scripted replies stand
in for it, so every command and edit here is one these tests wrote.

Usage: python -m unittest -v test_ch07
"""
import importlib
import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

import tasks
import harness                                           # sets the path to Chapter 1
import agentless
import experiment                                        # and to Chapter 5
import report
from llm import ScriptedClient, call                     # Chapter 1's
from tools import ToolError                              # Chapter 1's

HERE = Path(__file__).parent
TASKS = {t["id"]: t for t in tasks.load()}

# Each issue's concrete claim: (expression, its value with the bug, its value without it).
CLAIMS = {
    "money_half_up": ["str(money.round_cents(Decimal('2.665')))", "2.66", "2.67"],
    "money_dollar": ["safe(lambda: money.parse_amount('$12'))", "ValueError", "12.00"],
    "money_blank": ["safe(lambda: money.parse_amount('   '))", "ValueError", "None"],
    "money_zero": ["safe(lambda: money.parse_amount('0'))", "ValueError", "0.00"],
    "money_thousands": ["money.format_amount(Decimal('25000'))", "25000.00 USD", "25,000.00 USD"],
    "money_split": ["str(sum(money.split(Decimal('20.00'), 3)))", "20.01", "20.00"],
    "dates_spaces": ["safe(lambda: dates.parse_date(' 2026-05-04'))", "ValueError", "2026-05-04"],
    "dates_same_day": ["safe(lambda: dates.nights(date(2026,5,4), date(2026,5,4)))", "ValueError", "0"],
    "dates_travel_days": ["str(dates.travel_days(date(2026,5,4), date(2026,5,6)))", "2", "3"],
    "dates_saturday": ["str(dates.is_weekend(date(2026,5,2)))", "False", "True"],
    "dates_quarter": ["str((dates.quarter(date(2026,3,31)), dates.quarter(date(2026,12,1))))", "(2, 5)", "(1, 4)"],
    "rates_city_spaces": ["str(rates.rate(' Boston ', 'meals'))", "59", "79"],
    "rates_default": ["safe(lambda: rates.rate('Albany', 'meals'))", "KeyError", "59"],
    "rates_one_day": ["str(rates.meals_allowance('Boston', 1))", "79.00", "59.25"],
    "rates_middle_days": ["str(rates.meals_allowance('Chicago', 3))", "276.50", "197.50"],
    "rates_mileage": ["str(rates.mileage(100))", "67.00", "70.00"],
    "claims_receipt": ["str(claims.problems(Line('meals', Decimal('75.00'), date(2026,1,1))))",
                       "['receipt required']", "[]"],
    "claims_zero": ["str(claims.problems(Line('meals', Decimal('0.00'), date(2026,1,1))))", "[]",
                    "['amount must be positive']"],
    "claims_cap": ["str(claims.over_cap([Line('meals', Decimal('10'), date(2026,1,1))], {'meals': Decimal('10')}))",
                   "['meals']", "[]"],
    "claims_no_cap": ["str(claims.over_cap([Line('meals', Decimal('10'), date(2026,1,1))], {}))", "['meals']", "[]"],
    "claims_duplicate_kind": ["str(claims.duplicates([Line('meals', Decimal('10'), date(2026,1,1)), "
                              "Line('other', Decimal('10'), date(2026,1,1))]))", "[(0, 1)]", "[]"],
    "claims_kind_order": ["str(list(claims.by_kind([Line('meals', Decimal('1'), date(2026,1,1)), "
                          "Line('lodging', Decimal('1'), date(2026,1,1))])))", "['lodging', 'meals']",
                          "['meals', 'lodging']"],
    "summary_csv_quote": ["summary.to_csv([Line('meals', Decimal('1'), date(2026,1,1), 'lunch, team')]).splitlines()[1]",
                          "meals,1.00,2026-01-01,lunch\\, team", 'meals,1.00,2026-01-01,"lunch, team"'],
    "summary_largest_ties": ["str([x.day.day for x in summary.largest([Line('meals', Decimal('5'), date(2026,1,2)), "
                             "Line('meals', Decimal('5'), date(2026,1,1))], 2)])", "[2, 1]", "[1, 2]"],
}


def safe(f):
    try:
        return str(f())
    except Exception as e:
        return type(e).__name__


def evaluate(root, expr):
    """`expr` evaluated with the expenses package found under `root`."""
    for m in [k for k in sys.modules if k == "expenses" or k.startswith("expenses.")]:
        del sys.modules[m]
    sys.path.insert(0, str(root))
    try:
        ns = {"date": date, "Decimal": Decimal, "safe": safe}
        for m in ("money", "dates", "rates", "claims", "summary"):
            ns[m] = importlib.import_module(f"expenses.{m}")
        ns["Line"] = ns["claims"].Line
        return eval(expr, ns)
    finally:
        sys.path.remove(str(root))
        for m in [k for k in sys.modules if k == "expenses" or k.startswith("expenses.")]:
            del sys.modules[m]


def act(name, args, n):
    return {"role": "assistant", "content": "", "tool_calls": [call(name, args, f"c{n}")]}


def msg(text):
    return {"role": "assistant", "content": text}


class Folder(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TestTasks(Folder):
    def test_tasks_json_is_what_the_mutations_give(self):
        self.assertEqual(tasks.make_tasks(), tasks.load())

    def test_every_task_has_a_claim_and_every_claim_holds(self):
        self.assertEqual(set(CLAIMS), set(TASKS))
        for tid, (expr, buggy, fixed) in CLAIMS.items():
            with self.subTest(tid):
                work = tasks.start(TASKS[tid], self.tmp / tid)
                self.assertEqual(evaluate(work, expr), buggy)
                self.assertEqual(evaluate(tasks.REPO, expr), fixed)

    def test_the_start_hides_the_failing_tests_and_passes_the_rest(self):
        t = TASKS["dates_saturday"]
        work = tasks.start(t, self.tmp / "w")
        res = tasks.run_tests(work)
        self.assertEqual(set(res), set(t["PASS_TO_PASS"]))
        self.assertTrue(all(v == "pass" for v in res.values()))
        self.assertNotIn("test_weekend", (work / "tests" / "test_dates.py").read_text(encoding="utf-8"))

    def test_hide_takes_out_a_class_left_empty(self):
        text = "import unittest\n\n\nclass A(unittest.TestCase):\n    def test_x(self):\n        pass\n\n\n" \
               "class B(unittest.TestCase):\n    def test_y(self):\n        pass\n\n    def test_z(self):\n        pass\n"
        out = tasks.hide(text, {"A.test_x", "B.test_y"})
        self.assertNotIn("class A", out)
        self.assertIn("test_z", out)
        self.assertNotIn("test_y", out)


class TestGrade(Folder):
    def setUp(self):
        super().setUp()
        self.task = TASKS["dates_saturday"]
        self.work = tasks.start(self.task, self.tmp / "w")

    def fix(self):
        p = self.work / "expenses" / "dates.py"
        p.write_text(p.read_text(encoding="utf-8").replace("weekday() > 5", "weekday() >= 5"), encoding="utf-8")

    def test_the_bug_is_not_resolved(self):
        v = tasks.grade(self.task, self.work)
        self.assertFalse(v["resolved"])
        self.assertEqual(v["f2p"], 0)
        self.assertEqual(v["p2p"], len(self.task["PASS_TO_PASS"]))

    def test_the_fix_is_resolved(self):
        self.fix()
        self.assertTrue(tasks.grade(self.task, self.work)["resolved"])

    def test_changing_the_tests_changes_nothing(self):
        for f in (self.work / "tests").glob("test_*.py"):
            f.write_text("", encoding="utf-8")
        self.assertFalse(tasks.grade(self.task, self.work)["resolved"])
        self.fix()
        self.assertTrue(tasks.grade(self.task, self.work)["resolved"])

    def test_a_fix_that_breaks_another_test_is_not_resolved(self):
        self.fix()
        p = self.work / "expenses" / "money.py"
        p.write_text(p.read_text(encoding="utf-8").replace("ROUND_HALF_UP)", "ROUND_HALF_EVEN)")
                     .replace("import ROUND_HALF_UP,", "import ROUND_HALF_EVEN, ROUND_HALF_UP,"), encoding="utf-8")
        v = tasks.grade(self.task, self.work)
        self.assertEqual(v["f2p"], 1)
        self.assertFalse(v["resolved"])

    def test_a_hang_is_a_timeout_not_a_pass(self):
        p = self.work / "expenses" / "dates.py"
        p.write_text(p.read_text(encoding="utf-8").replace('    """True on Saturday and Sunday."""',
                                                           '    """True on Saturday and Sunday."""\n    while True:\n        pass'),
                     encoding="utf-8")
        v = tasks.grade(self.task, self.work, timeout=5)
        self.assertTrue(v["timeout"])
        self.assertFalse(v["resolved"])

    def test_code_that_disables_the_asserts_fools_the_grader_but_is_flagged(self):
        before = tasks.copy_repo(self.work, self.tmp / "before")
        p = self.work / "expenses" / "dates.py"
        p.write_text(p.read_text(encoding="utf-8") + "\nimport unittest\nfor _n in dir(unittest.TestCase):\n"
                     "    if _n in ('assertTrue', 'assertFalse', 'assertEqual'):\n        setattr(unittest.TestCase, _n, lambda *a, **k: None)\n",
                     encoding="utf-8")
        self.assertTrue(tasks.grade(self.task, self.work)["resolved"])   # the limit: it runs in the test process
        self.assertTrue(tasks.suspect(tasks.diff(before, self.work)))

    def test_a_forged_result_with_a_failing_exit_is_not_a_pass(self):
        ids = self.task["FAIL_TO_PASS"] + self.task["PASS_TO_PASS"]
        p = self.work / "expenses" / "dates.py"
        p.write_text(p.read_text(encoding="utf-8") + f"\nimport json, os\nprint(json.dumps({dict.fromkeys(ids, 'pass')!r}), flush=True)"
                     "\nos._exit(3)\n", encoding="utf-8")
        v = tasks.grade(self.task, self.work)
        self.assertFalse(v["resolved"])
        self.assertEqual(v["f2p"], 0)

    def test_class_fixtures_run(self):
        repo = self.tmp / "fx"
        (repo / "tests").mkdir(parents=True)
        (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (repo / "tests" / "test_f.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n"
            "        cls.x = 1\n\n    def test_x(self):\n        self.assertEqual(self.x, 1)\n", encoding="utf-8")
        self.assertEqual(tasks.run_tests(repo), {"tests.test_f.T.test_x": "pass"})
        self.assertEqual(tasks.run_tests(repo, ["tests.test_f.T.test_x"]), {"tests.test_f.T.test_x": "pass"})

    def test_a_failing_teardown_or_cleanup_is_an_error(self):
        for name, body in {"class": "    @classmethod\n    def tearDownClass(cls):\n        raise RuntimeError\n",
                           "cleanup": "    def setUp(self):\n        self.addCleanup(lambda: 1 / 0)\n"}.items():
            with self.subTest(name):
                repo = self.tmp / name
                (repo / "tests").mkdir(parents=True)
                (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
                (repo / "tests" / "test_f.py").write_text(
                    "import unittest\n\nclass T(unittest.TestCase):\n" + body + "\n    def test_x(self):\n"
                    "        pass\n", encoding="utf-8")
                self.assertEqual(tasks.run_tests(repo), {"tests.test_f.T.test_x": "error"})
        repo = self.tmp / "module"
        (repo / "tests").mkdir(parents=True)
        (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (repo / "tests" / "test_f.py").write_text(
            "import unittest\n\ndef tearDownModule():\n    raise RuntimeError\n\nclass T(unittest.TestCase):\n"
            "    def test_x(self):\n        pass\n", encoding="utf-8")
        self.assertEqual(tasks.run_tests(repo), {"tests.test_f.T.test_x": "error"})

    def test_the_diff_shows_the_fix(self):
        before = tasks.copy_repo(self.work, self.tmp / "before")
        self.fix()
        d = tasks.diff(before, self.work)
        self.assertIn("+++ b/expenses/dates.py", d)
        self.assertIn("+    return day.weekday() >= 5", d)


class TestJail(Folder):
    def test_the_deny_rules(self):
        refused = {"curl http://x": "network", "python -c \"import urllib.request\"": "network",
                   "git push": "network", "pip install foo": "install", "sudo ls": "privilege",
                   "reg query HKCU": "system", "type ..\\secret.txt": "outside", "dir ~": "outside",
                   "type C:\\Users\\x\\a.txt": "outside", "echo %USERPROFILE%": "outside", "echo $HOME": "outside",
                   "CURL http://x": "network", "PIP install foo": "install",
                   "type expenses/../../tasks.json": "outside", "type expenses\\..\\..\\tasks.json": "outside"}
        for c, rule in refused.items():
            with self.subTest(c):
                self.assertEqual(harness.denied(c, posix=False), rule)
        for c in ("python -m unittest discover -s tests -t .", "type expenses\\money.py", "dir /b expenses",
                  "findstr /n round expenses\\money.py", "git diff", "python -c \"print(1)\""):
            with self.subTest(c):
                self.assertIsNone(harness.denied(c, posix=False))
        self.assertEqual(harness.denied("cat /etc/passwd", posix=True), "outside")
        self.assertIsNone(harness.denied("ls > /dev/null", posix=True))

    def test_refusals_and_test_changes_are_recorded(self):
        work = tasks.start(TASKS["dates_saturday"], self.tmp / "w")
        events = []
        shell = harness.shell_tools(work, events)["shell"][0]
        with self.assertRaises(ToolError):
            shell("curl http://example.com")
        out = shell(f"python -c \"open('tests/test_money.py', 'a').write('#')\"")
        self.assertIn("[exit status 0]", out)
        self.assertEqual([e["kind"] for e in events], ["refused", "tests_changed", "command"])

    def test_paths_outside_the_work_are_refused(self):
        work = tasks.start(TASKS["dates_saturday"], self.tmp / "w")
        events = []
        view = harness.aci_tools(work, events)["view"][0]
        for p in ("../w.tmp", "..", str(HERE / "tasks.py")):
            with self.subTest(p), self.assertRaises(ToolError):
                view(p)
        self.assertEqual({e["rule"] for e in events}, {"outside"})


class TestACI(Folder):
    def setUp(self):
        super().setUp()
        self.work = tasks.start(TASKS["dates_saturday"], self.tmp / "w")
        self.events = []
        self.tools = {k: f for k, (f, _) in harness.aci_tools(self.work, self.events).items()}

    def test_view_shows_numbered_windows(self):
        out = self.tools["view"]("expenses/dates.py")
        self.assertTrue(out.startswith("[File: expenses/dates.py ("))
        self.assertIn("31:    return day.weekday() > 5", out)
        self.assertIn("expenses/", self.tools["view"]("."))

    def test_search_is_capped(self):
        self.assertIn("expenses/dates.py:", self.tools["search"]("def is_weekend"))
        self.assertIn(f"More than {harness.MATCHES}", self.tools["search"]("e"))

    def test_an_edit_that_does_not_compile_is_put_back(self):
        p = self.work / "expenses" / "dates.py"
        before = p.read_text(encoding="utf-8")
        out = self.tools["edit"]("expenses/dates.py", "31", "31", "    return day.weekday( >= 5")
        self.assertIn("Your changes have NOT been applied", out)
        self.assertEqual(p.read_text(encoding="utf-8"), before)
        self.assertEqual(self.events[-1]["kind"], "edit_reverted")
        out = self.tools["edit"]("expenses/dates.py", "31", "31", "    return day.weekday() >= 5")
        self.assertIn("replaced", out)
        self.assertIn("31:    return day.weekday() >= 5", out)
        self.assertIn("OK", self.tools["run_tests"]("tests.test_dates"))

    def test_run_tests_takes_test_names_only(self):
        with self.assertRaises(ToolError):
            self.tools["run_tests"]("discover -s C:/outside/tests -t C:/outside")
        self.assertEqual(self.events[-1]["rule"], "test_ids")
        self.assertIn("OK", self.tools["run_tests"]("tests.test_money tests.test_rates.TestRate"))

    def test_bad_line_numbers_are_an_error(self):
        with self.assertRaises(ToolError):
            self.tools["edit"]("expenses/dates.py", "900", "901", "x")
        with self.assertRaises(ToolError):
            self.tools["edit"]("expenses/dates.py", "a", "b", "x")


class TestCollapsed(unittest.TestCase):
    def test_only_the_last_five_tool_outputs_are_sent_whole(self):
        inner = ScriptedClient([msg("done")])
        messages = [{"role": "user", "content": "go"}]
        for i in range(8):
            messages += [act("view", {"path": "."}, i), {"role": "tool", "tool_call_id": f"c{i}", "content": f"out {i}\nx"}]
        before = json.dumps(messages)
        harness.Collapsed(inner).chat(messages)
        sent = [m["content"] for m in inner.seen[0] if m["role"] == "tool"]
        self.assertEqual(sent[:3], ["Old tool output omitted (2 lines)."] * 3)
        self.assertEqual(sent[3:], [f"out {i}\nx" for i in range(3, 8)])
        self.assertEqual(json.dumps(messages), before)


def repair(old, new):
    return msg(f"<<<<<<< SEARCH\n{old}\n=======\n{new}\n>>>>>>> REPLACE")


class TestAgentless(Folder):
    def setUp(self):
        super().setUp()
        self.task = TASKS["dates_saturday"]
        self.work = tasks.start(self.task, self.tmp / "w")

    def go(self, localise, samples):
        events = []
        info = agentless.run(self.task, self.work, ScriptedClient(localise), [ScriptedClient([s]) for s in samples], events)
        return info, events

    def test_the_vote_picks_the_common_fix_among_those_that_break_least(self):
        good = repair("    return day.weekday() > 5", "    return day.weekday() >= 5")
        same = repair("    return day.weekday() > 5", "    return (day.weekday()) >= 5")   # the same after ast
        breaks = repair('def is_weekend(day):', 'def is_weekend(day):\n    raise ValueError("no")')
        info, events = self.go([msg("The file is `expenses/dates.py`."), msg("is_weekend")],
                               [msg("no edit here"), breaks, good, same])
        self.assertEqual(info["file"], "expenses/dates.py")
        self.assertEqual(info["names"], ["is_weekend"])
        self.assertEqual([c["applied"] for c in info["candidates"]], [False, True, True, True])
        self.assertEqual(info["chosen"], 2)
        self.assertEqual(events, [{"kind": "edit_failed", "arg": "sample 0"}])
        self.assertTrue(tasks.grade(self.task, self.work)["resolved"])

    def test_the_code_shown_includes_the_imports(self):
        sample = ScriptedClient([msg("")])
        agentless.run(TASKS["money_half_up"], tasks.start(TASKS["money_half_up"], self.tmp / "m"),
                      ScriptedClient([msg("expenses/money.py"), msg("round_cents")]), [sample], [])
        prompt = sample.seen[0][0]["content"]
        self.assertIn("from decimal import ROUND_HALF_EVEN, Decimal", prompt)
        self.assertIn("def round_cents(value):", prompt)
        self.assertNotIn("def parse_amount", prompt)

    def test_a_repair_that_parses_but_does_not_compile_is_not_applied(self):
        self.assertIsNotNone(agentless.ast.parse("return 1"))
        self.assertIsNone(agentless.normal("return 1"))
        bad = repair("def is_weekend(day):", "return 1\ndef is_weekend(day):")
        info, _ = self.go([msg("expenses/dates.py"), msg("is_weekend")], [bad])
        self.assertEqual([c["applied"] for c in info["candidates"]], [False])
        self.assertIsNone(info["chosen"])

    def test_a_file_it_cannot_name_stops_the_pipeline(self):
        info, _ = self.go([msg("I am not sure.")], [])
        self.assertIsNone(info["file"])
        self.assertIsNone(info["chosen"])

    def test_names_come_in_the_order_given(self):
        info, _ = self.go([msg("dates.py"), msg("nights\nis_weekend")], [msg("")])
        self.assertEqual(info["file"], "expenses/dates.py")
        self.assertEqual(info["names"], ["nights", "is_weekend"])


class TestRuns(Folder):
    """One run of each arm through experiment.one, with scripted replies."""

    def setUp(self):
        super().setUp()
        self.task = TASKS["dates_saturday"]

    def run_arm(self, arm, replies):
        clients = [ScriptedClient(replies)] + [ScriptedClient([]) for _ in range(agentless.SAMPLES)]
        return experiment.one(self.tmp, 1, self.task, arm, clients)

    def test_the_aci_arm(self):
        row = self.run_arm("aci", [act("view", {"path": "expenses/dates.py"}, 1),
                                   act("edit", {"path": "expenses/dates.py", "start": "31", "end": "31",
                                                "text": "    return day.weekday() >= 5"}, 2),
                                   act("run_tests", {}, 3), msg("Saturday counts now.")])
        self.assertTrue(row["resolved"])
        self.assertEqual(row["status"], "answered")
        self.assertEqual(row["touched"], ["expenses/dates.py"])
        self.assertEqual([e["kind"] for e in row["events"]], ["edit", "tests_run"])
        self.assertEqual(row["calls"], 4)

    def test_the_shell_arm(self):
        fix = (f"python -c \"import pathlib; p = pathlib.Path('expenses/dates.py'); "
               f"p.write_text(p.read_text().replace('() > 5', '() >= 5'))\"")
        row = self.run_arm("shell", [act("shell", {"command": "type AGENTS.md"}, 1),
                                     act("shell", {"command": "curl http://example.com"}, 2),
                                     act("shell", {"command": fix}, 3), msg("Fixed.")])
        self.assertTrue(row["resolved"])
        self.assertEqual([e["kind"] for e in row["events"]], ["command", "refused", "command"])

    def test_a_run_that_does_nothing_is_not_resolved(self):
        row = self.run_arm("aci", [msg("It is fixed.")])
        self.assertFalse(row["resolved"])
        self.assertEqual(row["patch"], "")

    def test_the_agentless_arm(self):
        clients = [ScriptedClient([msg("expenses/dates.py"), msg("is_weekend")])] + [
            ScriptedClient([repair("    return day.weekday() > 5", "    return day.weekday() >= 5")])
            for _ in range(agentless.SAMPLES)]
        row = experiment.one(self.tmp, 1, self.task, "agentless", clients)
        self.assertTrue(row["resolved"])
        self.assertEqual(row["calls"], 2 + agentless.SAMPLES)
        self.assertFalse((self.tmp / "work" / "1_dates_saturday_agentless.start").exists())

    def test_a_folder_left_by_a_killed_run_is_started_again(self):
        stale = self.tmp / "work" / "1_dates_saturday_aci"
        (stale / "expenses").mkdir(parents=True)
        (stale / "expenses" / "junk.py").write_text("x = 1\n", encoding="utf-8")
        row = self.run_arm("aci", [msg("done")])
        self.assertEqual(row["patch"], "")

    def test_the_plan_interleaves_the_arms(self):
        p = experiment.plan([{"id": "a"}, {"id": "b"}], 2)
        self.assertEqual(len(p), 12)
        self.assertEqual([arm for _, _, arm in p[:3]], list(experiment.ARMS))


def row(tid, mod, arm, rep, resolved, **kw):
    return {"rep": rep, "id": tid, "module": f"expenses/{mod}.py", "arm": arm, "resolved": resolved,
            "f2p": 1 if resolved else 0, "p2p": kw.get("p2p", 10), "f2p_of": 1, "p2p_of": 10,
            "outcomes": {}, "status": "answered", "steps": 3, "calls": 3, "tokens": 1000, "seconds": 10.0,
            "patch": "x" if resolved else kw.get("patch", ""), "events": kw.get("events", []),
            "trace": kw.get("trace", {}), "detail": "", "answer": ""}


class TestReport(unittest.TestCase):
    def test_an_empty_run_gives_placeholders(self):
        out = report.files(*report.render([]))
        self.assertEqual(out["ch07_arms.tex"], report.PLACEHOLDER)
        self.assertIn("\\newcommand{\\chsevenAciResolved}{--}", out["ch07_numbers.tex"])
        self.assertEqual(out["ch07_numbers.tex"].count("\\newcommand"), len(report.MACROS))

    def test_the_numbers(self):
        rows = []
        for rep in (1, 2):
            rows += [row("a", "money", "aci", rep, True), row("b", "dates", "aci", rep, rep == 1),
                     row("a", "money", "shell", rep, rep == 1, events=[{"kind": "refused"}]),
                     row("b", "dates", "shell", rep, False, p2p=9, patch="y"),
                     row("a", "money", "agentless", rep, False, trace={"file": "expenses/money.py", "chosen": None}),
                     row("b", "dates", "agentless", rep, False, trace={"file": "expenses/money.py", "chosen": 0})]
        _, mods, n = report.render(rows)
        self.assertEqual((n["AciResolved"], n["ShellResolved"], n["AgentlessResolved"]), ("75.0", "25.0", "0.0"))
        self.assertEqual((n["AciPassK"], n["AciPassHatK"]), ("100.0", "50.0"))
        self.assertEqual((n["ShellPassK"], n["ShellPassHatK"]), ("50.0", "0.0"))
        self.assertEqual((n["ShellBroke"], n["ShellRefused"]), ("50.0", "50.0"))
        self.assertEqual(n["AciShellDiff"], "50.0")
        self.assertEqual((n["AciMoney"], n["AciDates"]), ("100.0", "50.0"))
        self.assertEqual((n["AgentlessFileRight"], n["AgentlessNoCandidate"]), ("50.0", "50.0"))
        self.assertEqual((n["Repeats"], n["Tasks"], n["ShellRefusals"], n["ShellCommands"]), (2, 2, 2, 2))
        self.assertEqual(n["AciSuspect"], "0.0")
        self.assertEqual(mods[2], "aci & 100.0 & 50.0 & -- & -- & -- \\\\")

    def test_a_run_with_runs_missing_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "manifest.json").write_text(json.dumps(
                {"settings": {"repeats": [1, 2], "tasks": ["a"], "arms": ["aci"]}}), encoding="utf-8")
            self.assertEqual(report.missing(tmp, [row("a", "money", "aci", 1, True)]), [(2, "a", "aci")])

    def test_only_the_chapters_design_makes_the_book_numbers(self):
        full = {"repeats": list(range(1, report.REPEATS + 1)), "tasks": [t["id"] for t in tasks.load()],
                "arms": list(report.ARMS)}
        self.assertIsNone(report.not_the_design(full))
        self.assertIn("repeats", report.not_the_design(full | {"repeats": [1]}))
        self.assertIn("tasks", report.not_the_design(full | {"tasks": ["dates_saturday"]}))


if __name__ == "__main__":
    unittest.main()
