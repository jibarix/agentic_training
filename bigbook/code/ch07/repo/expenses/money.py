"""Amounts of money: Decimal, rounded half up to the cent."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def round_cents(value):
    """Decimal('2.345') -> Decimal('2.35'): half a cent rounds up."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_amount(text):
    """'1,234.50', '$12' or ' 7.5 ' -> a Decimal to the cent; None for empty text.

    Anything else, a negative amount included, raises ValueError."""
    if text is None:
        return None
    s = str(text).strip().replace(",", "")
    if s.startswith("$"):
        s = s[1:]
    if not s:
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise ValueError(f"not an amount: {text!r}") from None
    if not value.is_finite() or value < 0:
        raise ValueError(f"not an amount: {text!r}")
    return round_cents(value)


def format_amount(value, currency="USD"):
    """Decimal('1234.5') -> '1,234.50 USD'."""
    return f"{round_cents(value):,.2f} {currency}"


def split(total, parts):
    """Split a total into `parts` amounts that add up to it exactly and differ by at most a cent;
    the first amounts take the extra cents."""
    if parts < 1:
        raise ValueError("parts must be at least 1")
    cents = int(round_cents(total) * 100)
    base, extra = divmod(cents, parts)
    return [round_cents(Decimal(base + (1 if i < extra else 0)) / 100) for i in range(parts)]
