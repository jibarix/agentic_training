"""The one tool here that changes the world: filing a reimbursement claim in a ledger file.

The ledger is the outside system. It keeps every claim it accepts, one JSON line each, and if a
claim arrives with a key it has already accepted, it returns the first receipt and writes nothing.
That is all an idempotency key is: the writer names each write, and the system that is written to
refuses the same name twice. A claim with no key is always written, so a retried claim with no key
is a second claim.

This ledger is a file with one writer at a time, and its check for the key and its append are two
steps. A crash between them, or half-way through the append, leaves either no claim or a torn last
line, which the next read cuts off (the claim was never accepted, and the run that resumes files it
again under the same key). Two writers at once could both pass the check. A real receiver makes the
key unique in its database and does the check and the write in one transaction.
"""
from decimal import Decimal, InvalidOperation
from pathlib import Path

from durable import append_jsonl, read_jsonl
from tools import ToolError                             # Chapter 1's

SPEC = {"type": "function", "function": {
    "name": "file_claim",
    "description": "File a reimbursement claim for an employee. Call it once, with the final total.",
    "parameters": {"type": "object", "properties": {
        "employee": {"type": "string", "description": "Employee id, e.g. EMP0101"},
        "amount": {"type": "string", "description": "Total in USD, e.g. 1234.50"},
        "trips": {"type": "string", "description": "Comma-separated trip ids, e.g. TR0001,TR0002"}},
        "required": ["employee", "amount"]}}}


class Ledger:
    def __init__(self, path):
        self.path = Path(path)

    def claims(self, repair=True):
        """The accepted claims. A torn last line is dropped, and cut off unless repair=False."""
        return read_jsonl(self.path, repair)[0]

    def post(self, employee, amount, trips="", key=None, crash_mid_write=False):
        try:
            value = Decimal(str(amount).replace(",", "").replace("$", "").strip())
        except InvalidOperation:
            raise ToolError("bad_arguments", f"amount '{amount}' is not a number",
                            "Give the amount as digits, e.g. 1234.50")
        if not value.is_finite() or value <= 0:
            raise ToolError("bad_arguments", f"amount '{amount}' is not a positive amount",
                            "A claim is for a positive amount in USD.")
        claims = self.claims()
        if key is not None:
            for c in claims:
                if c["key"] == key:
                    return f"claim {c['id']} already filed; nothing new written"
        claim = {"id": f"CL{len(claims) + 1:04d}", "key": key, "employee": employee.strip(),
                 "amount": str(value), "trips": trips.strip()}
        append_jsonl(self.path, claim, crash_mid_write)   # crash_mid_write: for the tests
        return f"claim {claim['id']} filed: {claim['employee']}, {claim['amount']} USD"

    def tool(self, keyed=True):
        """The tool's entry for a tools dict. keyed=False drops the key: every call writes."""
        def file_claim(employee, amount, trips="", key=None):
            return self.post(employee, amount, trips, key if keyed else None)
        return file_claim, SPEC
