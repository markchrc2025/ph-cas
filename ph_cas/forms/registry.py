"""FORMS: every BIR form the Ledger knows, and how each one behaves.

code        the form as the BIR writes it ("1601-EQ"), the user-facing name
key         the compact code of maps, fixtures and eBIRForms files ("1601EQ")
version     the ENCS version of the blank and map ("2019-01")
period      "month", "quarter" or "year"
money       "pesos" (the paper says do not enter centavos; half up once at the line)
            or "centavos" (exact decimals, never rounded)
output      "export" (an eBIRForms file is produced and the blank printed from it)
            or "print" (no eBIRForms file; the blank is printed from the draft)
            or "certificate" (issued, not filed)
namespace   the eBIRForms key namespace of an exported form
fiscal      whether the client's fiscal year shapes the period
due         the compliance calendar's rule id (ph_cas.tax.calendar)
title       the form's title as printed on the blank
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FormSpec:
    code: str
    key: str
    version: str
    period: str
    money: str
    output: str
    title: str
    namespace: str | None = None
    fiscal: bool = False
    due: str | None = None
    category: str = "Business Tax"


FORMS: dict[str, FormSpec] = {
    f.code: f
    for f in (
        FormSpec("2551Q", "2551Q", "2018-01", "quarter", "centavos", "export", "Quarterly Percentage Tax Return", "frm2551Qv2018", False, "DUE-2551Q"),
        FormSpec("2550Q", "2550Q", "2024-04", "quarter", "centavos", "export", "Quarterly Value-Added Tax Return", "frm2550qv2024", True, "DUE-2550Q"),
        FormSpec("0619-E", "0619E", "2018-01", "month", "centavos", "print", "Monthly Remittance Form of Creditable Income Taxes Withheld (Expanded)", None, False, "DUE-0619E", "Withholding"),
        FormSpec("1601-EQ", "1601EQ", "2019-01", "quarter", "centavos", "print", "Quarterly Remittance Return of Creditable Income Taxes Withheld (Expanded)", None, False, "DUE-1601EQ", "Withholding"),
        FormSpec("1601-C", "1601C", "2018-01", "month", "centavos", "print", "Monthly Remittance Return of Income Taxes Withheld on Compensation", None, False, None, "Withholding"),
        FormSpec("1600-VT", "1600VT", "2018-01", "month", "centavos", "print", "Monthly Remittance Return of Value-Added Tax Withheld", None, False, "DUE-1600VT", "Withholding"),
        FormSpec("1701Q", "1701Q", "2018-01", "quarter", "pesos", "export", "Quarterly Income Tax Return for Individuals, Estates and Trusts", "frm1701q", False, "DUE-1701Q", "Income Tax"),
        FormSpec("1701", "1701", "2018-01", "year", "pesos", "export", "Annual Income Tax Return for Individuals (including Mixed Income Earner), Estates and Trusts", "frm1701", False, "DUE-1701", "Income Tax"),
        FormSpec("1701A", "1701A", "2018-01", "year", "pesos", "export", "Annual Income Tax Return for Individuals Earning Income Purely from Business/Profession", "frm1701A", False, "DUE-1701", "Income Tax"),
        FormSpec("1702Q", "1702Q", "2018-01", "quarter", "pesos", "export", "Quarterly Income Tax Return for Corporations, Partnerships and Other Non-Individual Taxpayers", "frm1702q", True, "DUE-1702Q", "Income Tax"),
        FormSpec("1702-RT", "1702RT", "2018-01", "year", "pesos", "export", "Annual Income Tax Return for Corporations, Partnerships and Other Non-Individual Taxpayers Subject Only to Regular Income Tax Rate", "frm1702RT", True, "DUE-1702RT", "Income Tax"),
        FormSpec("1604-E", "1604E", "2018-01", "year", "centavos", "print", "Annual Information Return of Creditable Income Taxes Withheld (Expanded)", None, False, "DUE-1604E", "Withholding"),
        FormSpec("2307", "2307", "2018-01", "quarter", "centavos", "certificate", "Certificate of Creditable Tax Withheld at Source", None, False, None, "Withholding"),
    )
}

# the forms whose per-form engine has landed; the rest are registered but not yet buildable
BUILT: set[str] = {"2551Q", "2550Q", "0619-E", "1601-EQ", "2307", "1600-VT", "1604-E", "1701Q", "1702Q", "1701", "1701A", "1702-RT"}


def spec(code: str) -> FormSpec:
    try:
        return FORMS[code]
    except KeyError:
        raise ValueError(f"unknown BIR form {code}") from None


def by_key(key: str) -> FormSpec:
    for f in FORMS.values():
        if f.key == key:
            return f
    raise ValueError(f"unknown BIR form key {key}")
