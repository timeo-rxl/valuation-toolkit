"""Demo: run the whole toolkit on one example file.

Usage:
    python demo.py                        # Lassonde example
    python demo.py examples/acme.yaml     # fictional example
    python demo.py examples/your-company.yaml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from valuation import (  # noqa: E402
    CapitalAllocationInputs,
    Company,
    DCFInputs,
    DivestitureInputs,
    MultipleRange,
    ValuationExample,
    divestiture_analysis,
)
from valuation.report import render_text, summarise  # noqa: E402


def load_example(path: str | Path) -> ValuationExample:
    data = yaml.safe_load(Path(path).read_text())
    company = Company(**data["company"])
    dcf = DCFInputs(**data["dcf"])
    division = (
        DivestitureInputs(**data["division"]) if data.get("division") else None
    )
    selected = None
    if data.get("selected_multiple_range"):
        selected = MultipleRange(**data["selected_multiple_range"])
    example = ValuationExample(
        company=company,
        dcf=dcf,
        division=division,
        division_ebitda_scenarios=data.get("division_ebitda_scenarios", {}),
        trading_multiples=data.get("trading_multiples", []),
        precedent_multiples=data.get("precedent_multiples", []),
        selected_multiple_range=selected,
        notes=data.get("notes", []),
    )
    # Capital allocation needs the sale's net proceeds, which only exist
    # once the divestiture is priced — compute it, don't type it.
    ca = data.get("capital_allocation")
    if ca and division and selected:
        net = divestiture_analysis(division, selected.midpoint)[
            "net_proceeds_to_seller"
        ]
        example.capital_allocation = CapitalAllocationInputs(
            net_proceeds_m=net, **ca
        )
    return example


def main() -> None:
    parser = argparse.ArgumentParser(description="Valuation toolkit demo")
    parser.add_argument(
        "example", nargs="?", default="examples/lassonde.yaml",
        help="YAML example file (default: examples/lassonde.yaml)",
    )
    args = parser.parse_args()
    example = load_example(args.example)
    print(render_text(summarise(example), example))


if __name__ == "__main__":
    main()
