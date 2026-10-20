"""Run a repository's unit tests in a child process and print each test's outcome as JSON.

  python -I runner.py <repo> [test id ...]      e.g. tests.test_money.TestParse.test_empty_is_none

With no ids, every test under <repo>/tests is run. The output's last line is one JSON object,
{test id: "pass" | "fail" | "error" | "skip"}; an id that can't be loaded is an "error", and so is
every test, if any class or module fixture failed. It exits 0 when it got that far, and the grader
accepts nothing else. The child runs whatever code is in <repo>, which for this chapter is code a
model wrote, in the same process as the tests: that code can change unittest or print a JSON line
of its own, so the outcome is trustworthy only for code that doesn't attack the runner (tasks.py
flags patches that look as if they might). See README.md on where it may run.
"""
import json
import sys
import unittest


def ids(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from ids(t)
        else:
            yield t


class Record(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.out, self.fixtures = {}, []

    def addSuccess(self, test):
        self.out.setdefault(test.id(), "pass")       # a cleanup that fails afterwards still counts

    def addFailure(self, test, err):
        self.out[test.id()] = "fail"

    def addError(self, test, err):
        if isinstance(test, unittest.TestCase):
            self.out[test.id()] = "error"
        else:                                        # a class or module fixture (setUp/tearDown)
            self.fixtures.append(str(test))

    def addSkip(self, test, reason):
        self.out[test.id()] = "skip"

    def addExpectedFailure(self, test, err):
        self.out[test.id()] = "fail"

    def addUnexpectedSuccess(self, test):
        self.out[test.id()] = "fail"


def main(repo, wanted):
    sys.path.insert(0, repo)
    loader = unittest.TestLoader()
    if wanted:
        suite = unittest.TestSuite()
        for name in wanted:
            try:
                suite.addTests(loader.loadTestsFromName(name))
            except Exception:                        # a module that doesn't import, a name not there
                pass
    else:
        suite = loader.discover(f"{repo}/tests", top_level_dir=repo)
    rec = Record()
    found = list(ids(suite))
    suite.run(rec)                                   # the suite's own lifecycle: class and module fixtures run
    out = {}
    for t in found:
        tid = t.id()
        if tid.startswith("unittest.loader._FailedTest."):   # a test module that would not import
            out[tid] = "error"
        else:
            out[tid] = rec.out.get(tid, "error")
    if rec.fixtures:                                 # a fixture failed: no test's result can be trusted
        out = dict.fromkeys(out, "error")
    for name in wanted:
        out.setdefault(name, "error")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
