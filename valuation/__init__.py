"""Valuation toolkit — generic DCF, multiples, football field and
keep-vs-sell analysis for any listed company.
"""

from .dcf import dcf_exit_multiple_value, dcf_sensitivity, dcf_value, project_free_cash_flow
from .divestiture import (
    breakeven_multiple,
    capital_allocation,
    divestiture_analysis,
    keep_value,
    net_proceeds,
)
from .models import (
    CapitalAllocationInputs,
    Company,
    DCFInputs,
    DivestitureInputs,
    MultipleRange,
    ValuationExample,
)
from .multiples import (
    ev_from_multiple,
    ev_range,
    football_field,
    implied_price_from_multiple,
    range_from_multiples,
)

__all__ = [
    "Company",
    "DCFInputs",
    "DivestitureInputs",
    "CapitalAllocationInputs",
    "MultipleRange",
    "ValuationExample",
    "dcf_value",
    "dcf_exit_multiple_value",
    "dcf_sensitivity",
    "project_free_cash_flow",
    "ev_from_multiple",
    "ev_range",
    "range_from_multiples",
    "implied_price_from_multiple",
    "football_field",
    "net_proceeds",
    "keep_value",
    "breakeven_multiple",
    "divestiture_analysis",
    "capital_allocation",
]
