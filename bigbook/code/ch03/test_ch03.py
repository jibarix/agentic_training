"""Offline tests for Chapter 3: the statistics against the papers' own numbers and brute force,
and the scorer against the answers that broke Chapter 1's.

Usage: python -m unittest -v test_ch03
"""
import itertools
import json
import unittest
from pathlib import Path
from statistics import fmean

import stats
from score import score

USD = ["USD", "$", "dollar"]


class TestStats(unittest.TestCase):
    def test_miller_sample_size_example(self):
        # Section 5: omega^2 = 1/9, delta = 0.03, alpha = 0.05, power 0.8 -> about 969 questions
        self.assertEqual(round(stats.tasks_needed(0.03, 1 / 9)), 969)

    def test_miller_resampling_example(self):
        # Section 5: n = 198, omega^2 = 1/9, sigma^2 = 1/6 each; K from 1 to 10 -> MDE 13.2% to 7.5%
        # (the paper truncates: the values are 13.27% and 7.57%)
        self.assertEqual(int(1000 * stats.mde(198, 1 / 9, 1 / 6, 1 / 6)), 132)
        self.assertEqual(int(1000 * stats.mde(198, 1 / 9, 1 / 6, 1 / 6, 10, 10)), 75)

    def test_singleton_clusters_change_nothing(self):
        x = [1, 0, 0.5, 1, 1, 0, 2 / 3]
        self.assertAlmostEqual(stats.se_clustered(x, list(range(len(x)))), stats.se(x))

    def test_identical_clusters_count_once(self):
        # Two copies of every task: the clustered error is that of the distinct tasks (up to n-1 vs n)
        x = [1, 0, 1, 1, 0]
        doubled, groups = [v for v in x for _ in (0, 1)], [i for i in range(len(x)) for _ in (0, 1)]
        self.assertGreater(stats.se_clustered(doubled, groups), stats.se(doubled) * 1.3)

    def test_pairing_removes_shared_difficulty(self):
        a = {t: [v] for t, v in enumerate([1, 1, 0, 0, 1, 0, 1, 0])}
        b = {t: [v] for t, v in enumerate([1, 1, 0, 0, 1, 0, 1, 1])}
        c = stats.compare(a, b)
        self.assertAlmostEqual(c["diff"], -1 / 8)
        self.assertLess(c["se"], c["se_unpaired"] / 2)

    def test_pass_at_k_and_pass_hat_k_match_brute_force(self):
        for n in range(1, 7):
            for c in range(n + 1):
                runs = [1] * c + [0] * (n - c)
                for k in range(1, n + 1):
                    draws = list(itertools.combinations(runs, k))
                    self.assertAlmostEqual(stats.pass_at_k(n, c, k), fmean(any(d) for d in draws))
                    self.assertAlmostEqual(stats.pass_hat_k(n, c, k), fmean(all(d) for d in draws))

    def test_variance_parts_of_a_known_mix(self):
        # Half the tasks always right, half always wrong: all variance is between tasks
        between, within = stats.variance_parts({t: [t % 2] * 5 for t in range(10)})
        self.assertAlmostEqual(within, 0)
        self.assertAlmostEqual(between, 10 / 36)


class TestScorer(unittest.TestCase):
    def test_accepts(self):
        for a in ["Final answer: 272 USD", "**Final answer:** $272", "Final answer: 272 dollars.",
                  "Some text.\nFinal answer: 272.00 USD"]:
            self.assertTrue(score(a, 272, USD), a)

    def test_one_descriptive_word(self):
        self.assertTrue(score("Final answer: 13 paid holidays", 13, ["day", "holiday"]))
        self.assertTrue(score("Final answer: 2 floating holidays", 2, ["day", "holiday"]))

    def test_rejects(self):
        for a in ["Final answer: not 272 USD", "Final answer: 272 miles", "Final answer: 140 USD",
                  "Final answer: 272", "Final answer: 272 USD or 300 USD", "Final answer: 272 per day USD x",
                  "Final answer: 272 USD\nFinal answer: 140 USD"]:
            self.assertFalse(score(a, 272, USD), a)

    def test_no_line_is_unscored(self):
        self.assertIsNone(score("The answer is 272 USD.", 272, USD))


class TestTasks(unittest.TestCase):
    def test_held_out_tasks(self):
        tasks = json.loads((Path(__file__).parent / "tasks_heldout.json").read_text())
        dev = {t["id"] for t in json.loads((Path(__file__).parent.parent / "ch01/tasks.json").read_text())}
        self.assertEqual(len(tasks), 40)
        self.assertEqual(len({t["id"] for t in tasks}), 40)
        self.assertFalse(dev & {t["id"] for t in tasks})
        for t in tasks:
            self.assertTrue(score(f"Final answer: {t['answer']} {t['units'][0]}", t["answer"], t["units"]))


if __name__ == "__main__":
    unittest.main()
