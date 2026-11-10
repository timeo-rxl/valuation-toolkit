"""Trading comps, precedent transactions and the football field.

The same three lines of maths, reused for every method: a multiple
times a profit figure is an enterprise value; subtract net debt (and
minorities) and divide by shares to get a price. The football field
just lines the methods up side by side so the overlap — or the lack
of it — is visible at a glance.
"""

from __future__ import annotations

from statistics import median

from .models import Company, MultipleRange


def ev_from_multiple(profit_m: float, multiple: float) -> float:
    """Enterprise value = profit x multiple. That is the whole method."""
    return profit_m * multiple


def ev_range(profit_m: float, low: float, high: float) -> tuple[float, float]:
    return (profit_m * low, profit_m * high)


def range_from_multiples(multiples: list[float]) -> tuple[float, float, float]:
    """(low, median, high) of a set of peer multiples."""
    if not multiples:
        raise ValueError("Need at least one multiple.")
    return (min(multiples), median(multiples), max(multiples))


def implied_price_from_multiple(company: Company, multiple: float) -> float:
    """Share price if the whole group traded at ``multiple`` x LTM EBITDA."""
    return company.implied_price(ev_from_multiple(company.ltm_ebitda_m, multiple))


def football_field(
    ebitda_m: float, methods: list[MultipleRange]
) -> list[dict]:
    """One row per method: low/high multiple -> low/high enterprise value."""
    rows = []
    for m in methods:
        low_ev, high_ev = ev_range(ebitda_m, m.low, m.high)
        rows.append(
            {
                "method": m.label,
                "low_multiple": m.low,
                "high_multiple": m.high,
                "ev_low": low_ev,
                "ev_high": high_ev,
                "ev_mid": (low_ev + high_ev) / 2,
                "comment": m.comment,
            }
        )
    return rows
