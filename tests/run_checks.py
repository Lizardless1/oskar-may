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


# ---------------------------------------------------------------- Expense Pot
@check("expense pot: allowable total excludes non-allowable")
def _(page):
    """Hand calc: 51.98 + (32.00@70%=22.40) + 24.60 + 189.00 + 84.10 + 140.00 = 512.08.
    Client lunch 96.50 and own coffee 4.20 are not allowable -> 100.70 excluded."""
    open_product(page, "expense-pot", "ExpensePot.html")
    page.click("#demo")
    eq(page.inner_text("#sTotal"), "£512.08", "allowable total")
    eq(page.inner_text("#sBad"), "£100.70", "not allowable")
    eq(page.inner_text("#sCount"), "8", "entries")


@check("expense pot: business percentage applies per row")
def _(page):
    """70% of 100 is 70, not 100."""
    open_product(page, "expense-pot", "ExpensePot.html")
    page.click("#demo")
    page.locator("#rows tr").first.locator(".f-amt").fill("100")
    page.locator("#rows tr").first.locator(".f-pct").fill("70")
    page.dispatch_event("#rows tr:nth-child(1) .f-pct", "input")
    # first row drops from 51.98 to 70.00, so total moves by +18.02
    eq(page.inner_text("#sTotal"), "£530.10", "total after partial claim")


@check("expense pot: largest category reported")
def _(page):
    open_product(page, "expense-pot", "ExpensePot.html")
    page.click("#demo")
    contains(page.inner_text("#sTop"), "Equipment", "top category")
    contains(page.inner_text("#sTopSub"), "189.00", "top category amount")


# ---------------------------------------------------------------- Time Log
@check("time log: hours, value and effective rate")
def _(page):
    """Hand calc: 3 + 5.5 + 2 + 6 + 1.5 = 18.00h; billable 1237.50; effective 68.75."""
    open_product(page, "time-log", "TimeLog.html")
    page.click("#demo")
    eq(page.inner_text("#tHours"), "18.00", "hours")
    eq(page.inner_text("#tValue"), "£1,237.50", "billable")
    eq(page.inner_text("#tEff"), "£68.75", "effective rate")


@check("time log: repeated task merges into one invoice line")
def _(page):
    """5.5h + 2h of the same task must appear once, at 7.50h."""
    open_product(page, "time-log", "TimeLog.html")
    page.click("#demo")
    doc = page.inner_text("#doc")
    if doc.count("Sitemap and wireframes") != 1:
        raise AssertionError(f"task not merged, found {doc.count('Sitemap and wireframes')} lines")
    contains(doc, "7.50", "merged hours")
    contains(doc, "562.50", "merged amount")


@check("time log: unbilled time still counts toward effective rate")
def _(page):
    open_product(page, "time-log", "TimeLog.html")
    page.click("#demo")
    contains(page.inner_text("#doc"), "Client call (unbilled)", "unbilled row")
    # 1237.50 over 18h, not over the 16.5 billed hours
    eq(page.inner_text("#tEff"), "£68.75", "effective rate includes unbilled")


# ---------------------------------------------------------------- Cashflow
@check("cashflow: month 2 near-miss with a 45 day payment delay")
def _(page):
    """Cash 4200, income 4500, costs 600, draw 2200, delay 45, tax 8000 in month 10.

    Month 1: nothing paid yet -> 4200 - 2800 = 1400.
    Month 2: half of month 1's work lands -> 1400 + 2250 - 2800 = 850.
    Lowest point is 850 in month 2, NOT the tax month.
    """
    open_product(page, "cashflow", "Cashflow.html")
    page.click("#demo")
    rows = page.locator("#rows tr")
    eq(rows.count(), 12, "months projected")
    eq(page.inner_text("#lowest"), "£850.00", "lowest balance")
    # First month already sits at 1400 against 2800 of outgoings, so the first
    # month under one month's cover is month 1 itself, not the 850 low in month 2.
    contains(page.inner_text("#sTight"), "Nov", "first tight month")


@check("cashflow: tax lands in the named month only")
def _(page):
    """Month 10 carries the 8000 hit; no other month has a tax figure."""
    open_product(page, "cashflow", "Cashflow.html")
    page.click("#demo")
    tax_cells = page.evaluate(
        """() => [...document.querySelectorAll('#rows tr')]
                 .map(tr => tr.children[5].innerText.trim())
                 .filter(t => t !== '\u2014')"""
    )
    eq(len(tax_cells), 1, "months carrying tax")
    eq(tax_cells[0], "£8,000.00", "tax amount")


@check("cashflow: zero delay pays immediately")
def _(page):
    """With no delay, month 1 should receive a full month's income."""
    open_product(page, "cashflow", "Cashflow.html")
    page.fill("#cash", "0")
    page.fill("#income", "3000")
    page.fill("#costs", "0")
    page.fill("#personal", "0")
    page.fill("#tax", "0")
    page.fill("#delay", "0")
    page.dispatch_event("#delay", "input")
    first_income = page.evaluate(
        "() => document.querySelectorAll('#rows tr')[0].children[2].innerText.trim()"
    )
    eq(first_income, "£3,000.00", "month 1 income with no delay")


