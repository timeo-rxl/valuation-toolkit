"""Assemble every method into one summary, then render it as text.

``summarise`` does the maths; ``render_text`` only formats it, so the
same summary can feed a notebook, a slide or a JSON export later.
"""

from __future__ import annotations

from .dcf import dcf_sensitivity, dcf_value
from .divestiture import capital_allocation, divestiture_analysis
from .models import MultipleRange, ValuationExample
from .multiples import football_field, implied_price_from_multiple, range_from_multiples


def summarise(example: ValuationExample) -> dict:
    company = example.company
    out: dict = {"company": company}

    # --- Trading multiples: where does the group sit? ---
    out["group_ev_ebitda"] = company.ev_to_ebitda
    out["implied_prices"] = {
        m: implied_price_from_multiple(company, m)
        for m in sorted(set(example.trading_multiples + example.precedent_multiples))
    }

    # --- DCF on the division (or the group, if no division is set) ---
    dcf = dcf_value(example.dcf)
    out["dcf"] = dcf
    out["dcf_sensitivity"] = dcf_sensitivity(
        example.dcf, waccs=[0.08, 0.09, 0.10, 0.12], growths=[0.015, 0.02, 0.025]
    )

    # --- Football field on the division's EBITDA ---
    if example.division is not None:
        div = example.division
        ebitda = div.ebitda_m
        methods = [
            MultipleRange(
                "Value inside the group today",
                company.ev_to_ebitda,
                company.ev_to_ebitda,
                "The group's own trading multiple",
            )
        ]
        if example.trading_multiples:
            lo, _, hi = range_from_multiples(example.trading_multiples)
            methods.append(
                MultipleRange("Trading comparables", lo, hi, "Listed peers")
            )
        if example.precedent_multiples:
            lo, _, hi = range_from_multiples(example.precedent_multiples)
            methods.append(
                MultipleRange("Precedent transactions", lo, hi, "Past deals")
            )
        dcf_lo = min(out["dcf_sensitivity"].values())
        dcf_hi = max(out["dcf_sensitivity"].values())
        methods.append(
            MultipleRange(
                "DCF (WACC 8-12%, growth 1.5-2.5%)",
                dcf_lo / ebitda,
                dcf_hi / ebitda,
                "Implied multiples, for comparison only",
            )
        )
        if example.selected_multiple_range is not None:
            sel = example.selected_multiple_range
            methods.append(
                MultipleRange(f"Selected range ({sel.label})", sel.low, sel.high, sel.comment)
            )
        out["football_field"] = football_field(ebitda, methods)
        out["ebitda_scenarios"] = example.division_ebitda_scenarios

        # --- Keep vs. sell at the selected midpoint ---
        if example.selected_multiple_range is not None:
            mid = example.selected_multiple_range.midpoint
            out["divestiture"] = divestiture_analysis(div, mid)
            out["divestiture_scenarios"] = {
                name: divestiture_analysis(
                    _with_ebitda(div, ebitda_scn), mid
                )
                for name, ebitda_scn in example.division_ebitda_scenarios.items()
            }
            # Same sale, judged against the DCF hold value instead.
            out["divestiture_vs_dcf_hold"] = divestiture_analysis(
                div, mid, hold_value_m=dcf["enterprise_value"] * div.ownership_pct
            )

    # --- Capital allocation after the sale ---
    if example.capital_allocation is not None:
        out["capital_allocation"] = capital_allocation(example.capital_allocation)
    return out


def _with_ebitda(div, ebitda_m: float):
    from dataclasses import replace

    return replace(div, ebitda_m=ebitda_m)


def _m(x: float) -> str:
    return f"{x:,.1f}"


def _x(x: float) -> str:
    return f"{x:.2f}x"


