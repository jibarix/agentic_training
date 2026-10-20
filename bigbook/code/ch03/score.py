"""The scorer, revised after measuring Chapter 1's against 180 hand labels (see measure_scorer.py).

The one change: the number may be followed by one descriptive word before the unit, so that
"13 paid holidays" and "2 floating holidays" count. Everything else is as in Chapter 1: only the
last 'Final answer:' line is read, it must hold exactly one number, and no word may come before
the number except a currency unit, so "not 272 USD" still fails.
"""
import re
from decimal import Decimal

FINAL_LINE = re.compile(r"(?im)^[\s*_#>-]*final answer[\s*_]*:(.*)$")
NUM = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?"


def score(answer, expected, units):
    """True or False from the last 'Final answer:' line; None if there is no such line."""
    lines = FINAL_LINE.findall(answer)
    if not lines:
        return None
    line = re.sub(r"[*_]", "", lines[-1]).strip().rstrip(".").strip()
    m = re.fullmatch(rf"(\$|[A-Za-z]+)?\s*({NUM})\s*(?:([A-Za-z]+)\s+)?([A-Za-z]+)?", line)
    if not m:
        return False
    names = {u.lower() for u in units}
    is_unit = lambda w: w.lower() in names or w.lower().rstrip("s") in names
    before, after = m.group(1), m.group(4)       # group 3, the descriptive word, can be anything
    if not (before or after) or not all(is_unit(w) for w in (before, after) if w):
        return False
    return abs(Decimal(m.group(2).replace(",", "")) - Decimal(str(expected))) <= Decimal("0.01")