# ---------------------------------------------------------------- Pipeline
@check("pipeline: reply rate, chase and stale counts")
def _(page):
    """Seven contacts: 2 replied (29%), 1 due a chase at 6d, 1 stale at 34d, 1 won."""
    open_product(page, "pipeline", "Pipeline.html")
    page.click("#demo")
    eq(page.inner_text("#sTotal"), "7", "contacted")
    eq(page.inner_text("#sReplied"), "2", "replied")
    eq(page.inner_text("#sDue"), "1", "due a chase")
    eq(page.inner_text("#sStale"), "1", "going stale")
    eq(page.inner_text("#sWon"), "1", "won")


@check("pipeline: urgency flags land on the right rows")
def _(page):
    """Priya at 6 days is amber; Tom at 34 days is red; a reply is left alone."""
    open_product(page, "pipeline", "Pipeline.html")
    page.click("#demo")
    state = page.evaluate(
        """() => [...document.querySelectorAll('#rows tr')].map(tr => ({
             who: tr.querySelector('.f-who').value,
             cls: tr.className
           }))"""
    )
    by_who = {r["who"]: r["cls"] for r in state}
    eq(by_who.get("Priya"), "due", "Priya should be due")
    eq(by_who.get("Tom"), "stale", "Tom should be stale")
    eq(by_who.get("Sam"), "", "a replied contact must not be chased")
    eq(by_who.get("Samantha"), "", "a 1-day contact must not be chased")


@check("pipeline: status filter hides the rest")
def _(page):
    open_product(page, "pipeline", "Pipeline.html")
    page.click("#demo")
    page.click('.chip[data-f="Won"]')
    visible = page.evaluate(
        """() => [...document.querySelectorAll('#rows tr')]
                 .filter(tr => tr.style.display !== 'none').length"""
    )
    eq(visible, 1, "rows visible when filtering to Won")


# ---------------------------------------------------------------- VAT Guard
@check("vat guard: forward risk fires when run rate projects over the line")
def _(page):
    """62000 in 8 months = 7750/month -> 93000 rolling, over a 90000 threshold.

    Turnover to date is only 62000, which looks safe. The projection is not, and
    the tool must say so rather than reassure.
    """
    open_product(page, "vat-guard", "VatGuard.html")
    page.click("#demo")
    eq(page.inner_text("#headroom"), "£28,000", "headroom")
    eq(page.inner_text("#runRate"), "£7,750", "run rate")
    eq(page.inner_text("#wRolling"), "£93,000", "rolling projection")
    eq(page.inner_text("#crossing"), "4 months", "months to cross")
    contains(page.inner_text("#headline"), "Register before you cross", "headline")
    eq(page.get_attribute("#hero", "class"), "hero crit", "severity")


@check("vat guard: genuinely comfortable case stays green")
def _(page):
    """30000 in 8 months = 3750/month -> 45000 rolling, half the threshold."""
    open_product(page, "vat-guard", "VatGuard.html")
    page.fill("#turnover", "30000")
    page.dispatch_event("#turnover", "input")
    contains(page.inner_text("#headline"), "Comfortable", "headline")
    eq(page.get_attribute("#hero", "class"), "hero", "severity")
    # 45000 is the rolling projection, which lives in #wRolling.
    # (An earlier version of this test looked for it in the headline copy, where it
    # never appears - the comfortable branch talks about headroom, not the projection.)
    eq(page.inner_text("#wRolling"), "£45,000", "rolling projection")


@check("vat guard: past the threshold demands registration")
def _(page):
    open_product(page, "vat-guard", "VatGuard.html")
    page.fill("#turnover", "95000")
    page.dispatch_event("#turnover", "input")
    contains(page.inner_text("#headline"), "must be registered", "headline")
    eq(page.get_attribute("#hero", "class"), "hero crit", "severity")
    eq(page.inner_text("#headroom"), "-£5,000", "negative headroom")
    eq(page.get_attribute("#fill", "style"), "width: 100%;", "gauge full")


@check("vat guard: absorbing VAT costs a sixth, not a fifth")
def _(page):
    """20/120 = 16.67%. Confusing this with 20% is the common error."""
    open_product(page, "vat-guard", "VatGuard.html")
    page.click("#demo")
    eq(page.inner_text("#wCut"), "16.67%", "effective cut")
    eq(page.inner_text("#wVat"), "£1,550 per month", "monthly VAT at 20%")


