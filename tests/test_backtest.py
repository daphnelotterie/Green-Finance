"""Vérifications financières déterministes, sans réseau ni données du projet."""

import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.backtest import PortfolioBacktester, WalkForwardBacktester, compute_metrics, monthly_returns, monthly_table
from src.optimizer import load_prices
from src.prices import BENCHMARK_COLUMN, HistoricalPriceLoader, run_prices


def engine(prices, cost=0.001):
    """Isole la comptabilité du portefeuille des solveurs d'allocation."""
    backtester = WalkForwardBacktester.__new__(WalkForwardBacktester)
    backtester.prices = prices.copy()
    backtester.prices_val = prices.ffill()
    backtester.tickers = list(prices.columns)
    backtester.cost = cost
    backtester.window_weeks = 6
    return backtester


class HoldingsAndCostsTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2024-01-02", periods=3, freq="B")
        self.prices = pd.DataFrame({"A": [100., 200., 300.], "B": [100., 100., 100.]},
                                   index=self.dates)

    def test_buy_and_hold_keeps_shares_and_lets_weights_drift(self):
        values, turnover = engine(self.prices).simulate(
            {self.dates[0]: pd.Series({"A": .5, "B": .5})}, self.dates[-1])
        np.testing.assert_allclose(values, [1., 1.5, 2.])
        self.assertNotAlmostEqual(values.iloc[-1], 1.875)  # Résultat d'un 50/50 rééquilibré chaque jour.
        self.assertEqual(turnover, [])

    def test_rebalance_cost_hits_transaction_day_and_no_initial_fee(self):
        prices = self.prices.copy()
        prices.loc[self.dates[-1], "A"] = 200.
        values, turnover = engine(prices).simulate({
            self.dates[0]: pd.Series({"A": 1.}),
            self.dates[1]: pd.Series({"B": 1.}),
        }, self.dates[-1])
        # Vente de tout A puis achat de B : deux unités négociées par euro d'actif.
        np.testing.assert_allclose(values, [1., 2. * (1. - .002), 2. * (1. - .002)])
        self.assertEqual(turnover, [1.])
        self.assertTrue(values.index.is_unique)

    def test_turnover_uses_drifted_weights(self):
        weights = pd.Series({"A": .5, "B": .5})
        values, turnover = engine(self.prices).simulate(
            {self.dates[0]: weights, self.dates[1]: weights}, self.dates[-1])
        # A représente 2/3 au rebalance : retour à 1/2 => rotation de 1/6.
        self.assertAlmostEqual(turnover[0], 1. / 6.)
        self.assertAlmostEqual(values.loc[self.dates[1]], 1.5 * (1. - .001 / 3.))
        self.assertAlmostEqual(values.iloc[-1], 1.5 * (1. - .001 / 3.) * 1.25)

    def test_simulation_rejects_invalid_weights(self):
        invalid = [pd.Series({"A": .4, "B": .4}),
                   pd.Series({"A": 1.1, "B": -.1}),
                   pd.Series({"A": 1., "B": np.nan}),
                   pd.Series([.5, .5], index=["A", "A"])]
        for weights in invalid:
            with self.subTest(weights=weights.to_dict()), self.assertRaises(ValueError):
                engine(self.prices).simulate({self.dates[0]: weights}, self.dates[-1])

    def test_cannot_value_a_holding_before_its_first_price(self):
        prices = self.prices.copy()
        prices.loc[self.dates[0], "B"] = np.nan
        with self.assertRaises(ValueError):
            engine(prices).simulate({self.dates[0]: pd.Series({"A": .5, "B": .5})}, self.dates[-1])

    def test_attribution_reconciles_total_return_and_drifted_final_weights(self):
        backtester = engine(self.prices)
        backtester.start_oos, backtester.last_date = self.dates[0], self.dates[-1]
        weights = pd.Series({"A": .5, "B": .5})
        baseline, _ = backtester.simulate({self.dates[0]: weights}, self.dates[-1])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            backtester.weighted_portfolio_csv = root / "portfolio.csv"
            weights.rename("weight_decimal").to_csv(backtester.weighted_portfolio_csv, index_label="ticker")
            backtester.export_attribution(root, baseline)
            attribution = pd.read_csv(root / "attribution_post2024.csv", index_col=0)
        self.assertAlmostEqual(attribution["contribution_performance"].sum(), baseline.iloc[-1] - 1.)
        self.assertAlmostEqual(attribution.loc["A", "contribution_performance"], 1.)
        self.assertAlmostEqual(attribution.loc["B", "contribution_performance"], 0.)
        self.assertAlmostEqual(attribution.loc["A", "poids_final"], .75)
        self.assertAlmostEqual(attribution.loc["B", "poids_final"], .25)
        self.assertAlmostEqual(attribution["poids_final"].sum(), 1.)


