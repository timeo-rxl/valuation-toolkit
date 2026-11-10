"""Tests for the valuation toolkit.

Expected values are anchored to the Lassonde worked example, whose
inputs come from public filings — so a failure means the code drifted,
not that the example changed.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo import load_example  # noqa: E402
from valuation import (  # noqa: E402
    CapitalAllocationInputs,
    Company,
    DCFInputs,
    DivestitureInputs,
    dcf_sensitivity,
    dcf_value,
    divestiture_analysis,
    ev_range,
    football_field,
    implied_price_from_multiple,
    project_free_cash_flow,
    range_from_multiples,
)
from valuation.report import render_text, summarise  # noqa: E402


def lassonde():
    return load_example("examples/lassonde.yaml")


class TestCompany(unittest.TestCase):
    def test_lassonde_ev_and_multiple(self):
        c = lassonde().company
        self.assertAlmostEqual(c.market_cap_m, 1576.8, delta=0.5)
        self.assertAlmostEqual(c.enterprise_value_m, 2129.1, delta=0.5)
        self.assertAlmostEqual(c.ev_to_ebitda, 5.82, delta=0.01)

    def test_implied_price_at_peer_multiples(self):
        c = lassonde().company
        # (multiple x LTM EBITDA - net debt - NCI) / shares
        self.assertAlmostEqual(implied_price_from_multiple(c, 7.0), 297.66, delta=0.5)
        self.assertAlmostEqual(implied_price_from_multiple(c, 8.4), 373.55, delta=0.5)
        self.assertAlmostEqual(implied_price_from_multiple(c, 9.2), 416.91, delta=0.5)


class TestDCF(unittest.TestCase):
    def test_first_forecast_year(self):
        ex = lassonde()
        year1 = project_free_cash_flow(ex.dcf)[0]
        self.assertAlmostEqual(year1["sales"], 211.665, delta=0.01)
        self.assertAlmostEqual(year1["ebitda"], 34.93, delta=0.05)
        self.assertAlmostEqual(year1["fcf"], 21.30, delta=0.05)

    def test_base_case_matches_reference(self):
        # Reference: the corrected Excel DCF, WACC 9%, growth 2%.
        ev = dcf_value(lassonde().dcf)["enterprise_value"]
        self.assertAlmostEqual(ev, 314.6, delta=1.5)

    def test_higher_discount_rate_lowers_value(self):
        ex = lassonde()
        ev12 = dcf_value(ex.dcf, wacc=0.12)["enterprise_value"]
        self.assertAlmostEqual(ev12, 219.8, delta=1.5)

    def test_sensitivity_is_monotone(self):
        ex = lassonde()
        table = dcf_sensitivity(ex.dcf, waccs=[0.08, 0.09, 0.10], growths=[0.015, 0.02, 0.025])
        for g in [0.015, 0.02, 0.025]:
            self.assertGreater(table[(0.08, g)], table[(0.09, g)])
            self.assertGreater(table[(0.09, g)], table[(0.10, g)])
        for w in [0.08, 0.09, 0.10]:
            self.assertLess(table[(w, 0.015)], table[(w, 0.02)])
            self.assertLess(table[(w, 0.02)], table[(w, 0.025)])

    def test_wacc_must_exceed_growth(self):
        with self.assertRaises(ValueError):
            dcf_value(DCFInputs(100, 20, wacc=0.02, terminal_growth=0.02))


class TestMultiples(unittest.TestCase):
    def test_ev_range(self):
        low, high = ev_range(33.9, 8.4, 9.2)
        self.assertAlmostEqual(low, 284.9, delta=0.5)
        self.assertAlmostEqual(high, 312.0, delta=0.5)

    def test_range_from_multiples(self):
        lo, med, hi = range_from_multiples([9.2, 8.4, 8.87])
        self.assertEqual((lo, med, hi), (8.4, 8.87, 9.2))

    def test_football_field_selected_range(self):
        ex = lassonde()
        rows = {r["method"]: r for r in summarise(ex)["football_field"]}
        sel = rows["Selected range (Selected range)"]
        self.assertAlmostEqual(sel["ev_low"], 288.3, delta=0.5)
        self.assertAlmostEqual(sel["ev_high"], 339.1, delta=0.5)


class TestDivestiture(unittest.TestCase):
    def test_bridge_at_midpoint(self):
        ex = lassonde()
        d = divestiture_analysis(ex.division, 9.25)
        self.assertAlmostEqual(d["enterprise_value"], 313.7, delta=0.5)
        self.assertAlmostEqual(d["net_proceeds_to_seller"], 273.9, delta=0.5)
        self.assertAlmostEqual(d["value_created_vs_embedded"], 96.4, delta=0.5)
        self.assertAlmostEqual(d["value_created_per_share"], 14.27, delta=0.05)

    def test_breakeven_multiples(self):
        ex = lassonde()
        d = divestiture_analysis(ex.division, 9.25)
        self.assertAlmostEqual(d["breakeven_vs_embedded"], 6.00, delta=0.05)
        # Same sale judged against the DCF hold value (C$314.5m x 90%).
        dcf_hold = dcf_value(ex.dcf)["enterprise_value"] * 0.90
        d2 = divestiture_analysis(ex.division, 9.25, hold_value_m=dcf_hold)
        self.assertAlmostEqual(d2["breakeven_vs_hold"], 9.58, delta=0.1)

    def test_no_tax_below_basis(self):
        div = DivestitureInputs(
            division_name="Test", ebitda_m=10.0, tax_basis_m=1000.0
        )
        d = divestiture_analysis(div, 5.0)
        self.assertEqual(d["tax"], 0.0)
        self.assertAlmostEqual(d["net_proceeds_100pct"], 50.0 * 0.97, delta=0.01)

    def test_capital_allocation(self):
        ex = lassonde()
        s = summarise(ex)
        ca = s["capital_allocation"]
        self.assertAlmostEqual(ca["leverage_today"], 1.25, delta=0.01)
        self.assertAlmostEqual(ca["debt_repayment_leverage_neutral"], 48.6, delta=0.5)
        self.assertAlmostEqual(ca["capital_available"], 225.3, delta=0.5)
        self.assertAlmostEqual(ca["shares_repurchasable_m"], 0.965, delta=0.01)


class TestExamples(unittest.TestCase):
    def test_both_examples_run_end_to_end(self):
        for path in ["examples/lassonde.yaml", "examples/acme.yaml"]:
            ex = load_example(path)
            s = summarise(ex)
            self.assertGreater(s["dcf"]["enterprise_value"], 0)
            text = render_text(s, ex)
            self.assertIn(ex.company.name, text)
            self.assertIn("Enterprise value", text)


if __name__ == "__main__":
    unittest.main()
