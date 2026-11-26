# Calculator checks

Sixteen checks that pin the arithmetic of the paid products. Each expected value
was calculated by hand first and only then written into a test, so a failure
means either the code changed or the maths did — both worth stopping for.

## Why this lives here but the products do not

This repository is public and serves the marketing page. The products
themselves are the paid goods, so they are deliberately **not** in this repo and
`products/` is gitignored.

Point the runner at wherever the sources live:

```bash
OSKAR_PRODUCTS_DIR=/path/to/products python3 tests/run_checks.py
```

Default when the variable is unset is the MyClaw session directory on the build
machine, which is useless to anyone else — set the variable.

## Requirements

Only Playwright plus a Chromium build. No pytest, no other packages.

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Running

```bash
python3 tests/run_checks.py          # quiet pass/fail
VERBOSE=1 python3 tests/run_checks.py  # tracebacks on failure
```

Exit code is 0 when every check passes, 1 otherwise, so it works as a pre-push
gate.

## What is covered

| Check | The number that matters |
|---|---|
| Late payment interest | 2500 @ 12% for 58 days = 47.67 + 70 compensation |
| Late payment bands | 40 / 70 / 100 compensation tiers |
| Late payment not due | future due date charges nothing |
| Scope Guard totals | 900 subtotal, 1125 with 25% rush |
| Quote Desk | 4650 total, 1860 deposit, 2790 balance |
| Tax Pot | 44,000 profit → 8,171.80 total, 680.98/month |
| Tax Pot floor | under personal allowance owes nothing |
| Tax Pot allowance | 1,000 trading allowance beats 400 of expenses |
| Rate Ladder | 46,000 / 1,000h = 46/hour |
| Rate Ladder warning | market below floor must say so |
| Project Ledger | 7,700 outstanding, 4,400 overdue |
| Kickoff Kit | all three documents render |
| All products | no remote scripts, no network calls |

That last one is a product promise, not a nicety: every listing tells the buyer
that nothing leaves their browser. A stray analytics tag would make that a lie.
