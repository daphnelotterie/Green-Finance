"""Invariants d'allocation sur données synthétiques, sans réseau ni cache local."""

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.optimizer import ESGRiskBudgetingOptimizer, PedersenPortfolioOptimizer, ThematicConstraints


def universe():
    rows = []
    for i in range(30):
        rows.append({
            "ticker": f"ASSET_{i:02d}", "name": f"Entreprise {i}",
            "gics_sector_name": "Health Care" if i < 18 else "Information Technology" if i < 28 else "Industrials",
            "ITR": str(1.3 + i * .015), "GOVERNANCE_PILLAR_SCORE": str(5 + i % 5),
            "SDG_03_NET_ALIGNMENT_SCORE": str(3 + i % 4 if i < 18 else i % 3),
            "SDG_09_NET_ALIGNMENT_SCORE": str(i % 3 if i < 18 else 3 + i % 4),
            "Annualized return 5Y": str(.03 + .004 * i), "Volatility 5Y": str(.16 + .005 * i),
        })
    return rows


def prices():
    dates = pd.bdate_range("2020-01-02", "2025-12-31")
    rng = np.random.default_rng(9812)
    common = rng.normal(0, .007, (len(dates), 1))
    returns = common + rng.normal(.0001, .010, (len(dates), 30))
    return pd.DataFrame(100 * np.exp(np.cumsum(returns, axis=0)), index=dates,
                        columns=[row["ticker"] for row in universe()])


class OptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prices = prices()

    def optimizer(self, mode, rows=None, **kwargs):
        rows = universe() if rows is None else rows
        if mode == "original":
            return PedersenPortfolioOptimizer(None, rows=rows, verbose=False, **kwargs)
        return ESGRiskBudgetingOptimizer(None, rows=rows, prices=self.prices,
                                        as_of="2024-12-31", verbose=False, **kwargs)

    def test_both_modes_respect_every_constraint(self):
        for mode, floor in (("original", .01), ("esg_risk", 0.0)):
            with self.subTest(mode=mode):
                optimizer = self.optimizer(mode)
                weights = np.array(optimizer.optimize())
                self.assertAlmostEqual(weights.sum(), 1, places=9)
                self.assertGreaterEqual(weights.min(), floor - 1e-9)
                self.assertLessEqual(weights.max(), .045 + 1e-9)
                self.assertLessEqual(optimizer.report["Dépassement"], 1e-7)
                self.assertTrue(optimizer.diagnostics["converged"])
                self.assertAlmostEqual(optimizer.risk_contributions.sum(), 1, places=9)
                if mode == "esg_risk":
                    self.assertAlmostEqual(optimizer.budgets.sum(), 1, places=9)
                    self.assertTrue((optimizer.budgets > 0).all())

    def test_prices_after_allocation_date_cannot_change_esg_weights(self):
        first = self.optimizer("esg_risk")
        first.optimize()
        second = self.optimizer("esg_risk")
        second.prices = second.prices.copy()
        second.prices.loc[second.prices.index > "2024-12-31"] *= 1000
        second.optimize()
        np.testing.assert_array_equal(first.cov, second.cov)
        np.testing.assert_array_equal(first.weights, second.weights)
        self.assertEqual(first.covariance_details["last_return_week"], "2024-12-27")
        self.assertEqual(first.covariance_details["observations"], 156)

    def test_esg_does_not_require_historical_return_or_snapshot_volatility(self):
        rows = universe()
        for row in rows:
            del row["Annualized return 5Y"]
            del row["Volatility 5Y"]
        optimizer = self.optimizer("esg_risk", rows=rows)
        optimizer.optimize()
        self.assertTrue(optimizer.diagnostics["converged"])

    def test_infeasible_sector_constraints_stop_both_modes(self):
        for mode in ("original", "esg_risk"):
            with self.subTest(mode=mode):
                optimizer = self.optimizer(mode, constraints=ThematicConstraints(health=(.99, 1)))
                with self.assertRaisesRegex(ValueError, "infaisables"):
                    optimizer.optimize()

    def test_insufficient_weeks_are_rejected(self):
        optimizer = self.optimizer("esg_risk")
        optimizer.prices = optimizer.prices.loc["2024-01-01":]
        with self.assertRaisesRegex(ValueError, "Historique insuffisant"):
            optimizer.optimize()

    def test_missing_history_is_explicitly_reported(self):
        optimizer = self.optimizer("esg_risk")
        optimizer.prices = optimizer.prices.drop(columns=["ASSET_00"])
        optimizer.optimize()
        self.assertEqual(optimizer.n, 29)
        self.assertEqual(optimizer.diagnostics["excluded_assets"],
                         [{"ticker": "ASSET_00", "reason": "Cours absents"}])

    def test_original_missing_historical_inputs_cannot_fall_back_to_snapshot(self):
        optimizer = self.optimizer("original", market_inputs={})
        with self.assertRaisesRegex(ValueError, "historiques manquants"):
            optimizer.optimize()

    def test_missing_impact_data_cannot_be_replaced_with_zero(self):
        rows = universe()
        rows[0]["GOVERNANCE_PILLAR_SCORE"] = "NA"
        for mode in ("original", "esg_risk"):
            with self.subTest(mode=mode):
                optimizer = self.optimizer(mode, rows=rows)
                with self.assertRaisesRegex(ValueError, "GOVERNANCE_PILLAR_SCORE"):
                    optimizer.optimize()

    def test_csv_precision_preserves_budget_and_sector_bounds(self):
        optimizer = self.optimizer("original")
        optimizer.optimize()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio.csv"
            optimizer.export_final_portfolio(path)
            with path.open(encoding="utf-8", newline="") as stream:
                exported = list(csv.DictReader(stream))
        weights = [float(row["weight_decimal"]) for row in exported]
        report = optimizer.constraints.report(weights, [r["gics_sector_name"] for r in exported],
                                               [float(r["itr_celsius"]) for r in exported], .01, .045)
        self.assertLessEqual(report["Dépassement"], 1e-10)


if __name__ == "__main__":
    unittest.main()
