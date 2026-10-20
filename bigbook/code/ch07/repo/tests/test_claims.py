import unittest
from datetime import date
from decimal import Decimal

from expenses.claims import Line, by_kind, duplicates, over_cap, problems, total

D1, D2 = date(2026, 3, 1), date(2026, 3, 2)


class TestProblems(unittest.TestCase):
    def test_a_good_line(self):
        self.assertEqual(problems(Line("meals", Decimal("40"), D1)), [])

    def test_unknown_kind(self):
        self.assertEqual(problems(Line("golf", Decimal("40"), D1)), ["unknown kind 'golf'"])

    def test_zero_amount(self):
        self.assertEqual(problems(Line("meals", Decimal("0"), D1)), ["amount must be positive"])

    def test_receipt_above_the_limit(self):
        self.assertEqual(problems(Line("lodging", Decimal("75.01"), D1)), ["receipt required"])
        self.assertEqual(problems(Line("lodging", Decimal("75.01"), D1, receipt=True)), [])

    def test_no_receipt_needed_at_the_limit(self):
        self.assertEqual(problems(Line("lodging", Decimal("75.00"), D1)), [])


class TestTotals(unittest.TestCase):
    LINES = [Line("meals", Decimal("10.10"), D1), Line("lodging", Decimal("100"), D1),
             Line("meals", Decimal("5.05"), D2)]

    def test_total(self):
        self.assertEqual(total(self.LINES), Decimal("115.15"))

    def test_total_of_nothing(self):
        self.assertEqual(total([]), Decimal("0.00"))

    def test_by_kind_in_order(self):
        self.assertEqual(list(by_kind(self.LINES).items()),
                         [("meals", Decimal("15.15")), ("lodging", Decimal("100.00"))])

    def test_over_cap(self):
        caps = {"meals": Decimal("15.00"), "lodging": Decimal("100.00")}
        self.assertEqual(over_cap(self.LINES, caps), ["meals"])     # exactly at the cap is not over

    def test_no_cap_is_never_over(self):
        self.assertEqual(over_cap(self.LINES, {}), [])


class TestDuplicates(unittest.TestCase):
    def test_the_same_expense_twice(self):
        lines = [Line("meals", Decimal("10"), D1), Line("meals", Decimal("10"), D2),
                 Line("meals", Decimal("10"), D1)]
        self.assertEqual(duplicates(lines), [(0, 2)])

    def test_different_kind_is_not_a_duplicate(self):
        lines = [Line("meals", Decimal("10"), D1), Line("other", Decimal("10"), D1)]
        self.assertEqual(duplicates(lines), [])


if __name__ == "__main__":
    unittest.main()