class MonthlyReturnsTests(unittest.TestCase):
    def test_month_end_start_is_the_base_and_months_compound_to_total(self):
        dates = pd.bdate_range("2024-12-31", "2025-03-14")
        values = pd.Series(np.linspace(1., 1.3, len(dates)), index=dates)
        returns = monthly_returns(values)
        self.assertEqual([str(p) for p in returns.index], ["2025-01", "2025-02", "2025-03"])
        self.assertAlmostEqual(np.prod(1 + returns.values) - 1, .3)
        self.assertAlmostEqual(returns.iloc[0], values.loc["2025-01-31"] / values.iloc[0] - 1)

    def test_mid_month_start_counts_the_partial_month(self):
        dates = pd.bdate_range("2025-01-15", "2025-02-28")
        values = pd.Series(np.linspace(2., 2.2, len(dates)), index=dates)
        returns = monthly_returns(values)
        self.assertEqual([str(p) for p in returns.index], ["2025-01", "2025-02"])
        self.assertAlmostEqual(returns.iloc[0], values.loc["2025-01-31"] / 2. - 1)
        self.assertAlmostEqual(np.prod(1 + returns.values) - 1, .1)

    def test_monthly_table_reports_each_year_with_compounded_total(self):
        dates = pd.bdate_range("2024-12-31", "2026-02-27")
        values = pd.Series(np.exp(np.linspace(0, .2, len(dates))), index=dates)
        table = monthly_table({"fonds": values}, "test").set_index("Année")
        self.assertEqual(list(table.index), [2025, 2026])
        total = (1 + table["Année complète"]).prod() - 1
        self.assertAlmostEqual(total, values.iloc[-1] - 1)
        self.assertTrue(pd.isna(table.loc[2026, "mars"]))


