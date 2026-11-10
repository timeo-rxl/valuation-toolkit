# valuation-toolkit

**Value any listed company — DCF, trading comps, precedent transactions,
football field, and keep-vs-sell analysis — from one YAML file.**

No spreadsheets, no copy-paste errors: every method reads the same
inputs, and every number is reproducible with `python demo.py`.
15 tests, all passing.

## En français, en 30 secondes

On décrit une entreprise dans un petit fichier (`examples/*.yaml`) :
son cours, ses actions, sa dette, son EBITDA. L'outil calcule :

1. **Combien vaut le groupe** aujourd'hui (EV, EV/EBITDA) et quel cours
   il aurait s'il se vendait au multiple de ses concurrents.
2. **Un DCF** : il projette les flux de trésorerie sur 5 ans, les
   actualise, et donne la valeur d'entreprise — avec un tableau de
   sensibilité (si le WACC monte, la valeur baisse, et inversement).
3. **Un football field** : DCF, comparables boursiers et transactions
   passées, côte à côte, pour voir où les méthodes se recoupent.
4. **Vendre ou garder une division** : produits nets de la vente,
   valeur créée pour l'actionnaire, et le multiple minimum qui rend
   la vente meilleure que garder — puis ce que le cash permet de
   faire (rembourser la dette, racheter des actions).

## What it does

| Module | Question it answers |
| --- | --- |
| `valuation/dcf.py` | What is this business worth on its future cash flows? (Gordon growth + exit-multiple cross-check, sensitivity grid) |
| `valuation/multiples.py` | What is it worth at peer multiples? What share price does each multiple imply? |
| `valuation/divestiture.py` | Sell or keep a division? Net proceeds, value created per share, break-even sale multiple, leverage-neutral capital allocation |
| `valuation/report.py` | All methods, one summary, one readable report |
| `demo.py` | CLI — run any example YAML |

## Try it

```bash
pip install -r requirements.txt

python demo.py                         # Lassonde example
python demo.py examples/acme.yaml      # fictional example

python -m unittest discover -s tests -v   # 15 tests
```

## Worked example — Lassonde Industries Inc. (TSX: LAS.A)

`examples/lassonde.yaml` values the Summer Garden division. Group
figures are from Lassonde's public filings (annual MD&A 2025, Q3 2026);
the division scenarios are labelled case-study estimates, not guidance.

**The group today:** C$233.46/share, EV C$2,129m, EV / LTM EBITDA **5.82x**.
At a peer multiple the implied price would be C$373.55 (Conagra, 8.4x)
to C$416.91 (Campbell's, 9.2x).

**Football field — Summer Garden enterprise value (base 2027E EBITDA C$33.9m):**

| Method | EV |
| --- | --- |
| Value inside the group today (5.82x) | C$197m |
| Trading comparables (8.4x–9.2x) | C$285m–C$312m |
| Precedent transactions (7.8x–9.6x) | C$264m–C$325m |
| DCF (WACC 8–12%, growth 1.5–2.5%) | C$212m–C$394m |
| Selected range (8.5x–10.0x) | **C$288m–C$339m** |

**Keep vs. sell at the 9.25x midpoint:** EV C$313.6m → net proceeds to
Lassonde C$273.8m → value created **C$96.2m (C$14.24/share)** vs. what
the market already pays for the division inside the group. The sale
only beats keeping on a DCF yardstick above **9.58x** (at the 9% WACC,
keeping is worth C$9.3m more). After the sale: repay C$48.6m of debt
to keep leverage flat at 1.25x, leaving C$225.2m — buybacks below
intrinsic value would create a further C$44.6m.

## Value your own company

Copy an example and replace the numbers — no code changes needed:

```bash
cp examples/acme.yaml examples/your-company.yaml
python demo.py examples/your-company.yaml
```

The YAML is the whole model: company, DCF assumptions, division,
scenarios, peer multiples, selected range. Sources go in `notes:` —
a number without a source is a guess, and this toolkit treats it as one.

## Project structure

```
valuation-toolkit/
├── valuation/
│   ├── models.py       # Company, DCFInputs, DivestitureInputs — plain dataclasses
│   ├── dcf.py          # FCF projection, DCF, exit-multiple check, sensitivity
│   ├── multiples.py    # comps, precedents, football field
│   ├── divestiture.py  # net-proceeds bridge, keep-vs-sell, capital allocation
│   └── report.py       # one summary + text report
├── examples/
│   ├── lassonde.yaml   # Lassonde / Summer Garden (public filings + labelled estimates)
│   └── acme.yaml       # fictional company, round numbers
├── demo.py             # CLI
└── tests/
    └── test_valuation.py   # 15 tests, anchored to the Lassonde example
```

## Honesty notes

- This is a **teaching toolkit**, not research and not investment advice.
  Verify every input against the filings before any real use.
- The Lassonde example was inspired by a team case study (MIBS 2026,
  GMMR Investment Group). The code is original; no team files are
  included, and the division scenarios are estimates, clearly labelled.
- The DCF holds the base-year EBITDA margin flat for 5 years. That is
  the honest default without a forecast — if you have a better one,
  change the assumptions explicitly instead of trusting the default.
- A multiple is not a valuation: the football field exists so that no
  single method gets the last word.
