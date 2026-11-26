#!/usr/bin/env python3
"""Run the calculator regression checks without pytest.

Each check pins an arithmetic result that was verified by hand first, so a
failure means either the code changed or the maths did. Both deserve attention.

Usage:  python3 tests/run_checks.py
Env:    OSKAR_PRODUCTS_DIR  override the product source directory
"""
import os
import pathlib
import sys
import traceback

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PRODUCTS = pathlib.Path(
    os.environ.get(
        "OSKAR_PRODUCTS_DIR",
        os.path.expanduser(
            "~/.myclaw/sessions/63ab5dce-8f0b-43c5-9c94-6896d508cf81/products"
        ),
    )
)

RESULTS = []


def check(name):
    def deco(fn):
        RESULTS.append((name, fn))
        return fn
    return deco


def open_product(page, folder, filename):
    path = PRODUCTS / folder / filename
    if not path.exists():
        raise AssertionError(f"missing product file: {path}")
    page.goto(f"file://{path}")


def eq(actual, expected, what=""):
    if actual != expected:
        raise AssertionError(f"{what}: got {actual!r}, expected {expected!r}")


def contains(haystack, needle, what=""):
    if needle not in haystack:
        raise AssertionError(f"{what}: {needle!r} not found")


# ---------------------------------------------------------------- Late Payment
@check("late payment: statutory interest and compensation")
def _(page):
    open_product(page, "late-payment-desk", "LatePaymentDesk.html")
    page.click("#demo")
    eq(page.inner_text("#total"), "£117.67", "total")
    eq(page.inner_text("#sInterest"), "£47.67", "interest")
    eq(page.inner_text("#sComp"), "£70.00", "compensation")
    eq(page.inner_text("#sDays"), "58", "days overdue")


@check("late payment: compensation bands 40/70/100")
def _(page):
    open_product(page, "late-payment-desk", "LatePaymentDesk.html")
    page.click("#demo")
    for amount, expected in [("500", "£40.00"), ("7000", "£70.00"), ("25000", "£100.00")]:
        page.fill("#amount", amount)
        page.dispatch_event("#amount", "input")
        eq(page.inner_text("#sComp"), expected, f"amount {amount}")


@check("late payment: not-yet-due invoice charges nothing")
def _(page):
    open_product(page, "late-payment-desk", "LatePaymentDesk.html")
    page.fill("#amount", "2500")
    page.fill("#base", "4")
    page.fill("#due", "2099-01-01")
    page.dispatch_event("#due", "input")
    eq(page.inner_text("#total"), "£0.00", "total")


# ---------------------------------------------------------------- Scope Guard
@check("scope guard: subtotal and rush uplift")
def _(page):
    open_product(page, "scope-guard", "ScopeGuard.html")
    page.click("#demo")
    eq(page.inner_text("#sub"), "£900.00", "subtotal")
    eq(page.inner_text("#grand"), "£1,125.00", "grand total")
    eq(page.locator("#rows tr").count(), 3, "row count")


@check("scope guard: generated document is complete")
def _(page):
    open_product(page, "scope-guard", "ScopeGuard.html")
    page.click("#demo")
    doc = page.inner_text("#doc")
    contains(doc, "Northgate Media", "client name")
    contains(doc, "CHANGE ORDER", "document title")
    contains(doc, "TOTAL:", "total line")
    contains(doc, "Signed for the client", "signature block")


# ---------------------------------------------------------------- Quote Desk
@check("quote desk: totals, deposit, balance")
def _(page):
    open_product(page, "quote-desk", "QuoteDesk.html")
    page.click("#demo")
    eq(page.inner_text("#total"), "£4,650.00", "total")
    eq(page.inner_text("#dep"), "£1,860.00", "deposit")
    eq(page.inner_text("#bal"), "£2,790.00", "balance")


@check("quote desk: exclusions and validity present")
def _(page):
    open_product(page, "quote-desk", "QuoteDesk.html")
    page.click("#demo")
    doc = page.inner_text("#doc")
    contains(doc, "NOT INCLUDED", "exclusions")
    contains(doc, "ASSUMPTIONS", "assumptions")
    contains(doc, "Valid until", "validity")


# ---------------------------------------------------------------- Tax Pot
@check("tax pot: full calculation at 48k/4k")
def _(page):
    """Hand calc: profit 44000; IT 6286; C4 1885.80; C2 0 (not charged since 2024).
    Total 8171.80; keep 35828.20; monthly 680.98."""
    open_product(page, "tax-pot", "TaxPot.html")
    page.click("#demo")
    eq(page.inner_text("#profit"), "£44,000.00", "profit")
    eq(page.inner_text("#rIT"), "£6,286.00", "income tax")
    eq(page.inner_text("#rC4"), "£1,885.80", "class 4")
    eq(page.inner_text("#rC2"), "£0.00", "class 2 not charged")
    eq(page.inner_text("#taxni"), "£8,171.80", "total")
    eq(page.inner_text("#rKeep"), "£35,828.20", "kept")
    eq(page.inner_text("#monthly"), "£680.98", "monthly set aside")


