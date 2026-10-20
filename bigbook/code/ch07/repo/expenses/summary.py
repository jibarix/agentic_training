"""Summaries of a claim: text lines, CSV, the largest lines, totals by month."""
import csv
import io
from decimal import Decimal

from .claims import by_kind, total
from .money import format_amount, round_cents


def summary_lines(lines):
    """One 'kind: amount' line per kind with lines, then 'total: amount'."""
    out = [f"{kind}: {format_amount(t)}" for kind, t in by_kind(lines).items()]
    out.append(f"total: {format_amount(total(lines))}")
    return out


def to_csv(lines):
    """The lines as CSV text with the header kind,amount,day,note; amounts with two decimals,
    days as YYYY-MM-DD, and a note with a comma quoted."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["kind", "amount", "day", "note"])
    for line in lines:
        w.writerow([line.kind, f"{round_cents(line.amount):.2f}", line.day.isoformat(), line.note])
    return buf.getvalue()


def largest(lines, n=3):
    """The n lines with the largest amounts, largest first; of two equal amounts, the earlier day first."""
    return sorted(lines, key=lambda line: (-line.amount, line.day))[:n]


def month_totals(lines):
    """{'YYYY-MM': total} for each month with a line, in date order."""
    out = {}
    for line in sorted(lines, key=lambda line: line.day):
        key = line.day.strftime("%Y-%m")
        out[key] = out.get(key, Decimal("0")) + line.amount
    return {k: round_cents(v) for k, v in out.items()}