class InputAndMetricsTests(unittest.TestCase):
    def test_metrics_use_common_dates_and_benchmark_against_itself(self):
        dates = pd.date_range("2022-01-07", periods=100, freq="W-FRI")
        benchmark = pd.Series(np.exp(np.cumsum(.002 + .01 * np.sin(np.arange(len(dates))))), index=dates)
        # Les observations extrêmes hors de l'intersection ne doivent pas intervenir.
        extra = pd.Series([10000., .0001], index=[dates[0] - pd.Timedelta(days=7),
                                                 dates[-1] + pd.Timedelta(days=7)])
        metrics = compute_metrics(100. * benchmark, pd.concat([extra, benchmark]).sort_index())
        years = (dates[-1] - dates[0]).days / 365.25
        self.assertAlmostEqual(metrics["Rendement annualisé"], (benchmark.iloc[-1] / benchmark.iloc[0]) ** (1. / years) - 1.)
        self.assertAlmostEqual(metrics["Bêta"], 1.)
        self.assertAlmostEqual(metrics["Tracking error"], 0.)
        self.assertTrue(math.isnan(metrics["Ratio d'information"]))

    def test_metrics_reject_non_finite_valuations(self):
        dates = pd.date_range("2023-01-06", periods=12, freq="W-FRI")
        values = pd.Series(np.linspace(1., 2., len(dates)), index=dates)
        invalid = values.copy()
        invalid.iloc[4] = np.inf
        with self.assertRaises(ValueError):
            compute_metrics(invalid, values)

    def test_esg_snapshot_rejects_invalid_weights(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference = root / "universe.csv"
            pd.DataFrame({"ticker": ["A", "B"]}).to_csv(reference, index=False)
            invalid = [pd.DataFrame({"ticker": ["A", "B"], "weight_decimal": [1.1, -.1]}),
                       pd.DataFrame({"ticker": ["A", "B"], "weight_decimal": [1., np.nan]}),
                       pd.DataFrame({"ticker": ["A", "A"], "weight_decimal": [.5, .5]})]
            for frame in invalid:
                with self.subTest(frame=frame.to_dict()):
                    portfolio = root / "portfolio.csv"
                    frame.to_csv(portfolio, index=False)
                    with self.assertRaises(ValueError):
                        PortfolioBacktester(reference, portfolio)

    def test_price_cache_rejects_ambiguous_or_invalid_data(self):
        cases = {
            "duplicate_dates": "date,A\n2024-01-02,100\n2024-01-02,101\n",
            "duplicate_tickers": "date,A,A\n2024-01-02,100,101\n2024-01-03,102,103\n",
            "negative": "date,A\n2024-01-02,-1\n2024-01-03,2\n",
            "zero": "date,A\n2024-01-02,0\n2024-01-03,2\n",
            "infinite": "date,A\n2024-01-02,inf\n2024-01-03,2\n",
            "not_numeric": "date,A\n2024-01-02,abc\n2024-01-03,2\n",
            "invalid_date": "date,A\nnot-a-date,100\n2024-01-03,2\n",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.csv"
            for name, contents in cases.items():
                with self.subTest(case=name):
                    path.write_text(contents, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_prices(path)

    def test_price_cache_preserves_holes_before_listing(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "prices.csv"
            path.write_text("date,A,B\n2024-01-02,100,\n2024-01-03,101,50\n", encoding="utf-8")
            prices = load_prices(path)
        self.assertTrue(pd.isna(prices.iloc[0]["B"]))


class PointInTimeAndCurrencyTests(unittest.TestCase):
    def test_refreshing_one_mode_preserves_and_reconverts_other_cached_assets(self):
        dates = pd.date_range("2024-01-02", periods=2, freq="B")

        def downloaded_prices(loader):
            self.assertEqual({asset["ticker"] for asset in loader.assets}, {"A", "B"})
            self.assertEqual(len(loader.assets), 2)
            quotations = {"A.Y": [120., 120.], "B.Y": [12500., 12500.]}
            loader.prices_local = pd.DataFrame({ticker: quotations[ticker]
                for ticker in loader.yahoo_to_ticker}, index=dates)
            loader.benchmark_local = pd.Series([100., 101.], index=dates)
            return loader.prices_local

        def downloaded_fx(loader):
            loader.quote_currency = {"A.Y": ("USD", 1.), "B.Y": ("GBP", 100.)}
            loader.fx_rates = pd.DataFrame({"USD": [1.2, 1.2], "GBP": [.8, .8], "EUR": [1., 1.]}, index=dates)
            return loader.fx_rates

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            reference, requested, cache = root / "reference.csv", root / "requested.csv", root / "cache"
            pd.DataFrame({"ticker": ["A", "B"], "ticker_yahoo": ["A.Y", "B.Y"],
                          "currency": ["USD", "GBp"]}).to_csv(reference, index=False)
            pd.DataFrame({"ticker": ["A"], "weight_decimal": [1.]}).to_csv(requested, index=False)
            cache.mkdir()
            pd.DataFrame({"A": [1., 1.], "B": [2., 2.], BENCHMARK_COLUMN: [3., 3.]},
                         index=dates).to_csv(cache / "prix_eur.csv", index_label="date")
            # Seuls les téléchargements sont simulés : lecture de l'ancien cache,
            # union des titres, conversion et remplacement des trois CSV sont réels.
            with patch.object(HistoricalPriceLoader, "download_prices", autospec=True, side_effect=downloaded_prices), \
                 patch.object(HistoricalPriceLoader, "download_fx_rates", autospec=True, side_effect=downloaded_fx):
                output = run_prices(reference, requested, cache)
            refreshed = pd.read_csv(output, index_col=0)
            self.assertEqual(set(refreshed.columns), {"A", "B", BENCHMARK_COLUMN})
            np.testing.assert_allclose(refreshed["A"], [100., 100.])
            np.testing.assert_allclose(refreshed["B"], [156.25, 156.25])
            np.testing.assert_allclose(refreshed[BENCHMARK_COLUMN], [100., 101.])
            local = pd.read_csv(cache / "prix_devise_locale.csv", index_col=0)
            np.testing.assert_allclose(local["B"], [12500., 12500.])
            self.assertTrue((cache / "taux_de_change.csv").exists())
            self.assertFalse((cache / ".download").exists())

    def test_eligibility_and_market_inputs_ignore_future_prices(self):
        dates = pd.date_range("2018-01-01", "2018-04-20", freq="B")
        cutoff = pd.Timestamp("2018-03-14")  # Mercredi, semaine encore incomplète.
        prices = pd.DataFrame({"A": 100. + np.arange(len(dates), dtype=float),
                               "B": np.nan}, index=dates)
        prices.loc[prices.index > cutoff, "B"] = 50.
        backtester = engine(prices)
        expected_inputs = backtester.pedersen_market_inputs(cutoff, ["A"])
        self.assertEqual(backtester.available_tickers(cutoff), ["A"])
        backtester.prices.loc[backtester.prices.index > cutoff, :] = [100000., .0001]
        self.assertEqual(backtester.available_tickers(cutoff), ["A"])
        self.assertEqual(backtester.pedersen_market_inputs(cutoff, ["A"]), expected_inputs)

    def test_currency_conversion_respects_pence_and_quote_direction(self):
        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        loader = HistoricalPriceLoader.__new__(HistoricalPriceLoader)
        loader.prices_local = pd.DataFrame({"LONDON": [12500., 12500.], "US": [120., 120.]}, index=dates)
        loader.quote_currency = {"LONDON": ("GBP", 100.), "US": ("USD", 1.)}
        loader.fx_rates = pd.DataFrame({"GBP": [.8, 1.], "USD": [1.2, 1.5], "EUR": [1., 1.]}, index=dates)
        loader.benchmark_local = pd.Series([100., 101.], index=dates)
        loader.benchmark_currency, loader.base_currency = "EUR", "EUR"
        converted = loader.convert_to_base_currency()
        np.testing.assert_allclose(converted["LONDON"], [156.25, 125.])
        np.testing.assert_allclose(converted["US"], [100., 80.])
        np.testing.assert_allclose(loader.benchmark_base, [100., 101.])


if __name__ == "__main__":
    unittest.main()