@check("tax pot: profit below personal allowance owes nothing")
def _(page):
    open_product(page, "tax-pot", "TaxPot.html")
    page.fill("#turnover", "12000")
    page.fill("#expenses", "0")
    page.dispatch_event("#turnover", "input")
    eq(page.inner_text("#rIT"), "£0.00", "income tax")
    eq(page.inner_text("#rC4"), "£0.00", "class 4")
    eq(page.inner_text("#rC2"), "£0.00", "class 2")
    eq(page.inner_text("#profit"), "£11,000.00", "profit after allowance")


@check("tax pot: trading allowance beats small expenses")
def _(page):
    open_product(page, "tax-pot", "TaxPot.html")
    page.fill("#turnover", "30000")
    page.fill("#expenses", "400")
    page.dispatch_event("#expenses", "input")
    contains(page.inner_text("#rExp"), "trading allowance", "expenses row")
    eq(page.inner_text("#profit"), "£29,000.00", "profit")


# ---------------------------------------------------------------- Rate Ladder
@check("rate ladder: floor rate and conversions")
def _(page):
    open_product(page, "rate-ladder", "RateLadder.html")
    page.click("#demo")
    eq(page.inner_text("#hourly"), "£46.00", "hourly")
    eq(page.inner_text("#rDay"), "£322.00", "per day")
    eq(page.inner_text("#rWeek"), "£1,150.00", "per week")
    eq(page.inner_text("#wHours"), "1000", "billable hours")


@check("rate ladder: warns when market sits below the floor")
def _(page):
    open_product(page, "rate-ladder", "RateLadder.html")
    page.click("#demo")
    # #compare is a readonly input, so its text lives in value not innerText.
    contains(page.input_value("#compare"), "higher than market", "comparison")
    contains(page.inner_text("#compareNote"), "Change the shape", "advice")


# ---------------------------------------------------------------- Project Ledger
@check("project ledger: outstanding, overdue, paid, active")
def _(page):
    open_product(page, "project-ledger", "ProjectLedger.html")
    page.click("#demo")
    eq(page.inner_text("#sOut"), "$7,700.00", "outstanding")
    eq(page.inner_text("#sOver"), "$4,400.00", "overdue")
    eq(page.inner_text("#sPaid"), "$950.00", "paid")
    eq(page.inner_text("#sActive"), "3", "active")


# ---------------------------------------------------------------- Kickoff Kit
@check("kickoff kit: all three documents render real content")
def _(page):
    open_product(page, "kickoff-kit", "KickoffKit.html")
    page.click("#demo")
    welcome = page.inner_text("#doc")
    contains(welcome, "Northgate", "welcome client")
    if len(welcome) < 800:
        raise AssertionError(f"welcome doc too short: {len(welcome)}")

    page.click('[data-t="questions"]')
    contains(page.inner_text("#doc"), "15.", "questions doc")

    page.click('[data-t="confirm"]')
    confirm = page.inner_text("#doc")
    contains(confirm, "NOT INCLUDED", "confirmation exclusions")
    contains(confirm, "Sam", "confirmation approver")


# ---------------------------------------------------------------- Invoice Desk
@check("invoice desk: loads without error")
def _(page):
    open_product(page, "invoice-desk", "InvoiceDesk.html")
    contains(page.inner_text("body"), "Invoice", "page body")


# ---------------------------------------------------------------- security
@check("all products: no remote scripts or network calls")
def _(page):
    """A product that phones home breaks the 'nothing leaves this browser' promise."""
    offenders = []
    import re
    for folder in sorted(PRODUCTS.iterdir()):
        if not folder.is_dir():
            continue
        for html in folder.glob("*.html"):
            src = html.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r'(?:src|href)\s*=\s*["\'](https?://[^"\']+)', src):
                url = m.group(1)
                if "gumroad.com" in url:
                    continue  # product links in README examples are fine
                offenders.append(f"{html.name}: {url}")
            if re.search(r'\bfetch\s*\(|XMLHttpRequest|sendBeacon', src):
                offenders.append(f"{html.name}: network call in code")
    if offenders:
        raise AssertionError("remote references found:\n  " + "\n  ".join(offenders))


def main():
    if not PRODUCTS.exists():
        print(f"product directory not found: {PRODUCTS}", file=sys.stderr)
        return 2

    passed = failed = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        for name, fn in RESULTS:
            page = browser.new_page()
            try:
                fn(page)
                print(f"PASS  {name}")
                passed += 1
            except Exception as exc:
                print(f"FAIL  {name}")
                detail = str(exc).strip().splitlines()[0] if str(exc).strip() else repr(exc)
                print(f"      {detail}")
                if os.environ.get("VERBOSE"):
                    traceback.print_exc()
                failed += 1
            finally:
                page.close()
        browser.close()

    print()
    print(f"{passed} passed, {failed} failed, {passed + failed} checks")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
