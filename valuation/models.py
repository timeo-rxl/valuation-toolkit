"""Data structures for the valuation toolkit.

Everything is plain dataclasses with explicit units, so an example file
(YAML) maps 1-to-1 onto these objects. Money is in millions of the
company's currency unless a field says otherwise; multiples are in "x".
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Company:
    """A listed company, described by the handful of numbers a
    multiple-based valuation actually needs."""

    name: str
    ticker: str
    currency: str = "C$"
    share_price: float = 0.0          # current price, per share
    shares_outstanding_m: float = 0.0  # millions of shares
    net_debt_m: float = 0.0            # debt minus cash
    non_controlling_interests_m: float = 0.0
    ltm_ebitda_m: float = 0.0          # last-twelve-months adjusted EBITDA
    ltm_sales_m: float = 0.0

    @property
    def market_cap_m(self) -> float:
        return self.share_price * self.shares_outstanding_m

    @property
    def enterprise_value_m(self) -> float:
        """EV = market cap + net debt + non-controlling interests."""
        return self.market_cap_m + self.net_debt_m + self.non_controlling_interests_m

    @property
    def ev_to_ebitda(self) -> float:
        if self.ltm_ebitda_m == 0:
            raise ValueError("LTM EBITDA is zero, EV/EBITDA is undefined.")
        return self.enterprise_value_m / self.ltm_ebitda_m

    def implied_price(self, enterprise_value_m: float) -> float:
        """Share price implied by an enterprise value."""
        equity_value = (
            enterprise_value_m - self.net_debt_m - self.non_controlling_interests_m
        )
        return equity_value / self.shares_outstanding_m


@dataclass
class DCFInputs:
    """Assumptions for a 5-year unlevered DCF of one business.

    Year 0 is the base year (last reported year). Free cash flow is
    projected for years 1..``years``; the EBITDA margin is held at the
    base-year margin, which is the honest default when you have no
    better forecast — change it explicitly if you do.
    """

    base_year_sales_m: float
    base_year_ebitda_m: float
    sales_growth: float = 0.03
    da_pct_of_sales: float = 0.025       # depreciation & amortisation
    capex_pct_of_sales: float = 0.025
    nwc_pct_of_incremental_sales: float = 0.15
    tax_rate: float = 0.25
    wacc: float = 0.09
    terminal_growth: float = 0.02
    years: int = 5

    @property
    def base_ebitda_margin(self) -> float:
        return self.base_year_ebitda_m / self.base_year_sales_m


@dataclass
class MultipleRange:
    """A low-high EV/EBITDA (or EV/Sales) range from one method."""

    label: str
    low: float
    high: float
    comment: str = ""

    @property
    def midpoint(self) -> float:
        return (self.low + self.high) / 2


@dataclass
class DivestitureInputs:
    """Assumptions for a keep-vs-sell analysis of one division."""

    division_name: str
    ebitda_m: float                      # the year the sale multiple applies to
    ownership_pct: float = 1.0           # seller's share of the division
    separation_pct_of_ev: float = 0.01   # carve-out / separation costs
    transaction_pct_of_ev: float = 0.02  # advisory + legal fees
    tax_rate_on_gain: float = 0.25
    tax_basis_m: float = 0.0             # seller's tax basis in the division
    embedded_multiple: float = 0.0       # multiple the market already gives
    # the division inside the group (usually the group's own EV/EBITDA)
    shares_outstanding_m: float = 0.0
    share_price: float = 0.0


@dataclass
class CapitalAllocationInputs:
    """What happens to the cash once a division is sold."""

    net_proceeds_m: float                # cash to the seller, after all costs
    net_debt_m: float
    group_ebitda_ltm_m: float
    divested_ebitda_m: float             # EBITDA leaving the group
    share_price: float
    intrinsic_value_per_share: float = 0.0  # 0 = unknown, buyback value skipped
    shares_outstanding_m: float = 0.0


@dataclass
class ValuationExample:
    """One worked example: a company + a division + the assumptions."""

    company: Company
    dcf: DCFInputs
    division: DivestitureInputs | None = None
    division_ebitda_scenarios: dict[str, float] = field(default_factory=dict)
    trading_multiples: list[float] = field(default_factory=list)
    precedent_multiples: list[float] = field(default_factory=list)
    selected_multiple_range: MultipleRange | None = None
    capital_allocation: CapitalAllocationInputs | None = None
    notes: list[str] = field(default_factory=list)
