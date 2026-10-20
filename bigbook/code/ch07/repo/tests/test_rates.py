import unittest
from decimal import Decimal

from expenses.rates import lodging_allowance, meals_allowance, mileage, rate


class TestRate(unittest.TestCase):
    def test_listed_city_any_case(self):
        self.assertEqual(rate(" Boston ", "meals"), Decimal("79"))
        self.assertEqual(rate("DENVER", "lodging"), Decimal("199"))

    def test_city_not_listed_gets_the_default(self):
        self.assertEqual(rate("Albany", "meals"), Decimal("59"))
        self.assertEqual(rate("Albany", "lodging"), Decimal("110"))

    def test_unknown_kind(self):
        with self.assertRaises(KeyError):
            rate("Boston", "parking")


class TestMeals(unittest.TestCase):
    def test_four_day_trip(self):
        # 79 * 2 + 2 * 79 * 0.75
        self.assertEqual(meals_allowance("Boston", 4), Decimal("276.50"))

    def test_two_day_trip(self):
        self.assertEqual(meals_allowance("Denver", 2), Decimal("111.00"))

    def test_one_day_trip(self):
        self.assertEqual(meals_allowance("Albany", 1), Decimal("44.25"))

    def test_no_days_is_refused(self):
        with self.assertRaises(ValueError):
            meals_allowance("Boston", 0)


class TestLodgingAndMileage(unittest.TestCase):
    def test_lodging(self):
        self.assertEqual(lodging_allowance("Chicago", 3), Decimal("693.00"))
        self.assertEqual(lodging_allowance("Chicago", 0), Decimal("0.00"))

    def test_mileage(self):
        self.assertEqual(mileage(123), Decimal("86.10"))
        self.assertEqual(mileage("10.5"), Decimal("7.35"))

    def test_negative_miles_are_refused(self):
        with self.assertRaises(ValueError):
            mileage(-1)


if __name__ == "__main__":
    unittest.main()
