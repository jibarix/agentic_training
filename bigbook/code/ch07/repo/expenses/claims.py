"""Expense claims: lines, the checks on them, and totals."""
from dataclasses import dataclass
from decimal import Decimal

from .money import round_cents

KINDS = ("meals", "lodging", "mileage", "other")
RECEIPT_OVER = Decimal("75.00")        # a line above this amount needs a receipt


@dataclass
class Line:
    kind: str
    amount: Decimal
    day: object                        # a datetime.date
    note: str = ""
    receipt: bool = False


def problems(line):
    """What is wrong with one line, as a list of short strings; empty if nothing is."""
    out = []
    if line.kind not in KINDS:
        out.append(f"unknown kind '{line.kind}'")
    if line.amount <= 0:
        out.append("amount must be positive")
    if line.amount > RECEIPT_OVER and not line.receipt:
        out.append("receipt required")
    return out


def total(lines):
    """The sum of the lines' amounts, to the cent; 0.00 for no lines."""
    return round_cents(sum((line.amount for line in lines), Decimal("0")))


def by_kind(lines):
    """{kind: total} for each kind that has a line, in the order of KINDS."""
    out = {}
    for kind in KINDS:
        mine = [line for line in lines if line.kind == kind]
        if mine:
            out[kind] = total(mine)
    return out


def over_cap(lines, caps):
    """The kinds whose total is above their cap in `caps` ({kind: Decimal}); a kind with no cap is
    never over. Sorted by name."""
    return sorted(kind for kind, t in by_kind(lines).items() if kind in caps and t > caps[kind])


def duplicates(lines):
    """Pairs (i, j), i < j, of lines with the same kind, amount and day: the same expense entered twice."""
    out = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a, b = lines[i], lines[j]
            if (a.kind, a.amount, a.day) == (b.kind, b.amount, b.day):
                out.append((i, j))
    return out
