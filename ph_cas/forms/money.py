"""Exact money for the forms. Never float.

Whole-peso forms (the income-tax returns, the 2550Q, the 2551Q: "do not enter
centavos") round half up once, at the line, with whole_peso(). Centavo forms
(0619-E, 1601-EQ, 1601-C, 2307) keep exact decimals and report to the centavo,
half up, never changing a two-place input.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

ZERO = Decimal(0)
CENT = Decimal("0.01")
ONE = Decimal(1)


def dec(v) -> Decimal:
    """A typed or stored value read exactly: commas stripped; blank or not a number is 0."""
    if v is None or v == "":
        return ZERO
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        return ZERO
    if isinstance(v, int):
        return Decimal(v)
    if isinstance(v, float):
        # a float from the database or a form field: take it at the centavo it shows
        return Decimal(repr(v)).quantize(CENT, ROUND_HALF_UP)
    text = str(v).replace(",", "").strip()
    if text == "":
        return ZERO
    try:
        d = Decimal(text)
    except InvalidOperation:
        return ZERO
    return d if d.is_finite() else ZERO


def total(*xs) -> Decimal:
    """The exact sum."""
    s = ZERO
    for x in xs:
        s += dec(x)
    return s


def centavos(d) -> Decimal:
    """To the centavo, half up, never -0."""
    q = dec(d).quantize(CENT, ROUND_HALF_UP)
    return ZERO.quantize(CENT) if q == 0 else q


def whole_peso(d) -> Decimal:
    """The BIR rule for whole-peso forms: 49 centavos or less drop, 50 or more round up,
    symmetric around zero."""
    v = dec(d)
    sign = -1 if v < 0 else 1
    return sign * abs(v).quantize(ONE, ROUND_HALF_UP)


def text(d, places: int = 2) -> str:
    """"1234.50": what a draft stores and the export writer reads."""
    q = Decimal(10) ** -places
    return str(dec(d).quantize(q, ROUND_HALF_UP))


def amt(d) -> str:
    """Money the eBIRForms way: "1,234,567.00"."""
    return f"{dec(d).quantize(CENT, ROUND_HALF_UP):,.2f}"


def nonneg(d) -> Decimal:
    """A books total that falls below zero is shown as zero (the caller warns)."""
    v = dec(d)
    return v if v > 0 else ZERO
