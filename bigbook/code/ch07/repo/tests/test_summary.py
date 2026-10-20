import unittest
from datetime import date
from decimal import Decimal

from expenses.claims import Line
from expenses.summary import largest, month_totals, summary_lines, to_csv

LINES = [Line("lodging", Decimal("1200"), date(2026, 3, 2), "hotel"),
         Line("meals", Decimal("40.5"), date(2026, 2, 27), "dinner, client"),
         Line("meals", Decimal("40.5"), date(2026, 2, 26)),
         Line("mileage", Decimal("86.10"), date(2026, 3, 3))]


class TestSummary(unittest.TestCase):
    def test_lines_by_kind_then_total(self):
        self.assertEqual(summary_lines(LINES), ["meals: 81.00 USD", "lodging: 1,200.00 USD",
                                                "mileage: 86.10 USD", "total: 1,367.10 USD"])

    def test_no_lines(self):
        self.assertEqual(summary_lines([]), ["total: 0.00 USD"])


class TestCsv(unittest.TestCase):
    def test_header_and_rows(self):
        rows = to_csv(LINES).splitlines()
        self.assertEqual(rows[0], "kind,amount,day,note")
        self.assertEqual(rows[1], "lodging,1200.00,2026-03-02,hotel")

    def test_a_note_with_a_comma_is_quoted(self):
        self.assertEqual(to_csv(LINES).splitlines()[2], 'meals,40.50,2026-02-27,"dinner, client"')


class TestLargest(unittest.TestCase):
    def test_largest_first(self):
        self.assertEqual([x.amount for x in largest(LINES, 2)], [Decimal("1200"), Decimal("86.10")])

    def test_equal_amounts_earlier_day_first(self):
        got = largest(LINES, 4)[2:]
        self.assertEqual([x.day for x in got], [date(2026, 2, 26), date(2026, 2, 27)])


class TestMonths(unittest.TestCase):
    def test_month_totals_in_order(self):
        self.assertEqual(list(month_totals(LINES).items()),
                         [("2026-02", Decimal("81.00")), ("2026-03", Decimal("1286.10"))])


if __name__ == "__main__":
    unittest.main()
