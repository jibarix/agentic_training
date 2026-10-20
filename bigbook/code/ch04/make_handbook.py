"""Write this chapter's larger handbook tables and its long tasks, with answers computed from them.

The prose files (travel_policy.md, equipment.md, leave.md, remote_work.md, security.md) are written
by hand. The four tables and tasks_long.json come from here, from a fixed seed, so every answer is
arithmetic on the same data the agent reads. Running it again writes identical files.

Usage: python make_handbook.py
"""
import json
import random
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
BOOK = HERE / "handbook"
HEAD = "(fictional ACME Corp. handbook, 2026)"

CITIES = ["Albuquerque", "Atlanta", "Austin", "Baltimore", "Boise", "Boston", "Charlotte", "Chicago",
          "Cincinnati", "Cleveland", "Columbus", "Dallas", "Denver", "Detroit", "Hartford", "Honolulu",
          "Houston", "Indianapolis", "Kansas City", "Las Vegas", "Los Angeles", "Louisville", "Memphis",
          "Miami", "Milwaukee", "Minneapolis", "Nashville", "New Orleans", "New York", "Oakland",
          "Omaha", "Orlando", "Philadelphia", "Phoenix", "Pittsburgh", "Portland", "Raleigh",
          "Sacramento", "Salt Lake City", "San Diego"]
VEHICLES = {"car": Decimal("0.70"), "electric car": Decimal("0.62"), "van": Decimal("0.85"),
            "motorcycle": Decimal("0.45"), "none": Decimal("0")}
OFFICES = ["Austin", "Boston", "Seattle", "Chicago", "Denver", "Atlanta", "Phoenix", "Raleigh"]