def render_text(summary: dict, example: ValuationExample) -> str:
    c = example.company
    lines = [
        f"{c.name} ({c.ticker}) — valuation summary",
        "=" * 60,
        "",
        f"Share price: {c.currency}{c.share_price:,.2f}  |  Shares: "
        f"{c.shares_outstanding_m:.3f}m  |  Market cap: {c.currency}{_m(c.market_cap_m)}m",
        f"Net debt: {c.currency}{_m(c.net_debt_m)}m  |  EV: {c.currency}{_m(c.enterprise_value_m)}m"
        f"  |  EV / LTM EBITDA: {_x(summary['group_ev_ebitda'])}",
        "",
        "Implied share price if the group traded at a peer multiple:",
    ]
    for mult, price in sorted(summary["implied_prices"].items()):
        lines.append(f"  {_x(mult):>7}  ->  {c.currency}{price:,.2f}")
    dcf = summary["dcf"]
    lines += [
        "",
        f"DCF (WACC {dcf['wacc']:.0%}, terminal growth {dcf['terminal_growth']:.1%}):",
        f"  PV of free cash flow (5y): {c.currency}{_m(dcf['pv_fcf'])}m",
        f"  Terminal value: {c.currency}{_m(dcf['terminal_value'])}m "
        f"(PV {c.currency}{_m(dcf['pv_terminal_value'])}m)",
        f"  Enterprise value: {c.currency}{_m(dcf['enterprise_value'])}m",
        "",
        "DCF sensitivity — enterprise value (rows WACC, columns terminal growth):",
    ]
    growths = sorted({g for (_, g) in summary["dcf_sensitivity"]})
    lines.append("        " + "".join(f"{g:>12.1%}" for g in growths))
    for w in sorted({w for (w, _) in summary["dcf_sensitivity"]}):
        cells = "".join(
            f"{summary['dcf_sensitivity'][(w, g)]:>12,.0f}" for g in growths
        )
        lines.append(f"  {w:>4.0%}  {cells}")
    if "football_field" in summary:
        lines += ["", "Football field — enterprise value of the division:"]
        for row in summary["football_field"]:
            lines.append(
                f"  {row['method']:<38} {_x(row['low_multiple'])} - {_x(row['high_multiple'])}"
                f"  ->  {c.currency}{_m(row['ev_low'])}m - {c.currency}{_m(row['ev_high'])}m"
            )
    if "divestiture" in summary:
        d = summary["divestiture"]
        lines += [
            "",
            f"Keep vs. sell — {example.division.division_name} "
            f"at {d['sale_multiple']:.2f}x EBITDA:",
            f"  Enterprise value: {c.currency}{_m(d['enterprise_value'])}m",
            f"  Separation ({example.division.separation_pct_of_ev:.0%}) "
            f"+ costs ({example.division.transaction_pct_of_ev:.0%}) + tax: "
            f"{c.currency}{_m(d['separation'] + d['transaction_costs'] + d['tax'])}m",
            f"  Net proceeds to {c.name}: {c.currency}{_m(d['net_proceeds_to_seller'])}m",
            f"  Value inside the group today: {c.currency}{_m(d['embedded_value'])}m",
            f"  Value created by selling: {c.currency}{_m(d['value_created_vs_embedded'])}m "
            f"({c.currency}{d['value_created_per_share']:.2f} per share)",
            f"  Break-even sale multiple: {_x(d['breakeven_vs_embedded'])} "
            f"(vs. group multiple) / {_x(summary['divestiture_vs_dcf_hold']['breakeven_vs_hold'])} (vs. DCF hold value)",
        ]
        vs_dcf = summary["divestiture_vs_dcf_hold"]
        lines.append(
            f"  Sale vs. keeping, DCF hold value: "
            f"{c.currency}{vs_dcf['value_created_vs_hold']:+,.1f}m"
        )
        if summary.get("divestiture_scenarios"):
            lines.append("  Scenarios (same multiple, different EBITDA):")
            for name, sc in summary["divestiture_scenarios"].items():
                lines.append(
                    f"    {name:<6} EBITDA {c.currency}{_m(sc['enterprise_value'] / d['sale_multiple'])}m"
                    f"  ->  EV {c.currency}{_m(sc['enterprise_value'])}m"
                    f"  ->  value created {c.currency}{_m(sc['value_created_vs_embedded'])}m"
                )
    if "capital_allocation" in summary:
        ca = summary["capital_allocation"]
        lines += [
            "",
            "Capital allocation after the sale:",
            f"  Leverage today: {ca['leverage_today']:.2f}x net debt / EBITDA",
            f"  Debt repayment (keep leverage flat): {c.currency}{_m(ca['debt_repayment_leverage_neutral'])}m",
            f"  Capital left for growth / buybacks: {c.currency}{_m(ca['capital_available'])}m",
            f"  Shares repurchasable: {ca['shares_repurchasable_m']:.3f}m "
            f"({ca['shares_repurchasable_pct']:.1%} of shares outstanding)",
        ]
        if ca["buyback_value_created"]:
            lines.append(
                f"  Buyback value created (price below intrinsic value): "
                f"{c.currency}{_m(ca['buyback_value_created'])}m"
            )
    if example.notes:
        lines += ["", "Notes:"]
        lines += [f"  - {n}" for n in example.notes]
    return "\n".join(lines) + "\n"
