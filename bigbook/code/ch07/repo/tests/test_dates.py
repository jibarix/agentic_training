import unittest
from datetime import date

from expenses.dates import is_weekend, nights, parse_date, quarter, travel_days


class TestParse(unittest.TestCase):
    def test_iso_date(self):
        self.assertEqual(parse_date(" 2026-03-04 "), date(2026, 3, 4))

    def test_other_formats_are_refused(self):
        for bad in ("2026/03/04", "04-03-2026", "2026-3-4", "20260304"):
            with self.assertRaises(ValueError):
                parse_date(bad)


class TestNights(unittest.TestCase):
    def test_three_nights(self):
        self.assertEqual(nights(date(2026, 3, 1), date(2026, 3, 4)), 3)

    def test_same_day_is_zero(self):
        self.assertEqual(nights(date(2026, 3, 1), date(2026, 3, 1)), 0)

    def test_backwards_is_refused(self):
        with self.assertRaises(ValueError):
            nights(date(2026, 3, 4), date(2026, 3, 1))


class TestDays(unittest.TestCase):
    def test_both_ends_count(self):
        self.assertEqual(travel_days(date(2026, 3, 1), date(2026, 3, 4)), 4)

    def test_one_day_trip(self):
        self.assertEqual(travel_days(date(2026, 3, 1), date(2026, 3, 1)), 1)

    def test_across_a_month_end(self):
        self.assertEqual(travel_days(date(2026, 2, 27), date(2026, 3, 2)), 4)


class TestCalendar(unittest.TestCase):
    def test_weekend(self):
        self.assertTrue(is_weekend(date(2026, 3, 7)))       # Saturday
        self.assertTrue(is_weekend(date(2026, 3, 8)))       # Sunday

    def test_weekday(self):
        self.assertFalse(is_weekend(date(2026, 3, 6)))      # Friday
        self.assertFalse(is_weekend(date(2026, 3, 9)))      # Monday

    def test_quarters(self):
        got = [quarter(date(2026, m, 1)) for m in range(1, 13)]
        self.assertEqual(got, [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4])


if __name__ == "__main__":
    unittest.main()
