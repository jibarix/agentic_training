"""Write this chapter's 36 tasks (tasks.json) from Chapter 4's handbook, with answers computed from it.

The handbook is Chapter 4's, unchanged: the same tables from the same seed. The tasks are new.

  decomposable (24): a total over three to five independent pieces (one per trip), as in Chapter 4
    meals, mileage : one employee's trips, all billed to ACME
    full           : meals, lodging and mileage over two or three trips
    billed         : meals and lodging over the trips billed to ACME, skipping those billed to a client
  sequential (12): each lookup needs the answer to the one before, so nothing can be split
    chain_meals    : trip -> the employee who made it -> that employee's home office -> its meals rate
    chain_lodging  : the same chain, then the lodging the trip would have cost at the office city
    (every chain trip is billed to ACME, so the counterfactual's billing is not in question)

Chapter 4's tasks used 30 employees; none of them is used here. Only nine of the employees left have
three to five trips all billed to ACME, so the meals and mileage tasks share three employees (the
questions differ). Within a set no employee appears twice.

Usage: python make_tasks.py
"""
import json
import random
import sys
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).parent
CH04 = HERE.parent / "ch04"
sys.path.insert(0, str(CH04))
import make_handbook as hb                               # noqa: E402  Chapter 4's tables

UNITS = ["USD", "$", "dollar"]


def amounts(t, rates, parts):
    """One trip's reimbursement for the parts asked, as a Decimal."""
    return ((Decimal(hb.meals(t, rates)) if "meals" in parts else 0)
            + (Decimal(hb.lodging(t, rates)) if "lodging" in parts else 0)
            + (hb.mileage(t) if "mileage" in parts else 0))


def build():
    rates, staff, trips = hb.build()
    used = {t["id"].split("_")[1].upper() for t in json.loads((CH04 / "tasks_long.json").read_text(encoding="utf-8"))}
    by = {}
    for t in trips:
        by.setdefault(t["emp"], []).append(t)
    free = {e: ts for e, ts in sorted(by.items()) if e not in used}
    acme = {e: ts for e, ts in free.items() if all(t["billed"] == "ACME" for t in ts)}
    out = []

    def add(cluster, emp, ts, parts, text):
        per = {t["id"]: str(amounts(t, rates, parts)) for t in ts}
        out.append({"id": f"{cluster}_{emp.lower()}", "set": "decomposable", "cluster": cluster, "task": text,
                    "answer": float(sum(amounts(t, rates, parts) for t in ts)), "units": UNITS,
                    "employee": emp, "parts": sorted(parts, key=("meals", "lodging", "mileage").index),
                    "trips": [t["id"] for t in ts], "per_trip": per})

    three_five = [e for e, ts in acme.items() if 3 <= len(ts) <= 5]
    for emp in three_five[:6]:
        add("meals", emp, by[emp], {"meals"},
            f"What is the total meals per-diem ACME owes {emp} for all of their trips in the first quarter of 2026?")
    for emp in [e for e in reversed(three_five) if sum(t["miles"] > 0 for t in by[e]) >= 2][:6]:
        add("mileage", emp, by[emp], {"mileage"},
            f"What is the total mileage reimbursement for {emp}'s trips in the first quarter of 2026?")
    for emp in [e for e, ts in acme.items() if 2 <= len(ts) <= 3 and e not in three_five][:6]:
        add("full", emp, by[emp], {"meals", "lodging", "mileage"},
            f"What does ACME reimburse {emp} in total for their first-quarter 2026 trips, counting meals "
            f"per-diem, lodging and mileage?")
    mixed = [e for e, ts in free.items() if any(t["billed"] == "client" for t in ts)
             and 2 <= sum(t["billed"] == "ACME" for t in ts) <= 4]
    for emp in mixed[:6]:
        add("billed", emp, [t for t in by[emp] if t["billed"] == "ACME"], {"meals", "lodging"},
            f"What does ACME reimburse {emp} for meals per-diem and lodging in the first quarter of 2026?")

    # sequential: trips billed to ACME (a client-billed trip's lodging isn't ACME's to pay), whose employee
    # is unused here and whose office has rates, chosen with a fixed seed
    taken = {t["employee"] for t in out}
    pool = [t for t in trips if t["emp"] not in used | taken and staff[t["emp"]] in rates and t["nights"] > 0
            and t["billed"] == "ACME"]
    rnd, seen = random.Random(8), set()
    rnd.shuffle(pool)
    chosen = []
    for t in pool:
        if t["emp"] not in seen and t["city"] != staff[t["emp"]]:
            seen.add(t["emp"])
            chosen.append(t)
    for i, t in enumerate(chosen[:12]):
        office = staff[t["emp"]]
        meals_rate, cap = rates[office]
        chain = {"trip": t["id"], "employee": t["emp"], "office": office}
        if i < 6:
            days = 2 + i % 3
            out.append({"id": f"chain_meals_{t['id'].lower()}", "set": "sequential", "cluster": "chain_meals",
                        "task": f"The employee who made trip {t['id']} belongs to one of ACME's home offices. What "
                                f"meals per-diem would ACME pay for a {days}-day trip to the city of that office?",
                        "answer": float(meals_rate * days), "units": UNITS, "chain": chain | {"rate": meals_rate}})
        else:
            value = min(t["cost"], cap) * t["nights"]
            out.append({"id": f"chain_lodging_{t['id'].lower()}", "set": "sequential", "cluster": "chain_lodging",
                        "task": f"Suppose trip {t['id']} had gone to the home-office city of the employee who made it, "
                                f"with the same number of nights and the same hotel charge per night. How much "
                                f"lodging would ACME have reimbursed?",
                        "answer": float(value), "units": UNITS,
                        "chain": chain | {"nights": t["nights"], "cost": t["cost"], "cap": cap}})
    return out


def write():
    ts = build()
    (HERE / "tasks.json").write_text("[\n" + ",\n".join(" " + json.dumps(t) for t in ts) + "\n]\n", encoding="utf-8")
    return ts


if __name__ == "__main__":
    ts = write()
    print(len(ts), "tasks:", {c: sum(t["cluster"] == c for t in ts) for c in dict.fromkeys(t["cluster"] for t in ts)})
