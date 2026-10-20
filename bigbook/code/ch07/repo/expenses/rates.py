"""Per diem rates by city, and the mileage rate."""
from decimal import Decimal

from .money import round_cents

RATES = {
    "boston": {"meals": Decimal("79"), "lodging": Decimal("258")},
    "chicago": {"meals": Decimal("79"), "lodging": Decimal("231")},
    "denver": {"meals": Decimal("74"), "lodging": Decimal("199")},
}
DEFAULT = {"meals": Decimal("59"), "lodging": Decimal("110")}     # any city not listed
KINDS = ("meals", "lodging")
MILEAGE = Decimal("0.70")                                          # USD per mile
PARTIAL = Decimal("0.75")                                          # first and last day of travel


def city_key(city):
    """' Boston ' -> 'boston'."""
    return city.strip().lower()


def rate(city, kind):
    """The daily rate of `kind` ('meals' or 'lodging') in a city; the default rate for a city not
    listed. KeyError for any other kind."""
    if kind not in KINDS:
        raise KeyError(kind)
    return RATES.get(city_key(city), DEFAULT)[kind]


def meals_allowance(city, days):
    """Meals for a trip of `days` travel days: the full rate on each day in between, and 75% of it
    on the first and on the last day. A one-day trip gets 75% once."""
    if days < 1:
        raise ValueError("a trip has at least one day")
    r = rate(city, "meals")
    if days == 1:
        return round_cents(r * PARTIAL)
    return round_cents(r * (days - 2) + 2 * r * PARTIAL)


def lodging_allowance(city, nights):
    """Lodging for `nights` nights at the city's rate."""
    if nights < 0:
        raise ValueError("nights can't be negative")
    return round_cents(rate(city, "lodging") * nights)


def mileage(miles):
    """Reimbursement for driving `miles` miles at the mileage rate."""
    m = Decimal(str(miles))
    if m < 0:
        raise ValueError("miles can't be negative")
    return round_cents(m * MILEAGE)
