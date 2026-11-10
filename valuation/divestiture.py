"""Keep vs. sell — divestiture economics and capital allocation.

The question is never "what is the division worth?" on its own. It is
"what do shareholders get from selling, minus what they already own
inside the group, and what does the cash do next?" This module answers
exactly that, in three steps:

1. ``net_proceeds`` — the bridge from headline EV to cash in hand.
2. ``divestiture_analysis`` — value created vs. keeping, per share,
   and the break-even sale multiple (below it, keeping wins).
3. ``capital_allocation`` — leverage-neutral debt repayment first,
   then what the remaining cash can buy back.
"""

from __future__ import annotations

from .models import CapitalAllocationInputs, DivestitureInputs


def net_proceeds(ev_m: float, inputs: DivestitureInputs) -> dict:
    """Bridge: headline EV -> cash to the seller.

    Sale is cash-free / debt-free: the division carries no separate
    debt, so EV is the gross price. Costs are percentages of EV;
    tax applies only to the gain above the tax basis.
    """
    separation = ev_m * inputs.separation_pct_of_ev
    transaction = ev_m * inputs.transaction_pct_of_ev
    taxable_gain = max(0.0, ev_m - inputs.tax_basis_m)
    tax = taxable_gain * inputs.tax_rate_on_gain
    net_100 = ev_m - separation - transaction - tax
    return {
        "enterprise_value": ev_m,
        "separation": separation,
        "transaction_costs": transaction,
        "taxable_gain": taxable_gain,
        "tax": tax,
        "net_proceeds_100pct": net_100,
        "net_proceeds_to_seller": net_100 * inputs.ownership_pct,
    }


def keep_value(inputs: DivestitureInputs) -> float:
    """What the division is worth inside the group today, to the seller:
    EBITDA x the multiple the market already gives it, x ownership."""
    return inputs.ebitda_m * inputs.embedded_multiple * inputs.ownership_pct


def _net_to_seller_at_ev(ev_m: float, inputs: DivestitureInputs) -> float:
    return net_proceeds(ev_m, inputs)["net_proceeds_to_seller"]


def breakeven_multiple(
    inputs: DivestitureInputs, hold_value_m: float, tol: float = 1e-9
) -> float:
    """Lowest EV/EBITDA at which selling beats keeping (``hold_value_m``).

    Solved numerically (bisection) because tax on the gain makes the
    bridge non-linear once EV passes the tax basis.
    """
    lo, hi = 0.0, 100.0  # multiples; 100x is far beyond any sane answer
    if _net_to_seller_at_ev(hi * inputs.ebitda_m, inputs) < hold_value_m:
        raise ValueError("Even at 100x, selling does not beat keeping.")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if _net_to_seller_at_ev(mid * inputs.ebitda_m, inputs) < hold_value_m:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def divestiture_analysis(
    inputs: DivestitureInputs, sale_multiple: float, hold_value_m: float | None = None
) -> dict:
    """Full keep-vs-sell picture at one sale multiple.

    ``hold_value_m`` defaults to the DCF-free version — the value
    implied by the group's own trading multiple — and can be replaced
    by a DCF hold value to test the answer against a different yardstick.
    """
    ev = inputs.ebitda_m * sale_multiple
    bridge = net_proceeds(ev, inputs)
    embedded = keep_value(inputs)
    hold = embedded if hold_value_m is None else hold_value_m
    created = bridge["net_proceeds_to_seller"] - embedded
    return {
        **bridge,
        "sale_multiple": sale_multiple,
        "embedded_value": embedded,
        "hold_value_used": hold,
        "value_created_vs_embedded": created,
        "value_created_vs_hold": bridge["net_proceeds_to_seller"] - hold,
        "value_created_per_share": (
            created / inputs.shares_outstanding_m if inputs.shares_outstanding_m else 0.0
        ),
        "breakeven_vs_embedded": breakeven_multiple(inputs, embedded),
        "breakeven_vs_hold": breakeven_multiple(inputs, hold),
    }


def capital_allocation(inputs: CapitalAllocationInputs) -> dict:
    """After the sale: repay debt to keep leverage flat, then deploy
    the rest. Buybacks only create value if the price is below
    intrinsic value — hence the ``intrinsic_value_per_share`` input,
    which must be an honest estimate, not a hope.
    """
    leverage_today = inputs.net_debt_m / inputs.group_ebitda_ltm_m
    pro_forma_ebitda = inputs.group_ebitda_ltm_m - inputs.divested_ebitda_m
    debt_to_repay = max(
        0.0, inputs.net_debt_m - leverage_today * pro_forma_ebitda
    )
    capital_available = inputs.net_proceeds_m - debt_to_repay
    shares_repurchasable = (
        capital_available / inputs.share_price if inputs.share_price else 0.0
    )
    buyback_value_created = 0.0
    if inputs.intrinsic_value_per_share > inputs.share_price:
        buyback_value_created = shares_repurchasable * (
            inputs.intrinsic_value_per_share - inputs.share_price
        )
    return {
        "leverage_today": leverage_today,
        "pro_forma_ebitda": pro_forma_ebitda,
        "pro_forma_leverage_before_repayment": (
            inputs.net_debt_m / pro_forma_ebitda if pro_forma_ebitda else float("inf")
        ),
        "debt_repayment_leverage_neutral": debt_to_repay,
        "capital_available": capital_available,
        "shares_repurchasable_m": shares_repurchasable,
        "shares_repurchasable_pct": (
            shares_repurchasable / inputs.shares_outstanding_m
            if inputs.shares_outstanding_m
            else 0.0
        ),
        "buyback_value_created": buyback_value_created,
    }
