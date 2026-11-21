"""Règles des modes de filtrage sur entreprises synthétiques, sans données du projet."""

import unittest

from src.filters import (Company, EnvironmentalPillarFilter, FinancialQualityFilter, ParisAlignmentITRFilter,
                         PositiveContributionFilter)


def company(ticker, **fields):
    data = {"ticker": ticker, "name": ticker, "isin": f"XX{ticker}", "ROIC": "12", "Net margin": "15",
            "FCF yield": "2", "Debt assets": "30", "Volatility 5Y": "0.25", "ITR": "1.8",
            "ENVIRONMENTAL_PILLAR_SCORE": "6", "SDG_03_NET_ALIGNMENT_SCORE": "0", "SDG_09_NET_ALIGNMENT_SCORE": "0",
            "EST_EU_TAXONOMY_MAX_REV": "0", "CT_TOTAL_MAX_REV": "0"}
    data.update(fields)
    return Company(data)


class RecalibratedModeTests(unittest.TestCase):
    def setUp(self):
        # Univers de référence des quantiles : volatilités de 20 % à 59 %, ITR de 1,2 à 3,15 °C.
        self.universe = [company(f"U{i}", **{"Volatility 5Y": str(.20 + .01 * i), "ITR": str(1.2 + .05 * i),
                                              "ENVIRONMENTAL_PILLAR_SCORE": str(1 + .2 * i)}) for i in range(40)]

    def test_light_financial_filter_keeps_volatile_and_investing_companies(self):
        volatile_negative_fcf = company("VOLATILE", **{"Volatility 5Y": "0.55", "FCF yield": "-0.4"})
        light = FinancialQualityFilter(self.universe, filter_mode="recalibree")
        strict = FinancialQualityFilter(self.universe, filter_mode="daphne")
        self.assertTrue(light.evaluate(volatile_negative_fcf))
        self.assertFalse(strict.evaluate(volatile_negative_fcf))
        self.assertFalse(light.evaluate(company("DEBT", **{"Debt assets": "70"})))
        self.assertFalse(light.evaluate(company("LOSS", ROIC="2", **{"Net margin": "1"})))

    def test_light_financial_filter_requires_only_its_own_data(self):
        light = FinancialQualityFilter(self.universe, filter_mode="recalibree")
        self.assertFalse(light.evaluate(company("MISSING", ROIC="")))
        self.assertTrue(light.evaluate(company("NO_FCF", **{"FCF yield": ""})))

    def test_recalibrated_mode_uses_course_temperature_and_e_pillar_rules(self):
        itr = ParisAlignmentITRFilter(companies=self.universe, filter_mode="recalibree")
        self.assertGreater(itr.max_itr, 2.0)  # Q80 de l'univers, pas 2 °C
        self.assertTrue(itr.evaluate(company("WARM", ITR="2.7")))
        self.assertFalse(ParisAlignmentITRFilter(filter_mode="daphne").evaluate(company("WARM", ITR="2.7")))
        pillar = EnvironmentalPillarFilter(self.universe, filter_mode="recalibree")
        self.assertTrue(pillar.evaluate(company("TIE", ENVIRONMENTAL_PILLAR_SCORE=repr(pillar.min_score))))

    def test_recalibrated_mode_keeps_hybrid_contribution(self):
        health = company("HEALTH", SDG_03_NET_ALIGNMENT_SCORE="2.5", ITR="1.9")
        self.assertTrue(PositiveContributionFilter({}, filter_mode="recalibree").evaluate(health))
        self.assertFalse(PositiveContributionFilter({}, filter_mode="mohamed").evaluate(health))


if __name__ == "__main__":
    unittest.main()