def table(header, rows):
    w = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "| " + " | ".join(str(v).ljust(w[i]) for i, v in enumerate(r)) + " |"
    return "\n".join([line(header), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [line(r) for r in rows])


def build(seed=4):
    rnd = random.Random(seed)
    rates = {c: (rnd.randint(55, 92), 5 * rnd.randint(30, 64)) for c in CITIES}
    staff = {f"EMP{100 + i:04d}": OFFICES[i % len(OFFICES)] for i in range(1, 73)}
    trips, n = [], 0
    for emp in staff:
        for _ in range(rnd.randint(2, 5)):
            n += 1
            city = rnd.choice(CITIES)
            days = rnd.randint(1, 6)
            nights = days - 1
            vehicle = rnd.choice(["car", "car", "electric car", "van", "motorcycle", "none", "none"])
            miles = 0 if vehicle == "none" else rnd.randint(12, 420)
            cost = 5 * rnd.randint(28, 70) if nights else 0
            billed = "client" if rnd.random() < 0.15 else "ACME"
            month = rnd.randint(1, 3)
            trips.append({"id": f"TR{n:04d}", "emp": emp, "city": city, "start": f"2026-{month:02d}-{rnd.randint(1, 28):02d}",
                          "days": days, "nights": nights, "cost": cost, "vehicle": vehicle, "miles": miles,
                          "billed": billed})
    trips.sort(key=lambda t: (t["start"], t["id"]))
    return rates, staff, trips


def meals(t, rates):
    return rates[t["city"]][0] * t["days"]


def lodging(t, rates):
    return min(t["cost"], rates[t["city"]][1]) * t["nights"]


def mileage(t):
    return VEHICLES[t["vehicle"]] * t["miles"]


def facts(ts, rates, parts):
    """The values an agent must carry to the end of the task, each with the names it belongs to.

    A trip's days, nights, cost and miles belong to the trip id; a city's rates to the city (or the
    trip that went there); a vehicle's rate to the vehicle (or the trip). Values as the handbook
    prints them, so the mileage rate is "0.70", not "0.7".
    """
    out = []
    for t in ts:
        trip, city, vehicle = t["id"], t["city"], t["vehicle"]
        f = lambda what, value, *keys: out.append({"what": what, "value": str(value), "keys": list(keys)})
        f("trip", trip)
        if "meals" in parts:
            f("days", t["days"], trip)
            f("meals rate", rates[city][0], city, trip)
        if "lodging" in parts:
            f("nights", t["nights"], trip)
            f("hotel cost", t["cost"], trip)
            f("lodging cap", rates[city][1], city, trip)
        if "mileage" in parts:
            f("miles", t["miles"], trip)
            if vehicle != "none":
                f("mileage rate", f"{VEHICLES[vehicle]:.2f}", vehicle, trip)
    return out


def tasks(rates, staff, trips):
    by = {}
    for t in trips:
        by.setdefault(t["emp"], []).append(t)
    acme_only = {e: ts for e, ts in by.items() if all(t["billed"] == "ACME" for t in ts)}
    mixed = {e: ts for e, ts in by.items() if any(t["billed"] == "client" for t in ts)
             and sum(t["billed"] == "ACME" for t in ts) >= 2}
    out, used = [], set()
    pick = lambda pool, lo, hi: [e for e, ts in sorted(pool.items()) if lo <= len(ts) <= hi and e not in used]

    def add(cluster, emp, ts, parts, text):
        used.add(emp)
        value = sum((Decimal(meals(t, rates)) if "meals" in parts else 0)
                    + (Decimal(lodging(t, rates)) if "lodging" in parts else 0)
                    + (mileage(t) if "mileage" in parts else 0) for t in ts)
        out.append({"id": f"{cluster}_{emp.lower()}", "cluster": cluster, "task": text,
                    "answer": float(value), "units": ["USD", "$", "dollar"],
                    "trips": [t["id"] for t in ts], "facts": facts(ts, rates, parts)})

    for emp in pick(acme_only, 3, 5)[:6]:
        add("meals", emp, by[emp], {"meals"},
            f"What is the total meals per-diem ACME owes {emp} for all of their trips in the first quarter of 2026?")
    for emp in pick(acme_only, 3, 5)[:6]:
        add("lodging", emp, by[emp], {"lodging"},
            f"How much lodging does ACME reimburse {emp} for all of their trips in the first quarter of 2026?")
    for emp in [e for e in pick(acme_only, 3, 5) if sum(t["miles"] > 0 for t in by[e]) >= 2][:6]:
        add("mileage", emp, by[emp], {"mileage"},
            f"What is the total mileage reimbursement for {emp}'s trips in the first quarter of 2026?")
    for emp in pick(acme_only, 2, 3)[:6]:
        add("full", emp, by[emp], {"meals", "lodging", "mileage"},
            f"What does ACME reimburse {emp} in total for their first-quarter 2026 trips, counting meals "
            f"per-diem, lodging and mileage?")
    for emp in pick(mixed, 3, 5)[:6]:
        ts = [t for t in by[emp] if t["billed"] == "ACME"]
        add("billed", emp, ts, {"meals", "lodging"},
            f"What does ACME reimburse {emp} for meals per-diem and lodging in the first quarter of 2026?")
    return out


def write():
    rates, staff, trips = build()
    BOOK.mkdir(exist_ok=True)
    (BOOK / "per_diem.md").write_text(
        f"# Per-diem and lodging rates {HEAD}\n\n"
        "Rates for every approved destination. How they are paid is in travel_policy.md.\n\n"
        + table(["City", "Meals per-diem (USD/day)", "Lodging cap (USD/night)"],
                [[c, m, l] for c, (m, l) in rates.items()])
        + "\n\nCities not listed here have no approved rate; ask Finance before booking.\n", encoding="utf-8")
    (BOOK / "mileage.md").write_text(
        f"# Mileage rates {HEAD}\n\n"
        "Rates per mile driven on company business, by vehicle. The trip log records the total miles "
        "driven on each trip, including the return.\n\n"
        + table(["Vehicle", "Rate (USD/mile)"], [[v, f"{r:.2f}"] for v, r in VEHICLES.items() if v != "none"])
        + "\n\nTrips by plane or train with no vehicle (\"none\" in the trip log) have no mileage.\n",
        encoding="utf-8")
    (BOOK / "offices.md").write_text(
        f"# Offices and staff {HEAD}\n\nEvery employee belongs to one home office.\n\n"
        + table(["Employee", "Home office"], [[e, o] for e, o in staff.items()]) + "\n", encoding="utf-8")
    (BOOK / "trips_2026q1.md").write_text(
        f"# Trip log, first quarter of 2026 {HEAD}\n\n"
        "One row per trip. Lodging cost is what the hotel charged per night. Trips billed to a client "
        "are paid by the client, not by ACME (see travel_policy.md, section 5).\n\n"
        + table(["Trip", "Employee", "City", "Start", "Days", "Nights", "Lodging cost (USD/night)",
                 "Vehicle", "Miles", "Billed to"],
                [[t["id"], t["emp"], t["city"], t["start"], t["days"], t["nights"], t["cost"],
                  t["vehicle"], t["miles"], t["billed"]] for t in trips]) + "\n", encoding="utf-8")
    ts = tasks(rates, staff, trips)
    (HERE / "tasks_long.json").write_text(
        "[\n" + ",\n".join(" " + json.dumps(t) for t in ts) + "\n]\n", encoding="utf-8")
    return rates, staff, trips, ts


if __name__ == "__main__":
    _, _, trips, ts = write()
    print(f"{len(trips)} trips, {len(ts)} tasks:", {c: sum(t['cluster'] == c for t in ts) for c in
                                                    dict.fromkeys(t['cluster'] for t in ts)})
