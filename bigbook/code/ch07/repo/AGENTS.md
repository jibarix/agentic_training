# ACME expenses

A small Python package for expense claims: `expenses/` holds the code, `tests/` the unit tests.
Standard library only; nothing to install.

## Tests

Run every test from this folder:

    python -m unittest discover -s tests -t .

Run one file or one test:

    python -m unittest tests.test_money
    python -m unittest tests.test_money.TestParse.test_commas_and_dollar_sign

## Rules

- Fix the code in `expenses/`. Do not change, add or delete anything in `tests/`.
- Amounts are `Decimal`, rounded half up to the cent (`expenses/money.py`). Never use float for money.
- Keep each function's docstring true: it is the specification.
