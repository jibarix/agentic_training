"""One durable run of one strategy on one task, ending in one claim in the ledger.

Every model call and tool call goes through a journal (durable.py), so a run that is killed can be
started again with the same arguments and carries on from its last recorded call. The claim is
filed by code, from the strategy's number, through the same journal, with an idempotency key.

The layers, outermost first, for each model call:  Meter -> DurableClient -> RetryingClient -> client
and for each tool call:                            durable_tools -> retrying_tools -> (Flaky) -> tool
Retries sit inside the journal, so only a call's final result is recorded. A call that still fails
after its retries (the model server is down, say) stops the run with durable.Halted; nothing about it
is recorded, so running it again makes that call again.
"""
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "ch01"))
sys.path.insert(1, str(HERE.parent / "ch04"))
from handbook_tools import TOOLS                        # noqa: E402  Chapter 1's tools on Chapter 4's handbook
sys.path.insert(0, str(HERE))       # this folder first again: Chapters 1 and 4 also have a report.py

from durable import DurableClient, Journal, Run, durable_tools   # noqa: E402
from faults import Flaky, RetryingClient, retrying_tools          # noqa: E402
from ledger import Ledger                                          # noqa: E402
from strategies import STRATEGIES, Meter, Outcome, employee_of     # noqa: E402
from tools import ToolError                                        # noqa: E402  Chapter 1's


def durable_run(strategy, task, client, journal, ledger, run_id, crash=None, keyed=True,
                flaky=None, retry_kw=None, retry_log=None, tools=TOOLS):
    """Run (or resume) `strategy` on `task`. Returns (outcome, receipt, run, meter).

    journal, ledger: paths. crash: (call number, point) to kill the run there (durable.Run).
    keyed=False files the claim without an idempotency key. flaky: a faults.Flaky that fails a
    share of tool calls; its failures are drawn by the journal's call number, so a resumed run meets
    the same ones. A claim is filed only for an amount above zero; a claim the ledger refuses gives
    the receipt "not filed: ..." and the run still ends. retry_kw: settings for faults.retry, e.g. {"sleep": lambda s: None}."""
    retry_kw = {"attempts": 4, "base": 1.0, "cap": 30.0, "budget": 60.0, **(retry_kw or {})}
    run = Run(Journal(journal), run_id, crash)
    if flaky:
        flaky.at = lambda: run.seq - 1           # the number of the call being made
    base = {k: (flaky.tool(fn) if flaky else fn, spec) for k, (fn, spec) in tools.items()}
    book = Ledger(ledger)
    all_tools = durable_tools({**retrying_tools(base, log=retry_log, **retry_kw), "file_claim": book.tool(keyed)},
                              run, effects={"file_claim"})
    claim = all_tools.pop("file_claim")[0]
    meter = Meter(DurableClient(RetryingClient(client, log=retry_log, **retry_kw), run))
    out = STRATEGIES[strategy](task, meter, all_tools)
    receipt = None
    if out.amount is not None and Decimal(out.amount) > 0 and employee_of(task):
        try:
            receipt = claim(employee=employee_of(task), amount=out.amount,
                            trips=",".join(out.info.get("trips", [])))
        except ToolError as e:
            receipt = f"not filed: {e}"
    return out, receipt, run, meter


__all__ = ["durable_run", "Outcome", "Flaky"]