# ---------------------------------------------------------------- Terms Sheet
@check("terms sheet: default clauses render with the user's figures")
def _(page):
    """Ten clauses on by default; deposit, terms, revision count and law injected."""
    open_product(page, "terms-sheet", "TermsSheet.html")
    page.click("#demo")
    doc = page.inner_text("#doc")
    for clause in ["SCOPE OF WORK", "REVISIONS", "PAYMENT", "INTELLECTUAL PROPERTY",
                   "LIMITATION OF LIABILITY", "CANCELLATION", "CONFIDENTIALITY",
                   "SHOWING THE WORK", "YOUR RESPONSIBILITIES", "WHAT I PROMISE", "GENERAL"]:
        contains(doc, clause, clause)
    contains(doc, "deposit of 40%", "deposit figure")
    contains(doc, "within 14 days", "payment terms")
    contains(doc, "includes 2 round", "revision count")
    contains(doc, "law of England and Wales", "governing law")


@check("terms sheet: optional clauses are off until asked for")
def _(page):
    """Data protection and non-exclusivity must not appear by default."""
    open_product(page, "terms-sheet", "TermsSheet.html")
    page.click("#demo")
    doc = page.inner_text("#doc")
    if "DATA PROTECTION" in doc:
        raise AssertionError("data protection clause should be off by default")
    if "NON-EXCLUSIVITY" in doc:
        raise AssertionError("non-exclusivity clause should be off by default")


@check("terms sheet: toggling a clause removes it and renumbers")
def _(page):
    """A document with a gap in the numbering looks careless in front of a client."""
    open_product(page, "terms-sheet", "TermsSheet.html")
    page.click("#demo")
    page.click('#toggles input[data-c="payment"]')
    doc = page.inner_text("#doc")
    if "PAYMENT" in doc:
        raise AssertionError("payment clause should have been removed")

    nums = page.evaluate(
        r"""() => document.getElementById('doc').textContent
                 .split('\n')
                 .filter(l => /^\d+\. [A-Z]/.test(l))
                 .map(l => parseInt(l, 10))"""
    )
    expected = list(range(1, len(nums) + 1))
    eq(nums, expected, "clause numbering must stay sequential")


@check("terms sheet: enabling an optional clause adds it")
def _(page):
    open_product(page, "terms-sheet", "TermsSheet.html")
    page.click("#demo")
    page.click('#toggles input[data-c="data"]')
    contains(page.inner_text("#doc"), "DATA PROTECTION", "data protection clause")


# ---------------------------------------------------------------- Mileage Log
@check("mileage log: splits the trip that crosses 10,000 miles")
def _(page):
    """9600 then 800 then 420 miles.

    9600 * 0.45 = 4320
    the 800-mile trip straddles the line: 400 @ 45p = 180, 400 @ 25p = 100 => 280
    420 @ 25p = 105
    total 4705, with 10000 claimed at 45p and 820 at 25p.
    """
    open_product(page, "mileage-log", "MileageLog.html")
    page.click("#demo")
    eq(page.inner_text("#sMiles"), "10,820", "business miles")
    eq(page.inner_text("#sTotal"), "£4,705.00", "total claimable")
    eq(page.inner_text("#sRate1"), "£4,500.00", "claim at 45p")
    eq(page.inner_text("#sRate2"), "£205.00", "claim at 25p")
    eq(page.inner_text("#wM1"), "10,000", "miles at 45p")
    eq(page.inner_text("#wM2"), "820", "miles at 25p")


@check("mileage log: the straddling row is 280, not 360")
def _(page):
    """Naive 45p on everything would claim 360 for that trip. It must be 280."""
    open_product(page, "mileage-log", "MileageLog.html")
    page.click("#demo")
    claims = page.evaluate(
        """() => [...document.querySelectorAll('#rows tr')]
                 .map(tr => tr.querySelector('.f-claim').textContent.trim())"""
    )
    eq(claims[1], "£280.00", "straddling trip claim")
    # and prove the naive figure is different, so the test would catch a regression
    if claims[1] == "£360.00":
        raise AssertionError("regression: all miles claimed at 45p")


@check("mileage log: stays on 45p while under the threshold")
def _(page):
    """A short year must be a straight 45p calculation with nothing at 25p."""
    open_product(page, "mileage-log", "MileageLog.html")
    page.locator("#rows tr").first.locator(".f-miles").fill("1000")
    page.dispatch_event("#rows tr:nth-child(1) .f-miles", "input")
    # clear any extra rows left by a previous demo run in the same browser profile
    eq(page.inner_text("#sTotal"), "£450.00", "1000 miles at 45p")
    eq(page.inner_text("#sRate2"), "£0.00", "nothing over threshold")
    eq(page.inner_text("#wM2"), "0", "zero miles at 25p")


@check("mileage log: reports miles left before the drop")
def _(page):
    open_product(page, "mileage-log", "MileageLog.html")
    page.locator("#rows tr").first.locator(".f-miles").fill("4000")
    page.dispatch_event("#rows tr:nth-child(1) .f-miles", "input")
    contains(page.inner_text("#nadir"), "6,000", "miles remaining at 45p")


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
