"""Discounted cash flow (DCF) — the generic engine.

One idea, done properly: project unlevered free cash flow for a few
years, discount it at the WACC, add a terminal value. Two terminal
value methods are supported (Gordon growth, exit multiple) so the
answer can be cross-checked instead of trusted blindly.
"""

from __future__ import annotations

from .models import DCFInputs


def project_free_cash_flow(inputs: DCFInputs) -> list[dict]:
    """Year-by-year forecast. Year 0 is the base year (no cash flow).

    Returns one dict per forecast year (1..``years``) with sales,
    EBITDA, EBIT, NOPAT and unlevered free cash flow.
    """
    margin = inputs.base_ebitda_margin
    rows: list[dict] = []
    sales = inputs.base_year_sales_m
    for year in range(1, inputs.years + 1):
        prev_sales = sales
        sales = prev_sales * (1 + inputs.sales_growth)
        ebitda = sales * margin
        da = sales * inputs.da_pct_of_sales
        ebit = ebitda - da
        tax = ebit * inputs.tax_rate
        nopat = ebit - tax
        capex = sales * inputs.capex_pct_of_sales
        nwc_change = (sales - prev_sales) * inputs.nwc_pct_of_incremental_sales
        fcf = nopat + da - capex - nwc_change
        rows.append(
            {
                "year": year,
                "sales": sales,
                "ebitda": ebitda,
                "ebitda_margin": margin,
                "da": da,
                "ebit": ebit,
                "tax": tax,
                "nopat": nopat,
                "capex": capex,
                "nwc_change": nwc_change,
                "fcf": fcf,
            }
        )
    return rows


def dcf_value(
    inputs: DCFInputs,
    wacc: float | None = None,
    terminal_growth: float | None = None,
) -> dict:
    """Enterprise value by DCF with a Gordon-growth terminal value.

    ``wacc`` / ``terminal_growth`` override the inputs so sensitivity
    tables can reuse this one function.
    """
    wacc = inputs.wacc if wacc is None else wacc
    g = inputs.terminal_growth if terminal_growth is None else terminal_growth
    if wacc <= g:
        raise ValueError("WACC must be above terminal growth (else value is infinite).")
    rows = project_free_cash_flow(inputs)
    pv_fcf = sum(r["fcf"] / (1 + wacc) ** r["year"] for r in rows)
    last_fcf = rows[-1]["fcf"]
    terminal_value = last_fcf * (1 + g) / (wacc - g)
    pv_terminal = terminal_value / (1 + wacc) ** inputs.years
    return {
        "enterprise_value": pv_fcf + pv_terminal,
        "pv_fcf": pv_fcf,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal,
        "wacc": wacc,
        "terminal_growth": g,
        "years": rows,
    }


def dcf_exit_multiple_value(
    inputs: DCFInputs, exit_multiple: float, wacc: float | None = None
) -> dict:
    """Same DCF, but the terminal value is ``exit_multiple`` x final
    year EBITDA instead of Gordon growth. A useful second opinion."""
    wacc = inputs.wacc if wacc is None else wacc
    rows = project_free_cash_flow(inputs)
    pv_fcf = sum(r["fcf"] / (1 + wacc) ** r["year"] for r in rows)
    terminal_value = rows[-1]["ebitda"] * exit_multiple
    pv_terminal = terminal_value / (1 + wacc) ** inputs.years
    return {
        "enterprise_value": pv_fcf + pv_terminal,
        "pv_fcf": pv_fcf,
        "terminal_value": terminal_value,
        "pv_terminal_value": pv_terminal,
        "exit_multiple": exit_multiple,
        "wacc": wacc,
        "years": rows,
    }


def dcf_sensitivity(
    inputs: DCFInputs, waccs: list[float], growths: list[float]
) -> dict[tuple[float, float], float]:
    """Enterprise value for every (WACC, terminal growth) pair.

    WACC up -> value down; growth up -> value up. If a cell breaks
    that pattern, the inputs are wrong, not the table.
    """
    return {
        (w, g): dcf_value(inputs, wacc=w, terminal_growth=g)["enterprise_value"]
        for w in waccs
        for g in growths
    }
