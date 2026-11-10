"""Valuation toolkit — interactive Streamlit app.

The same engine as the CLI demo (``demo.py``), with the numbers as
controls: pick an example, change the share price, the WACC or the
sale multiple, and the DCF, the football field and the keep-vs-sell
answer recompute instantly.

Run:
    streamlit run app.py
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import streamlit as st

from demo import load_example
from valuation import CapitalAllocationInputs, MultipleRange, divestiture_analysis
from valuation.report import summarise

st.set_page_config(
    page_title="Valuation Toolkit",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Valuation Toolkit")
st.caption(
    "Value any listed company — DCF, trading comps, precedents, football field, "
    "and keep-vs-sell. The numbers below are editable: change an assumption and "
    "every answer recomputes."
)

EXAMPLES = {
    "Lassonde Industries (LAS.A) — worked example": "examples/lassonde.yaml",
    "Acme Foods — fictional example": "examples/acme.yaml",
}

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Company")
    example_name = st.selectbox("Example", list(EXAMPLES))
    base = load_example(Path(__file__).resolve().parent / EXAMPLES[example_name])
    company = base.company

    share_price = st.number_input(
        f"Share price ({company.currency})", min_value=0.01, value=float(company.share_price), step=1.0
    )
    net_debt = st.number_input(
        f"Net debt ({company.currency}m)", value=float(company.net_debt_m), step=10.0
    )
    ltm_ebitda = st.number_input(
        f"LTM EBITDA ({company.currency}m)", min_value=0.01, value=float(company.ltm_ebitda_m), step=10.0
    )
    ltm_sales = st.number_input(
        f"LTM sales ({company.currency}m)", min_value=0.01, value=float(company.ltm_sales_m), step=50.0
    )

    st.header("DCF assumptions")
    sales_growth = st.slider("Sales growth", 0.0, 0.10, float(base.dcf.sales_growth), 0.005, format="%.1f%%")
    wacc = st.slider("WACC", 0.05, 0.15, float(base.dcf.wacc), 0.005, format="%.1f%%")
    terminal_growth = st.slider(
        "Terminal growth", 0.0, 0.04, float(base.dcf.terminal_growth), 0.005, format="%.1f%%"
    )
    tax_rate = st.slider("Tax rate", 0.0, 0.40, float(base.dcf.tax_rate), 0.01, format="%.0f%%")

    sale_multiple = None
    division_ebitda = None
    if base.division is not None and base.selected_multiple_range is not None:
        st.header("Keep vs. sell")
        division_ebitda = st.number_input(
            f"Division EBITDA, 2027E ({company.currency}m)",
            min_value=0.01,
            value=float(base.division.ebitda_m),
            step=1.0,
        )
        sel = base.selected_multiple_range
        sale_multiple = st.slider(
            "Sale multiple (EV / EBITDA)",
            float(sel.low) - 2.0,
            float(sel.high) + 2.0,
            float(sel.midpoint),
            0.25,
            format="%.2fx",
        )

# ---------------------------------------------------------------- rebuild + summarise
company = replace(
    company,
    share_price=share_price,
    net_debt_m=net_debt,
    ltm_ebitda_m=ltm_ebitda,
    ltm_sales_m=ltm_sales,
)
dcf_inputs = replace(
    base.dcf,
    sales_growth=sales_growth,
    wacc=wacc,
    terminal_growth=terminal_growth,
    tax_rate=tax_rate,
)
example = replace(base, company=company, dcf=dcf_inputs)
if base.division is not None and sale_multiple is not None:
    division = replace(base.division, ebitda_m=division_ebitda)
    example = replace(
        example,
        division=division,
        selected_multiple_range=MultipleRange(
            "Selected", sale_multiple, sale_multiple, "Set with the slider"
        ),
    )
    if base.capital_allocation is not None:
        net = divestiture_analysis(division, sale_multiple)["net_proceeds_to_seller"]
        example = replace(
            example,
            capital_allocation=replace(
                base.capital_allocation, net_proceeds_m=net
            ),
        )

summary = summarise(example)
cur = company.currency


def money(x: float) -> str:
    return f"{cur}{x:,.1f}m"


def price(x: float) -> str:
    return f"{cur}{x:,.2f}"


# ---------------------------------------------------------------- group KPIs
st.subheader(f"{company.name} ({company.ticker}) — the group today")
cols = st.columns(4)
with cols[0]:
    st.metric("Share price", price(company.share_price))
with cols[1]:
    st.metric("Market cap", money(company.market_cap_m))
with cols[2]:
    st.metric("Enterprise value", money(company.enterprise_value_m))
with cols[3]:
    st.metric("EV / LTM EBITDA", f"{summary['group_ev_ebitda']:.2f}x")

st.subheader("Implied share price if the group traded at a peer multiple")
implied = pd.DataFrame(
    {
        "Multiple": [f"{m:.2f}x" for m in sorted(summary["implied_prices"])],
        "Implied price": [price(p) for p in (summary["implied_prices"][m] for m in sorted(summary["implied_prices"]))],
    }
)
st.dataframe(implied, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- DCF
dcf = summary["dcf"]
st.subheader("DCF — the division's future cash flows")
cols = st.columns(3)
with cols[0]:
    st.metric("DCF enterprise value", money(dcf["enterprise_value"]))
with cols[1]:
    st.metric("PV of FCF (5 years)", money(dcf["pv_fcf"]))
with cols[2]:
    st.metric("PV of terminal value", money(dcf["pv_terminal_value"]))

fcf_rows = [
    {
        "Year": r["year"],
        "Sales": money(r["sales"]),
        "EBITDA": money(r["ebitda"]),
        "EBIT": money(r["ebit"]),
        "NOPAT": money(r["nopat"]),
        "Free cash flow": money(r["fcf"]),
    }
    for r in dcf["years"]
]
st.dataframe(pd.DataFrame(fcf_rows), use_container_width=True, hide_index=True)

st.subheader("DCF sensitivity — enterprise value (WACC × terminal growth)")
growths = sorted({g for (_, g) in summary["dcf_sensitivity"]})
waccs = sorted({w for (w, _) in summary["dcf_sensitivity"]})
sens = pd.DataFrame(
    {
        f"g = {g:.1%}": [summary["dcf_sensitivity"][(w, g)] for w in waccs]
        for g in growths
    },
    index=[f"WACC {w:.0%}" for w in waccs],
)
st.dataframe(sens.style.format("{:,.0f}"), use_container_width=True)

# ---------------------------------------------------------------- football field
if "football_field" in summary:
    st.subheader("Football field — enterprise value of the division")
    ff_rows = [
        {
            "Method": r["method"],
            "Multiple": f"{r['low_multiple']:.2f}x – {r['high_multiple']:.2f}x",
            "EV low": money(r["ev_low"]),
            "EV mid": money(r["ev_mid"]),
            "EV high": money(r["ev_high"]),
        }
        for r in summary["football_field"]
    ]
    st.dataframe(pd.DataFrame(ff_rows), use_container_width=True, hide_index=True)
    try:
        import altair as alt

        ff_chart = pd.DataFrame(
            {
                "Method": [r["method"] for r in summary["football_field"]],
                "EV low": [r["ev_low"] for r in summary["football_field"]],
                "EV high": [r["ev_high"] for r in summary["football_field"]],
            }
        )
        base_chart = alt.Chart(ff_chart).encode(y=alt.Y("Method:N", sort=None))
        chart = (
            base_chart.mark_bar(color="#4e79a7")
            .encode(x="EV low:Q", x2="EV high:Q", tooltip=["Method", "EV low", "EV high"])
            .properties(height=40 * len(ff_chart) + 40)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        pass

# ---------------------------------------------------------------- keep vs sell
if "divestiture" in summary:
    d = summary["divestiture"]
    vs_dcf = summary["divestiture_vs_dcf_hold"]
    st.subheader(
        f"Keep vs. sell — {example.division.division_name} at {d['sale_multiple']:.2f}x EBITDA"
    )
    cols = st.columns(4)
    with cols[0]:
        st.metric("Sale EV", money(d["enterprise_value"]))
    with cols[1]:
        st.metric("Net proceeds to seller", money(d["net_proceeds_to_seller"]))
    with cols[2]:
        st.metric(
            "Value created vs. keeping (group multiple)",
            money(d["value_created_vs_embedded"]),
            delta=f"{d['value_created_per_share']:+.2f} per share",
        )
    with cols[3]:
        st.metric(
            "Value created vs. keeping (DCF hold)",
            money(vs_dcf["value_created_vs_hold"]),
        )

    if d["value_created_vs_embedded"] >= 0:
        st.success(
            f"At {d['sale_multiple']:.2f}x, selling creates {money(d['value_created_vs_embedded'])} "
            f"({price(d['value_created_per_share'])} per share) versus keeping the division "
            "inside the group at its own multiple."
        )
    else:
        st.warning(
            f"At {d['sale_multiple']:.2f}x, selling destroys {money(-d['value_created_vs_embedded'])} "
            "versus keeping the division inside the group at its own multiple."
        )
    st.markdown(
        f"**Break-even sale multiple:** {d['breakeven_vs_embedded']:.2f}x "
        f"(vs. group multiple) · {vs_dcf['breakeven_vs_hold']:.2f}x (vs. DCF hold value). "
        "Below it, keeping wins."
    )

    bridge = pd.DataFrame(
        {
            "Step": [
                "Headline EV",
                "Separation costs",
                "Transaction costs",
                "Tax on the gain",
                "Net proceeds (100%)",
            ],
            "Amount": [
                money(d["enterprise_value"]),
                f"−{money(d['separation'])}",
                f"−{money(d['transaction_costs'])}",
                f"−{money(d['tax'])}",
                money(d["net_proceeds_100pct"]),
            ],
        }
    )
    st.dataframe(bridge, use_container_width=True, hide_index=True)

    if summary.get("divestiture_scenarios"):
        st.subheader("Same multiple, different EBITDA scenarios")
        sc_rows = [
            {
                "Scenario": name,
                "EBITDA": money(sc["enterprise_value"] / d["sale_multiple"]),
                "Sale EV": money(sc["enterprise_value"]),
                "Net proceeds": money(sc["net_proceeds_to_seller"]),
                "Value created": money(sc["value_created_vs_embedded"]),
            }
            for name, sc in summary["divestiture_scenarios"].items()
        ]
        st.dataframe(pd.DataFrame(sc_rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- capital allocation
if "capital_allocation" in summary:
    ca = summary["capital_allocation"]
    st.subheader("Capital allocation after the sale")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Leverage today", f"{ca['leverage_today']:.2f}x net debt / EBITDA")
    with cols[1]:
        st.metric("Debt repayment (leverage-neutral)", money(ca["debt_repayment_leverage_neutral"]))
    with cols[2]:
        st.metric("Capital left", money(ca["capital_available"]))
    with cols[3]:
        st.metric(
            "Shares repurchasable",
            f"{ca['shares_repurchasable_m']:.3f}m",
            delta=f"{ca['shares_repurchasable_pct']:.1%} of shares",
        )
    if ca["buyback_value_created"]:
        st.info(
            f"Buybacks at a price below intrinsic value would create "
            f"{money(ca['buyback_value_created'])} of additional value."
        )

if base.notes:
    st.divider()
    st.subheader("Notes")
    for note in base.notes:
        st.markdown(f"- {note}")
st.caption(
    "Not investment advice. Verify every input against the company's filings before any real use."
)
