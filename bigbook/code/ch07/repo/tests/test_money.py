import unittest
from decimal import Decimal

from expenses.money import format_amount, parse_amount, round_cents, split


class TestRound(unittest.TestCase):
    def test_half_a_cent_rounds_up(self):
        self.assertEqual(round_cents(Decimal("2.345")), Decimal("2.35"))

    def test_below_half_rounds_down(self):
        self.assertEqual(round_cents(Decimal("2.344")), Decimal("2.34"))


class TestParse(unittest.TestCase):
    def test_commas_and_dollar_sign(self):
        self.assertEqual(parse_amount("$1,234.50"), Decimal("1234.50"))

    def test_spaces_and_one_decimal(self):
        self.assertEqual(parse_amount(" 7.5 "), Decimal("7.50"))

    def test_empty_is_none(self):
        self.assertIsNone(parse_amount("  "))
        self.assertIsNone(parse_amount(None))

    def test_zero_is_an_amount(self):
        self.assertEqual(parse_amount("0"), Decimal("0.00"))

    def test_negative_and_text_are_refused(self):
        for bad in ("-3", "abc", "NaN"):
            with self.assertRaises(ValueError):
                parse_amount(bad)


class TestFormat(unittest.TestCase):
    def test_thousands_and_cents(self):
        self.assertEqual(format_amount(Decimal("1234.5")), "1,234.50 USD")

    def test_other_currency(self):
        self.assertEqual(format_amount(Decimal("3"), "EUR"), "3.00 EUR")


class TestSplit(unittest.TestCase):
    def test_even_split(self):
        self.assertEqual(split(Decimal("9.00"), 3), [Decimal("3.00")] * 3)

    def test_extra_cents_go_first(self):
        self.assertEqual(split(Decimal("10.00"), 3), [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")])

    def test_one_part_and_none(self):
        self.assertEqual(split(Decimal("5.55"), 1), [Decimal("5.55")])
        with self.assertRaises(ValueError):
            split(Decimal("5"), 0)


if __name__ == "__main__":
    unittest.main()
